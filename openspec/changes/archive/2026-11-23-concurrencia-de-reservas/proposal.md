# Proposal

## Why

El flujo funcional de inventario y reservas permite crear y gestionar reservas pero carece de mecanismos formales de exclusión mutua atómica y expiración temporal. Bajo solicitudes concurrentes o transacciones en competencia, existe riesgo de sobreventa de cupos generales (tanto antes como después de confirmar compras), doble asignación del mismo asiento numerado o retención indefinida de inventario por compras abandonadas, violando los requerimientos de la cátedra de garantizar que un ticket no se venda dos veces.

## What Changes

- Implementar exclusión mutua atómica en la reserva de cupo general mediante serialización con `SELECT ... FOR UPDATE` a nivel de fila de modalidad, computando la ocupación total sobre reservas confirmadas y activas vigentes (`expira_en > NOW()`).
- Implementar exclusión mutua atómica en la reserva de asientos numerados mediante actualización condicional `UPDATE asientos SET estado = 'reservado' WHERE id = :id AND estado = 'libre'`.
- Implementar mecanismo de liberación perezosa (*lazy cleanup*) que libere reservas activas vencidas (`expira_en <= NOW()`) y restituya sus asientos a `libre` al consultar disponibilidad o intentar reservar, siguiendo un orden canónico de locks (`reservas` luego `asientos`) para evitar colisiones con confirmaciones tardías.
- Soportar `Idempotency-Key` en creación de reservas para reintentos transparentes ante fallos de red en el cliente orquestador (`compras-service`).
- Configurar tiempo de vida (TTL configurable vía `RESERVA_TTL_MINUTES`, por defecto 10 minutos) sobre la columna `expira_en` en tabla `reservas`.
- Rechazar con `409 Conflict` cualquier intento de reserva concurrente cuando el cupo esté agotado o el asiento haya sido tomado por otra transacción.
- Garantizar que una reserva vencida por TTL no pueda ser confirmada, respondiendo `409 Conflict` sin afectar asientos ya reasignados. Ambos changes se implementan y verifican de forma conjunta.

## Capabilities

### New Capabilities

- `concurrencia-de-reservas`: Exclusión mutua atómica en reservas de cupos y asientos, prevención de doble venta y expiración de reservas por TTL.

### Modified Capabilities

## Impact

- **Código afectado:** Lógica transaccional de reservas y disponibilidad en `backend/events-service/app/routers.py`.
- **Base de datos:** Utiliza la columna `expira_en TIMESTAMPTZ` provista en la migración `0002_add_inventario.py`.
- **ADRs:** ADR-0008 ("Control de concurrencia y expiración por TTL en reservas de inventario").
- **APIs:** Los endpoints existentes `POST .../reservas` y `POST .../reservas/{id}/confirmar` incorporan validación estricta de concurrencia y TTL.
