# ADR-0008: Control de concurrencia y expiración por TTL en reservas de inventario

- Estado: Aceptado
- Fecha: 2026-11-19

## Contexto

El trabajo práctico exige expresamente como desafío técnico central *"Garantizar que un ticket no se venda dos veces (idempotencia y control de concurrencia)"*.
En `events-service`, al recibir solicitudes de reserva concurrentes sobre una misma modalidad general o sobre un mismo asiento numerado, el sistema debe evitar sobreventa y condiciones de carrera sin degradar el rendimiento con bloqueos pesimistas innecesarios.
Asimismo, de acuerdo con [ADR-0006](0006-flujo-de-compra-completo.md), las reservas de entradas deben contar con un tiempo de vida (TTL) para que un abandono de compra no retenga asientos o cupos de manera indefinida.

## Decisión

1. **Control de concurrencia para modalidad general (cupos):**
   - Se fija la estrategia de serialización por fila mediante `SELECT id, cupo FROM modalidades WHERE id = :modalidad_id FOR UPDATE`.
   - Se computa atómicamente la ocupación vigente:
     `COUNT(id) FROM reservas WHERE modalidad_id = :modalidad_id AND estado IN ('activa', 'confirmada') AND (estado = 'confirmada' OR expira_en > NOW())`.
   - Si `ocupadas >= cupo`, se aborta la transacción y se retorna inmediatamente `409 Conflict`. Caso contrario, se inserta la nueva reserva activa dentro de la misma transacción.
   - El lock a nivel de fila se retiene únicamente durante los milisegundos de la transacción de reserva de esa modalidad específica, sin contención sobre otros eventos ni modalidades.

2. **Control de concurrencia para modalidad numerada (asientos individuales) y liberación perezosa:**
   - Previo a la asignación o al computar disponibilidad, se ejecuta una liberación perezosa (lazy cleanup) dentro de la transacción:
     `UPDATE reservas SET estado = 'liberada' WHERE modalidad_id = :mid AND estado = 'activa' AND expira_en <= NOW()`
     restituyendo a su vez `asientos.estado = 'libre'` para los asientos asociados a esas reservas caducadas.
   - La reserva efectiva se ejecuta con la sentencia atómica condicional:
     `UPDATE asientos SET estado = 'reservado' WHERE id = :asiento_id AND estado = 'libre'`
   - Si la sentencia afecta 0 filas, se responde `409 Conflict`.

3. **Mecanismo de expiración por TTL (Time-To-Live):**
   - Cada reserva se crea con `expira_en = NOW() + interval '10 minutes'` (configurable vía `RESERVA_TTL_MINUTES`).
   - En las consultas de disponibilidad y confirmación:
     - Disponibilidad contabiliza como libres los asientos que ya están `libre` o cuya reserva activa haya expirado.
     - `POST .../confirmar` valida `expira_en > NOW()`. Si ya venció, se transiciona a `liberada` (restituyendo el asiento a `libre`) y se rechaza con `409 Conflict`.
     - Si la reserva ya se encontraba `confirmada`, se retorna `200 OK` garantizando idempotencia. Si se encontraba `liberada`, se rechaza con `409 Conflict`.

## Consecuencias

### Positivas

- Garantía estricta contra sobreventa y doble venta de tickets bajo alta concurrencia tanto en ventas preliminares como post-confirmación.
- Los asientos y cupos retenidos por reservas abandonadas vuelven al inventario disponible de forma determinística mediante liberación perezosa.
- Comportamiento idempotente y seguro ante reintentos de confirmación y compensación.

### Negativas

- El lock `FOR UPDATE` serializa reservas concurrentes de la misma modalidad general (mitigado porque la transacción solo ejecuta un count indexado y un insert rápido).
- La liberación perezosa traslada la recuperación de asientos al momento de las consultas o intentos de reserva, requiriendo transacciones de escritura breves en operaciones de inventario.

## Alternativas consideradas

- **Columna mutable de cupo decrementable en `modalidades`:** Descartado para mantener trazabilidad histórica inmutable de cada reserva creada con su propio identificador y TTL.
- **Worker / Cron asíncrono desacoplado para TTL:** Se complementa con la liberación perezosa sincrónica para no depender de infraestructura externa de scheduling en el despliegue local mínimo.
- **Transacciones distribuidas (2PC):** Estrictamente prohibidas por las directivas de la cátedra ("materia oscura").
