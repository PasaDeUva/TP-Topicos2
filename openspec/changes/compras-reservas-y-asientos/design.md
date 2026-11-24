# Design

## Context

`compras-service` fue creado inicialmente para registrar compras simples de eventos generales sin validar cupos ni comunicarse con el inventario de `events-service` (ver [proposal.md](./proposal.md)). Por su parte, `events-service` ya implementó las capacidades `inventario-de-entradas` y `concurrencia-de-reservas`, exponiendo:
- `POST /eventos/{evento_id}/modalidades/{modalidad_id}/reservas` (con `asiento_id` opcional para numerada, y cabecera `Idempotency-Key`).
- `POST /eventos/{evento_id}/modalidades/{modalidad_id}/reservas/{reserva_id}/confirmar`.
- `DELETE /eventos/{evento_id}/modalidades/{modalidad_id}/reservas/{reserva_id}` (liberación).

Este diseño define cómo `compras-service` orquesta la reserva, confirmación y compensación de entradas generales y numeradas en ausencia de `payment-service`.

## Goals / Non-Goals

**Goals:**
- Soportar la compra de entradas en modalidades generales y numeradas (con `asiento_id`).
- Orquestar la reserva y confirmación atómica en `events-service` desde `compras-service`.
- Manejar conflictos de concurrencia (409) de `events-service` (cupo agotado o asiento ocupado/reservado) y propagarlos con semántica HTTP clara.
- Ejecutar compensación (`DELETE .../reservas/{rid}`) si la confirmación falla o da timeout.
- Extender el modelo relacional `compras` con `reserva_id`, `asiento_id` y `estado`.
- Mantener la idempotencia estricta por `(cliente_id, idempotency_key)` y propagar cabeceras (`Idempotency-Key`, `X-Correlation-Id`).

**Non-Goals:**
- Integración con `payment-service` o pasarelas de pago (diferido a etapas posteriores).
- Compra de múltiples tickets por solicitud (se mantiene en 1 ticket/asiento por compra en esta etapa).
- Devoluciones y reembolsos (pertenece a la Etapa III).
- Colas de venta y colas virtuales (Etapa III).

## Decisions

### 1. Modelo de Datos de `compras-service`

Modificar la tabla `compras` en `compras_db`:

```sql
ALTER TABLE compras
    ADD COLUMN reserva_id UUID NOT NULL,
    ADD COLUMN asiento_id UUID NULL,
    ADD COLUMN estado VARCHAR(32) NOT NULL DEFAULT 'confirmada';

CREATE INDEX ix_compras_reserva ON compras (reserva_id);
```

*Rationale:* Permite rastrear la reserva en `events-service`, registrar el asiento específico cuando corresponda, y modelar el estado de la compra.

### 2. Flujo Orquestado en `POST /compras`

1. **Validación del payload**:
   - `cliente_id`, `evento_id`, `modalidad_id` obligatorios (UUID).
   - Si `asiento_id` viene en el body, debe ser UUID válido.
   - Cabecera `Idempotency-Key` requerida (1..255 caracteres).
2. **Chequeo de Idempotencia local**:
   - Si ya existe una compra con `(cliente_id, idempotency_key)`:
     - Con mismos datos (`evento_id`, `modalidad_id`, `asiento_id`) $\rightarrow$ retorna `200 OK` con la compra existente.
     - Con datos divergentes $\rightarrow$ retorna `409 Conflict`.
3. **Consulta de Catálogo (`GET /eventos/{evento_id}`)**:
   - `404` si evento o modalidad no existen.
   - `409 Conflict` si `evento.activo == False`.
   - Validar coherencia de modalidad:
     - Si `modalidad.tipo == "numerado"` y no viene `asiento_id` $\rightarrow$ `400 Bad Request {"detail": "invalid body"}`.
     - Si `modalidad.tipo == "general"` y viene `asiento_id` $\rightarrow$ `400 Bad Request {"detail": "invalid body"}`.
4. **Reserva en `events-service`**:
   - `POST /eventos/{eid}/modalidades/{mid}/reservas` enviando `{"asiento_id": asiento_id}` si es numerada (o vacío si es general).
   - Se reenvía `Idempotency-Key` (derivada o misma clave) y `X-Correlation-Id`.
   - Si `events-service` responde `409 Conflict` (sin cupo o asiento no disponible) $\rightarrow$ responder `409 Conflict` sin guardar la compra.
   - Si responde `5xx` o timeout $\rightarrow$ responder `503 Service Unavailable`.
5. **Confirmación en `events-service`**:
   - `POST /eventos/{eid}/modalidades/{mid}/reservas/{reserva_id}/confirmar`.
   - Si la confirmación tiene éxito (200 con `status: "confirmada"`):
     - Persistir la compra en `compras_db` con `reserva_id`, `asiento_id`, `estado: "confirmada"`.
     - Responder `201 Created`.
   - Si la confirmación falla por error de red o 5xx:
     - Ejecutar compensación llamando a `DELETE /eventos/{eid}/modalidades/{mid}/reservas/{reserva_id}`.
     - Responder `503 Service Unavailable`.

### 3. Cliente de Eventos (`app/events_client.py`)

Se agregan a `EventsClient`:
- `reservar_entrada(evento_id, modalidad_id, asiento_id=None, idempotency_key=None, correlation_id=None) -> uuid.UUID`
- `confirmar_reserva(evento_id, modalidad_id, reserva_id, correlation_id=None) -> bool`
- `liberar_reserva(evento_id, modalidad_id, reserva_id, correlation_id=None) -> bool`

Manejo de excepciones:
- `EventsConflictError` ante HTTP 409.
- `EventsServiceError` ante HTTP 5xx, timeouts y errores de conexión (mapeado a HTTP 503).

## Risks / Trade-offs

- **[Fallo de red en la llamada de compensación]** $\rightarrow$ Si el `DELETE` de liberación falla, la reserva en `events-service` tiene un TTL (definido en `concurrencia-de-reservas`) tras el cual expira y se libera automáticamente por lazy cleanup.
- **[Doble llamada concurrente con la misma `Idempotency-Key`]** $\rightarrow$ `events-service` es idempotente ante la misma clave de reserva devolviendo el `reserva_id` original; `compras_db` mantiene la restricción `UNIQUE (cliente_id, idempotency_key)`, garantizando unicidad en la base de datos.
