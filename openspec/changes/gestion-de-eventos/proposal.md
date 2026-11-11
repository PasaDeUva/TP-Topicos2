# Proposal: Gestión de Eventos y Catálogo Mínimo (`gestion-de-eventos`)

## Why

El sistema de Ticketera Virtual necesita un servicio central y autónomo para persistir eventos y gestionar el stock de entradas (asientos numerados y zonas generales), permitiendo que el Bloque 3 (Compras) pueda consultar disponibilidad y reservar tickets de forma atómica.

Tras la revisión de alcance con el equipo (2026-11-11), esta propuesta acota el alcance a lo estrictamente indispensable para cumplir los requerimientos de la Etapa I del TP, evitando sobre-ingeniería en ciclos de vida complejos.

## What Changes

- Creación del microservicio `backend/events-service/` con FastAPI, Pydantic v2, SQLAlchemy 2, Alembic y PostgreSQL dedicado (`events_db`).
- Superficie de API compacta:
  - `GET /eventos` y `GET /eventos/{id}`: consulta de eventos y stock (retorna entidades tanto activas como inactivas).
  - `POST /eventos`: endpoint unificado de upsert (creación sin id, actualización con id) y baja lógica (`activo: false`). Validación estricta con `400 Bad Request` ante campos faltantes.
  - `POST /eventos/{id}/reservar`: reserva atómica con TTL de 10 minutos para Compras con prevención de sobreventa.
  - `POST /eventos/{id}/reservas/{reserva_id}/confirmar` y `liberar`: confirmación post-pago y restitución de inventario.
- Modelo relacional simplificado en 3 tablas (`eventos`, `modalidades_stock`, `reservas`) con identificadores UUID autogenerados.
- Middleware HTTP de bitácora que emite logs JSON estructurados a stdout (`method`, `path`, `status_code`, `duration_ms`, `X-Correlation-Id`).
- La implementación completa se empaqueta en un único Pull Request de ~450 líneas de código de producción.

## Ideas Descartadas / Pospuestas para Etapa II y III

En acuerdo con el equipo, las siguientes funcionalidades quedan formalmente fuera del alcance de la Etapa I:
- **Máquina de estados compleja (Borrador / Pausado / Despublicado):** Pospuesta; reemplazada por baja lógica mediante flag `activo: false`.
- **Venta programada (`fecha_inicio_venta`):** Descartada para Etapa I; los eventos creados admiten reservas de inmediato si están activos.
- **Ocultamiento automático por fecha:** Descartado para simplificar los contratos de consulta; el estado `activo` y las fechas viajan en el payload para interpretación del consumidor.
- **Búsqueda multicriterio avanzada (participantes, géneros):** Pospuesta formalmente a la Etapa III según el cronograma del TP.
- **Endpoints separados de creación y edición (POST vs PUT):** Unificado en `POST /eventos`.
- **Precarga / Seed automático:** Descartado; la creación de eventos de prueba se realiza vía API en pruebas de integración.

## Capabilities

### New Capabilities

- `gestion-de-eventos`: Gestión integral de eventos (upsert y baja lógica), consulta pública de catálogo y contratos de reserva/confirmación/liberación atómica de inventario con TTL de 10 minutos.

### Modified Capabilities

*(Ninguna).*

## Impact

- **Nuevas APIs:** Endpoints bajo `/eventos` para consulta, gestión de organizador y contratos de inventario para Compras.
- **Base de datos:** Instancia dedicada PostgreSQL (`events_db`) con tablas `eventos`, `modalidades_stock` y `reservas`.
- **Testing:** 100% pytest en Docker Compose cubriendo validaciones 400 Bad Request, concurrencia en reservas y ciclo de reserva/confirmación.
