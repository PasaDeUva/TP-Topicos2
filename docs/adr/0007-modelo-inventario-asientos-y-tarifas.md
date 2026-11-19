# ADR-0007: Modelo de datos para inventario de entradas, cupos, asientos y reservas

- Estado: Propuesto
- Fecha: 2026-11-19

## Contexto

`events-service` actúa como fuente de verdad del catálogo de eventos ([ADR-0003](0003-servicio-eventos-e-inventario.md)). Sin embargo, en la versión inicial se difirió la modelización de precios, cupos y mapas de asientos para no introducir supuestos prematuros.
Para soportar el flujo de compras orquestado ([ADR-0006](0006-flujo-de-compra-completo.md)) y los requerimientos del TP sobre modalidades `general` y `numerado` (definidos en `docs/glosario.md`), `events-service` requiere incorporar inventario y ciclo de vida de reservas.

## Decisión

1. **Ampliación de `modalidades`:**
   - Incorporar columna `precio NUMERIC(10, 2) NOT NULL` (precio base de la modalidad).
   - Incorporar columna `cupo INTEGER NULL` (capacidad total; obligatorio para `tipo = 'general'`).
2. **Entidades para modalidad `numerado`:**
   - Crear tabla `sectores` vinculada a `modalidades` (`id UUID PK`, `modalidad_id FK`, `nombre VARCHAR(100)`, `precio NUMERIC(10, 2)`).
   - Crear tabla `asientos` vinculada a `sectores` (`id UUID PK`, `sector_id FK`, `fila VARCHAR(10)`, `numero INTEGER`, `estado VARCHAR(20)`, con restricción `UNIQUE (sector_id, fila, numero)` y `CHECK (estado IN ('libre', 'reservado', 'vendido'))`).
3. **Entidad `reservas` en `events-service`:**
   - Crear tabla `reservas` (`id UUID PK`, `modalidad_id FK`, `asiento_id FK NULL`, `estado VARCHAR(20) NOT NULL DEFAULT 'activa'`, `creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()`, con `CHECK (estado IN ('activa', 'confirmada', 'liberada'))`).
   - Para modalidad `general`: `asiento_id` es `NULL`; la disponibilidad se calcula como `cupo - COUNT(reservas activas o confirmadas)`.
   - Para modalidad `numerado`: `asiento_id` referencia el asiento reservado y sincroniza su `estado`.
4. **Ciclo de vida funcional de reservas:**
   - Endpoints REST para consulta de disponibilidad (`GET .../disponibilidad`), creación de reserva (`POST .../reservas`), liberación (`DELETE .../reservas/{id}`) y confirmación (`POST .../reservas/{id}/confirmar`).
   - El control de concurrencia estricto y la expiración por TTL se desacoplan y abordan en el change técnico `concurrencia-de-reservas`.

## Consecuencias

### Positivas

- `events-service` consolida la responsabilidad integral del catálogo, precios e inventario físico/lógico.
- Se respeta la distinción conceptual del glosario: modalidad general gobernada por cupo numérico y modalidad numerada gobernada por asientos individuales.
- Provee los contratos HTTP requeridos por `compras-service` para orquestar la reserva y confirmación.

### Negativas

- Mayor complejidad en las consultas de agregación y detalle de evento (`selectinload` para modalidades, sectores y asientos).
- Las reservas temporales requieren posterior resolución de concurrencia y limpieza de expirados (se resuelve en el change complementario `concurrencia-de-reservas`).

## Alternativas consideradas

- **Gestionar el inventario dentro de `compras-service`:** Descartado para evitar duplicar el catálogo y violar el principio de fuente única de verdad ([ADR-0003](0003-servicio-eventos-e-inventario.md)).
- **Unificar cupo y asientos en una única estructura genérica:** Descartado porque la naturaleza de un asiento individual (fila, número, sector, precio diferencial) diverge funcionalmente de un contador escalar de cupo general.
