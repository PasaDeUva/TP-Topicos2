# Diseño: cliente web de acceso y cuenta

## Context

La motivación y el alcance están en [proposal.md](proposal.md); los comportamientos se detallan en [la spec](specs/acceso-cuenta-web/spec.md). `frontend/mock-app` es una aplicación de ejemplo con React, Vite y TypeScript que solo consulta el servicio mock. Identity implementa sesiones rotativas, pero sus endpoints actuales entregan el refresh token en JSON. El diseño de `gestion-de-accesos` reservó el tratamiento seguro de sesión web para un cambio posterior.

## Goals / Non-Goals

**Goals:**

- Incorporar una aplicación web extensible sin convertir el servicio mock en un componente de producción.
- Mantener una sola sesión lógica y las reglas actuales de Identity para API y navegador.
- Hacer verificables la protección CSRF, la restauración y la concurrencia real entre pestañas.

**Non-Goals:**

- Implementar catálogo, compras, administración de organizadores o consumidores de eventos.
- Resolver autenticación externa, verificación de email o recuperación pública de contraseña.
- Cambiar la validación de roles vigente de los servicios consumidores definida en ADR-0004.

## Decisions

### Aplicación y límites

Crear `frontend/web-app/` como aplicación independiente y conservar `frontend/mock-app/` como ejemplo. Usar el stack aceptado en ADR-0001. Separar la presentación de formularios y estados de la lógica de sesión y del cliente HTTP; no incorporar bibliotecas de estado o navegación sin una necesidad comprobada.

La aplicación ofrece registro de cliente u organizador, inicio, cuenta y solicitud de rol adicional. El registro exitoso dirige al inicio de sesión; no inicia una sesión implícitamente. El perfil muestra email, identificador y roles con estados; un organizador pendiente puede iniciar sesión para consultar su situación.

### Contrato de sesión web

Aplicar [ADR-0009](../../../docs/adr/0009-sesion-web-identity.md), propuesto, y los requisitos web diferidos en `gestion-de-accesos/design.md`. Añadir una interfaz web separada bajo `/auth/web/`, conservando los endpoints JSON actuales:

| Operación | Entrada | Resultado |
| --- | --- | --- |
| `POST /auth/web/login` | Email y contraseña en JSON; origen permitido. | JWT de acceso y token CSRF en JSON, refresh token solo en cookie HttpOnly. |
| `GET /auth/web/csrf` | Cookie de renovación vigente. | Token CSRF asociado a la sesión para restauración tras recarga, sin rotar la credencial. |
| `POST /auth/web/refresh` | Cookie, token CSRF en cabecera y origen permitido. | Rota el refresh token en cookie y devuelve nuevo JWT; nunca devuelve el refresh token en JSON. |
| `POST /auth/web/logout` | Cookie, token CSRF en cabecera y origen permitido. | Revoca la sesión renovable, elimina la cookie y retorna 204. |

El registro, consulta de cuenta y solicitud de roles reutilizan los endpoints existentes; los dos últimos usan el JWT de acceso. Las respuestas de sesión no son cacheables y los errores usan el formato existente `code`/`message`, sin contraseñas ni tokens. El login web no diferencia email inexistente, contraseña incorrecta ni acceso no permitido. Las validaciones y errores concretos se documentarán en OpenAPI y se probarán para ambos contratos.

Para no duplicar reglas ni depender de llamadas HTTP internas, extraer lógica de emisión, rotación y revocación a operaciones compartidas por los adaptadores JSON y web. Mantener transacciones, bloqueo de sesión, detección de reutilización, límite absoluto y revocación de sesiones de administrador al recuperar contraseña. Un refresh anterior reutilizado revoca la sesión; ningún JWT emitido supera su vencimiento absoluto.

### Cookie, CSRF y orígenes

La cookie es host-only, HttpOnly y con ruta que cubra todas las operaciones web de sesión; usa Secure en HTTPS y SameSite=Strict para despliegues de un mismo sitio. La excepción HTTP local se habilita explícitamente solo en Compose de desarrollo. Se elimina con los mismos atributos de ámbito utilizados para crearla. No almacenar el refresh token en localStorage, sessionStorage ni IndexedDB.

El JWT de acceso permanece en memoria y se descarta al cerrar, expirar o perder acceso. El token CSRF se vincula a la sesión y se entrega a JavaScript solo desde respuestas no cacheables de orígenes permitidos. Su verificación debe usar una comparación segura y permitir recuperarlo tras recargar sin exponer la credencial de renovación; cualquier material secreto necesario para generarlo debe ser estable y configurable fuera del repositorio. Los POST web de login, refresh y logout rechazan orígenes no permitidos; refresh y logout requieren además el token CSRF. La respuesta a GET de recuperación de CSRF no debe habilitar lectura desde orígenes no autorizados.

Para desarrollo usar un proxy de Vite desde el mismo origen del frontend hacia Identity; evitar abrir CORS indiscriminadamente. Si hay orígenes distintos, admitir solamente los configurados con credenciales. El alcance de esta entrega es un mismo sitio; un despliegue entre sitios diferentes requiere revisar explícitamente la política de cookies y el canal antes de habilitarlo.

Configurar un único origen de frontend por instancia de Identity, aunque frontend e Identity tengan orígenes distintos. Así todas las pestañas que comparten la cookie comparten también el ámbito de Web Locks y BroadcastChannel; una configuración con múltiples orígenes de frontend se rechaza.

### Coordinación y estados del cliente

Una capa de sesión centraliza inicio, restauración, renovación, consulta de perfil y cierre. Coordinar las operaciones que usan o invalidan refresh entre pestañas del mismo origen mediante exclusión mutua entre pestañas, adquirida antes de enviar la solicitud; nunca copiar el refresh token. Difundir el cierre para limpiar el estado de las otras pestañas. Si no se puede garantizar exclusión, fallar de forma segura y solicitar reautenticación en lugar de reutilizar una credencial incierta. Una respuesta perdida puede dejar el resultado desconocido y requerir un nuevo login.

La interfaz distingue carga, autenticado, error de credenciales, validación y servicio no disponible. Evitar reintentos automáticos de renovación no coordinados, logs de secretos y datos de una cuenta anterior tras cerrar sesión. Los escenarios de navegador deberán usar al menos dos pestañas reales para detectar concurrencia y verificar restauración, expiración y cierre.

## Risks / Trade-offs

- [Renovaciones concurrentes o respuesta perdida] → Exclusión entre pestañas, sin reintentos ciegos y reautenticación cuando el resultado no sea seguro.
- [CSRF o CORS permisivo] → Token vinculado a sesión, validación de origen, allowlist explícita y pruebas negativas.
- [HTTP local frente a cookies Secure] → Excepción restringida al entorno local y pruebas reales; otros entornos usan HTTPS.
- [Interfaz web altera contratos existentes] → Adaptadores separados sobre la misma lógica y pruebas de regresión del cliente API JSON.
- [Identity no disponible] → No afirmar que hay sesión válida; conservar un error recuperable sin exponer datos de otra cuenta.

## Migration Plan

Incorporar interfaz web y configuración compatible junto a los endpoints actuales; desplegar Identity preparado antes de habilitar el frontend. El rollback deshabilita el frontend y sus rutas web sin cambiar los endpoints JSON ni requerir migrar cuentas. Cualquier cambio de persistencia de sesión deberá incluir migración y reversión verificadas sobre una base de prueba.
