# Contrato para servicios consumidores

Antes de autorizar una operación protegida, el servicio consumidor valida el JWT localmente y consulta los roles actuales en Identity. Un JWT válido identifica la cuenta; no garantiza que un rol siga habilitado.

## 1. Validar identidad

- Obtener la clave pública de Identity desde una fuente confiable, separada de la clave privada.
- Aceptar solo `RS256` y verificar firma, `iss`, `aud` y `exp`; exigir también `sub`, `sid` e `iat`.
- Rechazar tokens ausentes, alterados, vencidos o con parámetros distintos de los configurados. `sub` es el UUID de la cuenta.
- El JWT de acceso dura como máximo una hora y no sobrepasa el límite absoluto de la sesión. Un JWT sin `sid` se rechaza tras activar este cambio; quien tenga una credencial de renovación vigente puede renovar o volver a iniciar sesión.

## 2. Verificar la sesión

Antes de cada nueva operación protegida, solicitar `POST /internal/sessions/verify` a través de un canal protegido con `X-Service-Id` y `X-Service-Token` propios. El cuerpo JSON contiene `{"access_token":"<JWT>"}`. El servicio debe tener permiso explícito booleano `sessions_read: true` en `SERVICE_CREDENTIALS_JSON`; configuraciones anteriores sin ese campo no conceden el nuevo permiso. Nunca enviar el token en la URL ni registrarlo.

Una respuesta `200` contiene únicamente `{"account_id":"<UUID>"}` y debe coincidir con el titular del token. `400` indica entrada malformada; `401`, credenciales o token inválidos o sesión revocada; `403`, servicio sin permiso; `503`, configuración no disponible. Cualquier error, timeout o respuesta malformada impide autorizar. Una autorización anterior a la revocación puede finalizar, pero una iniciada después debe rechazarse.

## 3. Consultar roles vigentes

Solicitar `GET /internal/accounts/{sub}/roles` con las cabeceras `X-Service-Id` y `X-Service-Token` propias del servicio. Identity configura `SERVICE_CREDENTIALS_JSON` como un objeto por servicio, cada uno con `token` y permiso booleano `roles_read`; los secretos deben suministrarse fuera del repositorio.

Una respuesta exitosa tiene la forma:

```json
{"account_id":"11111111-1111-1111-1111-111111111111","roles":[{"role":"organizador","status":"habilitado"}]}
```

`401` indica credenciales ausentes o inválidas; `403`, servicio sin permiso; `404`, cuenta inexistente; `503`, configuración de autenticación no disponible o inválida. Cualquier error, timeout, respuesta malformada o cuenta distinta de la solicitada impide verificar el rol.

## 4. Autorizar la operación

- Exigir el rol necesario en su estado permitido; para organizador, `habilitado`.
- Rechazar la operación si el rol no está habilitado **o no se puede verificar**. No usar claims de roles del JWT como sustituto.
- Verificar además las reglas propias del recurso, como la propiedad de un evento.
- Una operación autorizada antes de una deshabilitación puede terminar; una autorización nueva posterior debe rechazarla.

El canal seguro, la distribución y rotación de claves y la integración real de Eventos y Compras se acuerdan en su propio cambio. Una red interna por sí sola no autentica al servicio.
