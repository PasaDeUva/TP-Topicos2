# Spec Delta: Inventario de Entradas (`inventario-de-entradas`)

## Purpose

Define el comportamiento observable del inventario de entradas de `events-service`: disponibilidad de cupo o asientos por modalidad, y el ciclo de vida de una reserva (reservar, liberar, confirmar).

## ADDED Requirements

### Requirement: Consulta de disponibilidad
El sistema SHALL exponer `GET /eventos/{evento_id}/modalidades/{modalidad_id}/disponibilidad` retornando `200 OK` con `{"disponibles": <int>}`. Para modalidad `general` el valor corresponde al cupo total menos las reservas confirmadas y activas no vencidas; para modalidad `numerada` corresponde a los asientos en estado `libre` o con reserva activa expirada.

#### Scenario: Disponibilidad de modalidad general
- **GIVEN** una modalidad general con cupo 100, 10 reservas confirmadas y 5 reservas activas vigentes
- **WHEN** se solicita `GET /eventos/{id}/modalidades/{mid}/disponibilidad`
- **THEN** el sistema responde 200 OK con `{"disponibles": 85}`

#### Scenario: Disponibilidad de modalidad numerada
- **GIVEN** una modalidad numerada con 50 asientos, 5 en estado `reservado` vigente y 2 en estado `vendido`
- **WHEN** se solicita `GET /eventos/{id}/modalidades/{mid}/disponibilidad`
- **THEN** el sistema responde 200 OK con `{"disponibles": 43}`

#### Scenario: Modalidad inexistente
- **WHEN** se solicita disponibilidad con un `modalidad_id` que no existe o no pertenece al evento
- **THEN** el sistema responde 404 Not Found

### Requirement: Reserva de entrada
El sistema SHALL permitir reservar una entrada mediante `POST /eventos/{evento_id}/modalidades/{modalidad_id}/reservas`, retornando `{"reserva_id": "<uuid>"}` con código 201 Created. El endpoint SHALL aceptar opcionalmente la cabecera `Idempotency-Key` (hasta 255 caracteres) para garantizar reintentos seguros. Para modalidad `general` descuenta una unidad de la disponibilidad calculada; para modalidad `numerada` cambia el estado del asiento a `reservado`.

#### Scenario: Reserva exitosa en modalidad general
- **GIVEN** una modalidad de tipo `general` con cupo disponible mayor a cero
- **WHEN** se envía `POST .../reservas` sin body adicional
- **THEN** el sistema responde 201 Created con `{"reserva_id": "<uuid>"}`

#### Scenario: Reserva exitosa en modalidad numerada
- **GIVEN** un asiento en estado `libre` identificado por `asiento_id`
- **WHEN** se envía `POST .../reservas` con `{"asiento_id": "<uuid>"}`
- **THEN** el sistema responde 201 Created con `{"reserva_id": "<uuid>"}` y el asiento pasa a estado `reservado`

#### Scenario: Reintento idempotente de reserva con misma clave y mismos datos
- **GIVEN** una reserva creada previamente con una cabecera `Idempotency-Key`
- **WHEN** el cliente reintenta enviar `POST .../reservas` con la misma `Idempotency-Key` y el mismo payload
- **THEN** el sistema responde con el `reserva_id` original sin crear reservas adicionales ni duplicar la ocupación

#### Scenario: Conflicto por reutilización de Idempotency-Key con datos divergentes
- **GIVEN** una reserva creada previamente con una cabecera `Idempotency-Key`
- **WHEN** el cliente envía `POST .../reservas` reutilizando dicha `Idempotency-Key` pero con datos distintos (otro `asiento_id`)
- **THEN** el sistema responde con código 409 Conflict y no altera el inventario

