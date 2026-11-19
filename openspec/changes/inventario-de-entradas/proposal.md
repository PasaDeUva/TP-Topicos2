# Proposal

## Why

`events-service` es la fuente de verdad del catálogo pero no guarda precio, cupo ni estructura de asientos. Sin esos datos, `compras-service` no puede validar la disponibilidad de una modalidad ni el flujo de reserva-pago-confirmación definido en ADR-0006 puede implementarse.

## What Changes

- Agregar `precio` y `cupo` a `modalidades` en `events-service` (migración `0002`).
- Modelar asientos numerados: nuevas tablas `sectores` y `asientos` con estado `libre / reservado / vendido`.
- Extender `POST /eventos` y `PUT /eventos/{id}` para aceptar precio, cupo y, en modalidad numerada, sectores con sus asientos iniciales.
- Extender `GET /eventos/{id}` para exponer precio, cupo y, en modalidad numerada, sectores y asientos.
- Nuevo endpoint `GET /eventos/{id}/modalidades/{mid}/disponibilidad`: devuelve cupo restante (general) o cantidad de asientos libres (numerado).
- Nuevos endpoints de ciclo de vida de reservas (sin mecanismo de concurrencia, que se especifica en el change `concurrencia-de-reservas`):
  - `POST /eventos/{id}/modalidades/{mid}/reservas` → reservar; devuelve `reserva_id`.
  - `DELETE /eventos/{id}/modalidades/{mid}/reservas/{reserva_id}` → liberar (compensación ante pago fallido).
  - `POST /eventos/{id}/modalidades/{mid}/reservas/{reserva_id}/confirmar` → marcar vendido.

## Capabilities

### New Capabilities

- `inventario-de-entradas`: disponibilidad, precio, cupo y ciclo de vida de reservas de las modalidades de un evento.

### Modified Capabilities

- `gestion-de-eventos`: los endpoints de alta y edición de eventos pasan a aceptar precio, cupo y sectores; el detalle del evento pasa a exponer esos campos.

## Impact

- **APIs modificadas:** `POST /eventos`, `PUT /eventos/{id}`, `GET /eventos`, `GET /eventos/{id}`.
- **APIs nuevas:** `GET .../disponibilidad`, `POST .../reservas`, `DELETE .../reservas/{id}`, `POST .../reservas/{id}/confirmar`.
- **Base de datos:** migración `0002` en `events-service`; nuevas tablas `sectores` y `asientos`.
- **ADR nuevo:** ADR-0007 sobre modelo de inventario y frontera con `compras-service`.
- **Sin impacto en** `compras-service`, `identity-service` ni `compose.yaml`.
