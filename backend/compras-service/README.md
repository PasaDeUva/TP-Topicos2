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

### Autenticación y autorización con Identity

Registrar y consultar compras requiere un token Bearer con sesión vigente y rol cliente activo. El cliente se toma de la identidad autenticada; `cliente_id` puede omitirse del body o de la query y, si se envía, debe coincidir con ella. El detalle y el listado se limitan a compras propias. La autenticación se verifica antes de consultar una clave de idempotencia existente.

El contrato distingue `401` para token ausente, inválido o revocado; `403` para rol insuficiente o identificador proporcionado distinto; `404` para recurso inexistente o ajeno; y `503` cuando Identity o la configuración necesaria no puedan verificarse. Los clientes que antes operaban anónimamente deben enviar `Authorization: Bearer <access_token>`. La validación contra Eventos y la idempotencia existentes se mantienen. Ver [ADR-0013](../../docs/adr/0013-identidad-en-eventos-y-compras.md).

La configuración de integración utiliza `IDENTITY_SERVICE_URL`, `IDENTITY_JWT_ISSUER`, `IDENTITY_JWT_AUDIENCE`, `IDENTITY_TIMEOUT_SECONDS` e `IDENTITY_PURCHASES_SERVICE_TOKEN`. Compose monta la clave pública de Identity en `/keys/public/public.pem` sin acceso de escritura. Identity debe configurar la credencial `purchases` con `roles_read` y `sessions_read`; los secretos se suministran fuera del repositorio. Por defecto se exige HTTPS. Para desarrollo local o pruebas aisladas únicamente, `CONSUMER_ENV=local` e `IDENTITY_ALLOW_LOCAL_HTTP=true` habilitan HTTP a `identity-service` o loopback con credenciales de prueba.

En Compose, `IDENTITY_SERVICE_CREDENTIALS_JSON` configura las credenciales en Identity: la entrada `purchases` debe tener el mismo token que `IDENTITY_PURCHASES_SERVICE_TOKEN` y ambos permisos habilitados. Los valores locales predeterminados de Identity solo permiten consultar roles; no habilitan la verificación de sesiones.

El verificador `python backend/compras-service/scripts/verify_compose.py` ejecuta la integración aislada sin necesitar historial Git. Para incluir la prueba de reversión, agregue `--rollback-ref <revision>` con una revisión anterior disponible localmente; esa prueba verifica que las escrituras anónimas vuelven a estar habilitadas.

| Método | Ruta | Descripción | Códigos HTTP |
|---|---|---|---|
| `POST` | `/compras` | Registra una compra. Requiere header `Idempotency-Key`. | `201`, `200` (reintento), `400`, `401`, `403`, `404`, `409`, `503` |
| `GET` | `/compras?cliente_id={uuid}` | Lista las compras propias; `cliente_id` es opcional | `200`, `400`, `401`, `403`, `503` |
| `GET` | `/compras/{id}` | Obtiene una compra propia por su UUID | `200`, `400`, `401`, `403`, `404`, `503` |

### Ejemplo de compra

```bash
curl -i -X POST http://localhost:8003/compras \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Idempotency-Key: 6f1d2c1e-0000-4000-8000-000000000001" \
  -d '{"evento_id": "<uuid-del-evento>", "modalidad_id": "<uuid-de-la-modalidad-general>"}'
```

Repetir el mismo request con la misma `Idempotency-Key` y el mismo body devuelve `200` con la compra original, sin crear otra.

## Dependencias

- `events-service` valida que el evento exista, esté activo y que la modalidad elegida sea de tipo `general`. La consulta usa un timeout corto (`EVENTS_TIMEOUT_SECONDS`, 0.8 s por defecto).
- `identity-service` verifica la sesión vigente y provee los roles actuales mediante credenciales de servicio independientes.

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
curl -i -H "Authorization: Bearer $ACCESS_TOKEN" http://localhost:8003/compras
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
