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

Se unifica el DDL en la migración `0002_add_inventario.py` en `events-service`, incorporando la columna `expira_en` desde el inicio para coherencia con el change técnico:

```sql
ALTER TABLE modalidades
    ADD COLUMN precio NUMERIC(10, 2) NULL,
    ADD COLUMN cupo INTEGER NULL;

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
    CONSTRAINT ck_reservas_estado CHECK (estado IN ('activa', 'confirmada', 'liberada'))
);
CREATE INDEX ix_reservas_modalidad_estado ON reservas (modalidad_id, estado);
```

**Justificación:**
- Distinción clara de tarifas: en `general`, la tarifa plana vive en `modalidades.precio`. En `numerado`, `modalidades.precio` es `NULL` y cada sector gobierna su propia tarifa en `sectores.precio`.
- `ON DELETE RESTRICT` en `reservas` impide borrados accidentales de transacciones comerciales.

### 2. Integridad en `PUT /eventos/{id}`

- En el handler de `PUT /eventos/{id}`, previo a eliminar las modalidades omitidas del nuevo payload, se consulta:
  ```python
  reservas_existentes = await session.scalar(
      select(func.count(Reserva.id)).where(
          Reserva.modalidad_id.in_(ids_a_eliminar),
          Reserva.estado.in_(["activa", "confirmada"])
      )
  )
  if reservas_existentes > 0:
      raise HTTPException(status_code=409, detail="modalidad con reservas o ventas asociadas")
  ```

### 3. Contratos REST y respuestas uniformes

Se incorporan 4 endpoints bajo el router de eventos en `events-service`:
1. `GET /eventos/{id}/modalidades/{mid}/disponibilidad`:
   - En `general`: `cupo - COUNT(reservas activas no vencidas + confirmadas)`.
   - En `numerado`: `COUNT(asientos con estado = 'libre' o con reserva activa expirada)`.
   - Retorna `200 {"disponibles": <int>}` o `404`.
2. `POST /eventos/{id}/modalidades/{mid}/reservas`:
   - En `general`: valida disponibilidad > 0, crea reserva activa con `expira_en`, retorna `201 {"reserva_id": "<uuid>"}`.
   - En `numerado`: requiere body `{"asiento_id": "<uuid>"}`, valida asiento libre, actualiza asiento a `reservado`, crea reserva activa con `asiento_id` y `expira_en`, retorna `201 {"reserva_id": "<uuid>"}`.
   - Si no hay disponibilidad o el asiento no está libre: responde `409 {"detail": "sin disponibilidad"}` o `409 {"detail": "asiento no disponible"}`.
3. `DELETE /eventos/{id}/modalidades/{mid}/reservas/{reserva_id}`:
   - Si la reserva ya está `liberada` o `confirmada`: rechaza con `409 Conflict`.
   - Si está activa: cambia estado a `liberada`, restaura `asiento.estado = 'libre'`, y responde `200 {"status": "liberada"}`.
4. `POST /eventos/{id}/modalidades/{mid}/reservas/{reserva_id}/confirmar`:
   - Si ya está `confirmada`: responde `200 {"status": "confirmada"}` (idempotencia).
   - Si está `liberada` o vencida por TTL (`expira_en <= now()`): rechaza con `409 Conflict`.
   - Si está activa: cambia estado a `confirmada`, actualiza asiento a `vendido`, y responde `200 {"status": "confirmada"}`.

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
