# Spec Delta

## Purpose

Esta capacidad permite que los organizadores preparen eventos antes de publicarlos y protege las compras existentes frente a cambios posteriores en las condiciones del evento.

## ADDED Requirements

### Requirement: Gestión de borradores
El sistema DEBE (MUST) permitir que un organizador habilitado guarde un evento como Borrador y modifique sus datos antes de publicarlo.

#### Scenario: Organizador guarda un evento como borrador
- **WHEN** un organizador habilitado guarda un evento sin publicarlo
- **THEN** el sistema registra el evento como Borrador y permite que el organizador vuelva a editarlo

#### Scenario: Borrador no disponible para clientes
- **WHEN** un cliente consulta eventos disponibles o intenta comprar entradas
- **THEN** los eventos en estado Borrador no se listan ni aceptan compras

### Requirement: Publicación explícita de eventos
El sistema DEBE (MUST) permitir que un organizador habilitado publique explícitamente un evento que cumpla las reglas de publicación, sin requerir aprobación administrativa individual para ese evento.

#### Scenario: Organizador publica un evento
- **WHEN** un organizador habilitado publica explícitamente un evento válido
- **THEN** el sistema cambia el evento a Publicado sin requerir aprobación administrativa por evento

### Requirement: Datos obligatorios para publicar
El sistema DEBE (MUST) exigir nombre, descripción, fecha y hora, lugar, al menos una modalidad de entrada con su precio y la capacidad correspondiente antes de permitir la publicación de un evento.

#### Scenario: Publicación con datos obligatorios faltantes
- **WHEN** un organizador intenta publicar un evento al que le falta uno o más datos obligatorios
- **THEN** el sistema rechaza la publicación, informa qué datos faltan y mantiene el evento en Borrador

#### Scenario: Publicación con todos los datos obligatorios
- **WHEN** un organizador intenta publicar un evento que tiene todos los datos obligatorios completos
- **THEN** el sistema permite continuar con la publicación explícita del evento

### Requirement: Metadatos opcionales para búsqueda futura
El sistema DEBE (MUST) permitir asociar opcionalmente un tipo de evento y sus participantes. Estos metadatos no son obligatorios para publicar durante la Etapa I y deben quedar disponibles para la búsqueda avanzada de la Etapa III.

#### Scenario: Publicación sin metadatos opcionales
- **WHEN** un organizador publica un evento con todos los datos obligatorios pero sin tipo de evento ni participantes
- **THEN** el sistema permite la publicación

#### Scenario: Evento con metadatos opcionales
- **WHEN** un organizador registra un tipo de evento o participantes
- **THEN** el sistema conserva esos datos asociados al evento para su consulta y uso en búsquedas futuras

### Requirement: Disponibilidad de eventos publicados
El sistema DEBE (MUST) listar para los clientes los eventos Publicados y Pausados, indicar cuándo un evento está temporalmente no disponible y permitir compras únicamente para eventos Publicados que no estén despublicados y cuya fecha y hora de inicio de venta ya se alcanzó.

#### Scenario: Cliente consulta eventos publicados
- **WHEN** un cliente consulta eventos disponibles para comprar
- **THEN** el sistema incluye los eventos Publicados y Pausados, y excluye los eventos Borrador y Despublicados

#### Scenario: Evento pausado visible y temporalmente no disponible
- **WHEN** un cliente consulta un evento Pausado
- **THEN** el sistema lo muestra como temporalmente no disponible y no ofrece iniciar una compra

#### Scenario: Cliente intenta comprar un evento pausado o despublicado
- **WHEN** un cliente intenta iniciar una compra para un evento Pausado o Despublicado
- **THEN** el sistema rechaza el inicio de la compra

### Requirement: Información pública del evento
El sistema DEBE (MUST) mostrar en la ficha pública de un evento su descripción, fecha y hora, lugar, modalidades y precios de entradas, e indicar por modalidad si está Disponible o Agotada sin mostrar cantidades exactas restantes.

#### Scenario: Cliente consulta un evento con entradas disponibles
- **WHEN** un cliente abre la ficha de un evento visible que tiene entradas disponibles
- **THEN** el sistema muestra los datos del evento y marca como Disponibles las modalidades que pueden comprarse

#### Scenario: Cliente consulta una modalidad agotada
- **WHEN** una modalidad de entrada no tiene disponibilidad para nuevas compras
- **THEN** el sistema la marca como Agotada y no permite seleccionarla para una compra

### Requirement: Visibilidad de eventos pasados
El sistema DEBE (MUST) mantener los eventos Publicados visibles en el catálogo durante la fecha del evento y ocultarlos al comenzar el día calendario siguiente.

#### Scenario: Evento visible durante su fecha
- **WHEN** la fecha actual coincide con la fecha de un evento Publicado
- **THEN** el sistema mantiene el evento visible en el catálogo público

#### Scenario: Evento oculto después de su fecha
- **WHEN** comienza el día calendario siguiente a la fecha de un evento
- **THEN** el sistema excluye ese evento del catálogo público

### Requirement: Inicio programado de venta
El sistema DEBE (MUST) permitir que el organizador configure una fecha y hora de inicio de venta distinta de la publicación del evento. Si no configura un inicio futuro, las ventas comienzan al publicarse el evento.

#### Scenario: Venta programada para el futuro
- **WHEN** el organizador publica un evento con un inicio de venta posterior al momento actual
- **THEN** el evento queda visible como Publicado, pero el sistema rechaza compras hasta alcanzar la fecha y hora configuradas

