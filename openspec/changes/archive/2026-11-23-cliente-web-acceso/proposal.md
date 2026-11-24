# Propuesta: cliente web de acceso y cuenta

## Why

La plataforma ya dispone de Identity, pero el frontend actual solo muestra el estado de un servicio de ejemplo. Las personas necesitan una interfaz para registrarse, iniciar sesión y consultar su cuenta con una sesión web protegida.

## What Changes

- Incorporar una aplicación web de acceso y cuenta con registro de cliente u organizador, inicio de sesión, cierre de sesión y consulta de identidad y roles.
- Permitir solicitar el rol de cliente u organizador faltante y mostrar sus estados independientes, incluido organizador pendiente o deshabilitado.
- Adaptar Identity para entregar y renovar la sesión web mediante cookie HttpOnly y protección CSRF, manteniendo el contrato JSON existente para clientes API.
- Restaurar la sesión al recargar, coordinar renovación y cierre entre pestañas y manejar vencimiento, credenciales rechazadas y fallos del servicio.
- Integrar la aplicación y los servicios necesarios en Compose y documentar su ejecución y validación.
- Mantener fuera de esta primera versión el catálogo, las compras, la administración de organizadores y la integración funcional de Events y Purchases.

## Capabilities

### New Capabilities

- `acceso-cuenta-web`: acceso desde navegador, consulta de cuenta y roles, y protección de la sesión web.

### Modified Capabilities

Ninguna spec principal existente cambia. La capacidad `gestion-de-cuentas` sigue en el change activo `gestion-de-accesos`; la adaptación web debe preservar su contrato y coordinarse con su sincronización.

## Impact

- Frontend React, Vite y TypeScript según [ADR-0001](../../../docs/adr/0001-stack-inicial.md); la aplicación de ejemplo actual solo consulta `/api/health`.
- Identity, su contrato de sesión y sus pruebas deben extenderse sin romper los endpoints API actuales.
- Compose, proxy local, documentación y pruebas de navegador deben cubrir el flujo completo.
- La propuesta de sesión web se documenta en [ADR-0009](../../../docs/adr/0009-sesion-web-identity.md), complementando el [ADR-0004](../../../docs/adr/0004-autenticacion-entre-servicios.md).
