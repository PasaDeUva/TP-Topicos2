# Spec Delta: Inventario y Contratos (`inventario-y-contratos`)

## Purpose

Define el comportamiento observable de los contratos REST para el bloqueo atómico temporal (TTL de 10 minutos), confirmación definitiva y liberación de inventario de entradas consumidos por el microservicio de Compras, asegurando la no-sobreventa bajo condiciones de alta concurrencia.

## ADDED Requirements

### Requirement: Reserva atómica de inventario con expiración TTL
El sistema SHALL permitir reservar de forma atómica asientos numerados o cupos de zonas generales asociando un plazo de expiración estricto de 10 minutos (TTL) y rechazando la operación si la venta no se encuentra habilitada o no hay stock.

#### Scenario: Reserva exitosa de asiento numerado
- **GIVEN** un asiento numerado en estado DISPONIBLE en un evento habilitado para venta
- **WHEN** se envía un POST a `/eventos/{id}/reservar` indicando modalidad de asiento y código del asiento
- **THEN** el sistema asigna el estado RESERVADO al asiento, genera la reserva en estado PENDIENTE con expiración a los 10 minutos y responde 200 OK

#### Scenario: Reserva exitosa en zona general
- **GIVEN** una zona general con cupo disponible suficiente
- **WHEN** se envía un POST a `/eventos/{id}/reservar` indicando la zona y cantidad solicitada
- **THEN** el sistema decrementa de forma atómica el cupo disponible de la zona, emite la reserva con TTL y responde 200 OK

#### Scenario: Conflicto por intento de reserva sobre evento con venta no iniciada
- **GIVEN** un evento con venta_habilitada en falso
- **WHEN** se solicita un POST a `/eventos/{id}/reservar`
- **THEN** el sistema responde con código 409 Conflict

### Requirement: Prevención de sobreventa bajo concurrencia
El sistema SHALL garantizar que ante múltiples solicitudes de reserva concurrentes sobre el mismo recurso (asiento o último cupo disponible), exactamente una transacción sea aceptada y el resto rechazadas sin inconsistencias de stock.

#### Scenario: Intentos concurrentes sobre el mismo asiento
- **GIVEN** dos peticiones en paralelo intentando reservar el mismo asiento disponible
- **WHEN** ambas solicitudes son procesadas simultáneamente
- **THEN** exactamente una petición recibe 200 OK y la otra recibe 409 Conflict

#### Scenario: Cupo insuficiente en zona general
- **GIVEN** una zona general con cupo disponible menor a la cantidad solicitada
- **WHEN** se intenta reservar dicha cantidad
- **THEN** el sistema responde con código 409 Conflict y el cupo disponible no se altera

### Requirement: Confirmación definitiva de reserva post-pago
El sistema SHALL permitir al servicio de Compras confirmar una reserva pendiente siempre que el plazo de expiración no se haya superado, transformando la reserva en confirmada y el inventario en vendido definitivamente.

#### Scenario: Confirmación exitosa en término
- **GIVEN** una reserva en estado PENDIENTE cuya fecha de expiración no ha vencido
- **WHEN** Compras envía un POST a `/eventos/{id}/confirmar` con el ID de la reserva
- **THEN** el sistema cambia la reserva a estado CONFIRMADA, asienta el inventario como vendido y responde 200 OK

#### Scenario: Confirmación rechazada por reserva expirada
- **GIVEN** una reserva cuyo plazo de 10 minutos ya transcurrió
- **WHEN** se envía un POST a `/eventos/{id}/confirmar`
- **THEN** el sistema rechaza la confirmación con código 409 Conflict

### Requirement: Liberación y reintegro de inventario
El sistema SHALL restituir de forma atómica el inventario cuando una reserva pendiente sea liberada voluntariamente o cancelada por fallo en el proceso de pago.

#### Scenario: Liberación de reserva de asiento
- **GIVEN** una reserva pendiente asociada a un asiento numerado
- **WHEN** se envía un POST a `/eventos/{id}/liberar`
- **THEN** el sistema cambia el estado de la reserva a LIBERADA, retorna el asiento a estado DISPONIBLE y responde 200 OK

#### Scenario: Liberación de reserva de zona general
- **GIVEN** una reserva pendiente asociada a una zona general
- **WHEN** se envía un POST a `/eventos/{id}/liberar`
- **THEN** el sistema cambia la reserva a LIBERADA, incrementa atómicamente el cupo disponible de la zona y responde 200 OK
