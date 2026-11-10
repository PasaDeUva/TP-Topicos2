# Design: Gestión de Eventos y Catálogo (`gestion-de-eventos`)

## Context

El proyecto actual cuenta con servicios mock iniciales (`mock-service` y `mock-app`) y gobernanza de CI/CD. Este diseño establece la arquitectura técnica, modelo relacional, contratos OpenAPI 3.1 y políticas de concurrencia para el microservicio `backend/events-service/`. Ver [proposal.md](./proposal.md) para la justificación de alcance y el directorio `specs/` para los requerimientos funcionales descompuestos en 3 capacidades normativas. Las decisiones estructurales se registran en [ADR-0003](../../../docs/adr/0003-servicio-eventos-e-inventario.md).

## Goals / Non-Goals

**Goals:**
- Implementar el microservicio `events-service` de forma completamente autónoma con su base PostgreSQL dedicada (`events_db`).
- Descomponer la entrega en 3 vertical slices orientados a Pull Requests de ~600 líneas de código de producción (sin tests):
  1. `publicacion-eventos` (PR-1)
  2. `ciclo-de-vida-y-catalogo` (PR-2)
  3. `inventario-y-contratos` (PR-3)
- Garantizar reserva atómica concurrente sin sobreventa mediante locking pesimista en asientos y updates atómicos en zonas generales.
- Exponer contratos REST OpenAPI 3.1 claros y desacoplados para Compras con TTL de 10 minutos.
- Integrar middleware HTTP que emita logs estructurados en JSON a stdout con medición de `duration_ms` y propagación de `X-Correlation-Id`.
- Establecer una suite de testing 100% pytest para ejecución en Docker Compose (`backend-tests` y local).

**Non-Goals:**
- Implementar las vistas en React (frontend diferido a una spec/PR posterior).
- Implementar validación criptográfica de JWT (en Etapa I se confía en headers `X-User-Id` y `X-User-Role`).
- Implementar bus asíncrono o broker de mensajería (fuera del alcance de la Etapa I).

## Decisions

### 1. Database per Service y Stack Tecnológico
- **Decisión:** Base de datos relacional PostgreSQL 16 dedicada (`events_db`), con FastAPI, SQLAlchemy 2 (async), Alembic y Pydantic v2.
- **Alternativas consideradas:** Compartir base con Compras o Auth (descartado por violar límites de Bounded Context de DDD y reglas de cátedra).

### 2. Estructura del Servicio (`backend/events-service/`)
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
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── dependencies.py
│   ├── middleware/
│   │   └── logging.py
│   ├── models/
│   │   ├── evento.py
│   │   ├── modalidad.py
│   │   ├── asiento.py
│   │   ├── zona.py
│   │   └── reserva.py
│   ├── schemas/
│   │   ├── evento.py
│   │   ├── modalidad.py
│   │   └── reserva.py
│   ├── services/
│   │   ├── eventos.py
│   │   └── inventario.py
│   └── routers/
│       ├── catalogo.py
│       ├── eventos.py
│       └── contratos.py
└── tests/
    ├── conftest.py
    ├── test_models.py
    ├── test_middleware.py
    ├── test_eventos_crud.py
    ├── test_ciclo_de_vida.py
    ├── test_catalogo.py
    └── test_concurrencia_inventario.py
```

### 3. Modelo de Datos Relacional (PostgreSQL)

```
eventos
  id UUID PK
  organizador_id UUID NOT NULL
  nombre VARCHAR(255) NOT NULL
  descripcion TEXT NOT NULL
  fecha_inicio TIMESTAMPTZ NOT NULL
  fecha_fin TIMESTAMPTZ NOT NULL
  venue TEXT NOT NULL
  estado VARCHAR(20) NOT NULL DEFAULT 'BORRADOR'
    CHECK (estado IN ('BORRADOR','PUBLICADO','PAUSADO','DESPUBLICADO'))
  fecha_inicio_venta TIMESTAMPTZ NULL
  tipo_evento VARCHAR(50) NULL
  participantes TEXT[] NULL
  creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
  actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now()

