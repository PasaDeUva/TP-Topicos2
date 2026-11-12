# ADR-0003: Microservicio de Gestión de Eventos — Catálogo Mínimo

- Estado: Propuesto
- Fecha: 2026-11-12
- Supersede: versión anterior que incluía reservas, TTL y control de concurrencia

## Contexto

La plataforma de ticketera virtual necesita un servicio central y autónomo que actúe como fuente de verdad del catálogo de eventos. El servicio permite consultar, dar de alta, editar y dar de baja eventos, junto con sus modalidades de entrada (numerada o general). La venta, las reservas y el control de stock quedan fuera de este alcance.

## Decisión

1. **Autonomía y Base Dedicada:** Implementar el microservicio `backend/events-service/` con FastAPI, SQLAlchemy 2 (async), Pydantic v2 y Alembic, conectado a una base PostgreSQL 16 dedicada (`events_db`).
2. **Modelo Relacional de 2 Tablas:** `eventos` y `modalidades`, con identificadores UUID v4 autogenerados. La tabla `modalidades` define únicamente la forma de venta admitida (`tipo`: `numerado` o `general`). No incluye precio ni capacidad: el precio varía por sector o asiento y la capacidad depende del tipo de modalidad; ambos atributos corresponden al change de asientos y stock para evitar doble fuente de verdad.
3. **Superficie de API de 5 Endpoints REST Canónicos:**
   - `GET /eventos`: listado completo del catálogo (activos e inactivos).
   - `GET /eventos/{id}`: detalle del evento con sus modalidades; 404 si no existe.
   - `POST /eventos`: alta de evento y modalidades; retorna 201 Created o 400 Bad Request.
   - `PUT /eventos/{id}`: reemplazo completo del evento y **todas** sus modalidades (las omitidas se eliminan); retorna 200, 400 o 404.
   - `DELETE /eventos/{id}`: baja lógica (`activo = false`); retorna 200 o 404.
4. **Validación Estricta:** `nombre` requerido, `tipo` ∈ {`numerado`, `general`}. Retornar `400 Bad Request` con `{"detail": "invalid body"}` ante cualquier violación.
5. **`owner_id` sin validación de identidad:** El campo viaja en el body para identificar al organizador. La autenticación real se delega a un change futuro de integración con el servicio de autenticación.
6. **Alcance Diferido:** Reservas atómicas, TTL, control de concurrencia, tabla `reservas`, precio, capacidad y mapa de asientos se implementarán en changes posteriores.

## Consecuencias

### Positivas

- Microservicio sin dependencias en tiempo de ejecución hacia otros servicios: puede desarrollarse, testearse y desplegarse de forma completamente autónoma.
- Superficie reducida (~300 líneas de código de producción) facilita la revisión de PR.
- El servicio de compras puede consultar el catálogo vía `GET /eventos` y `GET /eventos/{id}` desde el primer día.

### Negativas

- La baja lógica manual traslada a los consumidores la responsabilidad de interpretar el booleano `activo`.
- `owner_id` sin validación de identidad es una deuda técnica explícita hasta la integración del servicio de autenticación.

## Alternativas consideradas

- **Incluir precio y capacidad en `modalidades`:** Descartado. El precio varía por sector o asiento en las numeradas y la capacidad en numeradas surge del mapa de asientos; guardarlos aquí crearía doble fuente de verdad con el change de asientos y stock.
- **Incluir reservas y control de concurrencia en esta etapa:** Descartado. Excede el alcance mínimo viable del catálogo y agrega complejidad que no aporta valor hasta implementar el flujo de compras.
- **Endpoint unificado de upsert (`POST /eventos`):** Descartado. Reemplazado por los 5 endpoints REST canónicos para mayor claridad de contratos y semántica HTTP correcta.
- **Seeds automáticos en Docker:** Descartado; los datos de prueba se crean vía API en tests de integración.
