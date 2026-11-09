# Tasks

## 1. Configurar lint y sus comandos

- [x] 1.1 Configurar Ruff y agregarlo a las dependencias de backend; verificar que `pyproject.toml` se pueda leer. Las pruebas funcionales de Ruff en Docker se completan en 5.1.
- [x] 1.2 Configurar ESLint y el script `lint` de frontend; verificar el manifiesto, lint, typecheck y tests en la aplicación local. La validación Docker se repite en 5.1.
- [x] 1.3 Documentar los comandos locales y Docker para ejecutar lint; verificar los servicios Docker contra `feature/local-environment` y ejecutar los comandos en 5.1, después de integrarla.

## 2. Ejecutar CI en pull requests

- [x] 2.1 Crear un workflow de GitHub Actions para PRs hacia `development` y `master` que ejecute lint, typecheck, tests y build Docker; verificar estructura, filtros, permisos y check estable. Ejecutar el pipeline completo en 5.1.
- [ ] 2.2 Verificar que todas las categorías fallen correctamente ante errores y que el nombre exacto del check quede registrado para branch protection.

## 3. Crear pull requests según Git Flow

- [x] 3.1 Crear y probar el mapeo de `feature/*` y `bugfix/*` a `development`, y `release/*` y `hotfix/*` a `master`; verificar que ramas no administradas no tengan destino.
- [x] 3.2 Crear el workflow que reutiliza la plantilla, evita PRs duplicados y limita permisos de `GITHUB_TOKEN`; verificar su YAML y lógica localmente. Documentar la aprobación manual requerida y validar el evento real en 5.2.

## 4. Aplicar convenciones y proteger ramas

- [x] 4.1 Agregar validación Conventional Commits al hook `commit-msg` y a CI; probar aceptación y rechazo localmente y documentar cómo activar los hooks. La ejecución real del job se valida en 5.1.
- [x] 4.2 Actualizar el PR template existente con el resultado requerido de CI; verificar que conserva sus secciones y checklist y que el workflow automático usa esa plantilla.
- [x] 4.3 Documentar la configuración de protección para `development` y `master` con el check definido por el workflow; verificar que coincida con `CI / checks`. Confirmar el nombre publicado por GitHub en 5.1.
- [ ] 4.4 Extender `pre-commit` para ejecutar Ruff en el `.venv` y ESLint en `node_modules`, y agregar `pre-push` para ejecutar tests con Docker Compose; verificar que linters/test fallidos bloqueen commit/push y que los mensajes identifiquen la causa.
- [ ] 4.5 Aplicar y verificar en GitHub las reglas para exigir PR y checks exitosos y rechazar pushes directos en ambas ramas protegidas.

## 5. Verificar integración

- [ ] 5.1 Después de que `feature/local-environment` se integre en `development`, actualizar `feature/ci-cd` con esa base y verificar `docker compose config`, los builds, lint válido e inválido, typecheck y tests.
- [ ] 5.2 Ejecutar una validación de extremo a extremo con PRs de prueba hacia ambos destinos; aprobar las ejecuciones requeridas por `GITHUB_TOKEN` y comprobar CI, reglas de protección, plantilla y creación automática sin duplicados antes de integrar `feature/ci-cd`.
