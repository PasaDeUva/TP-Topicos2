# Design: Gestión de Eventos y Catálogo Mínimo (`gestion-de-eventos`)

## Context

Tras la reunión de equipo del 2026-11-11, se redujo el diseño para enfocarse exclusivamente en lo indispensable para cumplir la Etapa I: permitir la venta de tickets garantizando unicidad y consistencia en la concurrencia, sin sobre-ingeniería en ciclos de vida. Ver [proposal.md](./proposal.md) y [specs/gestion-de-eventos/spec.md](./specs/gestion-de-eventos/spec.md).

## Goals / Non-Goals

**Goals:**
- Microservicio autónomo `events-service` con base de datos PostgreSQL 16 dedicada (`events_db`).
- Superficie mínima de API: 4 endpoints directos (`GET /eventos`, `GET /eventos/{id}`, `POST /eventos` para upsert/baja lógica, y operaciones de reserva para Compras).
- Manejo de UUIDs autogenerados para todas las entidades.
- Validación estricta en handlers: retornar `400 Bad Request` con `{"detail": "invalid body"}` ante cualquier campo obligatorio faltante.
- Garantizar no-sobreventa bajo concurrencia mediante `SELECT FOR UPDATE` (asientos numerados) y updates atómicos condicionales (zonas generales).
- Middleware de observabilidad HTTP con logs estructurados JSON (`duration_ms`, `X-Correlation-Id`).
- Implementación completa en un único Pull Request de ~450 líneas de código de producción.

**Non-Goals:**
- Máquina de estados compleja (Borrador/Pausado/Despublicado): reemplazada por baja lógica `activo: false`.
- Validación de inicio programado de venta (`fecha_inicio_venta`).
- Ocultamiento automático complejo de fechas; las fechas y el flag `activo` viajan en el payload de consulta.
- Interfaz gráfica React (diferida a spec/PR posterior).

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
│   ├── models.py           # Modelos ORM (eventos, modalidades_stock, reservas)
│   ├── schemas.py          # DTOs Pydantic v2
│   ├── services.py         # Lógica de dominio y concurrencia de reservas
│   └── routers.py          # Handlers de /eventos y /eventos/{id}/reservar...
└── tests/
    ├── conftest.py
    ├── test_eventos.py     # Tests de creación, edición, baja lógica y consultas
    └── test_reservas.py    # Tests de concurrencia, TTL y prevención de sobreventa
```

### 2. Modelo Relacional Simplificado (3 Tablas)

```sql
CREATE TABLE eventos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre VARCHAR(255) NOT NULL,
    descripcion TEXT,
    venue VARCHAR(255) NOT NULL,
    fecha TIMESTAMPTZ NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE modalidades_stock (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    evento_id UUID NOT NULL REFERENCES eventos(id) ON DELETE CASCADE,
    tipo VARCHAR(20) NOT NULL,           -- 'numerado' | 'general'
    nombre VARCHAR(100) NOT NULL,        -- 'Platea VIP', 'Campo'
    precio NUMERIC(10,2) NOT NULL,
    asiento_codigo VARCHAR(20),          -- 'A-1' (NULL si general)
    cupo_total INT,                      -- NULL si numerado
    cupo_disponible INT,                 -- NULL si numerado
    estado_asiento VARCHAR(20),          -- 'DISPONIBLE','RESERVADO','VENDIDO' (NULL si general)
    UNIQUE (evento_id, asiento_codigo)
);

CREATE TABLE reservas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    evento_id UUID NOT NULL REFERENCES eventos(id),
    modalidad_id UUID NOT NULL REFERENCES modalidades_stock(id),
    compra_id UUID NOT NULL,
    asiento_codigo VARCHAR(20),
    cantidad INT NOT NULL DEFAULT 1,
    estado VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE', -- 'PENDIENTE','CONFIRMADA','LIBERADA'
    expira_en TIMESTAMPTZ NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 3. Contratos REST y Manejo de Errores

- **Validación 400 Bad Request:** FastAPI interceptará `RequestValidationError` para devolver status code `400` y cuerpo `{"detail": "invalid body"}` si falta cualquier campo obligatorio (`nombre`, `venue`, `fecha`, o modalidades válidas con precio > 0).
- **GET /eventos:** Devuelve la lista completa de eventos incluyendo el valor booleano de `activo` (permite visualizar eventos activos e inactivos).
- **GET /eventos/{id}:** Devuelve el detalle del evento y modalidades con su atributo `activo`. Retorna 404 si el UUID no existe.
- **POST /eventos:**
  - Sin `id`: Crea evento nuevo y modalidades con UUIDs autogenerados. Retorna 201 Created.
  - Con `id`: Actualiza campos provistos. Retorna 200 OK.
  - Con `id` y `"activo": false`: Aplica baja lógica al evento. Retorna 200 OK.
- **POST /eventos/{id}/reservar:** Bloquea inventario con TTL de 10 min. Retorna 200 OK con `reserva_id` o 409 Conflict si no hay stock o el evento está inactivo (`activo: false`).
- **POST /eventos/{id}/reservas/{reserva_id}/confirmar:** Confirma reserva post-pago (`estado: CONFIRMADA`).
- **POST /eventos/{id}/reservas/{reserva_id}/liberar:** Libera reserva y restituye cupo/asiento (`estado: LIBERADA`).

### 4. Estrategia de Concurrencia
- **Asientos numerados:** Bloqueo pesimista `SELECT ... FOR UPDATE` sobre la fila correspondiente en `modalidades_stock`.
- **Zonas generales:** Update condicional atómico:
  ```sql
  UPDATE modalidades_stock
  SET cupo_disponible = cupo_disponible - :cantidad
  WHERE id = :modalidad_id AND cupo_disponible >= :cantidad
  RETURNING id;
  ```
  Si no retorna filas, no había cupo y se responde inmediatamente con 409 Conflict sin riesgo de sobreventa.

## Risks / Trade-offs

- **[Riesgo: Expiración de reservas sin llamada de Compras]** → **Mitigación:** Al momento de consultar disponibilidad o intentar reservar, las reservas en estado PENDIENTE con `expira_en < NOW()` se consideran expiradas y se reintegran de forma lazy.
