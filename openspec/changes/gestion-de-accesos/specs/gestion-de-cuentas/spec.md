# Spec Delta: Gestión de cuentas

## Purpose

Permitir que las personas accedan con una identidad única y que sus roles y habilitaciones puedan consultarse de forma confiable por la plataforma.

## ADDED Requirements

### Requirement: Registro de clientes
El sistema MUST permitir el registro de clientes con email y contraseña, habilitando inmediatamente el rol de cliente sin exigir verificación de email en la Etapa I.

#### Scenario: Registro exitoso de cliente
- **WHEN** una persona se registra con un email disponible y una contraseña válida
- **THEN** el sistema crea una cuenta con identificador propio y rol de cliente activo

#### Scenario: Email ya registrado
- **WHEN** una persona intenta crear una cuenta con un email ya registrado
- **THEN** el sistema rechaza la creación de una cuenta duplicada sin modificar la cuenta existente

### Requirement: Registro de organizadores
El sistema MUST permitir solicitar el rol de organizador con email y contraseña. El rol permanece pendiente de habilitación hasta que un administrador lo habilite, sin exigir verificación de email en la Etapa I.

#### Scenario: Registro de organizador
- **WHEN** una persona se registra como organizador con un email disponible y una contraseña válida
- **THEN** el sistema crea una cuenta con el rol de organizador pendiente y sin permisos de organizador habilitado

### Requirement: Longitud mínima de contraseña
El sistema MUST exigir una contraseña de al menos 8 caracteres al registrar una cuenta, sin requerir combinaciones específicas de mayúsculas, números o símbolos.

#### Scenario: Contraseña menor al mínimo
- **WHEN** una persona intenta registrarse con una contraseña de menos de 8 caracteres
- **THEN** el sistema rechaza el registro e informa la longitud mínima requerida

#### Scenario: Contraseña que cumple la longitud mínima
- **WHEN** una persona se registra con una contraseña de al menos 8 caracteres que no contiene combinaciones específicas de mayúsculas, números o símbolos
- **THEN** el sistema acepta la contraseña respecto de la regla de longitud

### Requirement: Inicio de sesión
El sistema MUST autenticar a clientes y organizadores mediante el email y la contraseña de su cuenta y MUST rechazar credenciales incorrectas.

#### Scenario: Credenciales válidas
- **WHEN** una persona presenta las credenciales correctas de una cuenta con acceso permitido
- **THEN** el sistema autentica a la persona y le permite consultar su identidad y roles

#### Scenario: Credenciales incorrectas
- **WHEN** una persona presenta un email o contraseña incorrectos
- **THEN** el sistema rechaza el inicio de sesión sin autenticarla

### Requirement: Emisión de credencial de acceso
El sistema MUST emitir una credencial de acceso con vigencia máxima de una hora al autenticar correctamente a una persona y MUST vincularla al identificador de su cuenta sin incluir su contraseña. Ninguna credencial de acceso MUST vencer después del límite absoluto de su sesión.

#### Scenario: Inicio de sesión exitoso
- **WHEN** una persona inicia sesión con credenciales válidas y acceso permitido
- **THEN** Identity entrega una credencial temporal asociada a su cuenta sin incluir la contraseña

### Requirement: Renovación de sesión
El sistema MUST permitir renovar el acceso mediante una credencial de renovación separada. Cada renovación exitosa MUST invalidar la credencial de renovación utilizada y emitir una nueva. La sesión MUST vencer como máximo 24 horas después del inicio de sesión, sin extender ese límite mediante renovaciones.

#### Scenario: Renovación dentro de la sesión
- **WHEN** una persona presenta una credencial de renovación vigente antes del límite de su sesión y su cuenta tiene acceso permitido
- **THEN** Identity entrega una nueva credencial de acceso y una nueva credencial de renovación e invalida la anterior

