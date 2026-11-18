# ADR-0005: Compras consulta Eventos de forma síncrona e idempotencia por clave

- Estado: Propuesto
- Fecha: 2026-11-18

## Contexto

El servicio de Compras registra compras de entradas para eventos cuyo catálogo pertenece a Eventos ([ADR-0003](0003-servicio-eventos-e-inventario.md)). Compras necesita saber si un evento existe, está activo y ofrece una modalidad general, sin duplicar esa información. Además, una misma solicitud puede reenviarse por un fallo de red o un reintento del cliente y no debe generar compras duplicadas.

## Decisión

1. **Base propia:** Compras usa una base PostgreSQL dedicada (`compras_db`) y no accede a la base de Eventos.
2. **Consulta síncrona al catálogo:** al registrar una compra, Compras consulta `GET /eventos/{id}` de Eventos por HTTP. No replica ni cachea el catálogo en esta etapa. La compra guarda solo los identificadores del evento y de la modalidad.
3. **Fallo parcial:** si Eventos no responde o devuelve un error inesperado, Compras rechaza la operación con `503 Service Unavailable` y no registra la compra.
4. **Idempotencia por clave:** cada solicitud de compra exige la cabecera `Idempotency-Key`. La clave es única por cliente, con restricción en la base de datos. Repetir la clave con el mismo contenido devuelve la compra original sin crear otra; repetirla con contenido distinto se rechaza con `409`.

## Consecuencias

### Positivas

- Eventos sigue siendo la única fuente de verdad del catálogo.
- Los servicios mantienen bases y despliegues independientes.
- La restricción única en la base resuelve también los reintentos concurrentes con la misma clave.

### Negativas

- Registrar una compra depende de la disponibilidad de Eventos.
- Si un evento se da de baja después de la compra, Compras conserva la compra sin enterarse del cambio.
- Cada compra agrega una llamada HTTP, con su latencia, al camino de escritura.

## Alternativas consideradas

- **Replicar el catálogo en Compras:** se descarta porque crea una segunda fuente de verdad y exige sincronización que esta etapa no justifica.
- **Compartir la base de datos con Eventos:** se descarta porque acopla los servicios y rompe el despliegue independiente.
- **Cache del catálogo en Compras:** se pospone a la etapa de cache.
- **Deduplicar por contenido sin clave de idempotencia:** se descarta porque impide distinguir un reintento de una compra legítimamente repetida.
