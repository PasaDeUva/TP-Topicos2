# Design

## Context

Ver `proposal.md` y `specs/gestion-de-cuentas/spec.md` para la motivación y los requisitos. El repositorio es greenfield y el stack acordado es Python/FastAPI, SQLAlchemy, MySQL/InnoDB, React/TypeScript/Vite y Docker. Este cambio corresponde al bloque Identity/Access de una arquitectura de tres servicios.

## Goals / Non-Goals

**Goals:**
- Dar un único dueño a las credenciales y asignaciones de roles.
- Mantener independientes los estados de cliente y organizador dentro de una misma cuenta.
- Proveer autenticación y autorización a Events y Purchases sin compartir sus bases de datos.

**Non-Goals:**
- Verificación de email, proveedores externos de identidad y aprobación administrativa por evento.
- Ser dueño de los datos de eventos o compras; esos pertenecen a sus servicios respectivos.

## Decisions

- **Identity es dueño de cuentas y asignaciones de roles.** Las credenciales y estados de rol viven en una base MySQL propia. Los demás servicios consumen credenciales firmadas y consultan las capacidades necesarias a través de la API de Identity; nunca leen sus tablas directamente. Se descarta compartir tablas de usuario entre servicios para conservar límites de datos claros.
- **Representar roles independientemente de la cuenta.** Una cuenta puede tener roles de cliente y organizador. La habilitación o desactivación del organizador modifica solo ese rol; un rol cliente activo sigue disponible.
- **Usar email y contraseña en la Etapa I.** No se exige verificación de email. La contraseña se almacena mediante un hash adaptativo de una sola vía; el mecanismo exacto de token/renovación se mantiene en el servicio Identity.
- **Validar el estado actual para operaciones protegidas.** Los servicios validan la firma de las credenciales y consultan a Identity para acciones que requieren un rol vigente. Si Identity no responde, esas mutaciones fallan de forma cerrada. Esto permite aplicar la desactivación del organizador sin consultar su base directamente.
- **Provisionar el primer administrador fuera del registro público.** El entorno de despliegue debe tener un mecanismo controlado de inicialización administrativa; no existe auto-registro de administradores.
- **Usar sesiones SQLAlchemy por request y transacciones explícitas.** Cada request obtiene una sesión acotada; los cambios de asignación de roles se confirman atómicamente.
- **Mantener el frontend desacoplado.** React/Vite consume la API de Identity; organizadores pendientes reciben una vista de estado y conservan la navegación de cliente si tienen activo ese rol.

## Risks / Trade-offs

- [La disponibilidad de Identity afecta mutaciones protegidas] → Fallar de forma cerrada para operaciones de organizador/administrador y mantener consultas públicas fuera de Identity cuando no requieran autorización.
- [Un token previamente emitido puede tener claims antiguos] → Consultar el estado vigente para mutaciones de rol en lugar de confiar únicamente en claims almacenados en el cliente.
- [Se pueden filtrar credenciales iniciales del administrador] → Provisionarlas mediante secretos del entorno, exigir rotación y nunca versionarlas.

## Migration Plan

El sistema es greenfield, por lo que no hay cuentas existentes para migrar. Inicializar la base de Identity y provisionar un administrador antes de habilitar el registro público.