#### Scenario: Reutilización de una credencial de renovación
- **WHEN** se presenta nuevamente una credencial de renovación que ya fue utilizada
- **THEN** Identity rechaza la renovación y revoca la sesión asociada

#### Scenario: Límite de la sesión alcanzado
- **WHEN** se intenta renovar una sesión transcurridas 24 horas desde el inicio de sesión
- **THEN** Identity rechaza la renovación y requiere un nuevo inicio de sesión

#### Scenario: Cuenta sin acceso permitido
- **WHEN** se intenta renovar una sesión de una cuenta que ya no tiene acceso permitido
- **THEN** Identity rechaza la renovación

#### Scenario: Renovación cerca del límite absoluto
- **WHEN** una persona renueva su sesión y resta menos de una hora para cumplir las 24 horas desde el inicio
- **THEN** la nueva credencial de acceso vence a más tardar al alcanzar ese límite

### Requirement: Protección de la sesión web
Para el cliente web, Identity MUST entregar la credencial de renovación mediante una cookie HttpOnly y MUST exigir un token CSRF válido asociado a la sesión para renovar o cerrar sesión. El cliente MUST mantener la credencial de acceso en memoria. El cierre de sesión MUST revocar la renovación y eliminar la cookie de renovación.

#### Scenario: Renovación sin protección CSRF válida
- **WHEN** se solicita renovar una sesión sin un token CSRF válido asociado a ella
- **THEN** Identity rechaza la solicitud sin renovar la sesión

#### Scenario: Cierre de sesión
- **WHEN** una persona solicita cerrar sesión con protección CSRF válida
- **THEN** Identity revoca la renovación de esa sesión y elimina su cookie de renovación

#### Scenario: Reutilización después del cierre
- **WHEN** se intenta renovar una sesión cuya renovación fue revocada por el cierre
- **THEN** Identity rechaza la solicitud

### Requirement: Verificación de credencial por servicios consumidores
El sistema MUST permitir a los servicios autorizados verificar una credencial de acceso y obtener el identificador de la cuenta autenticada. MUST rechazar credenciales ausentes, inválidas, alteradas o vencidas.

#### Scenario: Credencial válida
- **WHEN** un servicio autorizado verifica una credencial vigente y auténtica
- **THEN** Identity permite identificar la cuenta a la que pertenece

#### Scenario: Credencial inválida o vencida
- **WHEN** se intenta verificar una credencial ausente, inválida, alterada o vencida
- **THEN** Identity rechaza la verificación sin autenticar a la persona

### Requirement: Consulta del estado actual de roles
El sistema MUST ofrecer a los servicios autorizados una consulta interna de roles y estados actuales por identificador de cuenta, sin depender exclusivamente del estado existente al emitir la credencial. MUST verificar una credencial propia del servicio antes de responder y rechazar cuentas inexistentes.

#### Scenario: Rol de organizador deshabilitado después del inicio de sesión
- **WHEN** un administrador deshabilita el rol de organizador de una persona con credencial vigente y un servicio autorizado consulta sus roles
- **THEN** Identity informa que el rol de organizador está deshabilitado y conserva el estado independiente de sus demás roles

#### Scenario: Verificación no autorizada
- **WHEN** un consumidor no autorizado intenta consultar los roles actuales de otra cuenta
- **THEN** Identity rechaza la consulta

#### Scenario: Cuenta inexistente
- **WHEN** un servicio autorizado consulta roles de un identificador de cuenta inexistente
- **THEN** Identity rechaza la consulta sin informar roles de otra cuenta

### Requirement: Consulta de identidad propia
El sistema MUST permitir que una persona autenticada consulte su identificador estable, email y roles con sus estados; MUST NOT exponer su contraseña en esa consulta.

#### Scenario: Consulta autenticada
- **WHEN** una persona autenticada consulta su identidad
- **THEN** el sistema devuelve el identificador de su cuenta, su email y sus roles con sus estados, sin devolver la contraseña

