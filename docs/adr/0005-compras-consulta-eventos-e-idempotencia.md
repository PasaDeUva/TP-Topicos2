# ADR-0005: `compras-service` consulta `events-service` de forma síncrona e idempotencia por clave

- Estado: Aceptado
- Fecha: 2026-11-18

## Contexto

`compras-service` registra compras de entradas para eventos cuyo catálogo pertenece a `events-service` ([ADR-0003](0003-servicio-eventos-e-inventario.md)). `compras-service` necesita saber si un evento existe, está activo y ofrece una modalidad general, sin duplicar esa información. Además, una misma solicitud puede reenviarse por un fallo de red o un reintento del cliente y no debe generar compras duplicadas.

## Decisión

1. **Base propia:** `compras-service` usa una base PostgreSQL dedicada (`compras_db`) y no accede a la base de `events-service`.
2. **Consulta síncrona al catálogo (temporal, Etapa I):** al registrar una compra, `compras-service` consulta `GET /eventos/{id}` de `events-service` por HTTP. Es una simplificación de la Etapa I: se migrará a comunicación asíncrona en la Etapa III. No replica ni cachea el catálogo en esta etapa. La consulta tiene un timeout estricto menor a 1 segundo, configurable, para que la latencia de Eventos no degrade `compras-service`. La compra guarda solo los identificadores del evento y de la modalidad.
3. **Fallo parcial:** si `events-service` no responde o devuelve un error inesperado, `compras-service` rechaza la operación con `503 Service Unavailable` y no registra la compra.
4. **Idempotencia por clave:** cada solicitud de compra exige la cabecera `Idempotency-Key`. La clave es única por cliente, con restricción en la base de datos. Repetir la clave con el mismo contenido devuelve la compra original sin crear otra; repetirla con contenido distinto se rechaza con `409`.

## Consecuencias

### Positivas

- `events-service` sigue siendo la única fuente de verdad del catálogo.
- Los servicios mantienen bases y despliegues independientes.
- La restricción única en la base resuelve también los reintentos concurrentes con la misma clave.

### Negativas

- Registrar una compra depende de la disponibilidad de `events-service`.
- Si un evento se da de baja después de la compra, `compras-service` conserva la compra sin enterarse del cambio.
- Cada compra agrega una llamada HTTP, con su latencia, al camino de escritura.
- La consulta síncrona es una simplificación temporal de la Etapa I, no el diseño objetivo. Las directivas de la cátedra marcan las cadenas síncronas como anti-patrón en operaciones principales. Se revisará al introducir eventos asíncronos en la Etapa III.

## Alcance de esta decisión

Las decisiones de este ADR aplican al registro de compra de esta etapa. El flujo completo (reserva de tickets en `events-service`, creación del pago en `payment-service` y confirmación de la compra en `events-service`) queda fuera de este ADR. Esas integraciones se decidirán en un ADR propio cuando se diseñen sus changes. La idempotencia por clave definida aquí se mantiene como base para esos pasos.

## Alternativas consideradas

- **Replicar el catálogo en `compras-service`:** se descarta porque crea una segunda fuente de verdad y exige sincronización que esta etapa no justifica.
- **Compartir la base de datos con `events-service`:** se descarta porque acopla los servicios y rompe el despliegue independiente.
- **Cache del catálogo en `compras-service`:** se pospone a la etapa de cache.
- **Deduplicar por contenido sin clave de idempotencia:** se descarta porque impide distinguir un reintento de una compra legítimamente repetida.
