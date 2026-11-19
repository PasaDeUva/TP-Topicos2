# Spec Delta: Gestión de Eventos (`gestion-de-eventos`)

## MODIFIED Requirements

### Requirement: Alta de evento
El sistema SHALL permitir crear un evento con sus modalidades mediante `POST /eventos`. El campo `nombre` es obligatorio. El campo `owner_id` viaja en el body; la autenticación del organizador se delega a un change futuro. Los UUIDs del evento y sus modalidades SHALL ser autogenerados por el sistema. Cada modalidad SHALL incluir `precio` (obligatorio) y `cupo` (obligatorio si `tipo` es `general`). Las modalidades de tipo `numerado` SHALL aceptar una lista de sectores; cada sector incluye su nombre, precio propio y lista de asientos con `fila` y `numero`.

#### Scenario: Creación exitosa de evento
- **WHEN** se envía `POST /eventos` con `nombre`, `venue`, `fecha` y al menos una modalidad con `tipo` ∈ {`numerado`, `general`}
- **THEN** el sistema genera un UUID para el evento y sus modalidades, persiste la entidad con `activo: true` y responde con código 201 Created

#### Scenario: Creación rechazada por `nombre` faltante
- **WHEN** se envía `POST /eventos` omitiendo el campo `nombre`
- **THEN** el sistema responde con código 400 Bad Request y cuerpo `{"detail": "invalid body"}`

#### Scenario: Creación rechazada por `tipo` inválido
- **WHEN** se envía `POST /eventos` con una modalidad cuyo `tipo` no es `numerado` ni `general`
- **THEN** el sistema responde con código 400 Bad Request y cuerpo `{"detail": "invalid body"}`

#### Scenario: Creación rechazada por `precio` faltante en modalidad
- **WHEN** se envía `POST /eventos` con una modalidad sin `precio`
- **THEN** el sistema responde con código 400 Bad Request y cuerpo `{"detail": "invalid body"}`

#### Scenario: Creación rechazada por `cupo` faltante en modalidad general
- **WHEN** se envía `POST /eventos` con una modalidad de tipo `general` sin `cupo`
- **THEN** el sistema responde con código 400 Bad Request y cuerpo `{"detail": "invalid body"}`

#### Scenario: Creación exitosa de modalidad numerada con sectores y asientos
- **WHEN** se envía `POST /eventos` con una modalidad de tipo `numerado` con lista de sectores y asientos
- **THEN** el sistema persiste los sectores con su precio y los asientos con estado `libre`, y los incluye en la respuesta 201 Created

### Requirement: Consulta de eventos y detalle
El sistema SHALL exponer la consulta del catálogo de eventos y detalle por identificador retornando cada evento tanto si su atributo `activo` es verdadero como si es falso. La respuesta SHALL incluir `precio` y `cupo` de cada modalidad. Las modalidades de tipo `numerado` SHALL incluir la lista de sectores con sus asientos y su estado actual.

#### Scenario: Listado de eventos
- **WHEN** se solicita `GET /eventos`
- **THEN** el sistema responde con código 200 OK y la lista de todos los eventos registrados con sus modalidades, indicando el valor del campo `activo` de cada uno

#### Scenario: Detalle de evento existente
- **GIVEN** un evento registrado con un UUID determinado
- **WHEN** se solicita `GET /eventos/{id}`
- **THEN** el sistema responde con código 200 OK con la entidad completa incluyendo sus modalidades con `precio`, `cupo` (en general) y sectores con asientos (en numerado)

#### Scenario: Consulta de evento inexistente
- **WHEN** se solicita `GET /eventos/{id}` con un UUID que no existe en el sistema
- **THEN** el sistema responde con código 404 Not Found

### Requirement: Edición completa de evento
El sistema SHALL permitir reemplazar completamente un evento y todas sus modalidades mediante `PUT /eventos/{id}`. Las modalidades omitidas en el body son eliminadas (semántica de reemplazo total). Las reglas de validación de `precio`, `cupo` y sectores aplican igual que en el alta.

#### Scenario: Edición exitosa
- **GIVEN** un evento registrado con un UUID determinado
- **WHEN** se envía `PUT /eventos/{id}` con datos válidos y un conjunto de modalidades con precio y cupo
- **THEN** el sistema reemplaza los campos del evento y elimina las modalidades anteriores sustituyéndolas por las nuevas, respondiendo con código 200 OK

#### Scenario: Edición de evento inexistente
- **WHEN** se envía `PUT /eventos/{id}` con un UUID que no existe en el sistema
- **THEN** el sistema responde con código 404 Not Found

#### Scenario: Edición rechazada por datos inválidos
- **WHEN** se envía `PUT /eventos/{id}` omitiendo `nombre`, `precio` o con modalidades cuyo `tipo` no pertenece al enum
- **THEN** el sistema responde con código 400 Bad Request y cuerpo `{"detail": "invalid body"}`
