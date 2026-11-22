# ADR-0010: Consulta administrativa de organizadores

- Estado: Propuesto
- Fecha: 2026-11-20

## Contexto

Identity permite cambiar el estado de un organizador, pero no ofrece una consulta administrativa que permita encontrar las asignaciones desde la web. La consulta expondrá datos de cuentas y requiere control de acceso vigente.

## Decisión

Proponer una consulta aditiva en Identity para administradores activos que entregue únicamente identificador, email y estado del rol organizador. La autorización se comprueba en el servidor en cada solicitud. La web reutiliza la operación existente de cambio de estado y la sesión web actual; CORS permite PATCH solo para los orígenes ya configurados.

## Consecuencias

### Positivas

- Permite administrar solicitudes sin acceso directo a la base de datos.
- Conserva los contratos existentes y comprueba los permisos actuales en Identity.

### Negativas

- Agrega una superficie de API que expone datos personales a administradores autorizados.
- Requiere pruebas adicionales de autorización, CORS y manejo de estados concurrentes.

## Alternativas consideradas

- Acceso directo desde el cliente a la base: descartado por exposición de datos y credenciales.
- Identificar cuentas manualmente y usar solo el PATCH actual: descartado por no ofrecer descubrimiento de solicitudes.
