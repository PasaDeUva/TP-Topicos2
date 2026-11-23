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
| `PUT` | `/eventos/{id}` | Actualización completa con reemplazo de modalidades (preserva `id` y rechaza con 409 si la omitida tiene reservas) | `200`, `400`, `404`, `409` |
| `DELETE` | `/eventos/{id}` | Baja lógica del evento (`activo = false`) | `200`, `404` |
| `GET` | `/eventos/{id}/modalidades/{mid}/disponibilidad` | Consulta la cantidad de entradas o asientos disponibles | `200` (`{"disponibles": int}`), `404` |
| `POST` | `/eventos/{id}/modalidades/{mid}/reservas` | Crea una reserva temporal (soporta `Idempotency-Key` en headers) | `201` (`{"reserva_id": uuid}`), `200` (reintento idempotente), `400`, `404`, `409` |
| `DELETE` | `/eventos/{id}/modalidades/{mid}/reservas/{reserva_id}` | Libera una reserva activa restituyendo el asiento a `libre` | `200` (`{"status": "liberada"}`), `404`, `409` |
| `POST` | `/eventos/{id}/modalidades/{mid}/reservas/{reserva_id}/confirmar` | Confirma la venta de una reserva activa pasando el asiento a `vendido` | `200` (`{"status": "confirmada"}`), `404`, `409` |

### Modelo de Inventario y Tarifas

- **Modalidad General:** tarifa plana en `precio NUMERIC(10, 2)` y cupo en `cupo INTEGER` dentro de `modalidades`. La disponibilidad descuenta reservas confirmadas y activas vigentes.
- **Modalidad Numerada:** `precio` y `cupo` son `NULL` en `modalidades`. Cada ubicación se desagrega en `sectores` (con su propio `precio`) y `asientos` (`fila`, `numero`, `estado IN ('libre', 'reservado', 'vendido')`).
- **Reservas:** tabla `reservas` con TTL (`expira_en`), estado (`'activa'`, `'confirmada'`, `'liberada'`) y clave única de idempotencia (`uq_reservas_idempotency_key`). Integridad referencial con `ON DELETE RESTRICT` para evitar borrados accidentales de ventas históricas.

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