#### Scenario: Venta sin inicio futuro configurado
- **WHEN** el organizador publica un evento sin configurar un inicio de venta futuro
- **THEN** el evento queda disponible para compras desde su publicación

#### Scenario: Inicio programado alcanzado
- **WHEN** se alcanza la fecha y hora de inicio de venta de un evento Publicado que no está Pausado ni Despublicado
- **THEN** el sistema permite iniciar compras según la disponibilidad de entradas

### Requirement: Cierre automático de venta
El sistema DEBE (MUST) dejar de aceptar nuevos inicios de compra cuando comience el evento o cuando se hayan vendido todas las entradas disponibles, lo que ocurra primero. El inicio del evento no invalida reservas de compra que continúan dentro de su plazo vigente.

#### Scenario: Comienza el evento
- **WHEN** se alcanza la fecha y hora de inicio del evento
- **THEN** el sistema cierra la venta y rechaza nuevos inicios de compra aunque queden entradas disponibles, pero mantiene vigentes las reservas activas hasta su vencimiento

#### Scenario: Se agotan las entradas
- **WHEN** todas las entradas disponibles del evento se vendieron
- **THEN** el sistema cierra la venta y rechaza nuevas compras

### Requirement: Moderación administrativa de eventos
El sistema DEBE (MUST) permitir que un administrador pause o despublique un evento existente, impidiendo nuevas compras mientras el evento permanezca en ese estado. También DEBE (MUST) permitir reanudar un evento pausado solo si aún no comenzó y quedan entradas disponibles.

#### Scenario: Administrador pausa un evento
- **WHEN** un administrador pausa un evento Publicado
- **THEN** el sistema deja de ofrecerlo para nuevas compras mientras esté Pausado

#### Scenario: Administrador despublica un evento
- **WHEN** un administrador despublica un evento Publicado
- **THEN** el sistema deja de listarlo y rechaza nuevas compras

#### Scenario: Administrador reanuda un evento pausado
- **WHEN** un administrador reanuda un evento Pausado que todavía no comenzó y tiene entradas disponibles
- **THEN** el sistema lo devuelve al estado Publicado y aplica las reglas vigentes de inicio y cierre de venta

#### Scenario: Reanudación no permitida
- **WHEN** un administrador intenta reanudar un evento que ya comenzó o agotó sus entradas
- **THEN** el sistema rechaza la acción y no vuelve a habilitar la venta

### Requirement: Despublicación por el organizador
El sistema DEBE (MUST) permitir que un organizador despublique y vuelva a publicar su propio evento mientras no existan compras confirmadas y el evento cumpla las reglas de publicación. Si ya existe una compra confirmada, el organizador MUST NOT despublicar el evento mediante este flujo.

#### Scenario: Organizador despublica un evento sin compras confirmadas
- **WHEN** un organizador despublica su evento Publicado y no existen compras confirmadas
- **THEN** el sistema cambia el evento a Despublicado, lo oculta a los clientes y rechaza nuevas compras

#### Scenario: Organizador intenta despublicar un evento con compras confirmadas
- **WHEN** un organizador intenta despublicar su evento después de que exista una compra confirmada
- **THEN** el sistema rechaza la acción y conserva el evento y las compras existentes

#### Scenario: Organizador vuelve a publicar un evento despublicado
- **WHEN** un organizador vuelve a publicar su evento Despublicado, sin compras confirmadas y con los datos obligatorios completos
- **THEN** el sistema lo cambia a Publicado y aplica las reglas vigentes de inicio y cierre de venta

### Requirement: Protección de compras existentes
El sistema DEBE (MUST) permitir que el organizador edite un evento Publicado sin despublicarlo cuando no haya compras confirmadas ni reservas activas. DEBE (MUST) impedir cambios que alteren las condiciones de entradas compradas o reservadas durante una reserva Pendiente de pago vigente; una vez confirmada una compra, los precios del evento quedan bloqueados.

#### Scenario: Edición antes de la primera compra confirmada
- **WHEN** un organizador edita un evento Publicado que no tiene compras confirmadas ni reservas activas
- **THEN** el sistema guarda los cambios y mantiene el evento Publicado, sujeto a las reglas de inicio y cierre de venta

#### Scenario: Cambio que alteraría una reserva activa
- **WHEN** un organizador intenta cambiar la fecha, el lugar, la modalidad, el asiento o el precio de entradas asociadas a una reserva Pendiente de pago cuyo plazo de 10 minutos sigue vigente
- **THEN** el sistema rechaza el cambio y conserva las condiciones de la reserva hasta que se confirme o venza

#### Scenario: Edición tras vencer una reserva sin pago
- **WHEN** vence una reserva Pendiente de pago sin confirmación y no existen otras reservas activas ni compras confirmadas
- **THEN** el sistema libera las entradas y permite editar nuevamente las condiciones que no afectan otras compras

#### Scenario: Cambio que alteraría una compra confirmada
- **WHEN** un organizador intenta cambiar la fecha, ubicación, modalidad o asiento asignado de una entrada que forma parte de una compra confirmada
- **THEN** el sistema rechaza el cambio y conserva las condiciones asociadas a la compra

#### Scenario: Cambio de precio después de una venta confirmada
- **WHEN** un organizador intenta modificar cualquier precio de un evento con al menos una compra confirmada
- **THEN** el sistema rechaza el cambio de precio

#### Scenario: Pausa o despublicación de un evento con compras
- **WHEN** un administrador pausa o despublica un evento que tiene compras confirmadas
- **THEN** el sistema impide nuevas compras y conserva las compras y sus condiciones históricas
