# Compras Service

Microservicio mínimo para registrar la compra de entradas de la plataforma de ticketera virtual. Esta es la Etapa I: una compra registra el cliente, el evento y la modalidad elegida. No descuenta cupo, no cobra ni confirma la compra en `events-service`.

## Stack tecnológico

- **Lenguaje:** Python 3.12
- **Framework web:** FastAPI 0.115
- **ORM / Persistencia:** SQLAlchemy 2.0 (asyncio) con driver `psycopg` (v3)
- **Migraciones:** Alembic 1.14
- **Validación:** Pydantic v2
- **Cliente HTTP:** httpx (consulta de eventos a `events-service`)
- **Base de datos:** PostgreSQL 16 (`compras_db`)

## Endpoints de la API

| Método | Ruta | Descripción | Códigos HTTP |
|---|---|---|---|
| `POST` | `/compras` | Registra una compra. Requiere header `Idempotency-Key`. | `201` (creada), `200` (reintento idéntico, devuelve la misma compra), `400` (body o header inválido), `404` (evento o modalidad inexistente), `409` (clave reutilizada con otro body, evento inactivo o modalidad no disponible), `503` (`events-service` no responde) |
| `GET` | `/compras?cliente_id={uuid}` | Lista las compras de un cliente, de la más reciente a la más antigua | `200`, `400` (`cliente_id` inválido) |
| `GET` | `/compras/{id}` | Obtiene una compra por su UUID | `200`, `400` (UUID inválido), `404` |

### Ejemplo de compra

```bash
curl -i -X POST http://localhost:8003/compras \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: 6f1d2c1e-0000-4000-8000-000000000001" \
  -d '{"cliente_id": "22222222-2222-2222-2222-222222222222", "evento_id": "<uuid-del-evento>", "modalidad_id": "<uuid-de-la-modalidad-general>"}'
```

Repetir el mismo request con la misma `Idempotency-Key` y el mismo body devuelve `200` con la compra original, sin crear otra.

## Dependencias

- `events-service` valida que el evento exista, esté activo y que la modalidad elegida sea de tipo `general`. La consulta usa un timeout corto (`EVENTS_TIMEOUT_SECONDS`, 0.8 s por defecto).
- El `cliente_id` viaja en el body y en la query como dato temporal. No se valida JWT ni roles hasta que `gestion-de-accesos` esté integrado ([ADR-0004](../../docs/adr/0004-autenticacion-entre-servicios.md)).

## Variables de entorno

- `DATABASE_URL`: URL de conexión a la base principal (`compras_db`). Ejemplo: `postgresql+psycopg://compras:compras@compras-db:5432/compras_db`.
- `EVENTS_SERVICE_URL`: URL base de `events-service`. Ejemplo: `http://events-service:8000` dentro de Compose.
- `EVENTS_TIMEOUT_SECONDS`: timeout de la consulta a `events-service`, en segundos. Por defecto `0.8`.
- `COMPRAS_TEST_DATABASE_URL`: base exclusiva para tests (`compras_test`). Por defecto `postgresql+psycopg://compras:compras@compras-db:5432/compras_test`. Los tests se niegan a correr contra `compras_db`.

## Ejecución local con Docker Compose

Levantar la base de datos y el servicio:

```bash
docker compose up -d compras-service
```

El contenedor ejecuta `alembic upgrade head` al arrancar (`entrypoint.sh`). Para verificar que responde:

```bash
curl -i http://localhost:8003/compras?cliente_id=22222222-2222-2222-2222-222222222222
```

La documentación interactiva está en `http://localhost:8003/docs`.

## Migraciones con Alembic

```bash
# Aplicar migraciones
docker compose run --rm compras-service alembic upgrade head

# Verificar sincronización (drift) entre modelos y base de datos
docker compose run --rm compras-service alembic check
```

## Pruebas automatizadas

```bash
# Correr tests del servicio
docker compose run --rm backend-tests sh -c "cd compras-service && pytest -v"

# Correr linters
docker compose run --rm --no-deps backend-tests python -m ruff check compras-service

# Verificación de caja negra contra Compose real (events-service + compras-service y sus bases)
python backend/compras-service/scripts/verify_compose.py
```

El script levanta un proyecto Compose aislado con copias temporales de los servicios, crea un evento en Eventos y verifica por HTTP: compra 201, reintento idempotente 200 con el mismo id, conflicto 409 con otra modalidad, listado 200 y registros de bitácora con `correlation_id` y `duration_ms` en ambos servicios. Al terminar baja el proyecto y borra los volúmenes.

## Observabilidad y Bitácora HTTP

Cada solicitud emite un registro JSON con `duration_ms`, código HTTP, método, ruta y `X-Correlation-Id`. Si el cliente no envía el header, el servicio genera uno.
