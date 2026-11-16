# Design: gestión de accesos

## Context

La propuesta y `specs/gestion-de-cuentas/spec.md` definen el alcance funcional. El repositorio cuenta con un servicio de ejemplo, pero no con un servicio Identity. El stack aprobado es FastAPI, SQLAlchemy y PostgreSQL ([ADR-0001](../../../docs/adr/0001-stack-inicial.md)). El diseño de Events acepta por ahora `owner_id` sin autenticar y difiere su integración con identidad.

## Goals / Non-Goals

**Goals:**

- Delimitar un servicio Identity independiente y el contrato necesario para que otros servicios identifiquen usuarios y consulten roles vigentes.
- Conservar una identidad por cuenta con estados independientes para cliente y organizador.
- Evitar exponer contraseñas o secretos de firma a los consumidores.

**Non-Goals:**

- Implementar la integración en Events o Purchases dentro de este cambio.
- Verificación de email, proveedores externos, recuperación de contraseña y cobros reales.
- Implementar el cliente web y su protección de sesión específica; sus requisitos quedan registrados para una integración posterior.

## Decisions

### Límite de Identity y datos

El servicio Identity es dueño de cuentas, credenciales y asignaciones de roles. Usa una base PostgreSQL propia y expone sus capacidades mediante una API; los demás servicios no acceden directamente a sus tablas. Una cuenta tiene un identificador estable y puede tener roles de cliente y organizador con estados independientes. Se descarta duplicar cuentas por rol porque rompe la identidad compartida acordada.

Las contraseñas se almacenan solo como hashes generados mediante una función de hashing de contraseñas con sal y factor de costo configurable. Nunca se devuelven por API ni se registran en la bitácora. Los parámetros y la biblioteca concretos se seleccionarán durante el diseño detallado de implementación.

#### Modelo lógico de Identity

| Entidad | Datos y relaciones | Restricciones principales |
| --- | --- | --- |
| Cuenta | Identificador estable, email y hash de contraseña. | Identificador único; email obligatorio y único; hash obligatorio. |
| Asignación de rol | Cuenta, tipo de rol y estado. | Referencia obligatoria a una cuenta existente; combinación de cuenta y rol única; tipo y estado obligatorios. |
| Sesión | Identificador, cuenta, inicio, vencimiento absoluto y estado de revocación. | Identificador único; referencia obligatoria a una cuenta existente; vencimiento como máximo 24 horas después del inicio. |
| Credencial de renovación | Referencia a la sesión, representación verificable del secreto y estado de uso o revocación. | Cada credencial pertenece a una sesión; su representación es única y no almacena el secreto en texto plano; como máximo una credencial vigente por sesión. |

Los roles contemplados son cliente, organizador y administrador. Al registrarse, el cliente queda activo y el organizador pendiente; el administrador puede habilitar, deshabilitar o volver a habilitar al organizador. Los estados de cada asignación se conservan de forma independiente. El registro público no asigna el rol administrador.

La rotación marca la credencial anterior como consumida y crea la siguiente de manera atómica. Se conserva la información necesaria de las credenciales consumidas durante la vida de la sesión para identificar una reutilización y revocar esa sesión, incluso ante solicitudes concurrentes. El cierre de sesión revoca la sesión y su renovación vigente.

Este modelo describe entidades y restricciones, no el DDL definitivo: la migración de implementación definirá tipos SQL, índices y políticas de borrado sin debilitar estas reglas. Los datos de Eventos y Compras pertenecen a sus respectivos servicios y no forman parte de este esquema.

### Credencial e integración

Identity autentica email y contraseña y emite un JWT de acceso con vigencia máxima de una hora, firmado con RS256 mediante clave privada. Los servicios consumidores verificarán firma con clave pública confiable, algoritmo esperado, emisor, audiencia y vencimiento. Para operaciones protegidas consultarán a Identity el estado actual de los roles, sin confiar únicamente en claims del token. El intercambio de JWT y las alternativas se registran en [ADR-0004](../../../docs/adr/0004-autenticacion-entre-servicios.md), propuesto para revisión del equipo.

