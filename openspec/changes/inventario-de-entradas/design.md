# Design

## Context

`events-service` es la fuente de verdad del catálogo de eventos ([ADR-0003](../../../docs/adr/0003-servicio-eventos-e-inventario.md)). Hasta el momento, el catálogo define eventos y modalidades únicamente con nombre y tipo (`general` o `numerado`), sin tarifas, cupos ni mapa de asientos.
Por su parte, `compras-service` fue diseñado para orquestar reservas contra `events-service` ([ADR-0005](../../../docs/adr/0005-compras-consulta-eventos-e-idempotencia.md) y [ADR-0006](../../../docs/adr/0006-flujo-de-compra-completo.md)), requiriendo endpoints de inventario y reservas.
Ver [proposal.md](./proposal.md) y [specs/inventario-de-entradas/spec.md](./specs/inventario-de-entradas/spec.md).

## Goals / Non-Goals

**Goals:**
- Extender el modelo relacional de `events-service` para soportar precios y cupos en modalidades generales, y sectores con asientos para modalidades numeradas ([ADR-0007](../../../docs/adr/0007-modelo-inventario-asientos-y-tarifas.md)).
- Gestionar el ciclo de vida funcional de reservas: consulta de disponibilidad, creación de reserva, liberación (compensación) y confirmación de venta.
- Mantener compatibilidad hacia atrás en las operaciones existentes de catálogo (`GET /eventos`, `GET /eventos/{id}`, `POST /eventos`, `PUT /eventos/{id}`).

**Non-Goals:**
- Mecanismos de control de concurrencia para evitar sobreventa o condiciones de carrera (bloqueos atómicos, optimistas o pesimistas): se implementan en el change técnico `concurrencia-de-reservas`.
- Expiración automática de reservas por TTL: se difiere a `concurrencia-de-reservas` / Etapa III.
- Pagos, cobros y facturación: responsabilidad de `payment-service`.
- Reserva múltiple en una única operación (batch / cantidad > 1): alcance futuro.

## Decisions

### 1. Modelo de datos e inventario relacional

Se añade la migración `0002_add_inventario.py` en `events-service`:

```sql
ALTER TABLE modalidades
    ADD COLUMN precio NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
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
    modalidad_id UUID NOT NULL REFERENCES modalidades(id) ON DELETE CASCADE,
    asiento_id UUID NULL REFERENCES asientos(id) ON DELETE SET NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'activa',
    creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_reservas_estado CHECK (estado IN ('activa', 'confirmada', 'liberada'))
);
CREATE INDEX ix_reservas_modalidad_estado ON reservas (modalidad_id, estado);
```

**Justificación:**
- Separa la gestión escalar de cupo (modalidad general) del mapa posicional (asientos numerados), tal como lo estipula el glosario del proyecto.
- `reservas` registra los identificadores `reserva_id` retornados a los consumidores (p. ej. `compras-service`), desacoplando el estado interno de la venta.

**Alternativas consideradas:**
- *Manejar asientos como un contador simple sin filas ni números:* Descartado porque la modalidad numerada exige identificar y reservar ubicaciones exactas.
- *Guardar el inventario en `compras-service`:* Descartado por violar la frontera de bounded context; el catálogo y su capacidad residen en `events-service`.

### 2. Contratos REST y ciclo de vida de reservas

Se incorporan 4 endpoints bajo el router de eventos en `events-service`:
1. `GET /eventos/{id}/modalidades/{mid}/disponibilidad`:
   - En `general`: `cupo - COUNT(reservas activas o confirmadas)`.
   - En `numerado`: `COUNT(asientos con estado = 'libre')`.
   - Retorna `200 {"disponibles": <int>}` o `404`.
2. `POST /eventos/{id}/modalidades/{mid}/reservas`:
   - En `general`: valida disponibilidad > 0, crea reserva activa, retorna `201 {"reserva_id": "<uuid>"}`.
   - En `numerado`: requiere body `{"asiento_id": "<uuid>"}`, valida asiento libre, actualiza asiento a `reservado`, crea reserva activa con `asiento_id`, retorna `201 {"reserva_id": "<uuid>"}`.
   - Si no hay disponibilidad o el asiento no está libre: responde `409 {"detail": "sin disponibilidad"}` o `409 {"detail": "asiento no disponible"}`.
3. `DELETE /eventos/{id}/modalidades/{mid}/reservas/{reserva_id}`:
   - Cambia estado de reserva a `liberada`.
   - Si es numerada, restaura `asiento.estado = 'libre'`.
   - Responde `200 {"status": "liberada"}` o `404` si no existe, `409` si ya estaba confirmada.
4. `POST /eventos/{id}/modalidades/{mid}/reservas/{reserva_id}/confirmar`:
   - Cambia estado de reserva a `confirmada`.
   - Si es numerada, actualiza `asiento.estado = 'vendido'`.
   - Responde `200 {"status": "confirmada"}` o `404`/`409`.

**Justificación:** Satisface íntegramente el flujo de compensación y confirmación requerido por ADR-0006.

### 3. Actualización de esquemas de Catálogo

- `ModalidadIn`: añade `precio: Decimal = Field(ge=0)` y `cupo: int | None = Field(default=None, ge=1)`. Añade campo opcional `sectores: list[SectorIn] = []`.
- Se valida con `@model_validator(mode="after")` que si `tipo == "general"`, `cupo` sea obligatorio; si `tipo == "numerado"`, `sectores` contenga al menos un sector con asientos válidos.
- `ModalidadOut`: expone `precio`, `cupo`, y la lista de `sectores` con sus `asientos`.

## Risks / Trade-offs

- **[Sin exclusión mutua de concurrencia en esta spec]** → Dos reservas simultáneas sobre el último cupo o mismo asiento podrían pasar las validaciones antes de persistir.
  *Mitigación:* Se implementa a continuación en el change complementario `concurrencia-de-reservas` (mecanismo UPDATE condicional / locks).
- **[Acumulación de reservas no confirmadas sin TTL]** → Reservas que no lleguen a confirmarse o liberarse retendrán cupo.
  *Mitigación:* Se aborda en `concurrencia-de-reservas` con TTL y política de expiración.

## Migration Plan

1. Ejecutar `docker compose run --rm events-service alembic upgrade head` para aplicar la migración `0002_add_inventario.py`.
2. Las pruebas automáticas de regresión de `events-service` verifican que los tests existentes se adapten a los nuevos campos obligatorios de modalidad.
3. Reversión: `alembic downgrade -1` elimina las tablas `reservas`, `asientos`, `sectores` y remueve las columnas agregadas de `modalidades`.