modalidades (1:N con eventos)
  id UUID PK
  evento_id UUID NOT NULL FK -> eventos(id) ON DELETE CASCADE
  nombre VARCHAR(100) NOT NULL
  tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('asiento_numerado', 'zona_general'))
  precio NUMERIC(10,2) NOT NULL CHECK (precio > 0)

asientos (solo para tipo 'asiento_numerado')
  id UUID PK
  modalidad_id UUID NOT NULL FK -> modalidades(id) ON DELETE CASCADE
  evento_id UUID NOT NULL FK -> eventos(id) ON DELETE CASCADE
  asiento_codigo VARCHAR(20) NOT NULL
  estado VARCHAR(20) NOT NULL DEFAULT 'DISPONIBLE'
    CHECK (estado IN ('DISPONIBLE', 'RESERVADO', 'VENDIDO'))
  UNIQUE (evento_id, asiento_codigo)

zonas (solo para tipo 'zona_general')
  id UUID PK
  modalidad_id UUID NOT NULL FK -> modalidades(id) ON DELETE CASCADE
  evento_id UUID NOT NULL FK -> eventos(id) ON DELETE CASCADE
  cupo_total INTEGER NOT NULL CHECK (cupo_total > 0)
  cupo_disponible INTEGER NOT NULL CHECK (cupo_disponible >= 0)

reservas
  id UUID PK
  evento_id UUID NOT NULL FK -> eventos(id)
  compra_id UUID NOT NULL
  tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('asiento_numerado', 'zona_general'))
  asiento_id UUID NULL FK -> asientos(id)
  zona_id UUID NULL FK -> zonas(id)
  cantidad INTEGER NOT NULL DEFAULT 1 CHECK (cantidad > 0)
  estado VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE'
    CHECK (estado IN ('PENDIENTE', 'CONFIRMADA', 'LIBERADA'))
  expira_en TIMESTAMPTZ NOT NULL
  creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
