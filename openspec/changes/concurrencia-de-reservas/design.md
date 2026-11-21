# Design

## Context

`events-service` incorpora la gestión funcional de inventario y reservas ([ADR-0007](../../../docs/adr/0007-modelo-inventario-asientos-y-tarifas.md)). Para cumplir con la directiva central de la cátedra de evitar sobreventa y garantizar que ningún ticket se venda dos veces bajo concurrencia real, se formaliza el diseño técnico de exclusión mutua, prevención de sobreventa post-confirmación y expiración por tiempo de vida con liberación perezosa ([ADR-0008](../../../docs/adr/0008-control-de-concurrencia-y-ttl-reservas.md)).
Ver [proposal.md](./proposal.md) y [specs/concurrencia-de-reservas/spec.md](./specs/concurrencia-de-reservas/spec.md).

## Goals / Non-Goals

**Goals:**
- Garantizar atomicidad estricta y aislamiento en reservas concurrentes de modalidades generales y numeradas.
- Evitar condiciones de carrera y sobreventa devolviendo `409 Conflict` de forma determinística al postor perdedor, computando tanto reservas activas vigentes como ventas confirmadas.
- Implementar expiración de reservas por TTL (`expira_en`) con mecanismo de liberación perezosa (*lazy cleanup*) que restituya asientos a `libre` y cupos a disponible.
- Asegurar idempotencia en la reconfirmación de reservas ya confirmadas.

**Non-Goals:**
- Bloqueos distribuidos pesados vía Redis / Redlock o transacciones 2PC (prohibidas por las directivas de la cátedra).
- Infraestructura de colas de espera masivas y buffers encolados (pertenecen a Etapa III - Colas de venta).
- Devoluciones y reembolsos posteriores a la confirmación de venta (Etapa III).

## Decisions

### 1. Atomicidad en modalidad numerada y Liberación Perezosa

Al evaluar disponibilidad o intentar reservar en una modalidad numerada, se ejecuta primero una liberación perezosa transaccional de reservas caducadas:

```python
# Liberación perezosa de reservas activas vencidas
vencidas = await session.scalars(
    select(Reserva).where(
        Reserva.modalidad_id == modalidad_id,
        Reserva.estado == "activa",
        Reserva.expira_en <= func.now(),
    ).with_for_update()
)
for r in vencidas:
    r.estado = "liberada"
    if r.asiento_id:
        await session.execute(
            update(Asiento).where(Asiento.id == r.asiento_id).values(estado="libre")
        )

# Asignación atómica condicionada
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
- Garantiza que si una reserva expiró por TTL, su asiento vuelve a estar en estado `libre` para ser tomado inmediatamente por otra solicitud.
- La sentencia atómica `WHERE estado = 'libre'` garantiza la exclusión mutua directa a nivel de motor PostgreSQL sin deadlocks.

### 2. Aislamiento y conteo de ocupación en modalidad general

Para evitar sobreventa tanto en compras concurrentes como post-confirmación:

```python
modalidad = await session.scalar(
    select(Modalidad)
    .where(Modalidad.id == modalidad_id)
    .with_for_update()
)
# Conteo de reservas vigentes (confirmadas + activas no vencidas)
ocupadas = await session.scalar(
    select(func.count(Reserva.id)).where(
        Reserva.modalidad_id == modalidad_id,
        Reserva.estado.in_(["activa", "confirmada"]),
        or_(Reserva.estado == "confirmada", Reserva.expira_en > func.now()),
    )
)
if ocupadas >= modalidad.cupo:
    raise HTTPException(status_code=409, detail="sin disponibilidad")
```

**Justificación:**
- Corrige el riesgo de sobreventa post-confirmación: las reservas confirmadas permanecen computadas en la ocupación, mientras que las reservas activas vencidas dejan de restar cupo.
- `with_for_update()` sobre la fila de modalidad serializa la verificación y la inserción durante milisegundos, asegurando exactitud matemática.

### 3. Expiración por TTL e Idempotencia en Confirmación

- Cada reserva se crea con `expira_en = datetime.now(timezone.utc) + timedelta(minutes=settings.reserva_ttl_minutes)`.
- En la confirmación (`POST .../confirmar`):
  ```python
  if reserva.estado == "confirmada":
      return {"status": "confirmada"}
  if reserva.estado == "liberada":
      raise HTTPException(status_code=409, detail="reserva liberada")
  if reserva.expira_en <= datetime.now(timezone.utc):
      reserva.estado = "liberada"
      if reserva.asiento:
          reserva.asiento.estado = "libre"
      await session.commit()
      raise HTTPException(status_code=409, detail="reserva expirada")
  ```

## Risks / Trade-offs

- **[Carga de escritura durante lecturas de disponibilidad si hay vencidos]** → La liberación perezosa realiza updates en transacciones cortas.
  *Mitigación:* Solo afecta a filas puntuales que hayan vencido; no hay escaneo de tablas completas.

## Migration Plan

1. La columna `expira_en` se crea de forma unificada en la migración `0002_add_inventario.py` compartida con el change funcional.
2. Reversión: `alembic downgrade -1`.
