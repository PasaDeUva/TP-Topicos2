# Proposal: Gestión de Eventos y Catálogo (`gestion-de-eventos`)

## Why

El sistema de Ticketera Virtual carece de un servicio central y autónomo para gestionar el ciclo de vida de los eventos y su inventario de entradas. Esta propuesta introduce el microservicio `events-service` (Bloque 2) como único propietario del catálogo, estados de eventos y stock (asientos numerados y zonas generales), permitiendo la interacción desacoplada con el Bloque 1 (Auth) y el Bloque 3 (Compras).

## What Changes

- Creación del nuevo microservicio backend `backend/events-service/` con FastAPI, Pydantic v2, SQLAlchemy 2, Alembic y PostgreSQL dedicado (`events_db`).
- Exposición de endpoints para catálogo público, ciclo de vida del organizador/administrador y contratos de reserva/confirmación/liberación de inventario con TTL de 10 minutos para Compras.
- Inclusión del middleware de bitácora HTTP para emitir logs JSON estructurados a stdout (`method`, `path`, `status_code`, `duration_ms`, `X-Correlation-Id`).
- Configuración del servicio y base de datos dedicada en `compose.yaml`.
- Especificación formal dividida en 3 capacidades/specs vivas independientes, diseñadas para que la implementación posterior se ejecute en 3 Pull Requests secuenciales de ~600 líneas de código de producción cada uno (sin contar tests unitarios ni integración).
- Frontend diferido a una spec/PR complementario posterior.

## Capabilities

### New Capabilities

- `publicacion-eventos`: Gestión inicial de eventos en borrador, modelo de persistencia relacional con Alembic, middleware de observabilidad HTTP y operaciones del organizador (Base de PR-1 de implementación).
- `ciclo-de-vida-y-catalogo`: Transiciones de estado del evento (publicación explícita con validación, pausa, despublicación) y endpoints del catálogo público con ocultamiento automático y cálculo en tiempo real de disponibilidad (Base de PR-2 de implementación).
- `inventario-y-contratos`: Contratos de reserva atómica (TTL 10 min), confirmación definitiva y liberación de stock expuestos para Compras, con garantías de no-sobreventa bajo concurrencia (Base de PR-3 de implementación).

### Modified Capabilities

*(Ninguna. Las capacidades previas `local-environment` y `contribution-governance` no sufren cambios en sus requerimientos normativos).*

## Impact

- **Nuevas APIs:** Endpoints REST bajo `/catalogo/eventos` (público), `/eventos` (organizador) y contratos de inventario `/eventos/{id}/reservar|confirmar|liberar`.
- **Base de datos:** Instancia dedicada PostgreSQL (`events_db`) con tablas `eventos`, `modalidades`, `asientos`, `zonas`, `reservas`.
- **Infraestructura:** Agregado de `events-db` y `events-service` a `compose.yaml`.
- **Estrategia de Testing:** Tests unitarios e integración 100% pytest ejecutados en Docker Compose, cubriendo validaciones de schema, middleware, concurrencia en PostgreSQL y transiciones de estado.
- **Otros Bloques:** Bloque 1 interactúa únicamente por propagación de headers HTTP (`X-User-Id`, `X-User-Role`); Bloque 3 consumirá los contratos REST sin compartir base de datos.
