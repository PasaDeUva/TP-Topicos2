# Spec Delta: Gestión de Eventos (`gestion-de-eventos`)

## Purpose

Define el comportamiento observable para la gestión mínima de eventos (upsert y baja lógica), consulta pública de catálogo (incluyendo eventos activos e inactivos) y contratos REST de reserva atómica con TTL de 10 minutos para Compras con control de concurrencia.

## ADDED Requirements

### Requirement: Upsert y baja lógica de eventos
El sistema SHALL permitir a través de un único endpoint `POST /eventos` crear un evento cuando no se proporcione identificador, actualizarlo cuando se incluya un `id` existente, y aplicar baja lógica cuando se envíe `activo: false`. Los identificadores de eventos y modalidades SHALL ser UUIDs autogenerados por el sistema.

#### Scenario: Creación exitosa de evento
- **WHEN** se envía `POST /eventos` sin campo `id` con nombre, venue, fecha y al menos una modalidad con precio y cupo positivos
- **THEN** el sistema genera un UUID para el evento y sus modalidades, persiste la entidad con `activo: true` y responde con código 201 Created

#### Scenario: Creación rechazada por campos faltantes
- **WHEN** se envía `POST /eventos` omitiendo cualquier campo obligatorio (nombre, venue, fecha o modalidades)
- **THEN** el sistema rechaza la solicitud con código 400 Bad Request y cuerpo `{"detail": "invalid body"}`

#### Scenario: Actualización de evento existente
- **GIVEN** un evento previamente creado con un UUID determinado
- **WHEN** se envía `POST /eventos` incluyendo dicho `id` en el cuerpo con datos modificados
- **THEN** el sistema actualiza los datos del evento y responde con código 200 OK

#### Scenario: Baja lógica de evento
- **GIVEN** un evento activo con un UUID determinado
- **WHEN** se envía `POST /eventos` incluyendo dicho `id` y `"activo": false`
- **THEN** el sistema actualiza el atributo a falso preservando el registro y responde con código 200 OK

### Requirement: Consulta de eventos y detalle
El sistema SHALL exponer la consulta de eventos y detalle por identificador retornando el objeto tanto si su atributo `activo` es verdadero como si es falso.

#### Scenario: Listado de eventos
- **WHEN** se solicita un GET a `/eventos`
- **THEN** el sistema responde con código 200 OK y la lista de todos los eventos registrados con sus modalidades, indicando el estado del campo `activo` de cada uno

#### Scenario: Detalle de evento existente
- **GIVEN** un evento registrado con un UUID determinado
- **WHEN** se solicita un GET a `/eventos/{id}`
- **THEN** el sistema responde con código 200 OK con la entidad completa y su stock restante

#### Scenario: Consulta de evento inexistente
- **WHEN** se solicita un GET a `/eventos/{id}` con un UUID que no existe en el sistema
- **THEN** el sistema responde con código 404 Not Found

### Requirement: Reserva atómica de inventario con expiración TTL
El sistema SHALL permitir al Bloque de Compras reservar de forma atómica asientos numerados o cupos de zonas generales con una expiración estricta de 10 minutos (TTL), rechazando la operación si el evento está inactivo o si no hay stock disponible.

#### Scenario: Reserva exitosa de asiento numerado
- **GIVEN** un evento activo y un asiento numerado en estado DISPONIBLE
- **WHEN** se envía un POST a `/eventos/{id}/reservar` con modalidad_id, asiento_codigo y compra_id
- **THEN** el sistema bloquea el asiento a RESERVADO, emite la reserva con estado PENDIENTE y expira_en a 10 minutos, y responde con código 200 OK

#### Scenario: Reserva exitosa en zona general
- **GIVEN** un evento activo y una zona general con cupo disponible suficiente
- **WHEN** se envía un POST a `/eventos/{id}/reservar` con modalidad_id, cantidad y compra_id
- **THEN** el sistema decrementa atómicamente el cupo disponible, genera la reserva con TTL y responde con código 200 OK

#### Scenario: Conflicto por sobreventa o falta de disponibilidad
- **GIVEN** un asiento ya reservado o una zona sin cupo suficiente
- **WHEN** se intenta reservar dicho stock
- **THEN** el sistema responde con código 409 Conflict sin modificar el inventario

#### Scenario: Intento de reserva sobre evento dado de baja
- **GIVEN** un evento con `activo: false`
- **WHEN** se intenta reservar entradas
- **THEN** el sistema rechaza la operación con código 409 Conflict

### Requirement: Confirmación y liberación de reservas
El sistema SHALL permitir confirmar definitivamente una reserva vigente tras el pago o liberarla reintegrando el stock si la compra falla o el tiempo expira.

#### Scenario: Confirmación exitosa de reserva
- **GIVEN** una reserva en estado PENDIENTE cuyo plazo de 10 minutos no ha vencido
- **WHEN** se envía un POST a `/eventos/{id}/reservas/{reserva_id}/confirmar`
- **THEN** el sistema pasa la reserva a CONFIRMADA, asienta el asiento como VENDIDO y responde con código 200 OK

#### Scenario: Liberación de reserva y restitución de stock
- **GIVEN** una reserva en estado PENDIENTE
- **WHEN** se envía un POST a `/eventos/{id}/reservas/{reserva_id}/liberar`
- **THEN** el sistema pasa la reserva a LIBERADA, retorna el asiento a DISPONIBLE o incrementa el cupo de la zona y responde con código 200 OK

### Requirement: Bitácora HTTP y correlación
El sistema SHALL interceptar cada solicitud HTTP para registrar en formato JSON estructurado a stdout: método, ruta, código de estado, tiempo transcurrido en milisegundos y un identificador de correlación `X-Correlation-Id`.

#### Scenario: Emisión de log estructurado
- **WHEN** se procesa cualquier solicitud HTTP
- **THEN** el sistema emite a stdout un registro JSON con duration_ms, method, path, status_code y correlation_id, propagando la cabecera X-Correlation-Id en la respuesta
