# Spec Delta: Control de Concurrencia de Reservas (`concurrencia-de-reservas`)

## Purpose

Define las garantías de exclusión mutua, prevención de sobreventa y tiempo de vida (TTL) con liberación perezosa en las reservas de modalidades generales y numeradas en `events-service`.

## ADDED Requirements

### Requirement: Exclusión mutua atómica en modalidad general
El sistema MUST procesar las reservas de modalidad general garantizando que ninguna transacción concurrente provoque sobreventa más allá del cupo definido, computando en el cupo ocupado tanto las reservas confirmadas como las reservas activas no vencidas. Ante solicitudes concurrentes, el sistema SHALL admitir únicamente tantas reservas como cupo remanente exista y rechazar las demás con código 409 Conflict.

#### Scenario: Reserva atómica de cupo disponible
- **GIVEN** una modalidad general con cupo disponible exactamente igual a 1
- **WHEN** se reciben dos solicitudes simultáneas de reserva para dicha modalidad
- **THEN** una de las solicitudes responde con código 201 Created y la otra responde con código 409 Conflict

#### Scenario: Rechazo atómico al agotarse cupo considerando confirmadas y activas
- **GIVEN** una modalidad general con cupo 10 que posee 8 reservas confirmadas y 2 reservas activas vigentes
- **WHEN** se envía una solicitud `POST .../reservas`
- **THEN** el sistema responde con código 409 Conflict y no incrementa las reservas persistidas

### Requirement: Exclusión mutua atómica en modalidad numerada
El sistema MUST garantizar la asignación exclusiva y atómica de cada asiento en modalidades numeradas mediante actualización condicionada al estado `libre`. Si múltiples solicitudes compiten en simultáneo por el mismo `asiento_id`, exactamente una SHALL resultar exitosa y las restantes MUST ser rechazadas con código 409 Conflict.

#### Scenario: Asignación atómica de asiento libre en competencia
- **GIVEN** un asiento numerado en estado `libre`
- **WHEN** se envían concurrentemente múltiples solicitudes de reserva referenciando ese mismo `asiento_id`
- **THEN** únicamente una solicitud obtiene respuesta 201 Created y el asiento pasa a estado `reservado`, mientras que las restantes reciben código 409 Conflict

#### Scenario: Rechazo de reserva de asiento no libre
- **GIVEN** un asiento numerado con estado `reservado` o `vendido`
- **WHEN** se solicita reservar dicho asiento mediante `POST .../reservas`
- **THEN** el sistema responde con código 409 Conflict y el estado del asiento permanece inalterado

### Requirement: Control de tiempo de vida (TTL) y liberación perezosa
El sistema SHALL asignar una fecha de vencimiento (`expira_en`) a cada reserva creada, considerando vencida a toda reserva activa cuyo TTL haya expirado. El sistema SHALL ejecutar una liberación perezosa de reservas activas vencidas restituyendo sus asientos a estado `libre` al evaluar disponibilidad o recibir nuevas reservas, aplicando orden canónico de locks (`reservas` y luego `asientos`) y comprobando pertenencia activa. El sistema MUST rechazar la confirmación de reservas expiradas.

#### Scenario: Liberación perezosa de asiento vencido al intentar reservar
- **GIVEN** un asiento numerado en estado `reservado` cuya reserva activa asociada superó su fecha de vencimiento (`expira_en`)
- **WHEN** un nuevo cliente envía `POST .../reservas` solicitando ese mismo asiento
- **THEN** el sistema libera la reserva anterior, asigna el asiento al nuevo cliente y responde con código 201 Created

#### Scenario: Recuperación de disponibilidad por reserva vencida
- **GIVEN** una modalidad general o numerada donde existen reservas activas cuyo tiempo de vida (`expira_en`) ha expirado
- **WHEN** se consulta `GET .../disponibilidad` de dicha modalidad
- **THEN** el sistema contabiliza el cupo o asiento de las reservas vencidas como disponible

#### Scenario: Rechazo de confirmación de reserva expirada
- **GIVEN** una reserva activa cuyo tiempo de vida (`expira_en`) ha expirado
- **WHEN** se envía `POST .../reservas/{reserva_id}/confirmar`
- **THEN** el sistema responde con código 409 Conflict, transiciona la reserva a `liberada` y no confirma la venta

#### Scenario: Carrera entre confirmación y expiración concurrente
- **GIVEN** una reserva activa en modalidad numerada cuyo TTL está al límite de expiración
- **WHEN** concurren en paralelo la confirmación de la reserva y una nueva reserva que ejecuta liberación perezosa sobre ese asiento
- **THEN** la operación que obtiene primero el lock sobre la fila de la reserva resuelve atómicamente; si la confirmación entra primero se consolida la venta y el asiento pasa a `vendido`, y si la liberación entra primero la reserva caduca a `liberada`, el asiento vuelve a `libre`, y la confirmación posterior responde 409 Conflict sin alterar el asiento reasignado
