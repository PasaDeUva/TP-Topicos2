# ADR-0003: Microservicio de Gestión de Eventos e Inventario Mínimo

- Estado: Propuesto
- Fecha: 2026-11-11

## Contexto

El Trabajo Práctico Integrador de Tópicos II requiere la implementación del Bloque 2: Gestión de Eventos y Catálogo (`gestion-de-eventos`). En la reunión de equipo del 2026-11-11 se consensuó acotar el alcance inicial a lo indispensable para que el Bloque 3 (Compras) pueda vender tickets, garantizando no-sobreventa y consistencia en la concurrencia, sin sobrecargar la arquitectura con ciclos de vida complejos en la Etapa I.

## Decisión

1. **Autonomía y Base Dedicada:** Implementar el microservicio `backend/events-service/` con FastAPI, SQLAlchemy 2 (async), Pydantic v2 y Alembic, conectado a una base PostgreSQL 16 dedicada (`events_db`).
2. **Modelo Relacional Compacto:** Se reduce de 5 tablas a 3 tablas esenciales (`eventos`, `modalidades_stock`, `reservas`) utilizando identificadores UUID v4 autogenerados por el sistema.
3. **Superficie de API Mínima:**
   - `GET /eventos` y `GET /eventos/{id}`: Consulta de catálogo retornando eventos tanto con `activo: true` como con `activo: false`.
   - `POST /eventos`: Endpoint unificado de upsert (creación sin id, actualización con id) y baja lógica (`activo: false`).
   - Validación estricta en handlers retornando `400 Bad Request` con `{"detail": "invalid body"}` ante campos obligatorios faltantes.
   - Contratos para Compras: `POST /eventos/{id}/reservar` (reserva atómica con TTL de 10 minutos), `POST /eventos/{id}/reservas/{reserva_id}/confirmar` y `POST /eventos/{id}/reservas/{reserva_id}/liberar`.
4. **Estrategia de Concurrencia:** Bloqueo pesimista `SELECT ... FOR UPDATE` para asientos numerados y updates condicionales atómicos para zonas generales (`UPDATE ... WHERE cupo_disponible >= n RETURNING id`), impidiendo matemáticamente la sobreventa.
5. **Alcance Pospuesto para Etapas Posteriores:** Se documenta la postergación a Etapas II y III de: máquinas de 4 estados (pausado/despublicado), inicio programado de venta, y búsquedas multicriterio avanzadas.

## Consecuencias

### Positivas

- Reducción drástica del boilerplate y superficie de API (de 12 a solo 4 endpoints principales).
- Desbloqueo inmediato para el Bloque 3 (Compras) para comenzar el flujo de checkout y pago.
- Cumplimiento de la regla de PRs acotados: todo el backend se implementa en un único PR de ~450 líneas de código de producción.

### Negativas

- La baja lógica manual en `POST /eventos` traslada a los clientes la responsabilidad de interpretar el booleano `activo`.

## Alternativas consideradas

- **Máquina de estados completa en Etapa I:** Descartada por acuerdo de equipo para evitar sobre-ingeniería que comprometa los plazos de entrega.
- **Seeds automáticos en Docker:** Descartada; los datos de prueba se cargarán de forma transparente mediante llamadas al endpoint `POST /eventos` en pruebas integrales.
