# Proposal

## Why

El cierre de sesión revoca la renovación, pero un JWT emitido sigue siendo aceptado por Identity hasta su vencimiento. Esto permite seguir usando un token obtenido antes del cierre, incluso para consultar datos administrativos.

## What Changes

- Asociar los nuevos JWT de acceso a su sesión y comprobar su estado vigente en Identity en cada operación protegida.
- Ofrecer a servicios autorizados una verificación del estado de sesión para sus futuras integraciones, que deben rechazar operaciones protegidas si no pueden verificarlo.
- **BREAKING:** al activar el cambio, rechazar los JWT anteriores sin identificador de sesión. Sus titulares deberán renovar el acceso o iniciar sesión nuevamente.
- Documentar la nueva decisión arquitectónica y su relación con el ADR-0004; la decisión previa de validación local sin revocación inmediata queda afectada.
- Mantener fuera de alcance la integración de autenticación y autorización en Eventos y Compras; no afirmar que sus operaciones actuales estén protegidas por este cambio.

## Capabilities

### New Capabilities

- `revocacion-de-sesiones`: validación de sesiones revocadas y contrato para futuras integraciones de consumidores.

### Modified Capabilities

Ninguna en las especificaciones principales actuales. `gestion-de-accesos` y `cliente-web-acceso` contienen deltas existentes relacionados que deberán preservarse y reconciliarse al sincronizar.

## Impact

- Identity: emisión y validación de JWT, consulta de sesiones y autenticación entre servicios.
- Clientes web y API: transición para tokens antiguos, restauración y errores de sesión.
- Consumidores futuros: validación de sesión vigente y rechazo ante fallas de Identity.
- ADR, documentación de contratos y pruebas de seguridad, concurrencia y regresión.