La renovación utiliza una credencial separada y rotativa: cada uso exitoso invalida la anterior y emite otra junto con un nuevo JWT. La sesión termina como máximo 24 horas después del inicio de sesión y ningún JWT emitido puede vencer después de ese límite. Detectar la reutilización de una credencial anterior revoca la sesión; Identity conserva el estado necesario y rechaza renovaciones de cuentas sin acceso permitido.

#### Requisitos para la futura integración web

Estos requisitos se conservan para el cambio que integre el cliente web; no forman parte de la implementación ni de la verificación de esta entrega:

- Mantener el JWT de acceso en memoria y entregar la credencial de renovación en una cookie HttpOnly, sin atributo Domain, con SameSite=Strict cuando frontend e Identity compartan sitio y Secure en HTTPS.
- Tratar el HTTP local como una excepción explícita y verificarla en navegador; no depender de ella en otros entornos.
- Usar POST para renovación y cierre de sesión, exigir un token CSRF asociado a la sesión en un encabezado y validar ese token y los orígenes permitidos. Si los orígenes difieren, configurar CORS solo para los orígenes y credenciales permitidos.
- Coordinar renovaciones entre pestañas para evitar reutilizaciones simultáneas y contemplar que una respuesta perdida puede obligar a iniciar sesión nuevamente. Al cerrar sesión, eliminar la cookie de renovación.

#### Cierre de sesión y consumidores

El cierre de sesión invalida la renovación. Sin una consulta adicional de revocación, un JWT previamente emitido puede seguir siendo válido hasta su vencimiento; no se promete revocación inmediata del JWT en consumidores que verifican localmente.

La API de Identity ofrece la consulta de identidad propia y un endpoint interno que recibe el identificador de cuenta y devuelve los roles y estados actuales. Cada servicio consumidor dispone de una credencial propia, externa al repositorio, que Identity verifica y autoriza antes de responder. Se rechazan credenciales ausentes o inválidas y consultas de cuentas inexistentes. La conexión desde Events y Purchases y la protección del canal se acordarán con sus responsables antes de integrarlos; una red interna por sí sola no autentica al consumidor.

Events deberá verificar por separado que la identidad autenticada tenga rol organizador habilitado y sea dueña del evento; no se debe confiar en `owner_id` recibido del cliente. El cambio actual de Events aún no implementa esa validación, por lo que se requiere un cambio de integración posterior. Purchases deberá asociar las compras a la identidad autenticada y no a un identificador arbitrario enviado por el cliente.

### Contrato HTTP propuesto

La API utiliza JSON. Los endpoints de identidad propia y administración reciben el JWT de acceso en `Authorization: Bearer <token>`; el endpoint interno exige la credencial propia del servicio, no el JWT de una persona. Las rutas y estructuras siguientes se proponen para acordar con los consumidores antes de implementar.

| Método y ruta | Entrada | Respuesta exitosa | Errores principales |
| --- | --- | --- | --- |
| `POST /auth/register` | `email`, `password`, `role` (`cliente` u `organizador`) | `201`: `account_id`, `email`, roles y estados | `400`: datos inválidos; `409`: email registrado |
| `POST /auth/login` | `email`, `password` | `200`: `access_token`, `refresh_token`, `token_type`, `expires_in` | `400`: datos inválidos; `401`: credenciales incorrectas o acceso no permitido |
| `POST /auth/refresh` | `refresh_token` | `200`: nuevo `access_token`, nuevo `refresh_token`, `token_type`, `expires_in` | `400`: datos inválidos; `401`: credencial inválida, vencida o revocada, o cuenta sin acceso permitido |
| `POST /auth/logout` | `refresh_token` | `204`: sesión cerrada y renovación revocada | `400`: datos inválidos; `401`: credencial inválida, vencida o revocada |
| `GET /auth/me` | JWT de acceso | `200`: `account_id`, `email`, roles y estados | `401`: JWT ausente, inválido o vencido |
| `POST /auth/me/roles` | JWT de acceso y `role` (`cliente` u `organizador`) | `200`: roles y estados actualizados | `400`: rol inválido; `401`: JWT inválido; `409`: rol ya asignado |
| `PATCH /admin/organizers/{account_id}/status` | JWT de administrador y `status` (`habilitado` o `deshabilitado`) | `200`: `account_id` y estado del rol organizador | `400`: estado inválido; `401`: JWT inválido; `403`: sin permiso; `404`: cuenta o rol inexistente |
| `GET /internal/accounts/{account_id}/roles` | Credencial autorizada del servicio | `200`: `account_id` y roles con estados actuales | `401`: credencial ausente o inválida; `403`: servicio sin permiso; `404`: cuenta inexistente |

