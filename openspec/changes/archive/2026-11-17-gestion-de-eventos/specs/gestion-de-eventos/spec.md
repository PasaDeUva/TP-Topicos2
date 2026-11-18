# Spec Delta: Gestión de Eventos (`gestion-de-eventos`)

## Purpose

Define el comportamiento observable para la gestión mínima del catálogo de eventos: alta, consulta, edición completa y baja lógica de eventos junto con sus modalidades de entrada (numerada o general). Las reservas, el control de stock y la concurrencia quedan fuera de este change.

## ADDED Requirements

### Requirement: Alta de evento
El sistema SHALL permitir crear un evento con sus modalidades mediante `POST /eventos`. El campo `nombre` es obligatorio. El campo `owner_id` viaja en el body; la autenticación del organizador se delega a un change futuro. Los UUIDs del evento y sus modalidades SHALL ser autogenerados por el sistema.

#### Scenario: Creación exitosa de evento
- **WHEN** se envía `POST /eventos` con `nombre`, `venue`, `fecha` y al menos una modalidad con `tipo` ∈ {`numerado`, `general`}
- **THEN** el sistema genera un UUID para el evento y sus modalidades, persiste la entidad con `activo: true` y responde con código 201 Created

#### Scenario: Creación rechazada por `nombre` faltante
- **WHEN** se envía `POST /eventos` omitiendo el campo `nombre`
- **THEN** el sistema responde con código 400 Bad Request y cuerpo `{"detail": "invalid body"}`

#### Scenario: Creación rechazada por `tipo` inválido
- **WHEN** se envía `POST /eventos` con una modalidad cuyo `tipo` no es `numerado` ni `general`
- **THEN** el sistema responde con código 400 Bad Request y cuerpo `{"detail": "invalid body"}`

### Requirement: Consulta de eventos y detalle
El sistema SHALL exponer la consulta del catálogo de eventos y detalle por identificador retornando cada evento tanto si su atributo `activo` es verdadero como si es falso.

#### Scenario: Listado de eventos
- **WHEN** se solicita `GET /eventos`
- **THEN** el sistema responde con código 200 OK y la lista de todos los eventos registrados con sus modalidades, indicando el valor del campo `activo` de cada uno

#### Scenario: Detalle de evento existente
- **GIVEN** un evento registrado con un UUID determinado
- **WHEN** se solicita `GET /eventos/{id}`
- **THEN** el sistema responde con código 200 OK con la entidad completa incluyendo sus modalidades

#### Scenario: Consulta de evento inexistente
- **WHEN** se solicita `GET /eventos/{id}` con un UUID que no existe en el sistema
- **THEN** el sistema responde con código 404 Not Found

### Requirement: Edición completa de evento
El sistema SHALL permitir reemplazar completamente un evento y todas sus modalidades mediante `PUT /eventos/{id}`. Las modalidades omitidas en el body son eliminadas (semántica de reemplazo total).

#### Scenario: Edición exitosa
- **GIVEN** un evento registrado con un UUID determinado
- **WHEN** se envía `PUT /eventos/{id}` con datos válidos y un conjunto de modalidades
- **THEN** el sistema reemplaza los campos del evento y elimina las modalidades anteriores sustituyéndolas por las nuevas, respondiendo con código 200 OK

#### Scenario: Edición de evento inexistente
- **WHEN** se envía `PUT /eventos/{id}` con un UUID que no existe en el sistema
- **THEN** el sistema responde con código 404 Not Found

#### Scenario: Edición rechazada por datos inválidos
- **WHEN** se envía `PUT /eventos/{id}` omitiendo `nombre` o con modalidades cuyo `tipo` no pertenece al enum
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
