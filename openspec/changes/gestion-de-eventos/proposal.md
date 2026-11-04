# Proposal

## Why

Los organizadores necesitan preparar eventos antes de hacerlos públicos, y los clientes solo deben poder comprar entradas de eventos publicados. Una vez que existen compras, el sistema también debe proteger las condiciones de esas compras ante cambios posteriores del evento.

## What Changes

- Permitir guardar eventos como borradores, visibles para el organizador pero no listados ni disponibles para la compra.
- Permitir que un organizador habilitado publique explícitamente un evento, sin aprobación administrativa individual por evento.
- Permitir que administradores pausen o despubliquen eventos existentes; los eventos en esos estados dejan de aceptar nuevas compras.
- Restringir cambios que alteren condiciones de compras existentes.
- Bloquear cambios de precio para todas las entradas de un evento cuando ya existan compras asociadas.
- Mantener la reprogramación y cancelación de eventos fuera de este cambio; su resolución y las devoluciones se definirán en una etapa posterior.

## Capabilities

### New Capabilities

- `publicacion-eventos`: ciclo de borrador, publicación, pausa y despublicación de eventos, con protección de las compras existentes.

### Modified Capabilities

Ninguna. El proyecto todavía no tiene especificaciones de capacidades existentes.

## Impact

El cambio define el ciclo funcional de publicación de eventos y cómo sus cambios afectan la disponibilidad de nuevas compras y las condiciones previamente adquiridas. La aprobación inicial del organizador se define en `gestion-de-accesos`; aquí se cubre la publicación de cada evento. La cancelación, reprogramación y gestión de devoluciones quedan para cambios posteriores, incluyendo la Etapa III del TP. El stack acordado es Python/FastAPI, SQLAlchemy, MySQL con InnoDB, React con TypeScript y Vite, y Docker; el diseño detalla los límites y contratos de los servicios.
