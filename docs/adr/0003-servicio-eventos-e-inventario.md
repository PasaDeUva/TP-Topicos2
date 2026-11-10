# ADR-0003: Microservicio de Gestión de Eventos e Inventario

- Estado: Propuesto
- Fecha: 2026-11-10

## Contexto

El Trabajo Práctico Integrador de Tópicos II requiere la implementación del Bloque 2: Gestión de Eventos y Catálogo (`gestion-de-eventos`). En el sistema de Ticketera Virtual, la gestión de eventos, el catálogo público y el control estricto del inventario de entradas (asientos numerados y zonas generales) constituyen el núcleo operativo del negocio.

Se deben cumplir restricciones de arquitectura estrictas:
- Principio de autonomía por microservicio (*Database per Service*): prohibición explícita de compartir esquemas de base de datos entre microservicios o realizar acoplamiento temporal síncrono que bloquee disponibilidad.
- Prohibición de transacciones distribuidas en dos fases (2PC).
- Control de concurrencia riguroso que prevenga cualquier tipo de sobreventa de entradas.
- Regla de gobernanza de equipo: Pull Requests de tamaño acotado (~600 líneas de código de producción, excluyendo pruebas) con exactamente una especificación viva por PR.

## Decisión

1. **Autonomía y Base Dedicada:** Implementar el microservicio `backend/events-service/` con FastAPI, SQLAlchemy 2 (async), Pydantic v2 y Alembic, conectado exclusivamente a una instancia PostgreSQL 16 dedicada (`events_db`). Ningún otro servicio tiene acceso directo de lectura o escritura a esta base.
2. **Contratos REST Desacoplados para Compras:** Exponer operaciones atómicas de reserva (`POST /eventos/{id}/reservar`), confirmación (`POST /eventos/{id}/confirmar`) y liberación (`POST /eventos/{id}/liberar`) con expiración por TTL de 10 minutos. El Bloque 3 (Compras) interactúa únicamente mediante estas llamadas HTTP sin violar el límite del Bounded Context.
3. **Estrategia de Concurrencia:**
   - Para asientos numerados: Bloqueo pesimista `SELECT ... FOR UPDATE` sobre la fila del asiento dentro de la transacción y restricción `UNIQUE (evento_id, asiento_codigo)` a nivel de esquema.
   - Para zonas generales: Decremento atómico condicional mediante `UPDATE zonas SET cupo_disponible = cupo_disponible - :cantidad WHERE id = :id AND cupo_disponible >= :cantidad RETURNING id`. Si no retorna filas, se rechaza la transacción de inmediato con código HTTP 409 Conflict.
4. **Descomposición Incremental en 3 PRs:**
   - **PR-1 (`publicacion-eventos`):** Migración completa Alembic inicial (`0001_initial_schema.py`), modelos ORM, schemas, middleware HTTP de bitácora y endpoints de creación y edición del organizador (`POST /eventos`, `GET /eventos`, `GET /eventos/{id}`, `PUT /eventos/{id}`).
   - **PR-2 (`ciclo-de-vida-eventos`):** Transiciones de ciclo de vida (`publicar`, `pausar`, `despublicar`) y catálogo público (`/catalogo/eventos`, `/catalogo/eventos/{id}`) con cálculo dinámico de `venta_habilitada` y ocultamiento automático.
   - **PR-3 (`inventario-contratos`):** Contratos de reserva atómica, confirmación y liberación para Compras, tests de concurrencia y validación integral.
5. **Diferimiento del Frontend:** La interfaz de usuario (React) queda expresamente fuera de este change y será implementada en una Spec y PR posteriores para respetar el límite de líneas por PR.

## Consecuencias

### Positivas

- Aislamiento total del modelo de datos de eventos e inventario.
- Garantía matemática contra sobreventa en alta concurrencia mediante primitivas nativas de PostgreSQL.
- Cumplimiento de la gobernanza de PRs pequeños (~600 líneas) permitiendo revisiones ágiles y testeabilidad aislada.
- Trazabilidad y observabilidad garantizadas mediante el middleware de logs JSON con `duration_ms` y correlación de peticiones.

### Negativas

- Mayor número de entidades iniciales a persistir en la migración de Alembic.
- La expiración por TTL requiere que el servicio de eventos gestione limpiezas periódicas o validación en tiempo de lectura para reservas que no hayan sido confirmadas ni liberadas explícitamente.

## Alternativas consideradas

- **Base de datos compartida con Compras:** Descartada por violar el principio de *Database per Service* y acoplar los esquemas de persistencia.
- **Transacciones distribuidas (2PC):** Descartada por complejidad operativa, fragilidad de red y prohibición expresa de la cátedra.
- **Mega-PR con Backend y Frontend juntos:** Descartada porque superaría holgadamente las 1500 líneas de código, violando la regla de gobernanza de 600 líneas y dificultando el code review.
