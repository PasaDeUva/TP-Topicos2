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

## Decisions

### Límite de Identity y datos

El servicio Identity es dueño de cuentas, credenciales y asignaciones de roles. Usa una base PostgreSQL propia y expone sus capacidades mediante una API; los demás servicios no acceden directamente a sus tablas. Una cuenta tiene un identificador estable y puede tener roles de cliente y organizador con estados independientes. Se descarta duplicar cuentas por rol porque rompe la identidad compartida acordada.

Las contraseñas se almacenan solo como hashes generados mediante una función de hashing de contraseñas con sal y factor de costo configurable. Nunca se devuelven por API ni se registran en la bitácora. Los parámetros y la biblioteca concretos se seleccionarán durante el diseño detallado de implementación.

### Credencial e integración

Identity autentica email y contraseña y emite un JWT de acceso con vigencia máxima de una hora, firmado con RS256 mediante clave privada. Los servicios consumidores verificarán firma con clave pública confiable, algoritmo esperado, emisor, audiencia y vencimiento. Para operaciones protegidas consultarán a Identity el estado actual de los roles, sin confiar únicamente en claims del token. El intercambio de JWT y las alternativas se registran en [ADR-0004](../../../docs/adr/0004-autenticacion-entre-servicios.md), propuesto para revisión del equipo.

La renovación utiliza una credencial separada y rotativa: cada uso exitoso invalida la anterior y emite otra junto con un nuevo JWT. La sesión termina como máximo 24 horas después del inicio de sesión y ningún JWT emitido puede vencer después de ese límite. Detectar la reutilización de una credencial anterior revoca la sesión; Identity conserva el estado necesario y rechaza renovaciones de cuentas sin acceso permitido.

En el cliente web el JWT de acceso permanece en memoria y la credencial de renovación se entrega en una cookie HttpOnly, sin atributo Domain, con SameSite=Strict cuando frontend e Identity compartan sitio y Secure en HTTPS. El modo HTTP local requiere una excepción explícita y pruebas en navegador; no se debe depender de ella en otros entornos. Renovación y cierre de sesión usan POST y exigen un token CSRF asociado a la sesión y enviado en un encabezado; Identity valida el token y los orígenes permitidos. Si los orígenes difieren, CORS permite únicamente los orígenes configurados y credenciales. El cliente coordina las renovaciones entre pestañas para evitar reutilizaciones simultáneas; una respuesta perdida puede obligar a iniciar sesión otra vez.

El cierre de sesión invalida la renovación y elimina la cookie. Sin una consulta adicional de revocación, un JWT previamente emitido puede seguir siendo válido hasta su vencimiento; no se promete revocación inmediata del JWT en consumidores que verifican localmente.

La API de Identity ofrece la consulta de identidad propia y un endpoint interno que recibe el identificador de cuenta y devuelve los roles y estados actuales. Cada servicio consumidor dispone de una credencial propia, externa al repositorio, que Identity verifica y autoriza antes de responder. Se rechazan credenciales ausentes o inválidas y consultas de cuentas inexistentes. La conexión desde Events y Purchases y la protección del canal se acordarán con sus responsables antes de integrarlos; una red interna por sí sola no autentica al consumidor.

Events deberá verificar por separado que la identidad autenticada tenga rol organizador habilitado y sea dueña del evento; no se debe confiar en `owner_id` recibido del cliente. El cambio actual de Events aún no implementa esa validación, por lo que se requiere un cambio de integración posterior. Purchases deberá asociar las compras a la identidad autenticada y no a un identificador arbitrario enviado por el cliente.

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
