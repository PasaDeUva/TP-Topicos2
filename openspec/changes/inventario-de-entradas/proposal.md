# Proposal

## Why

`events-service` es la fuente de verdad del catálogo pero no guarda precio, cupo ni estructura de asientos. Sin esos datos, `compras-service` no puede validar la disponibilidad de una modalidad ni el flujo de reserva-pago-confirmación definido en ADR-0006 puede implementarse.

## What Changes

- Agregar `precio` (para general) y `cupo` a `modalidades` en `events-service`, mediante la migración unificada `0002_add_inventario.py`, aplicando backfill para preservar la consistencia con eventos preexistentes.
- Modelar asientos numerados: nuevas tablas `sectores` (con precio por sector) y `asientos` con estado `libre / reservado / vendido`.
- Crear tabla `reservas` con identificador `reserva_id`, vinculación a modalidad y asiento opcional, marca de expiración `expira_en`, y columna `idempotency_key` para garantizar reintentos seguros.
- Extender `POST /eventos` y `PUT /eventos/{id}` para aceptar precio y cupo en general, y sectores con precio y asientos en numerado. En `PUT /eventos/{id}`, aceptar `id: UUID` opcional por modalidad para preservar identidades existentes; rechazar con `409 Conflict` la eliminación de modalidades que cuenten con historial de reservas (`activa`, `confirmada` o `liberada`).
- Extender `GET /eventos/{id}` para exponer precio, cupo y, en modalidad numerada, sectores y asientos.
- Nuevo endpoint `GET /eventos/{id}/modalidades/{mid}/disponibilidad`: devuelve cupo restante (general, considerando confirmadas y activas no vencidas) o cantidad de asientos libres (numerado).
- Nuevos endpoints de ciclo de vida de reservas (implementados y verificados conjuntamente con el change complementario `concurrencia-de-reservas`):
  - `POST /eventos/{id}/modalidades/{mid}/reservas` → reservar con soporte opcional de cabecera `Idempotency-Key`; devuelve `reserva_id`.
  - `DELETE /eventos/{id}/modalidades/{mid}/reservas/{reserva_id}` → liberar (compensación ante pago fallido, 409 si ya no está activa).
  - `POST /eventos/{id}/modalidades/{mid}/reservas/{reserva_id}/confirmar` → confirmar venta (idempotente 200 si ya confirmada, 409 si liberada o expirada).

## Capabilities

### New Capabilities

- `inventario-de-entradas`: disponibilidad, precio, cupo y ciclo de vida de reservas de las modalidades de un evento.

### Modified Capabilities

- `gestion-de-eventos`: los endpoints de alta y edición de eventos pasan a aceptar precio, cupo y sectores, y el detalle del evento pasa a exponer esos campos, protegiendo modalidades con ventas contra borrado.

## Impact

- **APIs modificadas:** `POST /eventos`, `PUT /eventos/{id}`, `GET /eventos`, `GET /eventos/{id}`.
- **APIs nuevas:** `GET .../disponibilidad`, `POST .../reservas`, `DELETE .../reservas/{id}`, `POST .../reservas/{id}/confirmar`.
- **Base de datos:** migración unificada `0002_add_inventario.py` en `events-service` creando `sectores`, `asientos` y `reservas`.
- **ADRs:** ADR-0007 (modelo de inventario) y ADR-0008 (control de concurrencia y TTL).
- **Sin impacto en** `compras-service`, `identity-service` ni `compose.yaml`.
