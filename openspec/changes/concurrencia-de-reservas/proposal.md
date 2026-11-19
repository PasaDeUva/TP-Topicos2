# Proposal

## Why

El flujo funcional de inventario y reservas permite crear y gestionar reservas pero carece de mecanismos formales de exclusión mutua atómica y expiración temporal. Bajo solicitudes concurrentes o transacciones en competencia, existe riesgo de sobreventa de cupos generales, doble asignación del mismo asiento numerado o retención indefinida de inventario por compras abandonadas, violando los requerimientos de la cátedra de garantizar que un ticket no se venda dos veces.

## What Changes

- Implementar exclusión mutua atómica en la reserva de cupo general mediante actualización condicional o bloqueo a nivel de fila (`UPDATE ... WHERE disponible >= 1`).
- Implementar exclusión mutua atómica en la reserva de asientos numerados mediante actualización condicional `UPDATE asientos SET estado = 'reservado' WHERE id = :id AND estado = 'libre'`.
- Incorporar campo `expira_en` y lógica de expiración por tiempo de vida (TTL configurable, por defecto 10 minutos) para liberar automáticamente reservas activas no confirmadas.
- Rechazar con `409 Conflict` cualquier intento de reserva concurrente cuando el cupo esté agotado o el asiento haya sido tomado por otra transacción.
- Garantizar que una reserva vencida por TTL no pueda ser confirmada, respondiendo `409 Conflict`.

## Capabilities

### New Capabilities

- `concurrencia-de-reservas`: Exclusión mutua atómica en reservas de cupos y asientos, prevención de doble venta y expiración de reservas por TTL.

### Modified Capabilities

## Impact

- **Código afectado:** Lógica transaccional de reservas en `backend/events-service/app/routers.py` y cálculo de disponibilidad.
- **Base de datos:** Campo `expira_en TIMESTAMPTZ` en tabla `reservas`.
- **ADRs:** Incorporación de ADR-0008 ("Control de concurrencia y expiración por TTL en reservas de inventario").
- **APIs:** Los endpoints existentes `POST .../reservas` y `POST .../reservas/{id}/confirmar` incorporan validación estricta de concurrencia y TTL.
