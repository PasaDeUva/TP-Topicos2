# acceso-cuenta-web Specification

## Purpose
Permitir que las personas accedan desde el navegador y consulten o amplíen los roles de su cuenta mediante una sesión web protegida.

## Requirements

### Requirement: Registro desde el navegador
El cliente web MUST permitir solicitar el registro como cliente u organizador con email y contraseña, mostrar el resultado y no conceder permisos adicionales a los asignados por Identity.

#### Scenario: Registro de cliente
- **WHEN** una persona registra un cliente con datos válidos
- **THEN** el cliente informa el éxito y permite continuar al inicio de sesión

#### Scenario: Registro de organizador
- **WHEN** una persona registra un organizador con datos válidos
- **THEN** el cliente informa que el rol queda pendiente de habilitación

#### Scenario: Registro rechazado
- **WHEN** Identity rechaza el registro por datos inválidos o email existente
- **THEN** el cliente muestra un error comprensible y conserva los datos no sensibles necesarios para corregirlo

### Requirement: Inicio de sesión web
El cliente web MUST permitir iniciar sesión con email y contraseña y mostrar un estado comprensible cuando las credenciales sean rechazadas o el servicio no esté disponible.

#### Scenario: Acceso exitoso
- **WHEN** una persona inicia sesión correctamente
- **THEN** el cliente muestra su cuenta y roles sin exponer contraseñas ni credenciales de renovación

#### Scenario: Credenciales incorrectas
- **WHEN** Identity rechaza el inicio de sesión
- **THEN** el cliente informa que no pudo autenticar sin distinguir email inexistente de contraseña incorrecta

#### Scenario: Identity no disponible
- **WHEN** el cliente no puede completar el inicio de sesión por un fallo del servicio
- **THEN** informa el problema y no presenta a la persona como autenticada

### Requirement: Consulta de cuenta y roles
El cliente web MUST mostrar identificador, email y roles con sus estados vigentes a la persona autenticada, sin mostrar credenciales ni asumir permisos por el mero inicio de sesión.

#### Scenario: Organizador pendiente o deshabilitado
- **WHEN** una cuenta consulta su perfil con rol organizador pendiente o deshabilitado
- **THEN** el cliente muestra ese estado y conserva visibles los demás roles de la cuenta

#### Scenario: Consulta sin sesión válida
- **WHEN** una persona intenta consultar su cuenta sin una sesión válida
- **THEN** el cliente solicita iniciar sesión sin mostrar datos de una sesión anterior

### Requirement: Solicitud de rol adicional
El cliente web MUST permitir a una persona autenticada solicitar el rol de cliente u organizador que no tenga asignado y reflejar los estados devueltos por Identity.

#### Scenario: Cliente solicita organizador
- **WHEN** una cuenta con rol cliente solicita el rol organizador
- **THEN** el cliente muestra organizador pendiente y mantiene el estado del rol cliente

#### Scenario: Rol ya asignado
- **WHEN** Identity rechaza la solicitud de un rol ya asignado
- **THEN** el cliente informa el resultado sin presentar una modificación inexistente

### Requirement: Credenciales de sesión web
La credencial de renovación web MUST entregarse en una cookie HttpOnly sin Domain; MUST NOT aparecer en respuestas JSON para el navegador, URLs, logs ni almacenamiento web. El JWT de acceso MUST permanecer en memoria del cliente.

#### Scenario: Inicio y renovación web
- **WHEN** Identity inicia o renueva una sesión web
- **THEN** el navegador recibe la credencial de renovación mediante la cookie y la respuesta accesible a JavaScript no la contiene

#### Scenario: Atributos de cookie
- **WHEN** la sesión opera bajo HTTPS
- **THEN** la cookie utiliza Secure y, si frontend e Identity comparten sitio, SameSite=Strict

### Requirement: Protección contra solicitudes web no autorizadas
Identity MUST exigir un token CSRF válido asociado a la sesión y verificar el origen permitido en las solicitudes web de renovación y cierre. La configuración MUST especificar un único origen de frontend por instancia de Identity.

#### Scenario: Solicitud sin protección válida
- **WHEN** una solicitud web de renovación o cierre no presenta el token CSRF válido o procede de un origen no permitido
- **THEN** Identity rechaza la solicitud sin renovar ni cerrar la sesión

#### Scenario: Orígenes distintos autorizados
- **WHEN** frontend e Identity usan orígenes distintos y autorizados
- **THEN** el navegador puede completar las solicitudes con credenciales sin habilitar orígenes arbitrarios

### Requirement: Restauración y duración de sesión
El cliente web MUST intentar restaurar una sesión web válida al recargar y MUST respetar el límite absoluto de 24 horas desde el inicio de sesión, sin extenderlo mediante renovaciones.

#### Scenario: Recarga con sesión vigente
- **WHEN** una persona recarga la aplicación con una sesión renovable vigente
- **THEN** el cliente restaura el acceso y consulta la cuenta sin solicitar nuevamente la contraseña

#### Scenario: Sesión vencida o revocada
- **WHEN** la sesión no puede renovarse por vencimiento o revocación
- **THEN** el cliente descarta el estado autenticado y solicita iniciar sesión nuevamente

#### Scenario: Límite absoluto cercano
- **WHEN** se renueva una sesión con menos de una hora restante hasta su límite absoluto
- **THEN** la credencial de acceso nueva no vence después de ese límite

### Requirement: Coordinación entre pestañas
El cliente web MUST coordinar las operaciones de renovación y cierre de una misma sesión entre pestañas para evitar reutilizar simultáneamente una credencial rotativa y propagar el cierre a las demás pestañas.

#### Scenario: Renovación simultánea
- **WHEN** dos pestañas necesitan renovar la misma sesión al mismo tiempo
- **THEN** coordinan el acceso a la credencial y la sesión no se revoca por reutilización causada por el cliente

#### Scenario: Cierre desde otra pestaña
- **WHEN** una pestaña cierra la sesión
- **THEN** las demás dejan de mostrar el estado autenticado y no realizan nuevas renovaciones de esa sesión

#### Scenario: Resultado de renovación desconocido
- **WHEN** la respuesta de una renovación se pierde y el cliente no puede determinar su resultado
- **THEN** no reutiliza a ciegas la credencial anterior y puede requerir un nuevo inicio de sesión

### Requirement: Cierre de sesión web
El cierre web MUST revocar la sesión renovable y eliminar la cookie de renovación. El cliente MUST limpiar el JWT en memoria y dejar de mostrar datos de la cuenta.

#### Scenario: Cierre exitoso
- **WHEN** una persona cierra sesión con protección válida
- **THEN** Identity revoca la renovación y elimina la cookie, y el cliente vuelve al estado no autenticado

#### Scenario: Renovación después del cierre
- **WHEN** se intenta renovar con una credencial de una sesión cerrada
- **THEN** Identity rechaza la renovación

### Requirement: Compatibilidad con clientes API
La interfaz de sesión web MUST preservar el comportamiento JSON existente de registro, inicio, renovación y cierre para clientes API que no usan la cookie web.

#### Scenario: Cliente API existente
- **WHEN** un cliente API utiliza los endpoints JSON actuales con sus entradas válidas
- **THEN** recibe las mismas estructuras y códigos de respuesta acordados para ese contrato
