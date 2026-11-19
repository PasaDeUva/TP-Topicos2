# Spec Delta: Control de Concurrencia de Reservas (`concurrencia-de-reservas`)

## Purpose

Define las garantías de exclusión mutua, no sobreventa y tiempo de vida (TTL) en las operaciones de reserva de entradas para modalidades generales y numeradas en `events-service`.

## ADDED Requirements

### Requirement: Exclusión mutua atómica en modalidad general
El sistema MUST procesar las reservas de modalidad general garantizando que ninguna transacción concurrente provoque sobreventa más allá del cupo definido. Ante solicitudes en carrera que compitan por los últimos cupos, el sistema SHALL admitir únicamente tantas reservas como cupo remanente exista y rechazar las demás con código 409 Conflict.

#### Scenario: Reserva atómica de cupo disponible
- **GIVEN** una modalidad general con cupo disponible exactamente igual a 1
- **WHEN** se reciben dos solicitudes simultáneas de reserva para dicha modalidad
- **THEN** una de las solicitudes responde con código 201 Created y la otra responde con código 409 Conflict

#### Scenario: Rechazo atómico sin disponibilidad
- **GIVEN** una modalidad general cuyo cupo activo se encuentra totalmente cubierto por reservas vigentes
- **WHEN** se envía una solicitud `POST .../reservas`
- **THEN** el sistema responde con código 409 Conflict sin incrementar las reservas persistidas

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

### Requirement: Control de tiempo de vida (TTL) de reservas
El sistema SHALL asignar una fecha de vencimiento (`expira_en`) a cada reserva creada calculada a partir del TTL configurado. Toda reserva activa cuya fecha de vencimiento sea anterior al instante de evaluación MUST ser considerada vencida, liberando la disponibilidad del cupo o asiento asociado y rechazando cualquier intento posterior de confirmación.

#### Scenario: Recuperación de disponibilidad por reserva vencida
- **GIVEN** una reserva activa cuyo tiempo de vida (`expira_en`) ha sido superado
- **WHEN** se consulta `GET .../disponibilidad` de la modalidad asociada
- **THEN** el sistema contabiliza el cupo o asiento de la reserva vencida como disponible

#### Scenario: Rechazo de confirmación de reserva expirada
- **GIVEN** una reserva activa cuyo tiempo de vida (`expira_en`) ha expirado
- **WHEN** se envía `POST .../reservas/{reserva_id}/confirmar`
- **THEN** el sistema responde con código 409 Conflict y no confirma la venta
