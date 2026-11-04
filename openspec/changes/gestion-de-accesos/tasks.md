# Tasks

## 1. Bloque 1 — Accesos y cuentas

- [ ] 1.1 Configurar Docker Compose con MySQL/InnoDB, bases lógicas separadas por servicio y healthchecks; verificar que la base quede disponible al iniciar.
- [ ] 1.2 Crear el esqueleto del servicio Identity en FastAPI con SQLAlchemy y Dockerfile; verificar inicio, conexión a su base y endpoint de salud.
- [ ] 1.3 Crear el esqueleto React/Vite y el enrutamiento base de la aplicación; verificar que la compilación de producción termine correctamente.
- [ ] 1.4 Crear los modelos de cuentas y asignaciones de roles con estados independientes, aplicar migraciones y verificar roles simultáneos con pruebas de persistencia.
- [ ] 1.5 Implementar registro de clientes y organizadores con email/contraseña y sin verificación de email; verificar que clientes queden habilitados y organizadores pendientes con pruebas de API.
- [ ] 1.6 Implementar inicio de sesión y autorización para credenciales válidas/inválidas, estados pendientes/deshabilitados y roles simultáneos; verificar permisos con pruebas de API.
- [ ] 1.7 Implementar habilitación, desactivación y reactivación administrativa del rol de organizador; verificar que el rol cliente activo permanezca utilizable.
- [ ] 1.8 Crear mockups y vistas React para registro, inicio de sesión y estado Pendiente de habilitación; verificar los flujos de cliente y organizador con pruebas de UI.
- [ ] 1.9 Implementar bitácora HTTP de autenticación, resultado y duración y documentar la API de Identity; verificar registros y contrato OpenAPI.
- [ ] 1.10 Integrar en Docker Compose los Dockerfiles y configuraciones de Events y Purchases entregados por los Bloques 2 y 3; verificar que toda la solución levante y responda en sus endpoints de salud.
- [ ] 1.11 Crear `CONTRIBUTE.md` con ramas, pruebas y CI, y mantener la bitácora del proyecto; verificar que los pasos documentados sean ejecutables.
