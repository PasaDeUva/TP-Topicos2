# Design

## Context

Ver `proposal.md` y `specs/compras-cliente/spec.md` para el ciclo funcional de compra, pago, reserva e historial. Este cambio corresponde al bloque Purchases de una arquitectura de tres servicios. Identity es dueño de las cuentas; Events es dueño del inventario y las reservas; Purchases es dueño de compras, intentos de pago e historial.

## Goals / Non-Goals

**Goals:**
- Coordinar el ciclo de compra con la API de reservas de Events sin escrituras directas en bases ajenas.
- Preservar datos históricos inmutables para Mis Compras y recomendaciones posteriores.
- Mantener la simulación y reintentos de pago separados de los futuros estados de devolución y cola.

**Non-Goals:**
- Pasarela de pago real, devoluciones, colas de venta, códigos QR, recomendador o caché.
- Acceso directo a las bases de Identity o Events.

## Decisions

- **Purchases es dueño del agregado de compra.** Su base MySQL guarda Purchase, snapshots de PurchaseLine, PaymentAttempt, estado, customer id, event id y reservation id. El historial se consulta solo a través de este servicio y se filtra por el cliente autenticado.
- **Reservar antes de iniciar el pago.** En checkout, Purchases genera un id estable y solicita a Events reservar todas las líneas numeradas/por zona. Events valida el estado de venta y reserva las líneas durante 10 minutos. Si una línea no está disponible, no se crea una compra pagable. Si falla guardar la compra después de reservar, Purchases emite un comando idempotente para liberar la reserva.
- **Usar un adaptador de pago simulado.** PaymentAttempt comienza Pendiente y se resuelve como exitoso o fallido sin cobro real. Cada reintento agrega un intento a la misma compra y no reinicia el vencimiento de la reserva.
- **Confirmar inventario antes de marcar la compra Confirmada.** Ante éxito simulado, Purchases pide a Events confirmar la reserva de forma idempotente. La compra solo pasa a Confirmada y emite entradas después de recibir confirmación de Events. Un timeout provoca reintento/reconciliación, no una segunda emisión.
- **Mantener el vencimiento como autoridad de Events.** Purchases conserva la expiración devuelta por Events y reconcilia reservas vencidas para que el historial pase a Vencida una vez liberado el inventario. Confirmar o liberar repetidamente la misma reserva no cambia el resultado más de una vez.
- **Resolver pagos tardíos manualmente.** Si el simulador informa éxito tras vencer/liberar la reserva, Purchases marca Revisión requerida y no emite entradas. La devolución queda para la Etapa III.
- **Exponer una API de compras y flujos React.** React/Vite consulta Purchases para checkout y Mis Compras. Los snapshots conservan evento, tipo, fecha, precio y cantidad aunque el evento salga del catálogo público.
- **Usar REST síncrono e idempotente en el camino crítico.** La reserva/confirmación entre Purchases y Events es síncrona en la Etapa I; las colas se incorporan en la Etapa III.
- **Usar transacciones locales SQLAlchemy.** Cada operación de Purchases abre una transacción local para Purchase y PaymentAttempt; los bloqueos de inventario ocurren dentro de Events, sin transacción distribuida de base de datos.

## Risks / Trade-offs

- [Events y Purchases pueden divergir temporalmente ante fallos] → No confirmar una compra hasta confirmar la reserva en Events; reintentar idempotentemente y reconciliar su estado.
- [Un resultado de pago puede llegar tras el vencimiento] → Mantener Revisión requerida y resolver manualmente hasta implementar devoluciones en Etapa III.
- [El simulador no valida una pasarela real] → Mantener un límite de adaptador para sustituir el simulador sin cambiar el modelo de estados.
- [La disponibilidad puede cambiar desde que el cliente vio el evento] → Revalidar y reservar atómicamente durante checkout; devolver disponibilidad actual si la reserva falla.

## Migration Plan

El sistema es greenfield. Crear la base y migraciones de Purchases antes de habilitar checkout. No hay compras previas para migrar.
