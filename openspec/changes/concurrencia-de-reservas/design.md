# Design

## Context

`events-service` incorpora la gestión funcional de inventario y reservas ([ADR-0007](../../../docs/adr/0007-modelo-inventario-asientos-y-tarifas.md)). Para cumplir con la directiva central de la cátedra de evitar sobreventa y garantizar que ningún ticket se venda dos veces bajo concurrencia real, se formaliza el diseño técnico de exclusión mutua y expiración por tiempo de vida ([ADR-0008](../../../docs/adr/0008-control-de-concurrencia-y-ttl-reservas.md)).
Ver [proposal.md](./proposal.md) y [specs/concurrencia-de-reservas/spec.md](./specs/concurrencia-de-reservas/spec.md).

## Goals / Non-Goals

**Goals:**
- Garantizar atomicidad estricta y aislamiento en reservas concurrentes de modalidades generales y numeradas.
- Evitar condiciones de carrera y sobreventa devolviendo `409 Conflict` de forma determinística al postor perdedor.
- Implementar expiración de reservas por TTL (`expira_en`) impidiendo la confirmación de reservas vencidas y liberando la disponibilidad remanente.

**Non-Goals:**
- Bloqueos distribuidos mediante Redis o sistemas externos (se prioriza el motor relacional PostgreSQL).
- Infraestructura de colas de espera masivas y buffers encolados (pertenecen a Etapa III - Colas de venta).
- Devoluciones y reembolsos posteriores a la confirmación de venta (Etapa III).

## Decisions

### 1. Atomicidad en modalidad numerada (Asientos)

Se implementa actualización condicional atómica a nivel de fila sobre PostgreSQL:

```python
stmt = (
    update(Asiento)
    .where(Asiento.id == payload.asiento_id, Asiento.estado == "libre")
    .values(estado="reservado")
)
result = await session.execute(stmt)
if result.rowcount == 0:
    raise HTTPException(status_code=409, detail="asiento no disponible")
```

**Justificación:**
- PostgreSQL garantiza atómicamente la evaluación del predicado `estado == 'libre'`. La primera transacción actualiza la fila; las transacciones competidoras observan `rowcount == 0` y son rechazadas inmediatamente sin deadlocks ni necesidad de reintentos ciegos.

**Alternativas consideradas:**
- *Bloqueo optimista con versión (`version_id`):* Descartado por requerir lógica de reintento en aplicación y generar excepciones de concurrencia innecesarias frente a la sentencia condicional directa.

### 2. Aislamiento en modalidad general (Cupos)

Para evitar que dos transacciones simultáneas lean cupo disponible > 0 e inserten reservas superando el total:

```python
modalidad = await session.scalar(
    select(Modalidad)
    .where(Modalidad.id == modalidad_id)
    .with_for_update()
)
# Conteo de reservas activas vigentes (no expiradas por TTL)
activas = await session.scalar(
    select(func.count(Reserva.id))
    .where(
        Reserva.modalidad_id == modalidad_id,
        Reserva.estado == "activa",
        Reserva.expira_en > func.now()
    )
)
if activas >= modalidad.cupo:
    raise HTTPException(status_code=409, detail="sin disponibilidad")
```

**Justificación:**
- `with_for_update()` sobre la fila específica de la modalidad serializa únicamente las operaciones de reserva para esa modalidad puntual durante la transacción (~5 ms), garantizando exactitud matemática del cupo sin afectar a otros eventos ni modalidades.

**Alternativas consideradas:**
- *Columna mutable de cupo decrementable en `modalidades`:* Descartado para mantener trazabilidad inmutable de reservas individuales creadas con su propio identificador.

### 3. Expiración por TTL (Time-To-Live)

- Cada reserva se crea con:
  `expira_en = datetime.now(timezone.utc) + timedelta(minutes=10)` (configurable vía variable de entorno `RESERVA_TTL_MINUTES`).
- En la consulta de disponibilidad (`GET .../disponibilidad`), se filtran únicamente reservas `estado = 'activa' AND expira_en > now()` o confirmadas.
- En la confirmación (`POST .../confirmar`), se valida:
  ```python
  if reserva.expira_en <= datetime.now(timezone.utc):
      reserva.estado = "liberada"
      if reserva.asiento:
          reserva.asiento.estado = "libre"
      await session.commit()
      raise HTTPException(status_code=409, detail="reserva expirada")
  ```

## Risks / Trade-offs

- **[Contención en la fila de modalidad para alta demanda en modalidad general]** → `with_for_update` serializa reservas concurrentes de la misma modalidad.
  *Mitigación:* La transacción solo realiza un conteo indexado y un insert; el tiempo de retención es mínimo. Para escenarios masivos (>1.000 req/s), la arquitectura prevé colas de venta en Etapa III.
- **[Reservas vencidas permanecen en estado 'activa' en disco hasta ser consultadas o confirmadas]** →
  *Mitigación:* La condición `expira_en > func.now()` en disponibilidad y confirmación asegura consistencia inmediata en tiempo real sin requerir cron jobs pesados.

## Migration Plan

1. Incorporar la columna `expira_en TIMESTAMPTZ NOT NULL` a la tabla `reservas`.
2. Reversión: eliminar columna `expira_en` si se aplica downgrade.
