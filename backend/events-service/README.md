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

### Autenticación y autorización con Identity

Las consultas del catálogo son públicas. Crear, editar y dar de baja eventos requiere un token Bearer con sesión vigente y rol organizador habilitado. El propietario se toma de la identidad autenticada; `owner_id` puede omitirse y, si se envía, debe coincidir con ella. La edición y baja se limitan a eventos propios y no permiten transferir su propiedad.

Para estas operaciones, el contrato distingue `401` para token ausente, inválido o revocado; `403` para rol insuficiente o identificador proporcionado distinto; `404` para recurso inexistente o ajeno; y `503` cuando Identity o la configuración necesaria no puedan verificarse. El servicio rechaza la operación ante fallas de verificación. Los clientes que antes escribían anónimamente deben enviar `Authorization: Bearer <access_token>`. Ver [ADR-0013](../../docs/adr/0013-identidad-en-eventos-y-compras.md).

#### Migración de clientes existentes

1. Obtenga un `access_token` de Identity para una cuenta con rol organizador habilitado y envíelo como Bearer en cada solicitud de creación, edición o baja.
2. Omita `owner_id` o envíe únicamente el identificador de la cuenta autenticada. Las consultas `GET` del catálogo siguen siendo públicas.
3. Maneje el rechazo de credenciales (`401`), permisos (`403`), recursos ajenos o inexistentes (`404`) e indisponibilidad de Identity (`503`).

La configuración de integración utiliza `IDENTITY_SERVICE_URL`, `IDENTITY_JWT_ISSUER`, `IDENTITY_JWT_AUDIENCE`, `IDENTITY_TIMEOUT_SECONDS` e `IDENTITY_EVENTS_SERVICE_TOKEN`. Compose monta la clave pública de Identity en `/keys/public/public.pem` sin acceso de escritura. Identity debe configurar la credencial `events` con `roles_read` y `sessions_read`; los secretos se suministran fuera del repositorio. Por defecto se exige HTTPS. Para desarrollo local o pruebas aisladas únicamente, `CONSUMER_ENV=local` e `IDENTITY_ALLOW_LOCAL_HTTP=true` habilitan HTTP a `identity-service` o loopback con credenciales de prueba.

En Compose, `IDENTITY_SERVICE_CREDENTIALS_JSON` configura las credenciales en Identity: la entrada `events` debe tener el mismo token que `IDENTITY_EVENTS_SERVICE_TOKEN` y ambos permisos habilitados. Los valores locales predeterminados de Identity solo permiten consultar roles; no habilitan la verificación de sesiones.

El verificador `python backend/events-service/scripts/verify_compose.py` ejecuta la integración aislada sin necesitar historial Git. Para incluir la prueba de reversión, agregue `--rollback-ref <revision>` con una revisión anterior disponible localmente; esa prueba verifica que las escrituras anónimas vuelven a estar habilitadas.

El workflow de CI ejecuta el mismo verificador en el paso `Test Identity, Events and Purchases end-to-end`, independiente de las pruebas unitarias. Usa Identity real y cubre autenticación, autorización, revocación de sesión y rol de organizador deshabilitado.

| Método | Ruta | Descripción | Códigos HTTP |
|---|---|---|---|
| `GET` | `/eventos` | Lista todos los eventos (ordenados por fecha de creación) | `200` |
| `GET` | `/eventos/{id}` | Obtiene el detalle de un evento por su UUID | `200`, `400` (UUID inválido), `404` |
| `POST` | `/eventos` | Da de alta un nuevo evento con sus modalidades | `201`, `400`, `401`, `403`, `503` |
| `PUT` | `/eventos/{id}` | Actualización completa con reemplazo total de modalidades | `200`, `400`, `401`, `403`, `404`, `503` |
| `DELETE` | `/eventos/{id}` | Baja lógica del evento (`activo = false`) | `200`, `400`, `401`, `403`, `404`, `503` |

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
