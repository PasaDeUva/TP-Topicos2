# Proposal

## Why

La implementación inicial de `compras-service` solo cubría un registro mínimo para eventos generales sin validar cupos ni admitir asientos numerados. `events-service` ya cuenta con soporte completo de inventario y concurrencia (cupos, sectores, asientos, reservas, confirmación y liberación). Este cambio integra `compras-service` con dicho inventario para que orqueste la reserva y confirmación de entradas (tanto generales como numeradas) de forma atómica e idempotente, resolviendo la sobreventa y permitiendo la compra de asientos numerados sin requerir todavía un servicio de pagos.

## What Changes

- **Soporte de Modalidad Numerada y Asientos en `compras-service`**:
  - Aceptar `asiento_id` (UUID opcional/condicional) en el cuerpo de `POST /compras`.
  - Levantar la restricción que rechazaba la modalidad `numerado` con código 409.
  - Validar que ante modalidad `numerado` se provea obligatoriamente `asiento_id`, y que en modalidad `general` no se incluya.
- **Orquestación de Reserva y Confirmación**:
  - `compras-service` orquesta la transacción distribuyendo las operaciones hacia `events-service`:
    1. Solicita la reserva de cupo o asiento (`POST /eventos/{eid}/modalidades/{mid}/reservas`).
    2. Confirma la reserva (`POST /eventos/{eid}/modalidades/{mid}/reservas/{rid}/confirmar`).
    3. Si la confirmación o el proceso falla con error recuperable/5xx, ejecuta compensación liberando la reserva (`DELETE /eventos/{eid}/modalidades/{mid}/reservas/{rid}`).
  - Propaga `Idempotency-Key` y `X-Correlation-Id` en cada llamada hacia `events-service`.
- **Manejo de Errores de Concurrencia y Disponibilidad**:
  - Si `events-service` responde `409 Conflict` (por falta de cupo o asiento ya reservado/ocupado), `compras-service` traslada el `409 Conflict` al cliente sin crear ni persistir la compra.
- **Ciclo de Vida y Modelo de Datos de Compra**:
  - Extender la tabla `compras` con `reserva_id` (UUID NOT NULL), `asiento_id` (UUID nullable) y `estado` (`confirmada`, `fallida`).
  - Crear la correspondiente migración de Alembic en `compras-service`.

## Capabilities

### New Capabilities
<!-- Ninguna nueva capability; se amplía la existente. -->

### Modified Capabilities
- `gestion-de-compras`: Actualiza los requisitos de `POST /compras` para admitir modalidad numerada con `asiento_id`, orquestar la reserva y confirmación atómica en `events-service`, registrar el `reserva_id` y `estado`, y responder 409 ante falta de disponibilidad o conflicto de asiento reportado por el catálogo.

## Impact

- **APIs de `compras-service`**:
  - `POST /compras`: Nuevo campo opcional `asiento_id`, respuestas 409 por agotamiento de cupo o asiento no disponible, respuesta 201 con `reserva_id` y `estado`.
  - `GET /compras/{id}` y `GET /compras?cliente_id=`: Exponen `reserva_id`, `asiento_id` y `estado`.
- **Base de datos de `compras-service` (`compras_db`)**:
  - Nuevas columnas en tabla `compras`: `reserva_id`, `asiento_id` y `estado`.
- **Cliente HTTP (`app/events_client.py`)**:
  - Nuevos métodos para llamar a `POST .../reservas`, `POST .../confirmar` y `DELETE .../reservas/{rid}`.
- **Dependencias**:
  - `payment-service` queda explícitamente fuera de alcance para esta etapa.
