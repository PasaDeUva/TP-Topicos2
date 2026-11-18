# Proposal

## Why

La plataforma necesita que un cliente pueda comprar entradas de los eventos publicados. El catálogo ya existe en `events-service`, pero no hay un servicio que registre las compras. Esta primera entrega define el registro mínimo de una compra sobre una modalidad general, sin cupos ni montos, que todavía no existen en el catálogo ([ADR-0003](../../../docs/adr/0003-servicio-eventos-e-inventario.md)).

## What Changes

- Crear el microservicio `backend/compras-service/`, con la misma estructura que `events-service`: FastAPI, SQLAlchemy 2 async, Pydantic v2, Alembic y PostgreSQL dedicado (`compras_db`).
- Registrar una compra indicando `cliente_id`, `evento_id` y `modalidad_id`. Compras valida el evento y la modalidad consultando `GET /eventos/{id}` de `events-service`, sin escribir en su base ([ADR-0005](../../../docs/adr/0005-compras-consulta-eventos-e-idempotencia.md)).
- Aceptar la compra solo si el evento está activo y la modalidad es `general`.
- Exigir la cabecera `Idempotency-Key`: repetir la misma solicitud devuelve la compra ya registrada y no crea otra.
- Consultar una compra por id y listar las compras de un cliente.
- Responder `503` cuando `events-service` no está disponible, sin registrar la compra.
- Incluir una bitácora HTTP con tiempos y logs JSON, igual que `events-service`.
- Agregar al Compose los servicios `compras-db` y `compras-service`, y a CI la migración, `alembic check` y el lint del nuevo servicio.

## Fuera de alcance

- **Cupo y stock por modalidad:** la compra no descuenta ni verifica disponibilidad. Según ADR-0003, la capacidad pertenece al change de asientos y stock; incluirla ahora anticiparía esas decisiones.
- **Sobreventa y bloqueo de filas (`SELECT ... FOR UPDATE`):** sin stock no hay un recurso que proteger contra venta duplicada. La no doble carga de una misma solicitud se resuelve con la clave de idempotencia.
- **Montos, precios, pagos y facturación:** el precio varía por sector o asiento y no existe aún en el catálogo. Sin monto no hay cobro que modelar.
- **Cantidad de entradas por compra:** sin stock ni precio, una compra registra la elección de evento y modalidad, no un número de entradas.
- **Entradas numeradas, mapa de asientos y reservas con TTL:** dependen del change de asientos y stock.
- **Devoluciones, colas de venta, notificaciones en tiempo real, cache y recomendaciones:** pertenecen a las Etapas II y III.
- **Validación completa de JWT y roles:** el `cliente_id` viaja en la solicitud como dato temporal hasta que `gestion-de-accesos` esté integrado ([ADR-0004](../../../docs/adr/0004-autenticacion-entre-servicios.md)).

## Capabilities

### New Capabilities

- `gestion-de-compras`: registro idempotente de compras de entradas generales sobre eventos activos, y consulta de compras por id y por cliente.

### Modified Capabilities

Ninguna; `openspec/specs/` no tiene specs de compras ni modifica las existentes.

## Impact

- **Nuevas APIs:** `POST /compras`, `GET /compras/{id}` y `GET /compras?cliente_id=...`.
- **Base de datos:** instancia dedicada `compras-db` (`compras_db`) con la tabla `compras`.
- **Dependencias entre servicios:** Compras consume `GET /eventos/{id}` de Eventos por HTTP; Eventos no cambia.
- **Infraestructura:** `compose.yaml`, `.github/workflows/ci.yml`, `backend/README.md` y `docs/local-development.md`.
- **Deuda técnica explícita:** `cliente_id` sin autenticar, igual que `owner_id` en Eventos, hasta integrar Identity.
