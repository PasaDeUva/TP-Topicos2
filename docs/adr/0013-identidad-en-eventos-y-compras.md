# ADR-0013: Identidad autenticada en Eventos y Compras

- Estado: Propuesto
- Fecha: 2026-11-22

## Contexto

Eventos y Compras aceptan identificadores de cuenta suministrados por el cliente. Identity ya ofrece validación de sesión y roles; los ADR-0004 y ADR-0011 establecen las obligaciones de verificación y revocación.

## Decisión

Se propone que los servicios deriven la identidad de la credencial autenticada y verifiquen la sesión y los roles vigentes con Identity. Para facilitar la transición, `owner_id` y `cliente_id` podrán omitirse; si se proporcionan, deberán coincidir con la identidad autenticada. Eventos comprobará además la propiedad del recurso. Las consultas de catálogo conservan su carácter público.

Fuera de desarrollo local y pruebas aisladas, el canal hacia Identity utilizará HTTPS con verificación de certificados. Se admite HTTP solo con una habilitación explícita para desarrollo local o pruebas aisladas, usando credenciales de prueba y sin secretos reales; una red de contenedores no sustituye el canal protegido.

## Consecuencias

### Positivas

- Una solicitud no puede atribuir una operación a otra cuenta mediante un identificador arbitrario.
- Se conserva compatibilidad de forma para clientes que envían su propio identificador.

### Negativas

- Los clientes deben autenticarse y las operaciones protegidas dependen de Identity.
- Los clientes que enviaban identificadores ajenos dejarán de ser aceptados; se requieren pruebas y comunicación de transición.
- El entorno local HTTP requiere una excepción explícita y no representa la protección de transporte exigida en otros entornos.

## Alternativas consideradas

- Confiar en los identificadores enviados: descartado porque permite suplantar cuentas.
- Eliminar inmediatamente los campos: descartado para facilitar la transición de clientes compatibles.
