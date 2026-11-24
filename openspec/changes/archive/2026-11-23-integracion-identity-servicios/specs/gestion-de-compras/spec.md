# Spec Delta: gestión de compras

## MODIFIED Requirements

### Requirement: Registro de compra
El sistema SHALL permitir registrar una compra mediante `POST /compras` con `evento_id` y `modalidad_id` en el body. El sistema SHALL generar el UUID de la compra y su fecha de creación. La cuenta MUST tener sesión vigente y rol cliente activo. `cliente_id` es opcional y, si se envía, MUST coincidir con la cuenta autenticada, que se registra como cliente.

#### Scenario: Registro exitoso
- **GIVEN** un evento activo con una modalidad de tipo `general`
- **WHEN** un cliente activo envía `POST /compras` con la cabecera `Idempotency-Key` y los identificadores del evento y la modalidad
- **THEN** el sistema persiste la compra con su cuenta autenticada, UUID y fecha de creación, y responde con código 201 Created con la compra registrada

#### Scenario: Registro rechazado por datos inválidos
- **WHEN** un cliente activo envía `POST /compras` sin `evento_id` o `modalidad_id`, o con un identificador proporcionado que no es UUID
- **THEN** el sistema responde con código 400 Bad Request y cuerpo `{"detail": "invalid body"}`

#### Scenario: Cliente proporcionado coincide
- **WHEN** un cliente activo envía su propio identificador en `cliente_id`
- **THEN** el sistema acepta ese identificador respecto de la validación de identidad

#### Scenario: Cliente proporcionado no coincide
- **WHEN** una cuenta autenticada envía un `cliente_id` distinto de su cuenta
- **THEN** el sistema rechaza la operación sin registrar la compra

#### Scenario: Sin autorización para comprar
- **WHEN** una solicitud no tiene sesión válida o la cuenta no tiene rol cliente activo
- **THEN** el sistema rechaza la operación sin registrar la compra

### Requirement: Consulta de compras
El sistema SHALL permitir consultar una compra por identificador mediante `GET /compras/{id}` y listar las compras de la cuenta autenticada mediante `GET /compras`, ordenadas de la más reciente a la más antigua. La cuenta MUST tener sesión vigente y rol cliente activo. `cliente_id` en la consulta es opcional y, si se proporciona, MUST coincidir con la cuenta autenticada. El detalle MUST limitarse a compras propias.

#### Scenario: Detalle de compra existente
- **GIVEN** una compra registrada
- **WHEN** su cliente autenticado y activo solicita `GET /compras/{id}`
- **THEN** el sistema responde con código 200 OK con `id`, `cliente_id`, `evento_id`, `modalidad_id` y fecha de creación

#### Scenario: Compra inexistente
- **WHEN** un cliente autenticado y activo solicita `GET /compras/{id}` con un UUID que no existe
- **THEN** el sistema responde con código 404 Not Found

#### Scenario: Listado de compras de un cliente
- **GIVEN** un cliente con varias compras y otro cliente con compras distintas
- **WHEN** el primer cliente autenticado y activo solicita `GET /compras` con o sin su `cliente_id`
- **THEN** el sistema responde con código 200 OK solo con las compras de ese cliente, de la más reciente a la más antigua

#### Scenario: Listado sin cliente válido
- **WHEN** un cliente activo solicita `GET /compras` con un `cliente_id` proporcionado que no es UUID
- **THEN** el sistema responde con código 400 Bad Request

#### Scenario: Detalle de compra ajena
- **WHEN** una cuenta solicita el detalle de una compra que pertenece a otra cuenta
- **THEN** el sistema rechaza la solicitud sin revelar la compra

#### Scenario: Listado de otro cliente
- **WHEN** una cuenta proporciona en `cliente_id` un identificador distinto del suyo
- **THEN** el sistema rechaza la solicitud sin revelar compras ajenas

## ADDED Requirements

### Requirement: Validación vigente para compras
Compras MUST verificar la sesión y el rol actual antes de autorizar nuevas operaciones protegidas y MUST rechazar la operación si Identity no puede verificarlos.

#### Scenario: Sesión revocada
- **WHEN** una cuenta intenta operar en Compras con un token de una sesión revocada
- **THEN** el sistema rechaza la operación

#### Scenario: Identity no disponible
- **WHEN** Compras no puede comprobar de forma confiable la sesión o los roles
- **THEN** rechaza la operación protegida sin modificar ni revelar compras

### Requirement: Transporte para verificación de compras
Compras MUST usar HTTPS con verificación de certificados para comunicarse con Identity, salvo una excepción explícita de HTTP para desarrollo local o pruebas aisladas con credenciales de prueba.

#### Scenario: HTTP fuera del entorno local
- **WHEN** se configura HTTP hacia Identity fuera de desarrollo local o pruebas aisladas
- **THEN** Compras no autoriza operaciones protegidas

#### Scenario: Excepción local no habilitada
- **WHEN** se configura HTTP local sin habilitar explícitamente la excepción
- **THEN** Compras no autoriza operaciones protegidas

#### Scenario: Excepción local habilitada
- **WHEN** se habilita explícitamente HTTP en desarrollo local o pruebas aisladas con credenciales de prueba
- **THEN** Compras puede verificar la sesión y los roles mediante esa configuración
