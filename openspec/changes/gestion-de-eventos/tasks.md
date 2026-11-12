# Tasks: Implementación Mínima de Gestión de Eventos

## 1. Scaffolding, Base de Datos y Modelos

- [ ] 1.1 Crear estructura de directorios en `backend/events-service/`, archivo `Dockerfile` y `pyproject.toml` con FastAPI, SQLAlchemy 2, Alembic, Pydantic v2 y Psycopg3.
- [ ] 1.2 Configurar `compose.yaml` agregando los servicios `events-db` (PostgreSQL 16) y `events-service` con variables de entorno y volúmenes.
- [ ] 1.3 Configurar Alembic y generar la migración inicial `0001_initial_schema.py` creando las 2 tablas (`eventos`, `modalidades`) con IDs UUID autogenerados.
- [ ] 1.4 Implementar modelos ORM de SQLAlchemy en `app/models.py` respetando la relación `evento → modalidades` con CASCADE.

## 2. Middleware, Schemas y Handlers de Eventos

- [ ] 2.1 Implementar middleware HTTP de bitácora en `app/main.py` registrando logs JSON a stdout con `duration_ms` y propagación de `X-Correlation-Id`.
- [ ] 2.2 Configurar exception handler para validación de datos retornando `400 Bad Request` con `{"detail": "invalid body"}` ante campos faltantes o inválidos.
- [ ] 2.3 Implementar schemas Pydantic v2 en `app/schemas.py` con validaciones: `nombre` requerido, `precio >= 0`, `capacidad > 0`, `tipo` ∈ {`numerado`, `general`}.
- [ ] 2.4 Implementar handlers en `app/routers.py`:
  - `GET /eventos`: lista completa del catálogo (activos e inactivos) con modalidades anidadas.
  - `GET /eventos/{id}`: detalle del evento con modalidades; 404 si no existe.
  - `POST /eventos`: alta con UUIDs autogenerados; retorna 201 Created.
  - `PUT /eventos/{id}`: reemplazo completo del evento y **todas** sus modalidades; retorna 200 OK, 400 o 404.
  - `DELETE /eventos/{id}`: baja lógica (`activo = false`); retorna 200 OK o 404.

## 3. Testing Automatizado y Verificación

- [ ] 3.1 Configurar fixtures de base de datos de test en `tests/conftest.py`.
- [ ] 3.2 Implementar tests en `tests/test_eventos.py` validando:
  - Alta exitosa (201) y retorno de entidad con UUID generado.
  - Validaciones 400 (`nombre` faltante, `precio` negativo, `capacidad <= 0`, `tipo` inválido).
  - `GET /eventos` retorna activos e inactivos con modalidades.
  - `GET /eventos/{id}` devuelve 200 con entidad completa y 404 ante UUID inexistente.
  - `PUT /eventos/{id}` reemplaza modalidades (las omitidas desaparecen); retorna 400 y 404 según corresponda.
  - `DELETE /eventos/{id}` aplica baja lógica; retorna 404 ante UUID inexistente.
- [ ] 3.3 Ejecutar suite completa con pytest en Docker Compose verificando que el código de producción se mantenga en ~300 líneas.

## Workflow follow-up

- Ejecutar `openspec validate` para confirmar la integridad del change.
- Actualizar el PR en GitHub con la propuesta ajustada.
