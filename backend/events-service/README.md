# Events Service

Microservicio autónomo para la gestión del catálogo de eventos de la plataforma de ticketera virtual.

## Stack tecnológico

- **Lenguaje:** Python 3.12
- **Framework web:** FastAPI 0.115
- **ORM / Persistencia:** SQLAlchemy 2.0 (asyncio) con driver `psycopg` (v3)
- **Migraciones:** Alembic 1.14
- **Validación:** Pydantic v2
- **Base de datos:** PostgreSQL 16 (`events_db`)

## Endpoints de la API

| Método | Ruta | Descripción | Códigos HTTP |
|---|---|---|---|
| `GET` | `/eventos` | Lista todos los eventos (ordenados por fecha de creación) | `200` |
| `GET` | `/eventos/{id}` | Obtiene el detalle de un evento por su UUID | `200`, `400` (UUID inválido), `404` |
| `POST` | `/eventos` | Da de alta un nuevo evento con sus modalidades | `201`, `400` (validación fallida) |
| `PUT` | `/eventos/{id}` | Actualización completa con reemplazo total de modalidades | `200`, `400`, `404` |
| `DELETE` | `/eventos/{id}` | Baja lógica del evento (`activo = false`) | `200`, `404` |

## Variables de entorno

- `DATABASE_URL`: URL de conexión asíncrona a la base de datos principal (`events_db`). Ejemplo: `postgresql+psycopg://events:events@events-db:5432/events_db`.
- `TEST_DATABASE_URL`: URL de conexión a la base de datos exclusiva para tests (`events_test`). Ejemplo: `postgresql+psycopg://events:events@events-db:5432/events_test`.

## Ejecución local con Docker Compose

Levantar la base de datos y el servicio:

```bash
docker compose up -d events-service
```

El servicio ejecuta automáticamente las migraciones pendientes vía `alembic upgrade head` al arrancar el contenedor (`entrypoint.sh`).

Para verificar el estado de la aplicación:

```bash
curl -i http://localhost:8001/eventos
```

## Migraciones con Alembic

Para generar o aplicar migraciones:

```bash
# Aplicar migraciones
docker compose run --rm events-service alembic upgrade head

# Verificar sincronización (drift) entre modelos y base de datos
docker compose run --rm events-service alembic check
```

## Pruebas automatizadas

Los tests utilizan una base de datos aislada (`events_test`) para garantizar que la base de desarrollo no sea modificada ni borrada:

```bash
# Correr tests del servicio
docker compose run --rm backend-tests sh -c "cd events-service && pytest -v"

# Correr linters
docker compose run --rm --no-deps backend-tests python -m ruff check events-service
```

## Observabilidad y Bitácora HTTP

Cada solicitud procesada emite un registro estructurado en formato JSON con la latencia en milisegundos (`duration_ms`), código HTTP, método, ruta y el identificador de correlación `X-Correlation-Id`.
