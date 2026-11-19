# Tasks

## 1. Soporte de Modelo y Configuración de TTL

- [ ] 1.1 Incorporar columna `expira_en` en el modelo `Reserva` en `app/models.py` y en la migración de inventario; verificar aplicando `docker compose run --rm events-service alembic upgrade head` y `alembic check`.
- [ ] 1.2 Agregar variable de configuración `RESERVA_TTL_MINUTES` en `app/config.py` con valor por defecto de 10 minutos; verificar mediante prueba unitaria de carga de configuración.

## 2. Implementación de Exclusión Mutua en Reservas

- [ ] 2.1 Implementar la reserva atómica condicional de asientos numerados (`UPDATE asientos SET estado = 'reservado' WHERE id = :id AND estado = 'libre'`) en `app/routers.py`; verificar con test de concurrencia paralelo (`pytest -k test_reserva_asiento_concurrente`) que ante dos solicitudes simultáneas por el mismo asiento exactamente una responda 201 y la otra 409.
- [ ] 2.2 Implementar el aislamiento transaccional con `with_for_update()` en la reserva de modalidad general en `app/routers.py`; verificar con test de concurrencia (`pytest -k test_reserva_cupo_concurrente`) que ante múltiples solicitudes que excedan el cupo disponible se rechace el sobrante con 409.

## 3. Lógica y Validación de Expiración por TTL

- [ ] 3.1 Actualizar el cálculo de disponibilidad en `GET .../disponibilidad` para computar como disponibles las reservas activas cuyo `expira_en` haya vencido; verificar con test de disponibilidad tras expiración de reserva.
- [ ] 3.2 Implementar validación en `POST .../confirmar` que rechace con 409 reservas con TTL vencido y libere el asiento asociado; verificar con test de confirmación de reserva expirada.

## 4. Pruebas y Validación Final

- [ ] 4.1 Ejecutar suite completa de tests de `events-service` verificando ausencia de regresiones; verificar con `docker compose run --rm backend-tests pytest backend/events-service/tests`.

## Workflow follow-up

- Ejecutar `openspec validate concurrencia-de-reservas --strict`.
- Abrir Pull Request conjunto hacia `development` conteniendo ambos changes y sus ADRs asociados.
