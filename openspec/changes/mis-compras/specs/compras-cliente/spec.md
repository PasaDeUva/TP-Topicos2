# Spec Delta

## Purpose

Esta capacidad permite que los clientes compren varias entradas en una operación y consulten un historial confiable de sus compras, incluyendo el estado del pago y las entradas asociadas.

## ADDED Requirements

### Requirement: Acceso al historial propio
El sistema DEBE (MUST) permitir que un cliente consulte todas sus compras y DEBE (MUST) impedir que consulte compras pertenecientes a otro cliente.

#### Scenario: Cliente consulta su historial
- **WHEN** un cliente autenticado abre Mis Compras
- **THEN** el sistema muestra las compras asociadas a ese cliente y ninguna compra de otros clientes

#### Scenario: Cliente sin compras
- **WHEN** un cliente autenticado abre Mis Compras y no tiene compras
- **THEN** el sistema muestra un estado vacío informativo

### Requirement: Compra asociada a la cuenta del cliente
El sistema DEBE (MUST) asociar cada compra a la cuenta autenticada del cliente. En la Etapa I, no DEBE (MUST NOT) exigir datos individuales de cada asistente para las entradas incluidas en una compra.

#### Scenario: Compra de varias entradas por un cliente
- **WHEN** un cliente autenticado compra una o más entradas
- **THEN** el sistema asocia todas las entradas de esa compra a la cuenta del cliente que la inició

#### Scenario: Compra sin datos de cada asistente
- **WHEN** un cliente compra varias entradas en una misma operación
- **THEN** el sistema permite completar la compra sin solicitar datos personales individuales de los asistentes

### Requirement: Detalle histórico de cada compra
El sistema DEBE (MUST) mostrar todas las compras, sin filtrar por estado, de la más reciente a la más antigua, con el evento, las fechas de compra y del evento, el total y el desglose de entradas por tipo y cantidad. Los importes mostrados DEBEN (MUST) conservar los valores de la compra original.

#### Scenario: Compra con varios tipos de entrada
- **WHEN** el cliente consulta una compra que incluye más de un tipo de entrada
- **THEN** el sistema muestra cada tipo y su cantidad, junto con el evento, las fechas y el total original de la compra

#### Scenario: Historial con distintos estados
- **WHEN** el cliente tiene compras en distintos estados
- **THEN** el sistema incluye todas en el historial y las ordena de más reciente a más antigua

### Requirement: Inicio de compra y reserva de disponibilidad
Al iniciar una compra, el sistema DEBE (MUST) validar y reservar conjuntamente todas las entradas solicitadas, asignar el estado Pendiente de pago y establecer un vencimiento a los 10 minutos del inicio.

#### Scenario: Compra dentro de la disponibilidad
- **WHEN** un cliente inicia una compra para una cantidad disponible de entradas
- **THEN** el sistema reserva la cantidad solicitada para esa compra y establece su estado en Pendiente de pago con un vencimiento a los 10 minutos

#### Scenario: Disponibilidad insuficiente
- **WHEN** la disponibilidad no alcanza para alguna de las cantidades solicitadas
- **THEN** el sistema no inicia una compra parcial ni reserva entradas y comunica la disponibilidad actual

### Requirement: Soporte de entradas numeradas y por zona
El sistema DEBE (MUST) distinguir entradas numeradas, asociadas a un asiento específico, de entradas no numeradas, cuya disponibilidad se controla por la capacidad de una zona.

#### Scenario: Compra de entradas numeradas
- **WHEN** el cliente compra entradas numeradas asociadas a asientos específicos
- **THEN** el sistema reserva cada asiento seleccionado de forma individual y evita que se reserve o venda para otra compra

#### Scenario: Compra de entradas no numeradas
- **WHEN** el cliente compra una cantidad de entradas no numeradas para una zona
- **THEN** el sistema reserva esa cantidad contra la capacidad disponible de la zona sin asignar asientos individuales

#### Scenario: Compra combinada de modalidades
- **WHEN** una compra incluye entradas numeradas y no numeradas
- **THEN** el sistema aplica a cada línea la regla de reserva de su modalidad y acepta la compra solo si puede reservar todas las entradas solicitadas

### Requirement: Pago simulado en la Etapa I
El sistema DEBE (MUST) procesar los pagos de la Etapa I de forma simulada, sin realizar cobros reales, y permitir que un intento permanezca Pendiente hasta resolverse como exitoso o fallido.

#### Scenario: Inicio de intento de pago simulado
- **WHEN** el cliente inicia el pago de una compra
- **THEN** el sistema crea un intento de pago simulado en estado Pendiente sin realizar un cobro real

