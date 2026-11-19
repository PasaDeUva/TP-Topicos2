# Spec Delta: Inventario de Entradas (`inventario-de-entradas`)

## Purpose

Define el comportamiento observable del inventario de entradas de `events-service`: disponibilidad de cupo o asientos por modalidad, y el ciclo de vida de una reserva (reservar, liberar, confirmar).

## ADDED Requirements

### Requirement: Consulta de disponibilidad
El sistema SHALL exponer `GET /eventos/{evento_id}/modalidades/{modalidad_id}/disponibilidad` retornando la cantidad de entradas disponibles. Para modalidad `general` es el cupo restante; para modalidad `numerada` es la cantidad de asientos en estado `libre`.

#### Scenario: Disponibilidad de modalidad general
- **GIVEN** una modalidad de tipo `general` con cupo 100 y 10 reservas activas
- **WHEN** se solicita `GET /eventos/{id}/modalidades/{mid}/disponibilidad`
- **THEN** el sistema responde 200 OK con `{"disponibles": 90}`

#### Scenario: Disponibilidad de modalidad numerada
- **GIVEN** una modalidad de tipo `numerado` con 50 asientos, 5 en estado `reservado` y 2 en estado `vendido`
- **WHEN** se solicita `GET /eventos/{id}/modalidades/{mid}/disponibilidad`
- **THEN** el sistema responde 200 OK con `{"disponibles": 43}`

#### Scenario: Modalidad inexistente
- **WHEN** se solicita disponibilidad con un `modalidad_id` que no existe o no pertenece al evento
- **THEN** el sistema responde 404 Not Found

### Requirement: Reserva de entrada
El sistema SHALL permitir reservar una entrada mediante `POST /eventos/{evento_id}/modalidades/{modalidad_id}/reservas`. El sistema SHALL generar un `reserva_id` UUID y retornarlo. Para modalidad `general` descuenta una unidad del cupo; para modalidad `numerada` cambia el estado del asiento indicado a `reservado`.

#### Scenario: Reserva exitosa en modalidad general
- **GIVEN** una modalidad de tipo `general` con cupo disponible mayor a cero
- **WHEN** se envía `POST .../reservas` sin body adicional
- **THEN** el sistema responde 201 Created con `{"reserva_id": "<uuid>"}`

#### Scenario: Reserva exitosa en modalidad numerada
- **GIVEN** un asiento en estado `libre` identificado por `asiento_id`
- **WHEN** se envía `POST .../reservas` con `{"asiento_id": "<uuid>"}`
- **THEN** el sistema responde 201 Created con `{"reserva_id": "<uuid>"}` y el asiento pasa a estado `reservado`

#### Scenario: Sin disponibilidad en modalidad general
- **GIVEN** una modalidad de tipo `general` con cupo disponible igual a cero
- **WHEN** se envía `POST .../reservas`
- **THEN** el sistema responde 409 Conflict y no crea reserva

#### Scenario: Asiento no libre en modalidad numerada
- **GIVEN** un asiento en estado `reservado` o `vendido`
- **WHEN** se envía `POST .../reservas` referenciando ese asiento
- **THEN** el sistema responde 409 Conflict y no crea reserva

#### Scenario: Modalidad o evento inexistente
- **WHEN** se envía `POST .../reservas` con un `evento_id` o `modalidad_id` que no existe
- **THEN** el sistema responde 404 Not Found

#### Scenario: Asiento_id faltante en modalidad numerada
- **WHEN** se envía `POST .../reservas` sin `asiento_id` para una modalidad de tipo `numerado`
- **THEN** el sistema responde 400 Bad Request con `{"detail": "invalid body"}`

### Requirement: Liberación de reserva
El sistema SHALL permitir liberar una reserva mediante `DELETE /eventos/{evento_id}/modalidades/{modalidad_id}/reservas/{reserva_id}`. Para modalidad `general` incrementa el cupo; para modalidad `numerada` vuelve el asiento a estado `libre`.

#### Scenario: Liberación exitosa en modalidad general
- **GIVEN** una reserva activa de modalidad `general`
- **WHEN** se envía `DELETE .../reservas/{reserva_id}`
- **THEN** el sistema responde 200 OK y el cupo disponible se incrementa en uno

#### Scenario: Liberación exitosa en modalidad numerada
- **GIVEN** una reserva activa de modalidad `numerada` sobre un asiento `reservado`
- **WHEN** se envía `DELETE .../reservas/{reserva_id}`
- **THEN** el sistema responde 200 OK y el asiento vuelve a estado `libre`

#### Scenario: Reserva inexistente
- **WHEN** se envía `DELETE .../reservas/{reserva_id}` con un `reserva_id` que no existe
- **THEN** el sistema responde 404 Not Found

#### Scenario: Reserva ya confirmada
- **GIVEN** una reserva en estado `confirmada`
- **WHEN** se envía `DELETE .../reservas/{reserva_id}`
- **THEN** el sistema responde 409 Conflict y no modifica el estado

### Requirement: Confirmación de reserva
El sistema SHALL permitir confirmar una reserva mediante `POST /eventos/{evento_id}/modalidades/{modalidad_id}/reservas/{reserva_id}/confirmar`. Para modalidad `numerada` cambia el estado del asiento a `vendido`; para modalidad `general` la marca como vendida en el registro de reserva.

#### Scenario: Confirmación exitosa
- **GIVEN** una reserva activa (no liberada ni ya confirmada)
- **WHEN** se envía `POST .../reservas/{reserva_id}/confirmar`
- **THEN** el sistema responde 200 OK y el asiento (numerado) pasa a estado `vendido` o la reserva (general) queda marcada como confirmada

#### Scenario: Reserva inexistente
- **WHEN** se envía `POST .../reservas/{reserva_id}/confirmar` con un `reserva_id` que no existe
- **THEN** el sistema responde 404 Not Found

#### Scenario: Reserva ya liberada
- **GIVEN** una reserva previamente liberada
- **WHEN** se envía `POST .../reservas/{reserva_id}/confirmar`
- **THEN** el sistema responde 409 Conflict
