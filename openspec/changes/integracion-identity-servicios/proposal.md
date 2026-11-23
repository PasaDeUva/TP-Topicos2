# Proposal

## Why

Eventos y Compras aceptan identificadores de cuenta sin verificar quién realiza la solicitud. Identity ya proporciona sesión y roles vigentes, pero sus consumidores aún no los utilizan para autorizar operaciones.

## What Changes

- Integrar las operaciones protegidas de Eventos y Compras con la identidad, la sesión y los roles vigentes de Identity.
- Derivar `owner_id` y `cliente_id` de la cuenta autenticada; aceptar esos campos opcionales solo si coinciden con ella, conforme al [ADR-0013 propuesto](../../../docs/adr/0013-identidad-en-eventos-y-compras.md).
- Mantener públicas las consultas existentes del catálogo de Eventos; exigir organizador habilitado y propiedad para su gestión, y cliente activo y propiedad para compras.
- **BREAKING:** las operaciones protegidas requieren autenticación y rechazan identificadores ajenos, aunque se conserve la forma de los payloads compatibles.
- Mantener el registro mínimo e idempotencia de Compras. Se excluyen pantallas web nuevas, pagos, inventario y cambios en las reglas del catálogo.

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

- `gestion-de-eventos`: autorización de gestión e identidad del propietario.
- `gestion-de-compras`: autorización e identidad del cliente en registro y consulta.

## Impact

- Eventos y Compras: endpoints, validaciones, integración autenticada con Identity y pruebas.
- Identity y entorno: credenciales de servicio, permisos, disponibilidad y distribución confiable de claves.
- Clientes existentes: autenticación y transición de identificadores; respuestas de errores y documentación.
