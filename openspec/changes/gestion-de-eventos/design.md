# Design: Gestión de Eventos y Catálogo Mínimo (`gestion-de-eventos`)

## Context

Esta propuesta acota el alcance al CRUD del catálogo de eventos y sus modalidades de entrada. Las reservas, el control de stock y la concurrencia quedan formalmente diferidos a etapas posteriores. Ver [proposal.md](./proposal.md) y [specs/gestion-de-eventos/spec.md](./specs/gestion-de-eventos/spec.md).

## Goals / Non-Goals

**Goals:**
- Microservicio autónomo `events-service` con base de datos PostgreSQL 16 dedicada (`events_db`).
- 5 endpoints REST canónicos para el catálogo de eventos (`GET`, `GET/{id}`, `POST`, `PUT/{id}`, `DELETE/{id}`).
- Modelo relacional de 2 tablas (`eventos`, `modalidades`) con UUIDs autogenerados.
- `modalidades` define únicamente la forma de venta admitida: `tipo` ∈ {`numerado`, `general`}. No incluye precio ni capacidad.
- Validación estricta en handlers: `400 Bad Request` con `{"detail": "invalid body"}` ante `nombre` faltante o `tipo` fuera del enum.
- `PUT /eventos/{id}` con semántica de reemplazo total: las modalidades no incluidas en el body son eliminadas.
- `DELETE /eventos/{id}` con baja lógica: `activo = false`, sin borrar el registro.
- Middleware de observabilidad HTTP con logs estructurados JSON (`duration_ms`, `X-Correlation-Id`).
- Implementación completa en un único Pull Request de ~300 líneas de código de producción.

**Non-Goals:**
- Precio y capacidad en `modalidades`: diferidos al change de asientos y stock. El precio varía por sector o asiento; la capacidad en numeradas surge del mapa de asientos y en generales es un cupo. Guardarlos aquí crearía dos fuentes de verdad.
- Reservas, confirmaciones y liberaciones de stock: diferidos a la etapa de compras/stock.
- Control de concurrencia (`SELECT FOR UPDATE`, updates atómicos): fuera de esta etapa.
- Mapa de asientos individuales: `tipo` indica la modalidad de venta, no el seguimiento de asientos específicos.
- Autenticación de organizador: `owner_id` viaja en el body; la validación de identidad se delega a un change futuro.
- Máquina de estados compleja (Borrador/Pausado/Despublicado): reemplazada por baja lógica `activo: false`.

## Decisions

### 1. Estructura del Servicio (`backend/events-service/`)
```
backend/events-service/
├── Dockerfile
├── pyproject.toml
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
│       └── 0001_initial_schema.py
├── app/
│   ├── main.py             # FastAPI app + middleware bitácora HTTP + exception handlers (400)
│   ├── config.py           # Settings y variables de entorno
│   ├── database.py         # Conexión SQLAlchemy async con PostgreSQL
│   ├── models.py           # Modelos ORM (eventos, modalidades)
│   ├── schemas.py          # DTOs Pydantic v2
│   └── routers.py          # Handlers de /eventos
└── tests/
    ├── conftest.py
    └── test_eventos.py     # Tests de alta, edición, baja lógica, consultas y validaciones 400
```

### 2. Modelo Relacional (2 Tablas)

```sql
CREATE TABLE eventos (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id    UUID NOT NULL,
    nombre      VARCHAR(255) NOT NULL,
    descripcion TEXT,
    venue       VARCHAR(255) NOT NULL,
    fecha       TIMESTAMPTZ NOT NULL,
    activo      BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE modalidades (
    id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    evento_id UUID NOT NULL REFERENCES eventos(id) ON DELETE CASCADE,
    nombre    VARCHAR(100) NOT NULL,
    tipo      VARCHAR(20) NOT NULL CHECK (tipo IN ('numerado', 'general'))
);
```

> `owner_id` identifica al organizador del evento. La autenticación real (validar que el token pertenece a ese `owner_id`) se incorporará en un change futuro.

> `tipo` representa la forma de venta admitida: `numerado` (asientos asignados) o `general` (acceso libre). Precio, capacidad y mapa de asientos corresponden al change de asientos y stock.

### 3. Contratos REST

| Endpoint | Método | Respuestas |
|---|---|---|
| `/eventos` | GET | 200 |
| `/eventos/{id}` | GET | 200, 404 |
| `/eventos` | POST | 201, 400 |
| `/eventos/{id}` | PUT | 200, 400, 404 |
| `/eventos/{id}` | DELETE | 200, 404 |

**Detalle de contratos:**

- **GET /eventos:** Retorna lista completa del catálogo incluyendo eventos con `activo: false`. Incluye modalidades anidadas.
- **GET /eventos/{id}:** Retorna detalle del evento y sus modalidades. 404 si el UUID no existe.
- **POST /eventos:** Crea evento y modalidades con UUIDs autogenerados. Retorna 201 Created con la entidad creada.
- **PUT /eventos/{id}:** Reemplaza completamente el evento y **todas** sus modalidades. Las modalidades no incluidas en el body son eliminadas. Retorna 200 OK con la entidad actualizada.
- **DELETE /eventos/{id}:** Aplica baja lógica (`activo = false`). El registro se preserva. Retorna 200 OK.

**Validación 400 Bad Request:** FastAPI interceptará `RequestValidationError` para retornar status `400` con cuerpo `{"detail": "invalid body"}` ante `nombre` faltante o `tipo` fuera de {`numerado`, `general`}.

## Risks / Trade-offs

- **[Trade-off: Reemplazo total en PUT]** La semántica de `PUT /eventos/{id}` elimina todas las modalidades y las recrea. Es la opción más simple y predecible dado que el catálogo de modalidades es pequeño y siempre se envía completo desde el organizador.
- **[Deuda técnica: owner_id sin validación]** El campo `owner_id` se acepta sin validar identidad hasta que se integre el change de autenticación. Ver ADR-0003.
