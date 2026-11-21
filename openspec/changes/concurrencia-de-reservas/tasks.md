# Tasks

## 1. Soporte de Modelo y Configuración de TTL

- [ ] 1.1 Verificar que la columna `expira_en` y la columna `idempotency_key` formen parte de la migración `0002_add_inventario.py` y del modelo `Reserva` en `backend/events-service/app/models.py`; verificar aplicando `docker compose run --rm events-service alembic upgrade head` y `docker compose run --rm events-service alembic check`.
- [ ] 1.2 Agregar variable de configuración `RESERVA_TTL_MINUTES` en `backend/events-service/app/config.py` con valor por defecto de 10 minutos; verificar mediante prueba unitaria de carga de configuración en `tests/test_eventos.py`.

## 2. Implementación de Exclusión Mutua y Liberación Perezosa

- [ ] 2.1 Implementar la liberación perezosa con orden canónico de locks (`reservas` luego `asientos`) y la reserva atómica condicional de asientos numerados (`UPDATE asientos SET estado = 'reservado' WHERE id = :id AND estado = 'libre'`) en `backend/events-service/app/routers.py`; verificar con test de concurrencia paralelo en `tests/test_concurrencia.py` que solicitudes simultáneas sobre el mismo asiento resulten en un único 201 y el resto 409.
- [ ] 2.2 Implementar el aislamiento transaccional con `with_for_update()` en la reserva de modalidad general y cómputo de ocupación (`confirmadas + activas vigentes`) en `backend/events-service/app/routers.py`; verificar con test de concurrencia en `tests/test_concurrencia.py` que compras posteriores a confirmaciones no excedan el cupo.

## 3. Lógica y Validación de Expiración por TTL

- [ ] 3.1 Actualizar el cálculo de disponibilidad en `GET .../disponibilidad` para computar como disponibles las reservas activas cuyo `expira_en` haya vencido; verificar con test de disponibilidad tras expiración de reserva en `tests/test_concurrencia.py`.
- [ ] 3.2 Implementar validación en `POST .../confirmar` que retorne 200 idempotente si ya está confirmada y 409 si expiró por TTL, liberando el asiento asociado únicamente si continúa asignado a la reserva; verificar con test de confirmación en `tests/test_concurrencia.py`.

## 4. Pruebas y Validación Final

- [ ] 4.1 Ejecutar suite completa de tests de `events-service` verificando ausencia de regresiones; verificar con `docker compose run --rm backend-tests pytest events-service/tests`.

## Workflow follow-up

- Ejecutar `openspec validate concurrencia-de-reservas --strict`.
- Ambos changes (`concurrencia-de-reservas` e `inventario-de-entradas`) se implementan y verifican de forma conjunta bajo la misma migración `0002_add_inventario.py`.
