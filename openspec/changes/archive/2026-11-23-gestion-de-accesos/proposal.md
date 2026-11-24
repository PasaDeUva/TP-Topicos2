# Propuesta: gestión de accesos

## Why

La plataforma necesita identificar a sus usuarios y distinguir sus roles para que los demás servicios puedan atribuir acciones a una identidad. Esta primera entrega define el acceso y las cuentas sin depender de la implementación de Eventos o Compras.

## What Changes

- Incorporar una capacidad de registro e inicio de sesión con email y contraseña para clientes y organizadores, sin verificación de email en la Etapa I.
- Emitir credenciales de acceso de una hora y permitir renovar la sesión mediante credenciales de renovación rotativas, hasta un máximo de 24 horas desde el inicio de sesión.
- Permitir consultar la identidad y los roles propios de la cuenta autenticada.
- Distinguir los roles de cliente, organizador y administrador, y la habilitación del organizador, manteniendo independientes los roles de una misma cuenta.
- Permitir a un administrador habilitar o deshabilitar el rol de organizador y conservar las funciones de cliente que permanezcan activas.
- Inicializar y recuperar el primer administrador mediante procedimientos controlados, y preparar un entorno local que arranque con Docker Compose.
- Dejar explícita la necesidad de que los servicios consumidores validen identidad y permisos al integrar operaciones protegidas.

## Capabilities

### New Capabilities

- `gestion-de-cuentas`: registro, autenticación, consulta de identidad y administración de roles y habilitación de organizadores.

### Modified Capabilities

Ninguna; no existe una spec vigente de identidad en esta rama.

## Impact

El futuro servicio Identity tendrá límites independientes y usará el stack aceptado en [ADR-0001](../../../docs/adr/0001-stack-inicial.md). Eventos actualmente propone aceptar `owner_id` sin autenticar: validar ese campo y conectar Eventos y Compras con Identity requiere integración posterior y coordinación con sus responsables. Quedan fuera de esta primera entrega la verificación de email, proveedores externos, la integración efectiva con los demás servicios y las funciones de compra o gestión de eventos.
