# Spec Delta: Ciclo de Vida y Catálogo (`ciclo-de-vida-y-catalogo`)

## Purpose

Define el comportamiento para las transiciones de ciclo de vida del evento (publicación explícita con validación de completitud, pausa y despublicación) y la exposición del catálogo público con filtros, paginación, ocultamiento automático de eventos expirados y determinación dinámica de disponibilidad de venta.

## ADDED Requirements

### Requirement: Publicación explícita con validación de completitud
El sistema SHALL validar la completitud de los datos obligatorios del evento (nombre, descripción, venue, fecha inicio/fin y al menos una modalidad con precio > 0 y cupo > 0) para permitir la transición de BORRADOR a PUBLICADO de forma autónoma por el organizador.

#### Scenario: Publicación exitosa
- **GIVEN** un evento en estado BORRADOR con todos los campos obligatorios completos
- **WHEN** el organizador envía un POST a `/eventos/{id}/publicar`
- **THEN** el sistema cambia el estado a PUBLICADO y responde con código 200 OK

#### Scenario: Publicación rechazada por datos incompletos
- **GIVEN** un evento en BORRADOR sin venue definido o sin modalidades
- **WHEN** se envía un POST a `/eventos/{id}/publicar`
- **THEN** el sistema responde con código 422 Unprocessable Entity indicando los campos faltantes

#### Scenario: Publicación de un evento ya publicado
- **GIVEN** un evento en estado PUBLICADO
- **WHEN** se envía un POST a `/eventos/{id}/publicar`
- **THEN** el sistema responde con código 409 Conflict

### Requirement: Pausa y reactivación de eventos
El sistema SHALL permitir al organizador o administrador pausar temporalmente un evento en estado PUBLICADO, cesando inmediatamente la admisión de nuevas reservas y posibilitando su posterior reactivación.

#### Scenario: Pausar evento activo
- **GIVEN** un evento en estado PUBLICADO
- **WHEN** se envía un POST a `/eventos/{id}/pausar`
- **THEN** el sistema cambia el estado a PAUSADO, bloquea nuevas reservas y responde con código 200 OK

#### Scenario: Intento de pausar un borrador
- **GIVEN** un evento en estado BORRADOR
- **WHEN** se envía un POST a `/eventos/{id}/pausar`
- **THEN** el sistema responde con código 409 Conflict

### Requirement: Despublicación con preservación de historial
El sistema SHALL permitir la despublicación del evento, devolviéndolo a estado BORRADOR únicamente si carece de compras previas, o asignando el estado DESPUBLICADO si existen compras confirmadas para resguardar la trazabilidad histórica.

#### Scenario: Despublicar evento sin compras previas
- **GIVEN** un evento en estado PUBLICADO o PAUSADO sin compras ni reservas confirmadas
- **WHEN** se envía un POST a `/eventos/{id}/despublicar`
- **THEN** el sistema devuelve el evento al estado BORRADOR y responde con código 200 OK

#### Scenario: Despublicar evento con compras existentes
- **GIVEN** un evento con reservas confirmadas o tickets vendidos
- **WHEN** se envía un POST a `/eventos/{id}/despublicar`
- **THEN** el sistema asigna el estado DESPUBLICADO y responde con código 200 OK

### Requirement: Catálogo público con filtros y paginación
El sistema SHALL exponer una consulta pública y paginada de eventos en estado PUBLICADO, permitiendo filtrar por rango de fechas y tipo de evento, sin requerir cabeceras de autenticación.

#### Scenario: Consulta pública paginada
- **WHEN** un cliente envía un GET a `/catalogo/eventos?page=1&page_size=20`
- **THEN** el sistema responde con código 200 OK incluyendo la lista de eventos publicados y los metadatos de paginación

#### Scenario: Filtrado por tipo de evento
- **WHEN** se solicita un GET a `/catalogo/eventos?tipo_evento=concierto`
- **THEN** el sistema retorna únicamente los eventos publicados clasificados bajo dicho tipo

### Requirement: Ocultamiento automático de eventos finalizados
El sistema SHALL excluir automáticamente del catálogo público aquellos eventos cuya fecha de finalización sea anterior a la fecha actual del sistema.

#### Scenario: Evento expirado no visible en catálogo
- **GIVEN** un evento publicado cuya fecha_fin fue el día anterior
- **WHEN** se consulta el listado en `/catalogo/eventos`
- **THEN** el evento no aparece en los resultados devueltos

#### Scenario: Evento del día actual visible en catálogo
- **GIVEN** un evento publicado cuya fecha_fin corresponde al día actual
- **WHEN** se consulta el listado en `/catalogo/eventos`
- **THEN** el evento permanece visible en los resultados

### Requirement: Consulta de detalle público e inicio programado de venta
El sistema SHALL exponer el detalle de un evento publicado informando el cupo disponible por modalidad y calculando dinámicamente el valor del atributo venta_habilitada en base a la fecha_inicio_venta programada.

#### Scenario: Evento con venta futura programada
- **GIVEN** un evento publicado cuya fecha_inicio_venta es posterior a la fecha actual
- **WHEN** se consulta un GET a `/catalogo/eventos/{id}`
- **THEN** el sistema responde con código 200 OK y el campo `venta_habilitada: false`

#### Scenario: Evento con venta activa
- **GIVEN** un evento publicado cuya fecha_inicio_venta ya se cumplió o no fue especificada
- **WHEN** se consulta un GET a `/catalogo/eventos/{id}`
- **THEN** el sistema responde con código 200 OK y el campo `venta_habilitada: true`
