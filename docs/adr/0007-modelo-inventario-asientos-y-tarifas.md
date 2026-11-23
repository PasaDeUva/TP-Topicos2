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
   - En la migración `0002_add_inventario.py`, las columnas se añaden como anulables y se ejecuta un backfill de consistencia acotado a modalidades de tipo general (`UPDATE modalidades SET precio = 0.00 WHERE tipo = 'general' AND precio IS NULL; UPDATE modalidades SET cupo = 0 WHERE tipo = 'general' AND cupo IS NULL;`) para registros preexistentes de migración `0001`, preservando `precio IS NULL` para las modalidades numeradas según la restricción posterior. Los esquemas de entrada aceptan `cupo >= 0` para admitir la preservación y edición de modalidades generales migradas sin cupo inicial.
2. **Entidades para modalidad `numerado`:**
   - Crear tabla `sectores` vinculada a `modalidades` (`id UUID PK`, `modalidad_id FK`, `nombre VARCHAR(100)`, `precio NUMERIC(10, 2) NOT NULL`).
   - Crear tabla `asientos` vinculada a `sectores` (`id UUID PK`, `sector_id FK`, `fila VARCHAR(10)`, `numero INTEGER`, `estado VARCHAR(20)`, con restricción `UNIQUE (sector_id, fila, numero)` y `CHECK (estado IN ('libre', 'reservado', 'vendido'))`).
3. **Entidad `reservas` en `events-service`:**
   - Crear tabla `reservas` (`id UUID PK`, `modalidad_id FK`, `asiento_id FK NULL`, `estado VARCHAR(20) NOT NULL DEFAULT 'activa'`, `expira_en TIMESTAMPTZ NOT NULL`, `creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()`, `idempotency_key VARCHAR(255) NULL`, con `CHECK (estado IN ('activa', 'confirmada', 'liberada'))`, índice sobre `(modalidad_id, estado)` y restricción de unicidad global `CONSTRAINT uq_reservas_idempotency_key UNIQUE (idempotency_key)`).
   - Para modalidad `general`: `asiento_id` es `NULL`; la disponibilidad se calcula como `cupo - COUNT(reservas vigentes)` donde vigente significa `estado = 'confirmada' OR (estado = 'activa' AND expira_en > NOW())`.
   - Para modalidad `numerado`: `asiento_id` referencia el asiento reservado y sincroniza su `estado`.
4. **Preservación de identidades y protección contra borrado en `PUT /eventos/{id}`:**
   - El payload de modalidades admite `id: UUID` opcional. Si se envía un `id` existente del evento, se actualizan sus atributos preservando su identificador y relaciones hijas.
   - La eliminación de modalidades preexistentes omitidas en `PUT /eventos/{id}` está condicionada: si una modalidad posee registros en `reservas` en cualquier estado (`activa`, `confirmada` o `liberada`), el sistema rechaza la operación con `409 Conflict`. En la base de datos se utiliza restricción referencial `ON DELETE RESTRICT` que impida borrados accidentales y garantice la auditoría histórica.
5. **Ciclo de vida funcional de reservas:**
   - Endpoints REST para consulta de disponibilidad (`GET .../disponibilidad`), creación de reserva (`POST .../reservas` con soporte de `Idempotency-Key`), liberación (`DELETE .../reservas/{id}`) y confirmación (`POST .../reservas/{id}/confirmar`).

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
