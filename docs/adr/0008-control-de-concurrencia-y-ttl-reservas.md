# ADR-0008: Control de concurrencia y expiración por TTL en reservas de inventario

- Estado: Propuesto
- Fecha: 2026-11-19

## Contexto

El trabajo práctico exige expresamente como desafío técnico central *"Garantizar que un ticket no se venda dos veces (idempotencia y control de concurrencia)"*.
En `events-service`, al recibir solicitudes de reserva concurrentes sobre una misma modalidad general o sobre un mismo asiento numerado, el sistema debe evitar sobreventa y condiciones de carrera sin degradar el rendimiento con bloqueos pesimistas innecesarios.
Asimismo, de acuerdo con [ADR-0006](0006-flujo-de-compra-completo.md), las reservas de entradas deben contar con un tiempo de vida (TTL) para que un abandono de compra no retenga asientos o cupos de manera indefinida.

## Decisión

1. **Control de concurrencia para modalidad general (cupos):**
   - Utilizar sentencias SQL atómicas condicionales basadas en el estado persistido.
   - La reserva de cupo ejecuta una sentencia atómica:
     `UPDATE modalidades SET ... WHERE id = :modalidad_id AND (cupo - subquery_reservas_activas) >= :cantidad`
     o verificación atómica en transacción serializable/row-level lock sobre la fila de modalidad en `events-service`. Si no se afecta ninguna fila o no hay disponibilidad remanente, se retorna inmediatamente `409 Conflict`.
2. **Control de concurrencia para modalidad numerada (asientos individuales):**
   - Actualización atómica con predicado de exclusión mutua:
     `UPDATE asientos SET estado = 'reservado' WHERE id = :asiento_id AND estado = 'libre'`
   - Si la sentencia afecta 0 filas, significa que otro proceso en competencia ya tomó el asiento, respondiendo `409 Conflict`.
   - Se descarta el uso de `SELECT ... FOR UPDATE` global o bloqueos a nivel de tabla para favorecer la escalabilidad en lecturas y reservas de distintos asientos.
3. **Mecanismo de expiración por TTL (Time-To-Live):**
   - Cada reserva se crea con una marca temporal `expira_en` calculada a partir de un TTL configurable (default: 10 minutos).
   - En las consultas de disponibilidad y al intentar confirmar o reservar, las reservas con `estado = 'activa'` y `expira_en < NOW()` se consideran vencidas automáticamente y son liberadas para reingresar al inventario disponible.

## Consecuencias

### Positivas

- Garantía estricta contra sobreventa y doble venta de tickets bajo alta concurrencia.
- La actualización atómica con condición (`UPDATE ... WHERE estado = 'libre'`) delega el aislamiento a nivel de fila al motor relacional de PostgreSQL sin locks globales.
- Las reservas abandonadas son recuperadas automáticamente gracias al TTL, impidiendo la denegación de inventario.

### Negativas

- Las consultas de disponibilidad deben computar o filtrar reservas vencidas por TTL si aún no fueron depuradas explícitamente en la base.
- Si el TTL es demasiado corto, clientes con latencia de pago podrían ver cancelada su reserva; si es demasiado largo, se bloquea inventario útil.

## Alternativas consideradas

- **Bloqueo pesimista (`SELECT ... FOR UPDATE`):** Descartado para la reserva general por generar contención innecesaria de transacciones en escenarios de alta demanda masiva.
- **Transacciones distribuidas (2PC):** Estrictamente prohibidas por las directivas de la cátedra ("materia oscura").
- **Proceso de fondo (cron/worker) para limpiar TTL:** Se complementa con verificación pasiva en el momento de consulta y mutación para evitar depender de tareas asíncronas no garantizadas en el entorno local mínimo.
