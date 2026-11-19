# Design

## Context

`events-service` es la fuente de verdad del catálogo y expone `GET /eventos/{id}` con el evento, su flag `activo` y sus modalidades (`id`, `nombre`, `tipo`). No guarda precio ni capacidad ([ADR-0003](../../../docs/adr/0003-servicio-eventos-e-inventario.md)). `compras-service` se construye con el mismo stack y estructura que Eventos y se ejecuta con Docker Compose. Ver [proposal.md](./proposal.md) y [specs/gestion-de-compras/spec.md](./specs/gestion-de-compras/spec.md).

## Goals / Non-Goals

**Goals:**
- Microservicio autónomo `compras-service` con base `compras_db` dedicada y despliegue independiente.
- Tres endpoints REST: `POST /compras`, `GET /compras/{id}` y `GET /compras?cliente_id=`.
- Registro idempotente que tolere reintentos y solicitudes concurrentes con la misma clave.
- Tests que corran sin `events-service`, simulando su respuesta HTTP.

**Non-Goals:**
- Cupos, stock, montos, pagos, entradas numeradas, devoluciones y colas (ver "Fuera de alcance" en el proposal).
- Integración con `payment-service` y estados de la compra (reserva, pago, confirmación): ver "Flujo objetivo" en el proposal.
- Compra de varios tickets en una misma compra (entradas generales por cantidad o entradas numeradas por asiento), con un límite X por compra.
- Copiar o cachear datos del catálogo dentro de Compras.
- Autenticar al cliente: `cliente_id` viaja en el body como dato temporal.
- Reintentos automáticos o circuit breaker hacia Eventos.

## Decisions

### 1. Estructura del servicio

Réplica de `events-service`, sin duplicar lógica de dominio:

```
backend/compras-service/
├── Dockerfile
├── entrypoint.sh              # alembic upgrade head + exec
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt       # lo usa backend-tests
├── alembic.ini
├── alembic/versions/0001_initial_schema.py
├── scripts/init-test-db.sql   # CREATE DATABASE compras_test
├── app/
│   ├── main.py                # bitácora HTTP + handlers de error (400)
│   ├── config.py              # database_url, events_service_url, events_timeout_seconds
│   ├── database.py
│   ├── models.py              # Compra
│   ├── schemas.py             # CompraIn, CompraOut
│   ├── events_client.py       # cliente HTTP hacia events-service
│   └── routers.py             # /compras
└── tests/
    ├── conftest.py
    └── test_compras.py
```

### 2. Modelo de datos

Una sola tabla, sin copiar datos del catálogo:

```sql
CREATE TABLE compras (
    id               UUID PRIMARY KEY,
    cliente_id       UUID NOT NULL,
    evento_id        UUID NOT NULL,
    modalidad_id     UUID NOT NULL,
    idempotency_key  VARCHAR(255) NOT NULL,
    creado_en        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (cliente_id, idempotency_key)
);
CREATE INDEX ix_compras_cliente_creado ON compras (cliente_id, creado_en DESC);
```

`evento_id` y `modalidad_id` no son claves foráneas: pertenecen a otra base. Compras guarda solo los identificadores ([ADR-0005](../../../docs/adr/0005-compras-consulta-eventos-e-idempotencia.md)).

`CompraOut` no expone `idempotency_key`.

### 3. Flujo de `POST /compras`

1. FastAPI valida el body (`cliente_id`, `evento_id`, `modalidad_id` como UUID) y la cabecera `Idempotency-Key` (no vacía, hasta 255 caracteres). Cualquier fallo responde `400 {"detail": "invalid body"}`.
2. Busca una compra con `(cliente_id, idempotency_key)`. Si existe: con el mismo `evento_id` y `modalidad_id` responde `200` con la compra original; con otros valores responde `409`. No consulta a Eventos en este camino, de modo que un reintento sigue funcionando aunque Eventos caiga o el evento se dé de baja después.
3. Si no existe, consulta `GET /eventos/{evento_id}` en Eventos. `404` → `404`; error de red, timeout o `5xx` → `503`.
4. Busca la modalidad entre `modalidades` del evento (`404` si no está). Si `activo` es falso o `tipo != "general"` responde `409`.
5. Inserta la compra y responde `201`.

