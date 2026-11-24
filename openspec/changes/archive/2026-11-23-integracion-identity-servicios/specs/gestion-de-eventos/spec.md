# Spec Delta: gestión de eventos

## MODIFIED Requirements

### Requirement: Alta de evento
El sistema SHALL permitir crear un evento con modalidades mediante `POST /eventos`. `nombre` es obligatorio. La cuenta autenticada MUST ser organizador habilitado y propietario; `owner_id` es opcional y MUST coincidir si se envía. El sistema SHALL generar los UUIDs. Las modalidades generales SHALL exigir precio y cupo; las numeradas SHALL exigir sectores con nombre, precio y asientos (fila y número).

#### Scenario: Creación exitosa de evento
- **WHEN** un organizador habilitado envía `POST /eventos` con `nombre`, `venue`, `fecha` y al menos una modalidad válida de tipo `numerado` o `general`
- **THEN** el sistema genera un UUID para el evento y sus modalidades, asigna como propietario la cuenta autenticada, persiste la entidad con `activo: true` y responde con código 201 Created

#### Scenario: Creación rechazada por `nombre` faltante
- **WHEN** un organizador habilitado envía `POST /eventos` omitiendo el campo `nombre`
- **THEN** el sistema responde con código 400 Bad Request y cuerpo `{"detail": "invalid body"}`

#### Scenario: Creación rechazada por `tipo` inválido
- **WHEN** un organizador habilitado envía `POST /eventos` con una modalidad cuyo `tipo` no es `numerado` ni `general`
- **THEN** el sistema responde con código 400 Bad Request y cuerpo `{"detail": "invalid body"}`

#### Scenario: Creación rechazada por `precio` faltante en modalidad general
- **WHEN** un organizador habilitado envía `POST /eventos` con una modalidad de tipo `general` sin `precio`
- **THEN** el sistema responde con código 400 Bad Request y cuerpo `{"detail": "invalid body"}`

#### Scenario: Creación rechazada por `cupo` faltante en modalidad general
- **WHEN** un organizador habilitado envía `POST /eventos` con una modalidad de tipo `general` sin `cupo`
- **THEN** el sistema responde con código 400 Bad Request y cuerpo `{"detail": "invalid body"}`

#### Scenario: Creación exitosa de modalidad numerada con sectores y asientos
- **WHEN** un organizador habilitado envía `POST /eventos` con una modalidad de tipo `numerado` con lista de sectores con precio y asientos
- **THEN** el sistema persiste los sectores con su precio y los asientos con estado `libre`, y los incluye en la respuesta 201 Created

#### Scenario: Propietario proporcionado coincide
- **WHEN** un organizador habilitado envía su propio identificador en `owner_id`
- **THEN** el sistema acepta ese identificador respecto de la validación de propiedad

#### Scenario: Propietario proporcionado no coincide
- **WHEN** una persona autenticada envía un `owner_id` distinto de su cuenta
- **THEN** el sistema rechaza la solicitud sin crear un evento

#### Scenario: Sin autorización para crear
- **WHEN** una solicitud carece de sesión válida o la cuenta no tiene rol organizador habilitado
- **THEN** el sistema rechaza la creación sin modificar datos

### Requirement: Edición completa de evento
El sistema SHALL permitir editar un evento y sus modalidades mediante `PUT /eventos/{id}`. La cuenta MUST tener sesión vigente, rol organizador habilitado y ser propietaria; `owner_id` es opcional y MUST coincidir si se envía. Las modalidades con `id` existente preservan sus entidades hijas; las sin `id` se crean. Las omitidas solo se eliminan sin historial de reservas; en caso contrario el sistema MUST responder 409 Conflict. La propiedad no se transfiere.

#### Scenario: Edición exitosa
- **GIVEN** un evento registrado sin reservas asociadas en sus modalidades a eliminar
- **WHEN** su propietario con rol organizador habilitado envía `PUT /eventos/{id}` con datos válidos y un conjunto de modalidades
- **THEN** el sistema actualiza los campos y las modalidades identificadas por `id`, crea las nuevas y elimina las omitidas sin historial, respondiendo con código 200 OK

#### Scenario: Edición exitosa preservando modalidad existente mediante id
- **GIVEN** un evento existente con una modalidad numerada o general con un `id` conocido
- **WHEN** su propietario con rol organizador habilitado envía `PUT /eventos/{id}` con dicho `id` y nuevos datos de nombre o precio
- **THEN** el sistema actualiza la modalidad conservando su UUID original y las relaciones con sus entidades hijas