#### Scenario: Sin disponibilidad en modalidad general
- **GIVEN** una modalidad de tipo `general` cuya suma de reservas confirmadas y activas vigentes cubre la totalidad del cupo
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
El sistema SHALL permitir liberar una reserva activa mediante `DELETE /eventos/{evento_id}/modalidades/{modalidad_id}/reservas/{reserva_id}` respondiendo `200 OK` con `{"status": "liberada"}`. Para modalidad `general` la reserva pasa a estado `liberada`, recuperando la disponibilidad calculada; para modalidad `numerada` vuelve el asiento asociado a estado `libre`. El sistema MUST rechazar la liberación si la reserva ya no está activa.

#### Scenario: Liberación exitosa en modalidad general
- **GIVEN** una reserva en estado `activa` de modalidad `general`
- **WHEN** se envía `DELETE .../reservas/{reserva_id}`
- **THEN** el sistema responde 200 OK con `{"status": "liberada"}` y la reserva pasa a estado `liberada`

#### Scenario: Liberación exitosa en modalidad numerada
- **GIVEN** una reserva en estado `activa` sobre un asiento `reservado`
- **WHEN** se envía `DELETE .../reservas/{reserva_id}`
- **THEN** el sistema responde 200 OK con `{"status": "liberada"}`, la reserva pasa a `liberada` y el asiento vuelve a `libre`

#### Scenario: Reserva inexistente
- **WHEN** se envía `DELETE .../reservas/{reserva_id}` con un `reserva_id` que no existe
- **THEN** el sistema responde 404 Not Found

#### Scenario: Reserva ya confirmada
- **GIVEN** una reserva en estado `confirmada`
- **WHEN** se envía `DELETE .../reservas/{reserva_id}`
- **THEN** el sistema responde 409 Conflict y no modifica el estado ni el asiento

#### Scenario: Reserva ya liberada
- **GIVEN** una reserva en estado `liberada`
- **WHEN** se envía `DELETE .../reservas/{reserva_id}`
- **THEN** el sistema responde 409 Conflict y no altera ningún asiento reasignado

### Requirement: Confirmación de reserva
El sistema SHALL permitir confirmar una reserva mediante `POST /eventos/{evento_id}/modalidades/{modalidad_id}/reservas/{reserva_id}/confirmar` respondiendo `200 OK` con `{"status": "confirmada"}`. Para modalidad `numerada` cambia el estado del asiento a `vendido`; para modalidad `general` actualiza el estado de la reserva a `confirmada`. Reconfirmar una reserva ya confirmada MUST responder `200 OK` de forma idempotente.

#### Scenario: Confirmación exitosa
- **GIVEN** una reserva en estado `activa` no vencida
- **WHEN** se envía `POST .../reservas/{reserva_id}/confirmar`
- **THEN** el sistema responde 200 OK con `{"status": "confirmada"}` y el asiento pasa a `vendido` o la reserva queda `confirmada`

#### Scenario: Reconfirmación idempotente de reserva confirmada
- **GIVEN** una reserva que ya se encuentra en estado `confirmada`
- **WHEN** se envía nuevamente `POST .../reservas/{reserva_id}/confirmar`
- **THEN** el sistema responde 200 OK con `{"status": "confirmada"}` sin generar errores ni duplicados

#### Scenario: Reserva inexistente
- **WHEN** se envía `POST .../reservas/{reserva_id}/confirmar` con un `reserva_id` que no existe
- **THEN** el sistema responde 404 Not Found

#### Scenario: Reserva ya liberada
- **GIVEN** una reserva en estado `liberada`
- **WHEN** se envía `POST .../reservas/{reserva_id}/confirmar`
- **THEN** el sistema responde 409 Conflict

#### Scenario: Reserva vencida por TTL
- **GIVEN** una reserva en estado `activa` cuyo `expira_en` es anterior al instante de confirmación
- **WHEN** se envía `POST .../reservas/{reserva_id}/confirmar`
- **THEN** el sistema responde 409 Conflict, transiciona la reserva a `liberada` y no marca la venta
