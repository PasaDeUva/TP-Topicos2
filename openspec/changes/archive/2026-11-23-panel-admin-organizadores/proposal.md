# Proposal

## Why

La persona administradora puede modificar el estado de un organizador mediante Identity, pero la web no permite encontrar solicitudes ni gestionarlas. Un panel permite completar ese flujo sin depender de llamadas manuales a la API.

## What Changes

- Incorporar una consulta administrativa de organizadores con identidad mínima y estado del rol, protegida por el rol administrador vigente.
- Incorporar una vista web para consultar estados pendientes, habilitados y deshabilitados y habilitar o deshabilitar el rol mediante la operación existente.
- Permitir el método PATCH desde los orígenes web ya autorizados, sin ampliar la lista de orígenes ni alterar los contratos existentes.
- Mantener los flujos de cuenta, autenticación y roles independientes; no incluir administración general de usuarios ni gestión de eventos.

## Capabilities

### New Capabilities

- `administracion-organizadores`: consulta y gestión web segura de estados de organizador.

### Modified Capabilities

Ninguna en las especificaciones principales actuales. Los cambios activos `gestion-de-accesos` y `cliente-web-acceso` contienen deltas relacionados que deben preservarse.

## Impact

- Identity: nuevo contrato aditivo de consulta administrativa y configuración CORS; la mutación administrativa existente mantiene su contrato.
- Cliente React/Vite: vista administrativa, estados y consumo autenticado de API.
- Pruebas de autorización, privacidad, CORS, interfaz y regresión. Sin nuevas dependencias previstas.
