# gestion-de-compras Specification

## Purpose

Define el comportamiento observable del registro mínimo de compras de entradas: un cliente compra para un evento activo una modalidad general. Cupos, stock, montos y pagos quedan fuera de esta capability.

## Requirements

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

### Requirement: Idempotencia del registro
El sistema SHALL exigir la cabecera `Idempotency-Key` en `POST /compras`, con una longitud entre 1 y 255 caracteres, y SHALL tratar la clave como única por cliente. Repetir la solicitud con la misma clave y el mismo contenido MUST devolver la compra original sin crear otra.

#### Scenario: Reintento con la misma clave y el mismo contenido
- **GIVEN** una compra registrada con una clave de idempotencia determinada
- **WHEN** se envía `POST /compras` con la misma clave, el mismo cliente, evento y modalidad
- **THEN** el sistema responde con código 200 OK con la compra original y no crea una compra nueva

#### Scenario: Clave reutilizada con contenido distinto
- **GIVEN** una compra registrada con una clave de idempotencia determinada
- **WHEN** se envía `POST /compras` con la misma clave y el mismo cliente, pero con otro evento o modalidad
- **THEN** el sistema responde con código 409 Conflict y no crea una compra nueva

#### Scenario: Clave ausente o inválida
- **WHEN** se envía `POST /compras` sin la cabecera `Idempotency-Key`, con un valor vacío o con más de 255 caracteres
- **THEN** el sistema responde con código 400 Bad Request, cuerpo `{"detail": "invalid body"}` y no registra la compra

#### Scenario: Solicitudes concurrentes con la misma clave
- **WHEN** se reciben simultáneamente dos solicitudes idénticas con la misma clave de idempotencia
- **THEN** el sistema persiste una única compra y ambas respuestas devuelven la misma compra

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

### Requirement: Compensación automática de reserva
El sistema SHALL ejecutar una solicitud de liberación (`DELETE .../reservas/{reserva_id}`) en `events-service` si, tras haber reservado exitosamente una entrada, ocurre un fallo irrecuperable en la confirmación o la persistencia de la compra.

#### Scenario: Liberación de reserva ante fallo de confirmación
- **GIVEN** una reserva generada exitosamente en `events-service`
- **WHEN** la confirmación en `events-service` falla con un error 5xx o timeout
- **THEN** `compras-service` envía la solicitud de liberación de la reserva a `events-service` y responde con código 503 Service Unavailable sin persistir la compra como confirmada

### Requirement: Bitácora HTTP y correlación
El sistema SHALL interceptar cada solicitud HTTP para registrar en formato JSON estructurado a stdout: método, ruta, código de estado, tiempo transcurrido en milisegundos y un identificador de correlación `X-Correlation-Id`. Al consultar `events-service`, el sistema SHALL propagar ese identificador.

#### Scenario: Emisión de log estructurado
- **WHEN** se procesa cualquier solicitud HTTP
- **THEN** el sistema emite a stdout un registro JSON con `duration_ms`, `method`, `path`, `status_code` y `correlation_id`, y devuelve la cabecera `X-Correlation-Id` en la respuesta

#### Scenario: Propagación al catálogo
- **WHEN** el sistema consulta `events-service` para procesar una solicitud
- **THEN** la consulta incluye la cabecera `X-Correlation-Id` de la solicitud original

### Requirement: Validación vigente para compras
Compras MUST verificar la sesión y el rol actual antes de autorizar nuevas operaciones protegidas y MUST rechazar la operación si Identity no puede verificarlos.

#### Scenario: Sesión revocada
- **WHEN** una cuenta intenta operar en Compras con un token de una sesión revocada
- **THEN** Compras rechaza la operación

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