En las respuestas, `roles` representa una lista de objetos con `role` y `status`; los estados de cliente y organizador son independientes. `token_type` es `Bearer` y `expires_in` expresa segundos. Las credenciales de renovación son secretas: no se incluyen en bitácoras ni se transmiten en URLs. Los errores usan `code` y `message`, sin contraseñas, tokens ni detalles internos; el mensaje de login no distingue entre email inexistente, contraseña incorrecta y acceso no permitido.

Antes de autorizar una nueva operación protegida por rol, el consumidor consulta el estado actual y rechaza la operación si el rol no está habilitado o si la consulta falla. Una operación ya autorizada antes de que se haga efectiva una deshabilitación puede finalizar. El contrato y el canal de integración se acordarán con los responsables de los servicios consumidores; no se implementan esos consumidores en este cambio.

### Administración inicial

El registro público no concede el rol administrador. Un procedimiento de inicialización controlado crea el primer administrador con email y contraseña suministrados por configuración y almacena solo el hash. Repetirlo no duplica la cuenta ni restablece su contraseña. Un comando administrativo separado, restringido a quienes tienen acceso autorizado al entorno, permite recuperar el acceso cambiando la contraseña, sin endpoint público. Un rol de cliente activo sigue siendo utilizable aunque el de organizador esté pendiente o deshabilitado.

### Entorno local

Docker Compose debe permitir iniciar Identity y su base de datos con un solo comando. El arranque espera la disponibilidad de la base y completa las migraciones y el seed antes de aceptar solicitudes. Para desarrollo local se permiten credenciales conocidas de demostración, reemplazables por configuración no versionada; otros entornos deben proporcionar valores propios. Un paso de inicialización genera las claves de firma si no existen y las conserva entre reinicios: solo Identity recibe la privada y los consumidores reciben la pública. Las credenciales de los consumidores locales deben coincidir con las configuradas en Identity. La integración efectiva de Events y Purchases queda fuera de este cambio.

## Risks / Trade-offs

- [Identity no disponible durante una consulta de roles] → Las acciones protegidas fallan de forma cerrada; las consultas públicas no requieren esa dependencia.
- [Un token vigente contiene permisos obsoletos] → Consultar el estado actual para acciones protegidas y no autorizar solo con roles incorporados al token.
- [Claves comprometidas o mal distribuidas] → Mantener la clave privada fuera del repositorio y limitar la distribución de claves públicas a fuentes confiables; definir rotación antes de integrar.
- [Eventos todavía acepta `owner_id` sin validación] → Mantener la deuda explícita y coordinar un cambio de integración antes de considerar protegidas sus operaciones.

## Migration Plan

No hay cuentas existentes para migrar. La implementación deberá crear el esquema de Identity, provisionar el administrador inicial y comprobar los contratos antes de conectar los demás servicios. La estrategia de migraciones y reversión se detallará al planificar las tareas.

## Open Questions

- Acordar con el equipo la protección del canal y la distribución confiable y rotación de claves antes de integrar servicios; esa integración no forma parte de este cambio.
