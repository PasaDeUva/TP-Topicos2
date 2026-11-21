# ADR-0007: Modelo de datos para inventario de entradas, cupos, asientos y reservas

- Estado: Aceptado
- Fecha: 2026-11-19

## Contexto

`events-service` actúa como fuente de verdad del catálogo de eventos ([ADR-0003](0003-servicio-eventos-e-inventario.md)). Sin embargo, en la versión inicial se difirió la modelización de precios, cupos y mapas de asientos para no introducir supuestos prematuros.
Para soportar el flujo de compras orquestado ([ADR-0006](0006-flujo-de-compra-completo.md)) y los requerimientos del TP sobre modalidades `general` y `numerado` (definidos en `docs/glosario.md`), `events-service` requiere incorporar inventario y ciclo de vida de reservas con integridad referencial estricta.

## Decisión

1. **Ampliación de `modalidades` y distinción de tarifas:**
   - Para modalidad `general`: columna `precio NUMERIC(10, 2) NOT NULL` (tarifa única de la entrada general) y columna `cupo INTEGER NOT NULL` (capacidad total del evento para esa zona).
   - Para modalidad `numerado`: `precio` es `NULL` en la modalidad y se define a nivel de cada sector en `sectores.precio NUMERIC(10, 2) NOT NULL`, reflejando tarifas diferenciadas por ubicación física.
2. **Entidades para modalidad `numerado`:**
   - Crear tabla `sectores` vinculada a `modalidades` (`id UUID PK`, `modalidad_id FK`, `nombre VARCHAR(100)`, `precio NUMERIC(10, 2) NOT NULL`).
   - Crear tabla `asientos` vinculada a `sectores` (`id UUID PK`, `sector_id FK`, `fila VARCHAR(10)`, `numero INTEGER`, `estado VARCHAR(20)`, con restricción `UNIQUE (sector_id, fila, numero)` y `CHECK (estado IN ('libre', 'reservado', 'vendido'))`).
3. **Entidad `reservas` en `events-service`:**
   - Crear tabla `reservas` (`id UUID PK`, `modalidad_id FK`, `asiento_id FK NULL`, `estado VARCHAR(20) NOT NULL DEFAULT 'activa'`, `expira_en TIMESTAMPTZ NOT NULL`, `creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()`, con `CHECK (estado IN ('activa', 'confirmada', 'liberada'))`).
   - Para modalidad `general`: `asiento_id` es `NULL`; la disponibilidad se calcula como `cupo - COUNT(reservas vigentes)` donde vigente significa `estado = 'confirmada' OR (estado = 'activa' AND expira_en > NOW())`.
   - Para modalidad `numerado`: `asiento_id` referencia el asiento reservado y sincroniza su `estado`.
4. **Protección contra borrado de ventas e integridad:**
   - La eliminación o reemplazo de modalidades vía `PUT /eventos/{id}` está protegida: si una modalidad tiene reservas en estado `confirmada` o `activa`, el sistema rechaza la operación con `409 Conflict`. En la base de datos se utiliza restricción referencial que impida borrados silenciosos en cascada de transacciones comerciales.
5. **Ciclo de vida funcional de reservas:**
   - Endpoints REST para consulta de disponibilidad (`GET .../disponibilidad`), creación de reserva (`POST .../reservas`), liberación (`DELETE .../reservas/{id}`) y confirmación (`POST .../reservas/{id}/confirmar`).

## Consecuencias

### Positivas

- `events-service` consolida la responsabilidad integral del catálogo, precios e inventario físico/lógico sin ambigüedad en las tarifas.
- Se respeta la distinción conceptual del glosario: general gobernado por cupo y tarifa plana; numerado gobernado por sectores y asientos individuales.
- Se garantiza la integridad histórica: no es posible borrar ventas confirmadas mediante edición del evento.
- Provee los contratos HTTP requeridos por `compras-service` para orquestar la reserva y confirmación.

### Negativas

- Mayor complejidad en las consultas de agregación y detalle de evento (`selectinload` para modalidades, sectores y asientos).
- Se requiere validación de dependencias activas antes de permitir reemplazos totales en `PUT /eventos/{id}`.

## Alternativas consideradas

- **Precio obligatorio en modalidad para tipo numerado:** Descartado porque genera duplicidad y contradicción si los sectores tienen precios distintos.
- **Borrado en cascada de ventas:** Descartado por violar la integridad contable y transaccional del sistema de compras.
- **Gestionar el inventario dentro de `compras-service`:** Descartado para evitar duplicar el catálogo y violar el principio de fuente única de verdad ([ADR-0003](0003-servicio-eventos-e-inventario.md)).