**Concurrencia:** dos solicitudes con la misma clave pueden pasar el paso 2 a la vez. La restricción `UNIQUE (cliente_id, idempotency_key)` garantiza que solo una inserte. La otra captura `IntegrityError`, hace `rollback`, relee la compra y aplica la misma comparación del paso 2. No hay bloqueos de fila ni transacciones largas.

**Alternativa descartada:** bloquear por clave con un lock explícito (`SELECT ... FOR UPDATE` o advisory lock). La restricción única da la misma garantía con menos código y sin bloquear lecturas.

### 4. Cliente de Eventos

`events_client.py` expone `EventsClient.obtener_evento(evento_id, correlation_id)` sobre `httpx.AsyncClient` con la URL base `EVENTS_SERVICE_URL` (en Compose, `http://events-service:8000`) y un timeout corto configurable. Reenvía `X-Correlation-Id`. Devuelve el evento, `None` ante `404`, o lanza una excepción propia que el router traduce a `503`.

Se inyecta con `Depends(get_events_client)`. Los tests unitarios lo sustituyen con `app.dependency_overrides` por un cliente con `httpx.MockTransport`, sin agregar dependencias de test.

### 5. Contratos REST

| Endpoint | Método | Respuestas |
|---|---|---|
| `/compras` | POST | 200 (reintento), 201, 400, 404, 409, 503 |
| `/compras/{id}` | GET | 200, 400, 404 |
| `/compras?cliente_id=` | GET | 200, 400 |

El handler de `RequestValidationError` replica el de Eventos: `400` con `{"detail": "invalid path parameter"}` para errores de path y `{"detail": "invalid body"}` para el resto, incluidos query y cabecera.

### 6. Infraestructura

- `compose.yaml`: `compras-db` (PostgreSQL 16, puerto `5436:5432`, volumen propio, script de init con `compras_test`) y `compras-service` (puerto `8003:8000`, `EVENTS_SERVICE_URL`, `depends_on` de `compras-db` saludable y de `events-service`).
- `backend-tests` recibe `COMPRAS_TEST_DATABASE_URL`, porque `TEST_DATABASE_URL` ya apunta a la base de Eventos. El `conftest.py` de Compras rechaza correr contra `compras_db`, igual que el de Eventos.
- CI: agregar `compras-db`, `alembic upgrade head`, `alembic check` y `ruff check compras-service`.
- Documentación: filas de `compras-service` en `backend/README.md` y `docs/local-development.md`, más un `README.md` propio del servicio.

## Risks / Trade-offs

- **[Compras depende de la disponibilidad de Eventos]** → Responde `503` sin registrar nada; los reintentos con la misma clave son seguros. Los reintentos ya registrados no consultan a Eventos.
- **[Evento dado de baja después de la compra]** → Compras no se entera; la compra queda registrada. Se resolverá con el change de stock o con eventos asíncronos.
- **[`cliente_id` sin autenticar]** → Cualquiera puede registrar o listar compras de otro cliente. Deuda explícita hasta integrar Identity ([ADR-0004](../../../docs/adr/0004-autenticacion-entre-servicios.md)).
- **[Sin cantidad ni monto]** → Una compra es solo la elección de evento y modalidad; no reserva ni cobra nada. El modelo se ampliará con el change de asientos, stock y pagos mediante migraciones, incluida la cantidad de tickets (modalidad general) o los asientos (modalidad numerada) de una misma compra, hasta un límite X.
- **[Compra sin estado]** → Hoy una compra registrada es definitiva. Cuando exista el flujo reserva → pago → confirmación, se agregará un campo de estado a `compras` por migración; las compras de esta etapa se tratarán como ya confirmadas.
- **[Una compra distinta del mismo cliente para el mismo evento]** → Se permite con otra clave: sin cupos no hay regla de unicidad por persona.

## Migration Plan

Servicio y base nuevos: no hay datos previos ni cambios en Eventos. El despliegue ejecuta `alembic upgrade head` en el `entrypoint.sh`. La reversión consiste en retirar el servicio y su volumen.
