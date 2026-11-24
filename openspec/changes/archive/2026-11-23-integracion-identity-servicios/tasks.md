# Tasks

## 1. Contrato y configuración

- [x] 1.1 Documentar los contratos de autenticación, propiedad, compatibilidad de identificadores y errores de ambos servicios; verificar que coincidan con los escenarios y el ADR-0013.
- [x] 1.2 Configurar para cada servicio la clave pública confiable, origen de Identity, timeout y credenciales independientes con permisos `sessions_read` y `roles_read`; probar configuración válida, ausente e inválida, HTTPS y excepción HTTP local explícita sin registrar secretos.

## 2. Gestión de Eventos

- [x] 2.1 Implementar la validación local del JWT y las consultas autenticadas de sesión y roles en Eventos; probar tokens inválidos o revocados, roles pendientes/deshabilitados, errores de servicio y respuestas inconsistentes.
- [x] 2.2 Proteger alta, edición y baja derivando `owner_id` de la identidad; probar propietario propio y ajeno, identificador omitido/coincidente/distinto y que no se transfiera la propiedad.
- [x] 2.3 Mantener las consultas públicas de catálogo y documentar la transición de los endpoints de Eventos; verificar con pruebas de regresión para eventos activos e inactivos y clientes compatibles.

## 3. Gestión de Compras

- [x] 3.1 Implementar la validación local del JWT y las consultas autenticadas de sesión y roles en Compras; probar tokens inválidos o revocados, cliente sin rol activo, fallas y errores de credenciales de servicio.
- [x] 3.2 Proteger registro, detalle y listado derivando `cliente_id` de la identidad; probar identificador omitido/coincidente/distinto y acceso a compras ajenas sin filtración de datos.
- [x] 3.3 Preservar idempotencia por cliente autenticado y reintentos existentes después de autorizar; probar claves repetidas, contenido distinto, concurrencia y rechazo si Identity no puede verificar.
- [x] 3.4 Documentar la transición de los endpoints de Compras y sus respuestas; verificar ejemplos y regresión de validación de Eventos e idempotencia.

## 4. Integración y regresión

- [x] 4.1 En Compose aislado, probar con Identity real el alta y gestión de eventos propios, rechazo de eventos ajenos, compra propia y rechazo de compras ajenas.
- [x] 4.2 Probar en integración sesión revocada, organizador deshabilitado, caída de Identity y credenciales internas inválidas; verificar que no se autoricen operaciones protegidas ni se filtren secretos.
- [x] 4.3 Ejecutar suites, lint y verificaciones de Compose pertinentes; registrar resultados y confirmar que el catálogo público y los contratos no afectados siguen funcionando.
- [x] 4.4 Verificar la transición y reversión en entorno aislado, incluyendo el riesgo de reabrir operaciones anónimas, sin afectar servicios ni datos ajenos sin autorización.

## Verificación

- Suites con PostgreSQL aislado: Eventos 58 pruebas y Compras 58 pruebas aprobadas.
- Ruff aprobado para ambos servicios y los verificadores; `docker compose config --quiet` y `openspec validate integracion-identity-servicios --strict` aprobados.
- Ambos scripts de Compose ejecutaron con éxito el flujo integrado con Identity, correlación y fallos en proyectos temporales; la reversión se prueba explícitamente con `--rollback-ref <revision>`.
- La reversión a los contratos anteriores permite nuevamente escrituras anónimas en Eventos y Compras.