```

### 4. Superficie de API REST y Contratos OpenAPI 3.1

#### Catálogo Público (sin autenticación)
- `GET /catalogo/eventos`: Paginación y filtros (`fecha_desde`, `fecha_hasta`, `tipo_evento`). Oculta automáticamente eventos donde `fecha_fin < CURRENT_DATE`.
- `GET /catalogo/eventos/{id}`: Detalle del evento con cálculo dinámico `venta_habilitada = (fecha_inicio_venta IS NULL OR fecha_inicio_venta <= NOW())` y cupo disponible por modalidad en tiempo real.

#### Gestión del Organizador (requiere `X-User-Id` y `X-User-Role: organizador`)
- `POST /eventos`: Crea evento en estado `BORRADOR`. Retorna 201.
- `GET /eventos`: Lista eventos creados por el organizador en cualquier estado.
- `GET /eventos/{id}`: Detalle de evento propio (403 si pertenece a otro organizador).
- `PUT /eventos/{id}`: Edición de campos. Válido en `BORRADOR`. Retorna 409 si ya está publicado o si intenta cambiar precios/cupos de modalidades con compras.
- `POST /eventos/{id}/publicar`: Valida completitud y cambia a `PUBLICADO`.
- `POST /eventos/{id}/pausar`: Suspende la venta cambiando a `PAUSADO`.
- `POST /eventos/{id}/despublicar`: Pasa a `BORRADOR` si no hubo ventas, o a `DESPUBLICADO` si existen ventas previas.

#### Contratos para Bloque 3 (Compras)
- `POST /eventos/{id}/reservar`:
  ```json
  { "tipo": "zona_general", "zona_id": "uuid", "cantidad": 2, "compra_id": "uuid" }
  ```
  o
  ```json
  { "tipo": "asiento_numerado", "asiento_id": "uuid", "compra_id": "uuid" }
  ```
  Retorna 200 con `reserva_id`, `estado: PENDIENTE` y `expira_en: NOW() + 10 MIN`. Retorna 409 si no hay cupo o venta no habilitada.
- `POST /eventos/{id}/confirmar`:
  ```json
  { "reserva_id": "uuid", "compra_id": "uuid" }
  ```
  Valida que la reserva esté en `PENDIENTE` y `expira_en > NOW()`. Pasa el estado a `CONFIRMADA` y marca el stock como vendido definitivamente.
- `POST /eventos/{id}/liberar`:
  ```json
  { "reserva_id": "uuid" }
  ```
  Pasa reserva a `LIBERADA` y reincorpora el cupo o libera el asiento.

### 5. Estrategia de Concurrencia
- **Asientos Numerados:** Bloqueo pesimista `SELECT ... FOR UPDATE` sobre la fila del asiento dentro de la transacción de reserva.
- **Zonas Generales:** Actualización atómica condicional:
  ```sql
  UPDATE zonas
  SET cupo_disponible = cupo_disponible - :cantidad
  WHERE id = :zona_id AND cupo_disponible >= :cantidad
  RETURNING id;
  ```
  Si no retorna filas, no hubo cupo suficiente y se dispara 409 Conflict de inmediato sin condiciones de carrera.

### 6. Descomposición de la Entrega en 3 Specs / PRs (~600 líneas c/u)
1. **PR-1 (`publicacion-eventos`):** Migración completa Alembic inicial (`0001_initial_schema.py`), modelos ORM, schemas Pydantic, middleware HTTP de bitácora, configuración en Docker Compose y endpoints de gestión del organizador (`POST /eventos`, `GET /eventos`, `GET /eventos/{id}`, `PUT /eventos/{id}`) + suite de tests unitarios e integración.
2. **PR-2 (`ciclo-de-vida-y-catalogo`):** Transiciones de estado (`publicar`, `pausar`, `despublicar`), validación de completitud, endpoints de catálogo público (`/catalogo/eventos`, `/catalogo/eventos/{id}`) con ocultamiento automático y cálculo de `venta_habilitada` + tests de integración.
3. **PR-3 (`inventario-y-contratos`):** Contratos REST de reserva, confirmación y liberación para Compras, control de concurrencia y expiración por TTL (10 min) + tests de concurrencia y sobreventa.

## Testing Strategy

- **Entorno de ejecución:** Tests ejecutados 100% bajo Docker Compose con una base de datos PostgreSQL real y aislada, garantizando paridad absoluta con producción.
- **Estrategia por PR:**
  - **PR-1:** Tests unitarios de validación de modelos y serializadores Pydantic; tests de middleware HTTP (formato JSON de log y propagación de `X-Correlation-Id`); tests de integración para creación y edición de borradores (`conftest.py` con cliente `httpx.AsyncClient`).
  - **PR-2:** Tests de transiciones de ciclo de vida (verificación de rechazo por datos incompletos en `/publicar`, bloqueo de edición al publicar); tests de catálogo público (ocultamiento automático de fechas pasadas, filtros multicriterio y paginación).
  - **PR-3:** Tests de concurrencia y no-sobreventa mediante llamadas simultáneas (`asyncio.gather` / threads) sobre un mismo asiento (verificando exactamente un 200 y el resto 409) y sobrecupo en zonas generales; tests de ciclo de vida de reserva (confirmación en término vs. rechazo post-TTL y liberación atómica).

## Risks / Trade-offs

- **[Riesgo: Reservas pendientes que expiran sin que Compras llame a liberar]** → **Mitigación:** Al consultar stock o intentar reservar, las reservas expiradas son filtradas y se implementará un barrido periódico o lazy de expiración.
- **[Riesgo: Contención en reservas de alta concurrencia en la misma zona general]** → **Mitigación:** La query `UPDATE ... WHERE cupo_disponible >= n RETURNING` delega el locking a nivel de fila en PostgreSQL, garantizando transacciones ultracortas.
- **[Riesgo: Exceder el límite de ~600 líneas por PR]** → **Mitigación:** Modularización estricta por vertical slices y postergación deliberada del frontend a un change separado.
