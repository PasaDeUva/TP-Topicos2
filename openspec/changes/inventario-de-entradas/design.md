# Design

## Context

`events-service` es la fuente de verdad del catálogo de eventos ([ADR-0003](../../../docs/adr/0003-servicio-eventos-e-inventario.md)). Hasta el momento, el catálogo define eventos y modalidades únicamente con nombre y tipo (`general` o `numerado`), sin tarifas, cupos ni mapa de asientos.
Por su parte, `compras-service` fue diseñado para orquestar reservas contra `events-service` ([ADR-0005](../../../docs/adr/0005-compras-consulta-eventos-e-idempotencia.md) y [ADR-0006](../../../docs/adr/0006-flujo-de-compra-completo.md)), requiriendo endpoints de inventario y reservas.
Ver [proposal.md](./proposal.md) y [specs/inventario-de-entradas/spec.md](./specs/inventario-de-entradas/spec.md).

## Goals / Non-Goals

**Goals:**
- Extender el modelo relacional de `events-service` para soportar precios y cupos en modalidades generales, y sectores con tarifas y asientos para modalidades numeradas ([ADR-0007](../../../docs/adr/0007-modelo-inventario-asientos-y-tarifas.md)).
- Gestionar el ciclo de vida funcional de reservas: consulta de disponibilidad, creación de reserva, liberación (compensación) y confirmación de venta, garantizando respuestas uniformes e idempotencia en confirmación.
- Proteger la integridad de datos impidiendo que la edición total de eventos (`PUT /eventos/{id}`) elimine modalidades con entradas vendidas o reservadas.
- Mantener compatibilidad hacia atrás en las operaciones existentes de catálogo (`GET /eventos`, `GET /eventos/{id}`, `POST /eventos`, `PUT /eventos/{id}`).

**Non-Goals:**
- Colas masivas de espera y buffers encolados (alcance de Etapa III - Colas de venta).
- Pagos, cobros y facturación: responsabilidad de `payment-service`.
- Reserva múltiple en una única operación (batch / cantidad > 1): alcance futuro.

## Decisions

### 1. Modelo de datos e inventario relacional (Migración unificada)

Se unifica el DDL en la migración `0002_add_inventario.py` en `events-service`, incorporando la columna `expira_en`, el soporte para `idempotency_key` y el backfill de datos preexistentes:

```sql
-- 1. Ampliación de modalidades con backfill de datos existentes
ALTER TABLE modalidades
    ADD COLUMN precio NUMERIC(10, 2) NULL,
    ADD COLUMN cupo INTEGER NULL;

-- Backfill para registros preexistentes de migración 0001
UPDATE modalidades SET precio = 0.00 WHERE precio IS NULL;
UPDATE modalidades SET cupo = 0 WHERE tipo = 'general' AND cupo IS NULL;

-- Restricción de consistencia según el tipo de modalidad
ALTER TABLE modalidades ADD CONSTRAINT ck_modalidades_precio_cupo
    CHECK ((tipo = 'general' AND precio IS NOT NULL AND cupo IS NOT NULL AND precio >= 0 AND cupo >= 0)
        OR (tipo = 'numerado' AND precio IS NULL AND cupo IS NULL));

CREATE TABLE sectores (
    id UUID PRIMARY KEY,
    modalidad_id UUID NOT NULL REFERENCES modalidades(id) ON DELETE CASCADE,
    nombre VARCHAR(100) NOT NULL,
    precio NUMERIC(10, 2) NOT NULL
);

CREATE TABLE asientos (
    id UUID PRIMARY KEY,
    sector_id UUID NOT NULL REFERENCES sectores(id) ON DELETE CASCADE,
    fila VARCHAR(10) NOT NULL,
    numero INTEGER NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'libre',
    CONSTRAINT ck_asientos_estado CHECK (estado IN ('libre', 'reservado', 'vendido')),
    CONSTRAINT uq_asientos_sector_fila_numero UNIQUE (sector_id, fila, numero)
);

CREATE TABLE reservas (
    id UUID PRIMARY KEY,
    modalidad_id UUID NOT NULL REFERENCES modalidades(id) ON DELETE RESTRICT,
    asiento_id UUID NULL REFERENCES asientos(id) ON DELETE RESTRICT,
    estado VARCHAR(20) NOT NULL DEFAULT 'activa',
    expira_en TIMESTAMPTZ NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    idempotency_key VARCHAR(255) NULL,
    CONSTRAINT ck_reservas_estado CHECK (estado IN ('activa', 'confirmada', 'liberada'))
);
CREATE INDEX ix_reservas_modalidad_estado ON reservas (modalidad_id, estado);
CREATE INDEX ix_reservas_idempotency ON reservas (modalidad_id, idempotency_key);
```

**Justificación:**
- Distinción clara de tarifas: en `general`, la tarifa plana vive en `modalidades.precio`. En `numerado`, `modalidades.precio` es `NULL` y cada sector gobierna su propia tarifa en `sectores.precio`.
- El backfill garantiza que eventos y modalidades preexistentes en la base de datos sigan siendo válidos tras correr la migración sin violar las restricciones `NOT NULL`.
- `ON DELETE RESTRICT` en `reservas` impide borrados accidentales de transacciones comerciales y preserva la auditoría histórica.
- `idempotency_key` permite a clientes orquestadores como `compras-service` reintentar de forma segura sin riesgo de reservas duplicadas o fugas de cupo.

### 2. Preservación de identidades e integridad en `PUT /eventos/{id}`

