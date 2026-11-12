# Proposal: Gestión de Eventos y Catálogo Mínimo (`gestion-de-eventos`)

## Why

Se quiere desarrollar un microservicio de gestión de eventos que permita consultar, dar de alta, editar y dar de baja eventos, junto con sus modalidades de entrada (numerada o general). El servicio es la fuente de verdad del catálogo de eventos para la plataforma de ticketera virtual. La venta, las reservas y el control de stock quedan fuera de esta etapa.

## What Changes

- Creación del microservicio `backend/events-service/` con FastAPI, Pydantic v2, SQLAlchemy 2, Alembic y PostgreSQL dedicado (`events_db`).
- Superficie de API REST canónica de 5 endpoints:
  - `GET /eventos`: listado completo del catálogo (activos e inactivos).
  - `GET /eventos/{id}`: detalle de un evento con sus modalidades. Retorna 404 si no existe.
  - `POST /eventos`: alta de evento con sus modalidades. Retorna 201 Created o 400 Bad Request.
  - `PUT /eventos/{id}`: reemplazo completo del evento y sus modalidades. Retorna 200 OK, 400 o 404.
  - `DELETE /eventos/{id}`: baja lógica (`activo = false`). Retorna 200 OK o 404.
- Modelo relacional de 2 tablas (`eventos`, `modalidades`) con identificadores UUID autogenerados. La entidad `modalidades` define la forma de venta admitida (`numerado` o `general`); no incluye precio ni capacidad.
- Middleware HTTP de bitácora que emite logs JSON estructurados a stdout (`method`, `path`, `status_code`, `duration_ms`, `X-Correlation-Id`).
- La implementación completa se empaqueta en un único Pull Request de ~300 líneas de código de producción.

## Ideas Descartadas / Pospuestas

- **Máquina de estados compleja (Borrador / Pausado / Despublicado):** Reemplazada por baja lógica mediante flag `activo: false`.
- **Venta programada (`fecha_inicio_venta`):** Descartada para esta etapa.
- **Ocultamiento automático por fecha:** Descartado; el flag `activo` y las fechas viajan en el payload para interpretación del consumidor.
- **Búsqueda multicriterio avanzada:** Pospuesta a etapas posteriores.
- **Endpoint unificado de upsert (`POST /eventos`):** Reemplazado por los 5 endpoints REST canónicos.
- **Precios y capacidad en modalidades:** Pospuestos al change de asientos y stock. El precio varía por sector o asiento (en numeradas un precio por modalidad no es un dato correcto), y la capacidad depende del tipo (en numeradas surge del mapa de asientos y en generales es un cupo). Guardarlos en este modelo crearía dos fuentes de verdad y acoplaría reglas de negocio prematuramente.
- **Reservas, stock y control de concurrencia (TTL, `SELECT FOR UPDATE`, `reservas`):** Pospuestos formalmente a la etapa de compras/stock. No forman parte del catálogo de eventos.
- **Precarga / Seed automático:** Descartado; los datos de prueba se crean vía API en tests de integración.

## Capabilities

### New Capabilities

- `gestion-de-eventos`: CRUD de eventos y sus modalidades de entrada (numerada o general). El servicio actúa como fuente de verdad del catálogo para la plataforma.

### Modified Capabilities

*(Ninguna).*

## Impact

- **Nuevas APIs:** 5 endpoints REST bajo `/eventos` para consulta y gestión del catálogo.
- **Base de datos:** Instancia dedicada PostgreSQL (`events_db`) con 2 tablas: `eventos` y `modalidades`.
- **Testing:** 100% pytest en Docker Compose cubriendo altas, ediciones, bajas lógicas, validaciones 400 Bad Request y consultas.
