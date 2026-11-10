# Spec Delta: Publicación de Eventos (`publicacion-eventos`)

## Purpose

Define el comportamiento para la gestión inicial de eventos en borrador, incluyendo su creación, edición, persistencia de metadatos opcionales, consulta de eventos propios por el organizador y observabilidad mediante middleware de bitácora HTTP.

## ADDED Requirements

### Requirement: Creación de evento en estado borrador
El sistema SHALL permitir a un usuario autenticado con rol de organizador crear un nuevo evento en estado BORRADOR proporcionando los datos descriptivos y sus modalidades de entrada iniciales.

#### Scenario: Creación exitosa de borrador
- **GIVEN** una cabecera `X-User-Role: organizador` y `X-User-Id` válidos
- **WHEN** el organizador envía una petición POST a `/eventos` con datos descriptivos válidos y modalidades con precio y cupo positivos
- **THEN** el sistema responde con código 201 Created y el evento persistido en estado BORRADOR

#### Scenario: Creación rechazada por falta de campos obligatorios
- **WHEN** se envía una petición POST a `/eventos` omitiendo nombre, descripción o fechas
- **THEN** el sistema responde con código 422 Unprocessable Entity detallando los campos faltantes

#### Scenario: Petición sin autenticación de organizador
- **WHEN** se envía una petición POST a `/eventos` sin cabeceras de usuario
- **THEN** el sistema responde con código 401 Unauthorized

### Requirement: Consulta y listado de eventos de un organizador
El sistema SHALL permitir al organizador listar y consultar el detalle de todos sus eventos creados, independientemente del estado en el que se encuentren, restringiendo el acceso a eventos ajenos.

#### Scenario: Listado de eventos propios
- **GIVEN** un organizador con eventos creados en diversos estados
- **WHEN** solicita un GET a `/eventos` con su cabecera `X-User-Id`
- **THEN** el sistema responde con código 200 OK y el listado de todos sus eventos asociados

#### Scenario: Detalle de evento propio
- **WHEN** solicita un GET a `/eventos/{id}` siendo el creador del evento
- **THEN** el sistema responde con código 200 OK con la entidad completa del evento y sus modalidades

#### Scenario: Intento de consulta de evento ajeno
- **WHEN** solicita un GET a `/eventos/{id}` perteneciendo el evento a otro organizador
- **THEN** el sistema responde con código 403 Forbidden

### Requirement: Edición de evento en borrador y protección de compras
El sistema SHALL permitir la modificación libre de campos de un evento mientras permanezca en BORRADOR, y SHALL rechazar cambios de precio o cupo sobre modalidades adquiridas si existen compras o reservas previas.

#### Scenario: Edición exitosa de evento en borrador
- **GIVEN** un evento en estado BORRADOR perteneciente al organizador solicitante
- **WHEN** envía un PUT a `/eventos/{id}` con nuevos datos descriptivos o modalidades
- **THEN** el sistema actualiza la entidad y responde con código 200 OK

#### Scenario: Rechazo de edición si el evento ya está publicado
- **GIVEN** un evento en estado PUBLICADO
- **WHEN** envía un PUT a `/eventos/{id}`
- **THEN** el sistema responde con código 409 Conflict indicando que debe despublicarse antes de editar

#### Scenario: Rechazo de modificación de precio o cupo con compras existentes
- **GIVEN** un evento que posee reservas confirmadas o tickets vendidos
- **WHEN** se intenta modificar el precio o reducir el cupo de una modalidad adquirida
- **THEN** el sistema responde con código 409 Conflict protegiendo las condiciones adquiridas

### Requirement: Bitácora HTTP estructurada y correlación
El sistema SHALL interceptar cada solicitud HTTP entrante para emitir un registro de log estructurado en formato JSON a stdout conteniendo método, ruta, código de estado, duración en milisegundos y un identificador único de correlación.

#### Scenario: Emisión de log estructurado con correlation id generado
- **WHEN** se recibe una petición HTTP sin cabecera `X-Correlation-Id`
- **THEN** el sistema genera un UUID para la correlación, propaga dicho valor en la respuesta HTTP y emite un log JSON a stdout con duration_ms, method, path y status_code

#### Scenario: Propagación de correlation id existente
- **GIVEN** una petición con cabecera `X-Correlation-Id: abc-123`
- **WHEN** el servidor completa el procesamiento
- **THEN** el sistema emite el log JSON conteniendo `abc-123` en el campo correlation_id y retorna la misma cabecera en la respuesta
