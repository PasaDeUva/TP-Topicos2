# Tasks: Implementación Mínima de Gestión de Eventos

## 1. Scaffolding, Base de Datos y Modelos

- [ ] 1.1 Crear estructura de directorios en `backend/events-service/`, archivo `Dockerfile` y `pyproject.toml` con FastAPI, SQLAlchemy 2, Alembic, Pydantic v2 y Psycopg3.
- [ ] 1.2 Configurar `compose.yaml` agregando los servicios `events-db` (PostgreSQL 16) y `events-service` con variables de entorno y volúmenes.
- [ ] 1.3 Configurar Alembic y generar la migración inicial `0001_initial_schema.py` creando las 3 tablas (`eventos`, `modalidades_stock`, `reservas`) con IDs UUID autogenerados.
- [ ] 1.4 Implementar modelos ORM de SQLAlchemy en `app/models.py` respetando relaciones y restricción UNIQUE `(evento_id, asiento_codigo)`.

## 2. Middleware, Schemas y Handlers de Eventos

- [ ] 2.1 Implementar middleware HTTP de bitácora en `app/main.py` registrando logs JSON a stdout con `duration_ms` y propagación de `X-Correlation-Id`.
- [ ] 2.2 Configurar exception handler para validación de datos retornando `400 Bad Request` con `{"detail": "invalid body"}` ante campos faltantes.
- [ ] 2.3 Implementar schemas Pydantic v2 en `app/schemas.py` para upsert y respuestas de eventos con identificadores UUID.
- [ ] 2.4 Implementar handlers en `app/routers.py`:
  - `GET /eventos` y `GET /eventos/{id}` (retornando entidades tanto activas como inactivas).
  - `POST /eventos` unificado (creación 201 sin id, edición 200 con id, y baja lógica con `activo: false`).

## 3. Contratos de Inventario y Concurrencia para Compras

- [ ] 3.1 Implementar lógica de reservas con TTL de 10 minutos en `app/services.py`.
- [ ] 3.2 Implementar control de concurrencia: bloqueo pesimista en asientos (`SELECT FOR UPDATE`) y update atómico condicional en zonas (`UPDATE ... WHERE cupo >= n RETURNING id`).
- [ ] 3.3 Implementar endpoints de contrato para Compras:
  - `POST /eventos/{id}/reservar` (retorna 200 con TTL o 409 Conflict si no hay stock o `activo: false`).
  - `POST /eventos/{id}/reservas/{reserva_id}/confirmar` (asienta reserva confirmada).
  - `POST /eventos/{id}/reservas/{reserva_id}/liberar` (reintegra stock).

## 4. Testing Automatizado y Verificación

- [ ] 4.1 Configurar fixtures de base de datos de test en `tests/conftest.py`.
- [ ] 4.2 Implementar tests en `tests/test_eventos.py` validando creación 201, validaciones 400 (`invalid body`), edición y baja lógica, y consultas GET retornando entidades activas e inactivas.
- [ ] 4.3 Implementar tests en `tests/test_reservas.py` validando reservas atómicas, prevención de sobreventa bajo concurrencia simulada y confirmación/liberación.
- [ ] 4.4 Ejecutar suite completa con pytest en Docker Compose verificando que el código de producción se mantenga en ~450 líneas.

## Workflow follow-up

- Ejecutar `openspec validate` para confirmar la integridad del change.
- Actualizar el PR en GitHub con la propuesta reducida y consensuada con el equipo.
