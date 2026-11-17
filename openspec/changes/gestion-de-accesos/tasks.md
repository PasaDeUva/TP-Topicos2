# Tasks: gestión de accesos

## 1. Servicio y persistencia

- [x] 1.1 Crear `backend/identity-service/` con FastAPI, dependencias, configuración y Dockerfile; verificar que el servicio inicia y expone su estado de salud.
- [x] 1.2 Configurar PostgreSQL propio en Docker Compose para las pruebas de persistencia y Alembic con la migración inicial de cuentas, roles y sesiones; verificar migración y reversión sobre una base de prueba.
- [x] 1.3 Implementar almacenamiento de contraseñas con hash seguro y unicidad de email; verificar con pruebas de persistencia que no se guardan contraseñas en texto plano y se rechazan duplicados.

## 2. Cuentas y administración

- [x] 2.1 Implementar registro de cliente y organizador, validación de email y contraseña y solicitud de roles adicionales; probar emails inválidos y duplicados, longitud mínima, roles ya asignados e independencia de estados.
- [x] 2.2 Implementar inicialización idempotente del administrador y recuperación mediante comando controlado; probar que los reinicios no restablecen contraseñas y que la recuperación funciona.
- [x] 2.3 Implementar habilitación, deshabilitación y reactivación de organizadores; probar permisos de administrador y conservación del rol cliente.

## 3. Autenticación y sesión

- [x] 3.1 Implementar inicio de sesión y emisión y verificación de JWT RS256 con emisor, audiencia y vencimiento; probar credenciales incorrectas, firmas inválidas y límite de una hora.
- [x] 3.2 Implementar renovación rotativa persistida y revocación ante reutilización, con límite absoluto de 24 horas; probar usos concurrentes, cuentas sin acceso y vencimiento del JWT cerca del límite.
- [x] 3.3 Implementar cierre de sesión con revocación de la credencial de renovación; probar que no pueda reutilizarse después del cierre.
- [x] 3.4 Implementar consulta autenticada de identidad y roles propios; probar respuestas sin contraseña y rechazo de solicitudes no autenticadas.

## 4. Contrato para consumidores

- [x] 4.1 Implementar consulta interna de roles por identificador con credencial independiente por servicio; probar credenciales ausentes o inválidas, cuentas inexistentes y cambios de rol posteriores al login.
- [x] 4.2 Documentar el contrato de validación local de JWT y consulta de roles para los equipos consumidores; verificar firma, algoritmo, emisor, audiencia y expiración mediante pruebas de contrato, y comprobar que una nueva autorización rechaza roles deshabilitados o no verificables, sin integrar Eventos ni Compras.
- [x] 4.3 Verificar mediante pruebas de contrato que los endpoints de Identity respetan las rutas, datos y respuestas HTTP acordados en `design.md`, incluidos los errores de validación, autenticación y autorización.

## 5. Entorno local e integración

- [x] 5.1 Integrar Identity con la base ya configurada en Docker Compose, con dependencias saludables, migraciones y seed; verificar arranque desde una base vacía y reinicio sin duplicar el administrador.
- [x] 5.2 Generar claves locales si faltan, conservarlas entre reinicios y configurar credenciales locales reemplazables; verificar que solo Identity recibe la clave privada y que otros entornos requieren valores propios.
- [x] 5.3 Ejecutar las pruebas del servicio y comprobar el flujo de registro, acceso, renovación, administración y consulta interna en Compose; documentar comandos y resultados esperados.

## Workflow follow-up

- Revisar el ADR-0004 propuesto con el equipo antes de acordar la integración.
- Coordinar la integración efectiva de Eventos y Compras, el canal seguro y la distribución y rotación de claves en un cambio posterior.
- Al integrar el cliente web en un cambio posterior, retomar los requisitos de sesión web de `design.md` y definir y probar la cookie, CSRF, CORS, el cierre de sesión y la coordinación de renovaciones en navegador.
