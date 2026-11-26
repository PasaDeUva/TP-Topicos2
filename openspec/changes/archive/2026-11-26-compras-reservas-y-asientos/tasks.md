# Tasks

## 1. Modelo de Datos y Migración de Alembic

- [x] 1.1 Actualizar el modelo `Compra` en `backend/compras-service/app/models.py` agregando `reserva_id` (UUID not null), `asiento_id` (UUID nullable) y `estado` (String not null, default 'confirmada'); generar la migración `0002_reserva_asiento_estado.py` en Alembic y verificar con `alembic upgrade head` y `alembic check`.
- [x] 1.2 Actualizar los esquemas Pydantic en `backend/compras-service/app/schemas.py` (`CompraIn` con `asiento_id: UUID | None = None`, `CompraOut` exponiendo `reserva_id`, `asiento_id` y `estado`); verificar con tests de serialización/validación de schemas.

## 2. Cliente de Eventos (Reservas, Confirmación y Compensación)

- [x] 2.1 Extender `EventsClient` en `backend/compras-service/app/events_client.py` con métodos para reservar (`POST /eventos/{eid}/modalidades/{mid}/reservas`), confirmar (`POST .../reservas/{rid}/confirmar`) y liberar (`DELETE .../reservas/{rid}`), propagando `Idempotency-Key` y `X-Correlation-Id`.
- [x] 2.2 Agregar manejo de excepciones específicas (`EventsConflictError` para 409 y `EventsServiceError` para 5xx/timeout/red); verificar mediante tests unitarios con `httpx.MockTransport` cubriendo 200/201, 409, 503 y liberación de reservas.

## 3. Orquestación del Endpoint POST /compras y Consultas

- [x] 3.1 Actualizar `POST /compras` en `backend/compras-service/app/routers.py` para validar la coherencia entre `modalidad.tipo` y `asiento_id` (400 si falta en numerada o si sobra en general), y orquestar el flujo reserva $\rightarrow$ confirmación $\rightarrow$ persistencia.
- [x] 3.2 Implementar manejo de conflictos 409 de `events-service` (sin cupo o asiento ocupado) y compensación por rollback (`DELETE /reservas/{rid}`) si la confirmación falla o da timeout; verificar con tests de fallas parciales.
- [x] 3.3 Actualizar `_responder_existente` y la lógica de reintento idempotente en `POST /compras` para contemplar `asiento_id` y devolver la compra existente con su `reserva_id` y `estado`.
- [x] 3.4 Actualizar endpoints de consulta `GET /compras/{id}` y `GET /compras?cliente_id=` para incluir `reserva_id`, `asiento_id` y `estado`; verificar con tests unitarios.

## 4. Pruebas de Integración y Regresión

- [x] 4.1 Actualizar la suite de pruebas en `backend/compras-service/tests/test_compras.py` cubriendo compra general exitosa, compra numerada con asiento exitosa, rechazo por falta de cupo (409), rechazo por asiento no disponible (409), rechazo por modalidad numerada sin asiento (400) y por general con asiento (400).
- [x] 4.2 Ejecutar la suite completa de pruebas en el contenedor `backend-tests` con `docker compose run --rm backend-tests` y validar que todos los tests de `compras-service`, `events-service` y demás servicios pasen sin regresiones.

## Workflow follow-up

- Ejecutar `openspec validate compras-reservas-y-asientos --strict`.
- Archivar el change cuando la implementación esté completa y verificada.
