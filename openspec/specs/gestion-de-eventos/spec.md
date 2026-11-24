# gestion-de-eventos Specification

## Purpose
Define el comportamiento observable para la gestión mínima del catálogo de eventos: alta, consulta, edición completa y baja lógica de eventos junto con sus modalidades de entrada (numerada o general). Las reservas, el control de stock y la concurrencia quedan fuera de este change.

## Requirements

### Requirement: Alta de evento
El sistema SHALL permitir crear un evento con sus modalidades mediante `POST /eventos`. El campo `nombre` es obligatorio y el `owner_id` viaja en el body. Los UUIDs del evento y modalidades SHALL ser autogenerados. Las modalidades `general` SHALL exigir `precio` y `cupo`. Las modalidades `numerado` SHALL exigir sectores con nombre, precio y asientos (`fila`, `numero`).

#### Scenario: Creación exitosa de evento
- **WHEN** se envía `POST /eventos` con `nombre`, `venue`, `fecha` y al menos una modalidad con `tipo` ∈ {`numerado`, `general`}
- **THEN** el sistema genera un UUID para el evento y sus modalidades, persiste la entidad con `activo: true` y responde con código 201 Created

#### Scenario: Creación rechazada por `nombre` faltante
- **WHEN** se envía `POST /eventos` omitiendo el campo `nombre`
- **THEN** el sistema responde con código 400 Bad Request y cuerpo `{"detail": "invalid body"}`

#### Scenario: Creación rechazada por `tipo` inválido
- **WHEN** se envía `POST /eventos` con una modalidad cuyo `tipo` no es `numerado` ni `general`
- **THEN** el sistema responde con código 400 Bad Request y cuerpo `{"detail": "invalid body"}`

#### Scenario: Creación rechazada por `precio` faltante en modalidad general
- **WHEN** se envía `POST /eventos` con una modalidad de tipo `general` sin `precio`
- **THEN** el sistema responde con código 400 Bad Request y cuerpo `{"detail": "invalid body"}`

#### Scenario: Creación rechazada por `cupo` faltante en modalidad general
- **WHEN** se envía `POST /eventos` con una modalidad de tipo `general` sin `cupo`
- **THEN** el sistema responde con código 400 Bad Request y cuerpo `{"detail": "invalid body"}`

#### Scenario: Creación exitosa de modalidad numerada con sectores y asientos
- **WHEN** se envía `POST /eventos` con una modalidad de tipo `numerado` con lista de sectores con precio y asientos
- **THEN** el sistema persiste los sectores con su precio y los asientos con estado `libre`, y los incluye en la respuesta 201 Created

### Requirement: Consulta de eventos y detalle
El sistema SHALL exponer la consulta del catálogo de eventos y detalle por identificador retornando cada evento tanto si su atributo `activo` es verdadero como si es falso. La respuesta SHALL incluir `precio` y `cupo` de cada modalidad general. Las modalidades de tipo `numerado` SHALL incluir la lista de sectores con su precio, sus asientos y su estado actual.

#### Scenario: Listado de eventos
- **WHEN** se solicita `GET /eventos`
- **THEN** el sistema responde con código 200 OK y la lista de todos los eventos registrados con sus modalidades, indicando el valor del campo `activo` de cada uno

#### Scenario: Detalle de evento existente
- **GIVEN** un evento registrado con un UUID determinado
- **WHEN** se solicita `GET /eventos/{id}`
- **THEN** el sistema responde con código 200 OK con la entidad completa incluyendo sus modalidades con `precio` y `cupo` (en general) o sectores con precio y asientos (en numerado)

#### Scenario: Consulta de evento inexistente
- **WHEN** se solicita `GET /eventos/{id}` con un UUID que no existe en el sistema
- **THEN** el sistema responde con código 404 Not Found

### Requirement: Edición completa de evento
El sistema SHALL permitir editar un evento y sus modalidades mediante `PUT /eventos/{id}`. Las modalidades pueden incluir opcionalmente su `id: UUID` para actualizar modalidades existentes preservando sus entidades hijas; las modalidades sin `id` se crean como nuevas. Las modalidades omitidas en el body son eliminadas únicamente si no poseen registros en el historial de reservas (`activa`, `confirmada` o `liberada`); en caso contrario el sistema MUST rechazar con 409 Conflict.

#### Scenario: Edición exitosa
- **GIVEN** un evento registrado con un UUID determinado sin reservas asociadas en sus modalidades a eliminar
- **WHEN** se envía `PUT /eventos/{id}` con datos válidos y un conjunto de modalidades con precio y cupo
- **THEN** el sistema reemplaza los campos del evento, actualiza las modalidades identificadas por `id` o crea las nuevas, y elimina las modalidades omitidas que no tengan historial, respondiendo con código 200 OK

#### Scenario: Edición exitosa preservando modalidad existente mediante id
- **GIVEN** un evento existente con una modalidad numerada o general con un `id` conocido
- **WHEN** se envía `PUT /eventos/{id}` enviando dicho `id` en la modalidad con nuevos datos de nombre o precio
- **THEN** el sistema actualiza la modalidad conservando su UUID original y las relaciones con sus entidades hijas

#### Scenario: Edición rechazada por modalidades con reservas o ventas asociadas
- **GIVEN** un evento existente con una modalidad que posee al menos una reserva en cualquier estado (`activa`, `confirmada` o `liberada`)
- **WHEN** se envía `PUT /eventos/{id}` omitiendo dicha modalidad del payload
- **THEN** el sistema responde con código 409 Conflict y preserva el evento y sus modalidades sin cambios

#### Scenario: Edición de evento inexistente
- **WHEN** se envía `PUT /eventos/{id}` con un UUID que no existe en el sistema
- **THEN** el sistema responde con código 404 Not Found

#### Scenario: Edición rechazada por datos inválidos
- **WHEN** se envía `PUT /eventos/{id}` omitiendo `nombre`, `precio` en general o con modalidades cuyo `tipo` no pertenece al enum
- **THEN** el sistema responde con código 400 Bad Request y cuerpo `{"detail": "invalid body"}`

### Requirement: Baja lógica de evento
El sistema SHALL permitir dar de baja un evento mediante `DELETE /eventos/{id}`, marcando `activo = false` sin eliminar el registro de la base de datos.

#### Scenario: Baja lógica exitosa
- **GIVEN** un evento activo con un UUID determinado
- **WHEN** se envía `DELETE /eventos/{id}`
- **THEN** el sistema actualiza `activo` a `false` preservando el registro y responde con código 200 OK

#### Scenario: Baja de evento inexistente
- **WHEN** se envía `DELETE /eventos/{id}` con un UUID que no existe en el sistema
- **THEN** el sistema responde con código 404 Not Found

### Requirement: Bitácora HTTP y correlación
El sistema SHALL interceptar cada solicitud HTTP para registrar en formato JSON estructurado a stdout: método, ruta, código de estado, tiempo transcurrido en milisegundos y un identificador de correlación `X-Correlation-Id`.

#### Scenario: Emisión de log estructurado
- **WHEN** se procesa cualquier solicitud HTTP
- **THEN** el sistema emite a stdout un registro JSON con `duration_ms`, `method`, `path`, `status_code` y `correlation_id`, propagando la cabecera `X-Correlation-Id` en la respuesta
