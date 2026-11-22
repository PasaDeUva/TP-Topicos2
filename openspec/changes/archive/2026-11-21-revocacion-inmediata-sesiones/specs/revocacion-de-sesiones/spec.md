# Spec Delta

## Purpose

Impedir que una sesión revocada continúe autorizando nuevas operaciones protegidas en Identity y ofrecer verificación para futuras integraciones.

## ADDED Requirements

### Requirement: Token de acceso asociado a una sesión
Identity MUST emitir tokens de acceso vinculados a la sesión concreta de la cuenta y verificar que la sesión pertenezca al titular del token.

#### Scenario: Inicio y renovación
- **WHEN** una cuenta inicia sesión o renueva una sesión vigente
- **THEN** el token emitido identifica la cuenta y la sesión correspondiente sin exponer credenciales de renovación

#### Scenario: Asociación incorrecta
- **WHEN** se presenta un token cuya sesión no corresponde a la cuenta indicada
- **THEN** Identity rechaza la solicitud protegida

### Requirement: Rechazo inmediato después de la revocación
Identity MUST rechazar nuevas solicitudes protegidas cuyo token pertenezca a una sesión revocada, inexistente o vencida, aun cuando el JWT no haya vencido.

#### Scenario: Cierre de sesión
- **WHEN** se cierra una sesión y luego se usa su token anterior para una operación protegida
- **THEN** Identity rechaza la operación

#### Scenario: Revocación por reutilización
- **WHEN** una credencial de renovación reutilizada provoca la revocación de su sesión
- **THEN** Identity rechaza nuevas operaciones con los tokens de esa sesión

#### Scenario: Sesiones independientes
- **WHEN** se revoca una sesión y la misma cuenta tiene otra sesión vigente
- **THEN** los tokens de la otra sesión siguen siendo aceptables mientras cumplan las demás validaciones

#### Scenario: Operación ya autorizada
- **WHEN** una operación fue autorizada antes de hacerse efectiva la revocación
- **THEN** el sistema puede permitir que finalice

### Requirement: Transición de tokens anteriores
Identity MUST rechazar los tokens de acceso anteriores que no permitan identificar su sesión al activar el cambio.

#### Scenario: Token anterior sin sesión
- **WHEN** se presenta un token anterior sin identificador de sesión a una operación protegida
- **THEN** Identity lo rechaza y el cliente debe renovar el acceso o solicitar un nuevo inicio de sesión

### Requirement: Verificación para consumidores autorizados
Identity MUST permitir que un servicio autorizado verifique la vigencia de la sesión asociada a un token de acceso, sin exponer contraseñas ni credenciales de renovación.

#### Scenario: Servicio verifica una sesión activa
- **WHEN** un servicio autorizado verifica un token válido de una sesión activa
- **THEN** Identity confirma la identidad asociada y la vigencia de la sesión

#### Scenario: Token revocado o inválido
- **WHEN** un servicio autorizado verifica un token inválido, vencido o asociado a una sesión revocada
- **THEN** Identity rechaza la verificación sin confirmar la identidad

#### Scenario: Consumidor no autorizado
- **WHEN** un servicio sin credenciales válidas o sin permiso solicita la verificación
- **THEN** Identity rechaza la solicitud sin revelar información de la sesión

### Requirement: Integraciones futuras con verificación cerrada
Los futuros consumidores MUST verificar el estado vigente de la sesión antes de autorizar operaciones protegidas y MUST rechazar la operación si no pueden verificarlo.

#### Scenario: Identity no disponible
- **WHEN** un consumidor futuro no puede obtener una verificación confiable del estado de sesión
- **THEN** rechaza la nueva operación protegida

#### Scenario: Consulta después de un cierre
- **WHEN** un consumidor futuro intenta autorizar una operación con un token de una sesión ya cerrada
- **THEN** rechaza la operación aunque la firma y el vencimiento del JWT sean válidos