- En el esquema `ModalidadIn`, se incorpora `id: UUID | None = None`.
- Al recibir `PUT /eventos/{id}`:
  1. Si una modalidad en el payload incluye `id`:
     - Se valida que pertenezca al evento a editar.
     - Se actualizan sus atributos (`nombre`, `precio`, `cupo`) en la base de datos preservando su identificador original y sus relaciones hijas (`sectores`, `asientos`, `reservas`).
  2. Si una modalidad en el payload no incluye `id`:
     - Se crea como una nueva modalidad asociada al evento.
  3. Para las modalidades preexistentes del evento que hayan sido omitidas en el payload:
     - Se verifica si poseen registros históricos de reservas:
       ```python
       reservas_historicas = await session.scalar(
           select(func.count(Reserva.id)).where(
               Reserva.modalidad_id.in_(ids_a_eliminar)
           )
       )
       if reservas_historicas > 0:
           raise HTTPException(
               status_code=409,
               detail="No se puede eliminar una modalidad con historial de reservas o ventas"
           )
       ```
     - Si no tienen reservas históricas de ningún estado, se eliminan limpiamente sin violar la restricción referencial de clave foránea.

### 3. Contratos REST y respuestas uniformes

Se incorporan 4 endpoints bajo el router de eventos en `events-service`:
1. `GET /eventos/{id}/modalidades/{mid}/disponibilidad`:
   - En `general`: `cupo - COUNT(reservas activas no vencidas + confirmadas)`.
   - En `numerado`: `COUNT(asientos con estado = 'libre' o con reserva activa expirada)`.
   - Retorna `200 {"disponibles": <int>}` o `404`.
2. `POST /eventos/{id}/modalidades/{mid}/reservas`:
   - Acepta cabecera opcional `Idempotency-Key` (hasta 255 caracteres).
   - Si se recibe `Idempotency-Key`, consulta si ya existe una reserva para `(modalidad_id, idempotency_key)`:
     - Si existe y los datos coinciden: retorna `200 OK` (o `201`) con `{"reserva_id": "<uuid>"}` original sin reservar nuevamente.
     - Si existe pero con datos distintos (otro asiento o modalidad): responde `409 Conflict` (`idempotency_conflict`).
   - En `general`: valida disponibilidad > 0, crea reserva activa con `expira_en` y la clave de idempotencia, retorna `201 {"reserva_id": "<uuid>"}`.
   - En `numerado`: requiere body `{"asiento_id": "<uuid>"}`, valida asiento libre, actualiza asiento a `reservado`, crea reserva activa con `asiento_id`, `expira_en` y la clave, retorna `201 {"reserva_id": "<uuid>"}`.
   - Si no hay disponibilidad o el asiento no está libre: responde `409 {"detail": "sin disponibilidad"}` o `409 {"detail": "asiento no disponible"}`.
3. `DELETE /eventos/{id}/modalidades/{mid}/reservas/{reserva_id}`:
   - Aplica orden canónico de locks (`reservas` luego `asientos`).
   - Si la reserva ya está `liberada` o `confirmada`: rechaza con `409 Conflict`.
   - Si está activa: verifica que sea dueña del asiento, cambia estado a `liberada`, restaura `asiento.estado = 'libre'`, y responde `200 {"status": "liberada"}`.
4. `POST /eventos/{id}/modalidades/{mid}/reservas/{reserva_id}/confirmar`:
   - Aplica orden canónico de locks.
   - Si ya está `confirmada`: responde `200 {"status": "confirmada"}` (idempotencia).
   - Si está `liberada` o vencida por TTL (`expira_en <= now()`): rechaza con `409 Conflict`.
   - Si está activa: cambia estado a `confirmada`, actualiza asiento a `vendido`, y responde `200 {"status": "confirmada"}`.

### 4. Integración conjunta de changes

Este change y el change complementario `concurrencia-de-reservas` comparten el esquema relacional provisto por la migración `0002_add_inventario.py`, los modelos SQLAlchemy en `app/models.py` y las operaciones del ciclo de vida de reservas. Se implementan y verifican de forma conjunta en `events-service`.

### 4. Actualización de esquemas de Catálogo

- `ModalidadIn`:
  - `precio: Decimal | None = None`
  - `cupo: int | None = None`
  - `sectores: list[SectorIn] = []`
  - Validación con `@model_validator(mode="after")`:
    - Si `tipo == "general"`: `precio` y `cupo` obligatorios (`precio >= 0`, `cupo >= 1`).
    - Si `tipo == "numerado"`: `sectores` debe tener al menos un sector, cada sector con `precio >= 0` y lista de asientos.
- `ModalidadOut`: expone `precio`, `cupo` y `sectores` con sus `asientos`.

## Risks / Trade-offs

- **[Bloqueo de eliminación en PUT]** → Organizadores no pueden eliminar modalidades con ventas activas.
  *Mitigación:* Es el comportamiento correcto de negocio. Para suspender ventas futuras se utiliza la baja lógica (`activo = false`) sin destruir la trazabilidad.

## Migration Plan

1. Ejecutar `docker compose run --rm events-service alembic upgrade head` para aplicar la migración `0002_add_inventario.py`.
2. Las pruebas automáticas de regresión de `events-service` verifican que los tests existentes se adapten a los nuevos campos obligatorios de modalidad.
3. Reversión: `alembic downgrade -1` elimina las tablas `reservas`, `asientos`, `sectores` y remueve las columnas agregadas de `modalidades`.