#### Scenario: Consulta sin autenticación
- **WHEN** una persona no autenticada intenta consultar la identidad propia
- **THEN** el sistema rechaza la consulta

### Requirement: Roles independientes en una cuenta
El sistema MUST permitir que una misma cuenta tenga roles de cliente y organizador, conservando el estado de cada rol independientemente.

#### Scenario: Cliente solicita el rol de organizador
- **WHEN** un cliente autenticado solicita el rol de organizador
- **THEN** el sistema agrega el rol pendiente a su cuenta y conserva activo su rol de cliente

#### Scenario: Organizador solicita el rol de cliente
- **WHEN** un organizador autenticado solicita el rol de cliente
- **THEN** el sistema agrega el rol de cliente activo a su cuenta sin modificar el estado de organizador

### Requirement: Acceso de organizador pendiente
El sistema MUST permitir iniciar sesión a un organizador pendiente para consultar su estado y MUST NOT otorgarle permisos de organizador habilitado.

#### Scenario: Organizador pendiente con rol cliente
- **WHEN** una cuenta con rol cliente activo y organizador pendiente inicia sesión
- **THEN** puede consultar el estado pendiente y conserva sus permisos de cliente, sin permisos de organizador habilitado

### Requirement: Habilitación de organizadores
El sistema MUST permitir a un administrador habilitar, deshabilitar y volver a habilitar el rol de organizador; una persona sin rol administrador MUST NOT realizar esas acciones.

#### Scenario: Administrador habilita un organizador
- **WHEN** un administrador habilita un rol de organizador pendiente
- **THEN** el sistema cambia ese rol a habilitado y lo refleja en la consulta de identidad y roles

#### Scenario: Administrador deshabilita y reactiva un organizador
- **WHEN** un administrador deshabilita un rol de organizador y luego vuelve a habilitarlo
- **THEN** el sistema refleja cada cambio en el estado de ese rol sin deshabilitar el rol de cliente de la cuenta

#### Scenario: Usuario sin permisos intenta habilitar un organizador
- **WHEN** una persona sin rol administrador intenta cambiar la habilitación de un organizador
- **THEN** el sistema rechaza la operación sin modificar el estado del rol

### Requirement: Administrador inicial y recuperación
El sistema MUST permitir crear el primer administrador mediante un procedimiento de inicialización controlado con credenciales suministradas por configuración. La contraseña MUST almacenarse como hash. Repetir la inicialización MUST NOT duplicar la cuenta ni restablecer su contraseña. La recuperación MUST realizarse mediante un procedimiento administrativo controlado, sin exponer una operación pública de restablecimiento.

#### Scenario: Inicialización del administrador
- **WHEN** se ejecuta la inicialización en una instalación sin administrador inicial
- **THEN** el sistema crea la cuenta administradora con las credenciales configuradas y almacena su contraseña como hash

#### Scenario: Inicialización repetida
- **WHEN** se repite la inicialización y el administrador inicial ya existe
- **THEN** el sistema no crea otra cuenta ni modifica su contraseña

#### Scenario: Recuperación administrativa
- **WHEN** una persona con acceso autorizado al entorno ejecuta el procedimiento administrativo de recuperación
- **THEN** el sistema permite establecer una nueva contraseña para el administrador sin exponer la operación públicamente

### Requirement: Acceso de organizador deshabilitado
El sistema MUST impedir las funciones del rol organizador deshabilitado y conservar el acceso de cliente cuando ese rol esté activo.

#### Scenario: Cuenta con rol cliente activo
- **WHEN** se deshabilita el rol organizador de una cuenta que tiene rol cliente activo
- **THEN** la persona puede seguir accediendo como cliente pero no como organizador habilitado

#### Scenario: Cuenta sin otro rol activo
- **WHEN** una persona cuyo único rol es organizador deshabilitado intenta iniciar sesión
- **THEN** el sistema rechaza el acceso a la cuenta
