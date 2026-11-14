# Tasks: gestión de accesos

## 1. Servicio y persistencia

- [ ] 1.1 Crear `backend/identity-service/` con FastAPI, dependencias, configuración y Dockerfile; verificar que el servicio inicia y expone su estado de salud.
- [ ] 1.2 Configurar PostgreSQL propio y Alembic con la migración inicial de cuentas, roles y sesiones; verificar migración y reversión sobre una base de prueba.
- [ ] 1.3 Implementar almacenamiento de contraseñas con hash seguro y unicidad de email; verificar con pruebas de persistencia que no se guardan contraseñas en texto plano y se rechazan duplicados.

## 2. Cuentas y administración

- [ ] 2.1 Implementar registro de cliente y organizador, validación de contraseña y solicitud de roles adicionales; probar duplicados, longitud mínima e independencia de estados.
- [ ] 2.2 Implementar inicialización idempotente del administrador y recuperación mediante comando controlado; probar que los reinicios no restablecen contraseñas y que la recuperación funciona.
- [ ] 2.3 Implementar habilitación, deshabilitación y reactivación de organizadores; probar permisos de administrador y conservación del rol cliente.

## 3. Autenticación y sesión

- [ ] 3.1 Implementar inicio de sesión y emisión y verificación de JWT RS256 con emisor, audiencia y vencimiento; probar credenciales incorrectas, firmas inválidas y límite de una hora.
- [ ] 3.2 Implementar renovación rotativa persistida y revocación ante reutilización, con límite absoluto de 24 horas; probar usos concurrentes, cuentas sin acceso y vencimiento del JWT cerca del límite.
- [ ] 3.3 Implementar cookie HttpOnly, protección CSRF y cierre de sesión por POST; probar rechazo de CSRF inválido, revocación de renovación y eliminación de cookie.
- [ ] 3.4 Implementar consulta autenticada de identidad y roles propios; probar respuestas sin contraseña y rechazo de solicitudes no autenticadas.
- [ ] 3.5 Documentar el contrato del cliente web para JWT en memoria, recuperación de CSRF y coordinación de renovaciones; verificar en navegador el flujo de recarga, renovación y cierre, incluidos CORS y el modo local.

## 4. Contrato para consumidores

- [ ] 4.1 Implementar consulta interna de roles por identificador con credencial independiente por servicio; probar credenciales ausentes o inválidas, cuentas inexistentes y cambios de rol posteriores al login.
- [ ] 4.2 Documentar el contrato de validación local de JWT y consulta de roles para los equipos consumidores; verificar firma, algoritmo, emisor, audiencia y expiración mediante pruebas de contrato sin integrar Eventos ni Compras.

## 5. Entorno local e integración

- [ ] 5.1 Incorporar Identity y su base a Docker Compose con dependencias saludables, migraciones y seed; verificar arranque desde una base vacía y reinicio sin duplicar el administrador.
- [ ] 5.2 Generar claves locales si faltan, conservarlas entre reinicios y configurar credenciales locales reemplazables; verificar que solo Identity recibe la clave privada y que otros entornos requieren valores propios.
- [ ] 5.3 Ejecutar las pruebas del servicio y comprobar el flujo de registro, acceso, renovación, administración y consulta interna en Compose; documentar comandos y resultados esperados.

## Workflow follow-up

- Revisar el ADR-0004 propuesto con el equipo antes de acordar la integración.
- Coordinar la integración efectiva de Eventos y Compras, el canal seguro y la distribución y rotación de claves en un cambio posterior.