#### Scenario: Resultado exitoso del simulador
- **WHEN** el simulador resuelve un intento Pendiente como exitoso antes del vencimiento de la reserva
- **THEN** el sistema confirma la compra y emite las entradas reservadas una sola vez

#### Scenario: Resultado fallido del simulador
- **WHEN** el simulador resuelve un intento Pendiente como fallido mientras la reserva sigue vigente
- **THEN** el sistema registra el fallo y permite reintentar el pago de la misma compra

### Requirement: Confirmación de compra pagada
El sistema DEBE (MUST) confirmar la compra y emitir las entradas asociadas cuando el pago se confirma antes del vencimiento de una reserva iniciada mientras la venta estaba abierta. El cierre de ventas para nuevas compras no invalida reservas activas.

#### Scenario: Pago exitoso dentro del plazo
- **WHEN** el pago de una compra Pendiente de pago se confirma antes de su vencimiento
- **THEN** el sistema cambia su estado a Confirmada y emite una sola vez las entradas reservadas

#### Scenario: Pago exitoso después del inicio del evento
- **WHEN** una compra se inició mientras la venta estaba abierta y el pago se confirma después del inicio del evento, pero antes del vencimiento de su reserva
- **THEN** el sistema cambia la compra a Confirmada y emite una sola vez las entradas reservadas

### Requirement: Reintento de pago fallido
El sistema DEBE (MUST) permitir reintentar el pago de una compra fallida antes del vencimiento, usando la misma compra y registrando cada intento por separado sin extender la reserva original.

#### Scenario: Intento de pago rechazado
- **WHEN** un intento de pago falla mientras la reserva sigue vigente
- **THEN** el sistema registra el intento fallido, cambia la compra a Fallida y conserva las entradas reservadas hasta el vencimiento original

#### Scenario: Reintento antes del vencimiento
- **WHEN** falla un intento de pago y el cliente reintenta mientras la reserva sigue vigente
- **THEN** el sistema conserva la compra, registra un nuevo intento, vuelve a Pendiente de pago y mantiene el vencimiento original

#### Scenario: Reintento después del vencimiento
- **WHEN** el cliente intenta reintentar el pago de una compra cuyo plazo venció
- **THEN** el sistema rechaza el reintento y mantiene la compra como Vencida

### Requirement: Vencimiento y liberación de entradas
Al alcanzar el vencimiento de 10 minutos sin un pago confirmado, el sistema DEBE (MUST) marcar la compra como Vencida y liberar todas las entradas reservadas para que vuelvan a estar disponibles.

#### Scenario: Compra sin pago al vencer la reserva
- **WHEN** se alcanza el vencimiento de una compra que no tiene un pago confirmado
- **THEN** el sistema cambia su estado a Vencida y libera la totalidad de las entradas reservadas

### Requirement: Tratamiento de pagos tardíos
Si un pago se confirma después del vencimiento de la reserva, el sistema DEBE (MUST) marcar la compra como Revisión requerida y MUST NOT confirmar la compra ni emitir entradas automáticamente.

#### Scenario: Pago confirmado después del vencimiento
- **WHEN** se confirma un pago de una compra cuya reserva ya venció
- **THEN** el sistema registra el pago tardío, marca la compra como Revisión requerida y deja su resolución para gestión manual

### Requirement: Protección contra ventas duplicadas
El sistema DEBE (MUST) preservar la unicidad de venta de cada entrada ante solicitudes concurrentes y notificaciones de pago repetidas, de modo que cada entrada reservada se confirme como máximo una vez.

#### Scenario: Notificación de pago repetida
- **WHEN** el sistema recibe más de una notificación del mismo pago exitoso
- **THEN** la compra permanece Confirmada y las entradas se emiten una sola vez

#### Scenario: Solicitudes concurrentes por la última disponibilidad
- **WHEN** varios clientes intentan reservar simultáneamente entradas cuya disponibilidad no alcanza para todas las solicitudes
- **THEN** el sistema reserva cada entrada para como máximo una compra y rechaza las solicitudes que exceden la disponibilidad restante

### Requirement: Separación de estados de procesos futuros
El estado de compra DEBE (MUST) representar el ciclo de reserva y pago. Las futuras solicitudes de ingreso a una cola de venta y las solicitudes de devolución DEBEN (MUST) mantener estados propios vinculados a la compra, sin reemplazar su estado ni sus datos históricos.

#### Scenario: Solicitud de devolución en una etapa futura
- **WHEN** se incorpora una solicitud de devolución para una compra confirmada
- **THEN** el sistema registra el estado de la devolución por separado y conserva el historial original de la compra

#### Scenario: Cliente en una futura cola de venta
- **WHEN** un cliente espera en una cola de venta antes de iniciar una compra
- **THEN** el estado de la cola se mantiene separado y la compra no pasa a Pendiente de pago hasta que se inicie
