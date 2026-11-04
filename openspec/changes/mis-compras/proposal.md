# Propuesta

## Why

Los clientes necesitan consultar las compras que realizaron y conocer su estado, los eventos y las entradas incluidas. Definir desde la Etapa I el ciclo de pago y la reserva de inventario permite ofrecer un historial coherente y preparar el núcleo de compras sin anticipar decisiones tecnológicas ni implementar funcionalidades de etapas posteriores.

## What Changes

- Incorporar el historial **Mis Compras**, con compras de todos los estados, ordenadas de la más reciente a la más antigua.
- Mostrar evento, fecha, total histórico y desglose de entradas por tipo y cantidad.
- Soportar compras de entradas numeradas, asociadas a asientos específicos, y no numeradas, limitadas por la capacidad de una zona.
- Definir los estados y transiciones de compra para el pago pendiente, la confirmación, el fallo con reintento, el vencimiento de la reserva y la revisión manual de pagos tardíos.
- Usar un flujo de pago simulado en la Etapa I para ejercitar los resultados pendiente, exitoso y fallido, sin integrar una pasarela externa.
- Reservar la disponibilidad durante un máximo de 10 minutos desde el inicio de la compra y liberarla al vencer el plazo.
- Proteger la compra contra ventas duplicadas por reintentos o notificaciones de pago repetidas.
- Conservar la relación entre cliente, compra, evento y entradas para que el historial pueda servir como insumo de recomendaciones en una etapa posterior.
- Mantener separados el ciclo de compra/pago y los futuros ciclos de cola de venta y devolución.

## Capabilities

### New Capabilities

- `compras-cliente`: ciclo de compra de entradas y consulta de las compras propias del cliente.

### Modified Capabilities

Ninguna. El proyecto todavía no tiene especificaciones de capacidades existentes.

## Impact

El cambio define comportamiento para el flujo de compra, el registro de intentos de pago, la reserva de entradas y la consulta del historial por parte del cliente. La aplicación aún no tiene código en este repositorio. La selección tecnológica acordada es Python/FastAPI, SQLAlchemy, MySQL con InnoDB, React con TypeScript y Vite, y Docker; el diseño técnico se detallará después de cerrar las specs funcionales. El historial estructurado podrá ser utilizado por las recomendaciones de la Etapa II, sin incluir aquí preferencias ni el recomendador. Las políticas de caché se definirán en su propio cambio. Las colas de venta, las devoluciones, la búsqueda avanzada y las pruebas de carga quedan para la Etapa III; sus estados y procesos no se implementan ni se mezclan con los estados de pago de esta etapa. La generación y visualización de códigos QR también queda fuera de alcance por ahora.
