# Design

## Context

Ver `proposal.md` y `specs/publicacion-eventos/spec.md` para la motivación y el ciclo funcional. Este cambio corresponde al bloque Events de una arquitectura de tres servicios. Identity es dueño de las cuentas; Purchases es dueño de compras e intentos de pago. Events es la fuente de verdad para eventos, ofertas de entradas, inventario y reservas.

## Goals / Non-Goals

**Goals:**
- Tener una única fuente de verdad para publicación, modalidad de entradas, ventana de venta e inventario disponible.
- Reservar asientos y capacidad de zona atómicamente para evitar sobreventa concurrente.
- Exponer detalles públicos del evento y operaciones de reserva internas para Purchases.

**Non-Goals:**
- Compras/pagos, gestión de cuentas, devoluciones, colas de venta, ordenamiento avanzado de búsqueda o políticas de caché.
- Reprogramación o cancelación de eventos con compras confirmadas; esos flujos pertenecen a etapas posteriores.

## Decisions

- **Events es dueño del evento y su inventario de entradas.** La base MySQL propia guarda metadatos del evento, tipos de entrada, asientos/zonas, estado de venta, reservas e inventario vendido. Purchases conserva sus compras y snapshots inmutables de las líneas; ningún servicio lee tablas del otro.
- **La reserva de inventario es una transacción local de Events.** Purchases solicita reservar por identificador idempotente de compra y líneas de entrada. Events valida publicación, horario y disponibilidad, y reserva todas las líneas en una transacción InnoDB con bloqueos de fila y restricciones de unicidad. Si una línea no está disponible, no hay reserva parcial.
- **Events evalúa si se puede iniciar una venta.** Estado Publicado/Pausado/Despublicado, inicio de venta, comienzo del evento y agotamiento se validan al crear reservas. Una reserva existente permanece válida hasta vencer a los 10 minutos, incluso si se cierra la venta para nuevas compras.
- **Events vence las reservas de inventario.** Un proceso de fondo libera de forma idempotente reservas cuyo plazo de 10 minutos terminó; la transición es mutuamente excluyente con la confirmación de pago.
- **Usar REST síncrono en la Etapa I.** React/Vite consulta detalles y disponibilidad a Events. Purchases usa operaciones de reservar, confirmar, liberar y consultar reserva. El broker de mensajes se reserva para las colas de la Etapa III; las operaciones internas usan identificadores idempotentes para poder reintentarse.
- **Conservar snapshots en Purchases.** Purchases guarda evento, tipo de entrada, precio al comprar, cantidad y referencia de reserva para Mis Compras y recomendaciones futuras; modificaciones u ocultamiento del catálogo no reescriben el historial.
- **Aislar bases por servicio.** Docker Compose usa un servidor MySQL local con una base lógica, credenciales y engine SQLAlchemy por servicio. La infraestructura local compartida no implica compartir tablas ni transacciones.
- **Construir respuestas públicas desde Events.** La API devuelve descripción, fecha/hora, lugar, modalidad/precio y estado de disponibilidad (`Disponible`, `Agotada` o temporalmente no disponible si la venta no abrió o está Pausada), sin mostrar cantidades exactas.
- **Instrumentar cada API HTTP.** Middleware por servicio mide duración y registra autenticación/resultado; llamadas entre servicios incluyen identificadores de correlación.

## Risks / Trade-offs

- [La reserva y confirmación entre Events y Purchases pueden fallar parcialmente] → Usar operaciones idempotentes de reserva/confirmación/liberación, timeouts acotados, reintentos y reconciliación antes de marcar una compra Confirmada.
- [Events puede estar temporalmente fuera de servicio durante el checkout] → No iniciar nuevas reservas; consultar y completar reservas existentes cuando el servicio vuelva antes del vencimiento.
- [Un único servidor MySQL local es una simplificación de desarrollo] → Mantener una base lógica y permisos separados por servicio para poder mover bases independientemente después.
- [La disponibilidad puede cambiar entre catálogo y checkout] → Events revalida y reserva de forma atómica; ante carrera devuelve la indisponibilidad actual.

## Migration Plan

El sistema es greenfield. Crear la base y migraciones de Events antes de habilitar la publicación. No hay eventos de producción para migrar; se pueden usar fixtures de desarrollo para mockups y pruebas.
