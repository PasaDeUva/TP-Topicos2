# Spec Delta: Gestión de Compras (`gestion-de-compras`)

## Purpose

Define el comportamiento observable del registro mínimo de compras de entradas: un cliente compra para un evento activo una modalidad general. Cupos, stock, montos y pagos quedan fuera de esta capability.

## ADDED Requirements

### Requirement: Registro de compra
El sistema SHALL permitir registrar una compra mediante `POST /compras` con `cliente_id`, `evento_id` y `modalidad_id` en el body. El sistema SHALL generar el UUID de la compra y su fecha de creación. El `cliente_id` no se autentica en esta etapa.

#### Scenario: Registro exitoso
- **GIVEN** un evento activo con una modalidad de tipo `general`
- **WHEN** se envía `POST /compras` con la cabecera `Idempotency-Key` y los identificadores del cliente, el evento y la modalidad
- **THEN** el sistema persiste la compra con su UUID y fecha de creación, y responde con código 201 Created con la compra registrada

#### Scenario: Registro rechazado por datos inválidos
- **WHEN** se envía `POST /compras` sin `cliente_id`, `evento_id` o `modalidad_id`, o con alguno que no es un UUID
- **THEN** el sistema responde con código 400 Bad Request y cuerpo `{"detail": "invalid body"}`

### Requirement: Validación contra el catálogo de eventos
El sistema SHALL validar el evento y la modalidad consultando `GET /eventos/{id}` de `events-service`, sin modificar el catálogo. El sistema MUST rechazar la compra si el evento no existe, si la modalidad no pertenece al evento, si el evento está inactivo o si la modalidad no es `general`.

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
- **GIVEN** un evento activo con una modalidad de tipo `numerado`
- **WHEN** se envía `POST /compras` para esa modalidad
- **THEN** el sistema responde con código 409 Conflict y no registra la compra

#### Scenario: Catálogo no disponible
- **WHEN** `events-service` no responde o devuelve un error inesperado al validar el evento
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
El sistema SHALL permitir consultar una compra por identificador mediante `GET /compras/{id}` y listar las compras de un cliente mediante `GET /compras?cliente_id={id}`, ordenadas de la más reciente a la más antigua.

#### Scenario: Detalle de compra existente
- **GIVEN** una compra registrada
- **WHEN** se solicita `GET /compras/{id}`
- **THEN** el sistema responde con código 200 OK con `id`, `cliente_id`, `evento_id`, `modalidad_id` y fecha de creación

#### Scenario: Compra inexistente
- **WHEN** se solicita `GET /compras/{id}` con un UUID que no existe
- **THEN** el sistema responde con código 404 Not Found

#### Scenario: Listado de compras de un cliente
- **GIVEN** un cliente con varias compras y otro cliente con compras distintas
- **WHEN** se solicita `GET /compras?cliente_id={id}`
- **THEN** el sistema responde con código 200 OK solo con las compras de ese cliente, de la más reciente a la más antigua

#### Scenario: Listado sin cliente válido
- **WHEN** se solicita `GET /compras` sin `cliente_id` o con un valor que no es UUID
- **THEN** el sistema responde con código 400 Bad Request

### Requirement: Bitácora HTTP y correlación
El sistema SHALL interceptar cada solicitud HTTP para registrar en formato JSON estructurado a stdout: método, ruta, código de estado, tiempo transcurrido en milisegundos y un identificador de correlación `X-Correlation-Id`. Al consultar `events-service`, el sistema SHALL propagar ese identificador.

#### Scenario: Emisión de log estructurado
- **WHEN** se procesa cualquier solicitud HTTP
- **THEN** el sistema emite a stdout un registro JSON con `duration_ms`, `method`, `path`, `status_code` y `correlation_id`, y devuelve la cabecera `X-Correlation-Id` en la respuesta

#### Scenario: Propagación al catálogo
- **WHEN** el sistema consulta `events-service` para procesar una solicitud
- **THEN** la consulta incluye la cabecera `X-Correlation-Id` de la solicitud original
