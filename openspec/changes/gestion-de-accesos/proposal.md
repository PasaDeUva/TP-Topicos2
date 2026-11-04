# Proposal

## Why

La plataforma necesita distinguir las capacidades de administradores, organizadores y clientes, y controlar cuándo un organizador puede operar. Definir el registro, la habilitación y el acceso por rol para la Etapa I evita confundir la activación de una cuenta con la aprobación individual de cada evento.

## What Changes

- Definir los roles funcionales de administrador, organizador y cliente.
- Permitir que los organizadores se registren por su cuenta, con la cuenta pendiente hasta que un administrador la habilite.
- Permitir que un organizador pendiente inicie sesión para consultar el estado de su cuenta, sin acceder a las funciones de organizador.
- Habilitar el diseño y la publicación de eventos cuando el administrador activa al organizador, sin requerir aprobación administrativa por cada evento.
- Permitir que el administrador desactive a un organizador, bloquee su acceso e interrumpa la publicación de sus eventos existentes.
- Dejar la verificación de email fuera del alcance inicial.

## Capabilities

### New Capabilities

- `gestion-de-cuentas`: roles, estados de cuenta y habilitación de las capacidades asociadas a cada rol.

### Modified Capabilities

Ninguna. El proyecto todavía no tiene especificaciones de capacidades existentes.

## Impact

El cambio define el comportamiento de acceso para administradores, organizadores y clientes, con foco en el ciclo de habilitación de organizadores y el control de sus eventos. La aplicación aún no tiene código en este repositorio. El stack acordado es Python/FastAPI, SQLAlchemy, MySQL con InnoDB, React con TypeScript y Vite, y Docker; los límites del servicio de identidad y sus contratos se detallan en el diseño. La aprobación de cuentas de organizador se realiza una vez por cuenta; la aprobación de cada evento queda fuera del flujo.