#### Scenario: Edición rechazada por modalidades con reservas o ventas asociadas
- **GIVEN** un evento existente con una modalidad que posee al menos una reserva en cualquier estado (`activa`, `confirmada` o `liberada`)
- **WHEN** su propietario con rol organizador habilitado envía `PUT /eventos/{id}` omitiendo dicha modalidad del payload
- **THEN** el sistema responde con código 409 Conflict y preserva el evento y sus modalidades sin cambios

#### Scenario: Edición de evento inexistente
- **WHEN** un organizador habilitado envía `PUT /eventos/{id}` con un UUID que no existe en el sistema
- **THEN** el sistema responde con código 404 Not Found

#### Scenario: Edición rechazada por datos inválidos
- **WHEN** el propietario habilitado envía `PUT /eventos/{id}` omitiendo `nombre`, `precio` en general o con modalidades cuyo `tipo` no pertenece al enum
- **THEN** el sistema responde con código 400 Bad Request y cuerpo `{"detail": "invalid body"}`

#### Scenario: Edición de evento ajeno
- **WHEN** una cuenta intenta editar un evento que pertenece a otra cuenta
- **THEN** el sistema rechaza la solicitud sin modificar el evento

#### Scenario: Intento de cambiar propietario
- **WHEN** el propietario envía un `owner_id` distinto de su cuenta autenticada
- **THEN** el sistema rechaza la solicitud sin transferir ni modificar el evento

### Requirement: Baja lógica de evento
El sistema SHALL permitir dar de baja un evento mediante `DELETE /eventos/{id}`, marcando `activo = false` sin eliminar el registro de la base de datos. La cuenta MUST tener sesión vigente, rol organizador habilitado y ser propietaria del evento.

#### Scenario: Baja lógica exitosa
- **GIVEN** un evento activo con un UUID determinado
- **WHEN** su propietario con rol organizador habilitado envía `DELETE /eventos/{id}`
- **THEN** el sistema actualiza `activo` a `false` preservando el registro y responde con código 200 OK

#### Scenario: Baja de evento inexistente
- **WHEN** un organizador habilitado envía `DELETE /eventos/{id}` con un UUID que no existe en el sistema
- **THEN** el sistema responde con código 404 Not Found

#### Scenario: Baja de evento ajeno
- **WHEN** una cuenta intenta dar de baja un evento que pertenece a otra cuenta
- **THEN** el sistema rechaza la solicitud sin modificar el evento

## ADDED Requirements

### Requirement: Validación vigente para gestión de eventos
Eventos MUST verificar la sesión y el rol actual antes de autorizar nuevas operaciones de gestión y MUST rechazar la operación si Identity no puede verificarlos.

#### Scenario: Organizador deshabilitado después de iniciar sesión
- **WHEN** una cuenta intenta gestionar un evento después de que su rol organizador fue deshabilitado
- **THEN** Eventos rechaza la operación aunque su token no haya vencido

#### Scenario: Sesión revocada
- **WHEN** una cuenta intenta gestionar un evento con un token de una sesión revocada
- **THEN** Eventos rechaza la operación

#### Scenario: Identity no disponible
- **WHEN** Eventos no puede comprobar de forma confiable la sesión o los roles
- **THEN** rechaza la operación protegida sin modificar datos

### Requirement: Transporte para verificación de eventos
Eventos MUST usar HTTPS con verificación de certificados para comunicarse con Identity, salvo una excepción explícita de HTTP para desarrollo local o pruebas aisladas con credenciales de prueba.

#### Scenario: HTTP fuera del entorno local
- **WHEN** se configura HTTP hacia Identity fuera de desarrollo local o pruebas aisladas
- **THEN** Eventos no autoriza operaciones protegidas

#### Scenario: Excepción local no habilitada
- **WHEN** se configura HTTP local sin habilitar explícitamente la excepción
- **THEN** Eventos no autoriza operaciones protegidas

#### Scenario: Excepción local habilitada
- **WHEN** se habilita explícitamente HTTP en desarrollo local o pruebas aisladas con credenciales de prueba
- **THEN** Eventos puede verificar la sesión y los roles mediante esa configuración
