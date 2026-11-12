# ADR-0003: Microservicio de Gestión de Eventos — Catálogo Mínimo

- Estado: Propuesto
- Fecha: 2026-11-12
- Supersede: versión anterior que incluía reservas, TTL y control de concurrencia

## Contexto

El Trabajo Práctico Integrador de Tópicos II requiere la implementación del Bloque 2: Gestión de Eventos y Catálogo (`gestion-de-eventos`). Tras la revisión de PR #7 se acotó el alcance a lo estrictamente necesario: un microservicio que actúa como fuente de verdad del catálogo de eventos para la plataforma de ticketera virtual. La venta, las reservas y el control de stock quedan fuera de esta etapa y serán responsabilidad del Bloque 3 (Compras).

## Decisión

1. **Autonomía y Base Dedicada:** Implementar el microservicio `backend/events-service/` con FastAPI, SQLAlchemy 2 (async), Pydantic v2 y Alembic, conectado a una base PostgreSQL 16 dedicada (`events_db`).
2. **Modelo Relacional de 2 Tablas:** `eventos` y `modalidades`, con identificadores UUID v4 autogenerados. Se elimina la tabla `reservas` y los campos de seguimiento de asientos individuales (`asiento_codigo`, `cupo_disponible`, `estado_asiento`). `tipo` en `modalidades` indica la modalidad de venta (`numerado` / `general`), no el estado de un asiento específico.
3. **Superficie de API de 5 Endpoints REST Canónicos:**
   - `GET /eventos`: listado completo del catálogo (activos e inactivos).
   - `GET /eventos/{id}`: detalle del evento con sus modalidades; 404 si no existe.
   - `POST /eventos`: alta de evento y modalidades; retorna 201 Created o 400 Bad Request.
   - `PUT /eventos/{id}`: reemplazo completo del evento y **todas** sus modalidades (las omitidas se eliminan); retorna 200, 400 o 404.
   - `DELETE /eventos/{id}`: baja lógica (`activo = false`); retorna 200 o 404.
4. **Validación Estricta:** `nombre` requerido, `precio >= 0`, `capacidad > 0`, `tipo` ∈ {`numerado`, `general`}. Retornar `400 Bad Request` con `{"detail": "invalid body"}` ante cualquier violación.
5. **`owner_id` sin validación de identidad:** El campo viaja en el body para identificar al organizador. La autenticación real se delega al Bloque 1 (Auth) en un change futuro.
6. **Alcance Diferido al Bloque 3 (Compras):** Reservas atómicas, TTL, `SELECT FOR UPDATE`, updates condicionales, tabla `reservas`, y control de sobreventa se implementarán en el Bloque 3. No forman parte del catálogo de eventos.

## Consecuencias

### Positivas

- Microservicio sin dependencias en tiempo de ejecución hacia otros bloques: puede desarrollarse, testearse y desplegarse de forma completamente autónoma.
- Superficie reducida (~300 líneas de código de producción) facilita la revisión y el cumplimiento del límite de PR acotados.
- El Bloque 3 (Compras) puede consultar el catálogo vía `GET /eventos` y `GET /eventos/{id}` desde el primer día.

### Negativas

- La baja lógica manual traslada a los consumidores la responsabilidad de interpretar el booleano `activo`.
- `owner_id` sin validación de identidad es una deuda técnica explícita hasta la integración del Bloque 1.

## Alternativas consideradas

- **Incluir reservas y control de concurrencia en esta etapa:** Descartado por revisión de PR. Excede el alcance mínimo viable y agrega complejidad que no aporta valor hasta que el Bloque 3 esté en desarrollo.
- **Endpoint unificado de upsert (`POST /eventos`):** Descartado. Reemplazado por los 5 endpoints REST canónicos para mayor claridad de contratos y semántica HTTP correcta.
- **Seeds automáticos en Docker:** Descartado; los datos de prueba se crean vía API en tests de integración.
