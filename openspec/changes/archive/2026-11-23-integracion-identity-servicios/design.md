# Design

## Context

Eventos usa `owner_id` del body y Compras usa `cliente_id` del body o query. Identity ya expone verificación de sesión y consulta de roles autenticadas por servicio. El contrato actual y el [ADR-0011](../../../docs/adr/0011-revocacion-inmediata-sesiones.md) exigen comprobar el estado vigente sin depender solo de claims.

## Goals / Non-Goals

**Goals:** aplicar el límite de confianza documentado en [ADR-0013 propuesto](../../../docs/adr/0013-identidad-en-eventos-y-compras.md) sin duplicar cuentas ni almacenar tokens.

**Non-Goals:** implementar interfaces web nuevas, pagos, inventario o integración de servicios no identificados en la propuesta.

## Decisions

1. **Autenticación y roles:** cada consumidor verifica localmente firma RS256, emisor, audiencia, expiración y claims requeridos con una clave pública confiable. Luego envía el token completo por canal protegido a `POST /internal/sessions/verify`, comprueba que el `account_id` coincida con el `sub` verificado y consulta los roles actuales. No usar caché que retrase revocaciones. Se descarta confiar solo en el JWT, que no refleja la revocación ni los roles actuales.
2. **Credenciales y transporte:** Eventos y Compras usan identidades y secretos propios, con permisos `sessions_read` y `roles_read` explícitos. Los valores se suministran por configuración fuera del repositorio; los defaults existentes que solo habilitan roles no conceden sesiones automáticamente. Fuera de local/pruebas aisladas se exige HTTPS con validación de certificados. HTTP se permite solo con habilitación explícita para desarrollo local o pruebas aisladas, con credenciales de prueba y sin secretos reales. La excepción debe rechazarse fuera de esos entornos. No registrar tokens, secretos ni cuerpos sensibles.
3. **Autorización de recursos:** Eventos exige organizador `habilitado` para escritura y contrasta el propietario guardado para edición y baja. Compras exige cliente `activo`, filtra por identidad verificada y protege el detalle individual. Los campos opcionales existentes solo se aceptan si coinciden con la cuenta verificada; no permiten transferencias de propiedad. Las lecturas de catálogo mantienen el contrato actual, incluso su tratamiento de eventos inactivos.
4. **Errores y fallos:** token ausente, inválido o revocado recibe `401`; rol insuficiente o identificador proporcionado distinto recibe `403`; recurso inexistente o ajeno recibe `404`. Fallas de red, timeout, configuración, credenciales de servicio o respuestas inconsistentes de Identity reciben `503`; ninguna permite operar. La respuesta `401` de verificación se distingue por su `code`: `invalid_credentials` corresponde al token de usuario y `invalid_service_credentials` a la dependencia. Otros errores inesperados de la dependencia se tratan como no verificables.
5. **Compras idempotentes:** autenticar y verificar rol antes de buscar la clave; conservar la unicidad por cliente autenticado y la respuesta sin consultar Eventos para un reintento ya registrado. Se descarta buscar primero porque podría revelar una compra antes de verificar permisos.

## Risks / Trade-offs

- [Identity no disponible o revocación concurrente] → fallar cerrado; una operación ya autorizada puede finalizar, las nuevas posteriores a la revocación se rechazan.
- [Transición de clientes] → comunicar el requisito de token y la regla de coincidencia; los clientes anónimos y suplantaciones dejarán de funcionar.
- [Secretos y claves] → aprovisionar credenciales por servicio y clave pública confiable sin incluir secretos reales en repositorio o logs; probar errores de configuración y ausencia de filtraciones.
- [HTTP local no cifra credenciales] → exigir opt-in explícito y restringirlo a desarrollo local o pruebas aisladas; usar credenciales de prueba y exigir HTTPS validado fuera de esos entornos.
- [Cambios paralelos de inventario] → coordinar la integración con el PR de inventario antes de aplicar cambios solapados en contratos de Eventos.

## Migration Plan

Revisar ADR y contratos; habilitar credenciales y canal de Identity en entorno aislado; desplegar consumidores compatibles con verificación y actualizar clientes. Verificar autenticación, revocación, propiedad y fallas en Compose aislado antes de cualquier despliegue al entorno activo. La reversión reabre las operaciones anónimas de las versiones anteriores, por lo que debe comunicarse y limitarse; no eliminar datos ni secretos existentes.
