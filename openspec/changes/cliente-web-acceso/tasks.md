# Tareas: cliente web de acceso y cuenta

## 1. Base y compatibilidad de Identity

- [x] 1.1 Extraer la lógica de inicio, rotación y revocación de sesión para reutilizarla sin llamadas HTTP internas; ejecutar las pruebas actuales, incluidas concurrencia y recuperación administrativa.
- [x] 1.2 Preparar configuración explícita de orígenes, cookie y material CSRF estable, con excepción HTTP limitada a desarrollo; probar rechazo de configuración incompleta fuera del entorno local.
- [x] 1.3 Si la implementación requiere cambios persistentes para CSRF o sesiones, agregar migración reversible; verificar actualización y reversión sin perder cuentas ni sesiones compatibles. No aplica: CSRF se deriva de la sesión existente y no se modifica el esquema.

## 2. Contrato web de sesión

- [x] 2.1 Implementar `POST /auth/web/login` y emisión de cookie host-only HttpOnly; probar credenciales incorrectas, origen no permitido, atributos y que el JSON no exponga el refresh token.
- [x] 2.2 Implementar `GET /auth/web/csrf` para una sesión vigente, con respuesta no cacheable; probar recarga, sesión inválida y restricciones de lectura desde orígenes no autorizados.
- [x] 2.3 Implementar `POST /auth/web/refresh` con cookie, CSRF, origen y rotación atómica; probar rechazos, reutilización, concurrencia y límite absoluto de 24 horas.
- [x] 2.4 Implementar `POST /auth/web/logout` con revocación y eliminación de cookie; probar CSRF y origen inválidos, cierre exitoso y rechazo de renovación posterior.
- [x] 2.5 Documentar rutas y errores web en OpenAPI y verificar mediante pruebas que el contrato JSON previo de registro, login, refresh y logout conserva códigos y estructuras.

## 3. Cliente web de acceso y cuenta

- [x] 3.1 Crear `frontend/web-app/` con React, Vite y TypeScript, configuración de Compose y proxy local a Identity; verificar arranque, build, lint y typecheck sin modificar el mock.
- [x] 3.2 Implementar registro de cliente y organizador e inicio de sesión, con estados de carga y errores; probar datos inválidos, email duplicado, credenciales rechazadas y fallo del servicio.
- [x] 3.3 Implementar cuenta e identidad autenticada con roles y estados, solicitud del rol faltante y control de duplicados; probar organizador pendiente/deshabilitado e independencia del rol cliente.
- [x] 3.4 Implementar estado de sesión con JWT solo en memoria, restauración, expiración y limpieza al cerrar; probar que no queden credenciales ni datos de otra cuenta tras logout o sesión inválida.
- [x] 3.5 Implementar exclusión mutua y propagación entre pestañas para refresh y logout, con fallo seguro si no puede garantizarse; probar concurrencia, cierre remoto y respuesta de renovación perdida.

## 4. Verificación integral y documentación

- [x] 4.1 Ejecutar pruebas de navegador con dos pestañas sobre frontend e Identity en Compose: registro, login, recarga, renovación simultánea, estados de rol y logout; verificar que no ocurra reutilización involuntaria.
- [x] 4.2 Verificar en navegador cookie HttpOnly, SameSite y Secure bajo HTTPS, excepción HTTP local, CSRF y orígenes; comprobar que el refresh token no aparezca en JSON, almacenamiento web ni logs.
- [x] 4.3 Documentar arranque, configuración de orígenes y secretos, comandos de prueba, recuperación ante sesión vencida y límites de soporte; ejecutar los comandos documentados.
- [x] 4.4 Ejecutar suite de backend, regresión API JSON, lint, typecheck, build y pruebas de navegador; registrar resultados y comprobar que Events y el mock continúan pasando.

## Workflow follow-up

- Revisar el ADR-0009 con el equipo antes de integrar la implementación.
- Coordinar el cierre del change `gestion-de-accesos` y la sincronización de su spec sin duplicar requisitos.
- Planificar catálogo, compras, administración y la integración de servicios en cambios posteriores.
