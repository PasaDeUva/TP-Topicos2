# Spec Delta

## Purpose

Permitir que una persona administradora consulte y gestione de forma segura las habilitaciones de organizadores desde la web.

## ADDED Requirements

### Requirement: Consulta administrativa de organizadores
Identity MUST permitir a un administrador activo consultar las cuentas con rol organizador y su estado actual, incluyendo identificador y email, sin exponer contraseñas ni credenciales.

#### Scenario: Consulta con distintos estados
- **WHEN** un administrador activo consulta organizadores pendientes, habilitados y deshabilitados
- **THEN** recibe los identificadores, emails y estados actuales de esas asignaciones

#### Scenario: Consulta vacía
- **WHEN** un administrador activo consulta y no hay roles de organizador
- **THEN** recibe una lista vacía

#### Scenario: Consulta no autorizada
- **WHEN** una persona sin credencial válida o sin rol administrador activo intenta consultar
- **THEN** Identity rechaza la consulta sin revelar datos de organizadores

### Requirement: Gestión web de organizadores
El cliente web MUST permitir a un administrador activo consultar el listado y habilitar o deshabilitar un rol de organizador mediante Identity.

#### Scenario: Habilitar una solicitud
- **WHEN** el administrador habilita un organizador pendiente o deshabilitado y la operación tiene éxito
- **THEN** la interfaz muestra el estado confirmado por Identity

#### Scenario: Deshabilitar un organizador
- **WHEN** el administrador deshabilita un organizador habilitado y la operación tiene éxito
- **THEN** la interfaz muestra su estado deshabilitado sin alterar sus demás roles

#### Scenario: Operación rechazada
- **WHEN** Identity rechaza la operación o el servicio no está disponible
- **THEN** la interfaz informa el error y no presenta el cambio como confirmado

### Requirement: Protección y estados de la interfaz administrativa
El cliente MUST mostrar la gestión solo para una cuenta identificada como administradora activa y MUST tratar la autorización de Identity como definitiva.

#### Scenario: Permiso revocado
- **WHEN** Identity rechaza el acceso administrativo por falta de permisos
- **THEN** el cliente deja de mostrar datos administrativos y comunica la falta de autorización

#### Scenario: Sesión inválida
- **WHEN** Identity informa que la sesión no es válida
- **THEN** el cliente descarta los datos protegidos y solicita iniciar sesión nuevamente

#### Scenario: Carga, ausencia y error
- **WHEN** la consulta está en curso, no devuelve organizadores o falla
- **THEN** el cliente muestra respectivamente un estado de carga, vacío o error con posibilidad de reintento cuando corresponda

### Requirement: Compatibilidad del acceso web
Identity MUST permitir al origen web configurado consultar y gestionar organizadores sin habilitar orígenes arbitrarios ni modificar los contratos existentes.

#### Scenario: Solicitud entre orígenes permitidos
- **WHEN** el navegador del origen autorizado solicita la operación administrativa con los encabezados requeridos
- **THEN** la política CORS permite la solicitud y la autorización sigue siendo verificada por Identity

#### Scenario: Origen no autorizado
- **WHEN** un origen no autorizado intenta realizar la solicitud desde el navegador
- **THEN** la política CORS no concede acceso a la respuesta
