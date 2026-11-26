# Spec Delta: gestion-de-compras

## MODIFIED Requirements

### Requirement: Registro de compra
El sistema SHALL permitir registrar una compra mediante `POST /compras` con `evento_id`, `modalidad_id` y opcionalmente `asiento_id` en el body. El sistema SHALL exigir `asiento_id` cuando la modalidad seleccionada sea de tipo `numerado`, y SHALL rechazar la presencia de `asiento_id` cuando la modalidad sea de tipo `general`. El sistema SHALL generar el UUID de la compra, asociar el `reserva_id` obtenido del inventario, registrar su `estado` como `confirmada` y guardar la fecha de creación. La cuenta MUST tener sesión vigente y rol cliente activo. `cliente_id` es opcional y, si se envía, MUST coincidir con la cuenta autenticada, que se registra como cliente.

#### Scenario: Registro exitoso
- **GIVEN** un evento activo con una modalidad de tipo `general` con cupo disponible
- **WHEN** un cliente activo envía `POST /compras` con la cabecera `Idempotency-Key` y los identificadores del evento y la modalidad sin `asiento_id`
- **THEN** el sistema reserva y confirma la entrada en `events-service`, persiste la compra con su cuenta autenticada, `estado: "confirmada"`, UUID autogenerado, `reserva_id` y fecha de creación, y responde 201 Created

#### Scenario: Registro exitoso en modalidad numerada
- **GIVEN** un evento activo con una modalidad de tipo `numerado` y un asiento libre identificado por `asiento_id`
- **WHEN** un cliente activo envía `POST /compras` con la cabecera `Idempotency-Key`, identificadores de evento, modalidad y el `asiento_id` correspondiente
- **THEN** el sistema reserva y confirma el asiento en `events-service`, persiste la compra con su cuenta autenticada, `asiento_id`, `reserva_id` y `estado: "confirmada"`, y responde 201 Created

#### Scenario: Registro rechazado por datos inválidos
- **WHEN** un cliente activo envía `POST /compras` sin `evento_id` o `modalidad_id`, o con un identificador proporcionado que no es UUID
- **THEN** el sistema responde con código 400 Bad Request y cuerpo `{"detail": "invalid body"}`

#### Scenario: Modalidad numerada sin asiento_id
- **GIVEN** un evento activo con una modalidad de tipo `numerado`
- **WHEN** se envía `POST /compras` omitiendo el campo `asiento_id`
- **THEN** el sistema responde con código 400 Bad Request y cuerpo `{"detail": "invalid body"}`

#### Scenario: Modalidad general con asiento_id provisto
- **GIVEN** un evento activo con una modalidad de tipo `general`
- **WHEN** se envía `POST /compras` incluyendo un `asiento_id`
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

### Requirement: Validación contra el catálogo de eventos
El sistema SHALL validar el evento y la modalidad consultando `GET /eventos/{id}` de `events-service`, y orquestar la reserva y confirmación en el inventario. El sistema MUST rechazar la compra si el evento no existe, si la modalidad no pertenece al evento, si el evento está inactivo, si el inventario responde sin disponibilidad o conflicto de asiento (409), o si `events-service` no está disponible (503).

#### Scenario: Evento inexistente
- **WHEN** se envía `POST /compras` con un `evento_id` que `events-service` no conoce
- **THEN** el sistema responde con código 404 Not Found y no registra la compra

#### Scenario: Modalidad que no pertenece al evento
- **GIVEN** un evento existente
- **WHEN** se envía `POST /compras` con un `modalidad_id` que no figura entre las modalidades de ese evento
- **THEN** el sistema responde con código 404 Not Found y no registra la compra

#### Scenario: Evento inactivo
- **GIVEN** un evento con `activo: false`
- **WHEN** se envía `POST /compras` para una de sus modalidades
- **THEN** el sistema responde con código 409 Conflict y no registra la compra

#### Scenario: Modalidad no general
- **GIVEN** un evento activo con una modalidad de tipo `numerado` donde el asiento solicitado no está disponible
- **WHEN** se envía `POST /compras` para esa modalidad y asiento
- **THEN** el sistema responde con código 409 Conflict y no registra la compra

#### Scenario: Sin cupo disponible en modalidad general
- **GIVEN** un evento activo con modalidad `general` cuyo cupo se encuentra agotado
- **WHEN** se envía `POST /compras` para dicha modalidad
- **THEN** `events-service` responde 409 en la reserva, `compras-service` responde 409 Conflict al cliente y no registra la compra

#### Scenario: Asiento no disponible en modalidad numerada
- **GIVEN** un evento activo con modalidad `numerado` y un asiento en estado `reservado` o `vendido`
- **WHEN** se envía `POST /compras` intentando comprar dicho asiento
- **THEN** `events-service` responde 409 en la reserva, `compras-service` responde 409 Conflict al cliente y no registra la compra

#### Scenario: Catálogo no disponible
- **WHEN** `events-service` no responde o devuelve un error inesperado al validar el evento o procesar la reserva
- **THEN** el sistema responde con código 503 Service Unavailable y no registra la compra

### Requirement: Consulta de compras
El sistema SHALL permitir consultar una compra por identificador mediante `GET /compras/{id}` y listar las compras de la cuenta autenticada mediante `GET /compras`, ordenadas de la más reciente a la más antigua, incluyendo en la respuesta `id`, `cliente_id`, `evento_id`, `modalidad_id`, `reserva_id`, `asiento_id`, `estado` y `creado_en`. La cuenta MUST tener sesión vigente y rol cliente activo. `cliente_id` en la consulta es opcional y, si se proporciona, MUST coincidir con la cuenta autenticada. El detalle MUST limitarse a compras propias.

#### Scenario: Detalle de compra existente
- **GIVEN** una compra registrada
- **WHEN** su cliente autenticado y activo solicita `GET /compras/{id}`
- **THEN** el sistema responde con código 200 OK incluyendo `id`, `cliente_id`, `evento_id`, `modalidad_id`, `reserva_id`, `asiento_id`, `estado` y `creado_en`

#### Scenario: Compra inexistente
- **WHEN** un cliente autenticado y activo solicita `GET /compras/{id}` con un UUID que no existe
- **THEN** el sistema responde con código 404 Not Found

#### Scenario: Listado de compras de un cliente
- **GIVEN** un cliente con varias compras y otro cliente con compras distintas
- **WHEN** el primer cliente autenticado y activo solicita `GET /compras` con o sin su `cliente_id`
- **THEN** el sistema responde con código 200 OK solo con las compras de ese cliente, de la más reciente a la más antigua con todos sus atributos

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

### Requirement: Compensación automática de reserva
El sistema SHALL ejecutar una solicitud de liberación (`DELETE .../reservas/{reserva_id}`) en `events-service` si, tras haber reservado exitosamente una entrada, ocurre un fallo irrecuperable en la confirmación o la persistencia de la compra.

#### Scenario: Liberación de reserva ante fallo de confirmación
- **GIVEN** una reserva generada exitosamente en `events-service`
- **WHEN** la confirmación en `events-service` falla con un error 5xx o timeout
- **THEN** `compras-service` envía la solicitud de liberación de la reserva a `events-service` y responde con código 503 Service Unavailable sin persistir la compra como confirmada
