# Tasks

## 1. Servicio, base de datos e infraestructura

- [x] 1.1 Crear `backend/compras-service/` con `Dockerfile`, `entrypoint.sh`, `pyproject.toml`, `requirements.txt` y `requirements-dev.txt` (mismas versiones que `events-service`, con `httpx` en runtime); verificar con `docker compose build compras-service`.
- [x] 1.2 Agregar `compras-db` (PostgreSQL 16, puerto `5436`, volumen propio, `scripts/init-test-db.sql` con `compras_test`) y `compras-service` (puerto `8003`, `EVENTS_SERVICE_URL`, `depends_on`) a `compose.yaml`, y `COMPRAS_TEST_DATABASE_URL` a `backend-tests`; verificar con `docker compose up -d compras-db compras-service` y `curl http://localhost:8003/docs`.
- [x] 1.3 Configurar Alembic, implementar el modelo `Compra` en `app/models.py` y generar la migración `0001_initial_schema.py` con la restricción `UNIQUE (cliente_id, idempotency_key)` y el índice por cliente; verificar con `docker compose run --rm compras-service alembic upgrade head` y `alembic check`.
- [x] 1.4 Implementar `app/config.py` y `app/database.py`, y documentar el servicio en `backend/compras-service/README.md`, `backend/README.md` y `docs/local-development.md`; verificar que los comandos documentados se ejecutan tal cual.

## 2. Middleware, validación y cliente de Eventos

- [x] 2.1 Implementar en `app/main.py` el middleware de bitácora (logs JSON con `duration_ms` y `X-Correlation-Id`) y el handler de validación que responde `400` con `{"detail": "invalid body"}` o `{"detail": "invalid path parameter"}`; verificar con tests de log emitido, cabecera propagada y `400`.
- [x] 2.2 Implementar `app/events_client.py` y `get_events_client`: consulta `GET /eventos/{id}`, reenvía `X-Correlation-Id`, devuelve `None` ante `404` y lanza una excepción propia ante error de red, timeout o `5xx`; verificar con tests usando `httpx.MockTransport` para `200`, `404`, `500` y timeout.
- [x] 2.3 Implementar `app/schemas.py` (`CompraIn`, `CompraOut` sin `idempotency_key`); verificar con tests de UUID inválido y campos faltantes.

## 3. Endpoints de compras

- [x] 3.1 Implementar `POST /compras` en `app/routers.py` siguiendo el flujo del design: clave de idempotencia, validación contra Eventos (`404`, `409`, `503`) e inserción (`201`); verificar con tests de registro exitoso, evento inexistente, modalidad ajena al evento, evento inactivo, modalidad `numerado`, Eventos caído y body inválido.
- [x] 3.2 Implementar la idempotencia completa: reintento idéntico devuelve `200` con la compra original sin llamar a Eventos, clave con contenido distinto devuelve `409`, clave ausente o vacía devuelve `400`, y la carrera por `IntegrityError` relee la compra existente; verificar con tests de reintento, contenido distinto, clave ausente y dos solicitudes concurrentes que dejan una única fila.
- [x] 3.3 Implementar `GET /compras/{id}` y `GET /compras?cliente_id=` ordenado por `creado_en` descendente; verificar con tests de detalle `200`, `404`, UUID inválido `400`, listado filtrado por cliente, orden y `cliente_id` ausente o inválido `400`.

## 4. Pruebas y CI

- [x] 4.1 Configurar `tests/conftest.py` (base `compras_test` con rechazo de `compras_db`, sesión, cliente HTTP y fábrica de eventos simulados) y confirmar que los tests de los grupos 2 y 3 residen en `tests/test_compras.py`; verificar con `docker compose run --rm backend-tests sh -c "cd compras-service && pytest"`.
- [x] 4.2 Actualizar `.github/workflows/ci.yml` con `compras-db`, `alembic upgrade head`, `alembic check` y `ruff check` para `compras-service`; verificar con `docker compose run --rm --no-deps backend-tests python -m ruff check mock-service events-service compras-service`.
- [x] 4.3 Verificar la integración real: con `events-service` y `compras-service` levantados, crear un evento general por `POST /eventos` y registrar una compra por `POST /compras` con `curl`, confirmando `201`, el reintento con `200` y el listado por cliente.
- [x] 4.4 Ejecutar la suite completa con `docker compose run --rm backend-tests` y confirmar que los tests de `events-service` y `mock-service` siguen pasando.

## Workflow follow-up

- Ejecutar `openspec validate gestion-de-compras --strict`.
- Aceptar ADR-0005 en revisión del equipo antes de archivar.
- Abrir el Pull Request hacia `development` desde `feature/gestion-de-compras`.
- Archivar el change cuando todas las tareas estén completas.
