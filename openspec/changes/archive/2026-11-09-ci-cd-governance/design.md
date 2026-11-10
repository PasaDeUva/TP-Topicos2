# Design

## Context

El proyecto ya tiene Git Flow documentado, una plantilla de PR y un hook
pre-commit que valida whitespace. No tiene workflows de GitHub Actions,
configuración de Ruff o ESLint, ni Dockerfiles o Compose en esta rama. La
infraestructura Docker está en el change `local-environment` y debe integrarse
antes de ejecutar esos checks en Docker. Ver [proposal.md](./proposal.md) para
la motivación y [spec](./specs/contribution-governance/spec.md) para los
comportamientos requeridos.

## Goals / Non-Goals

**Goals:**

- Mantener nombres estables de checks CI para usarlos en protección de ramas.
- Ejecutar verificaciones en el entorno Docker que el proyecto usa para tests y
  build, evitando instalaciones de dependencias de la aplicación en el runner.
- Usar permisos mínimos en los workflows, concediendo escritura de PR solo al
  workflow que crea PRs automáticos.

**Non-Goals:**

- Administrar branch protection exclusivamente desde workflows; los workflows
  no configuran las reglas del repositorio en GitHub.
- Permitir que los workflows creen o integren cambios directamente en ramas
  protegidas.

## Decisions

1. **Separar CI de creación automática de PRs.** CI se ejecuta en eventos de
   pull request hacia `development` y `master`. Un workflow separado responde
   a publicación de ramas y aplica el mapeo Git Flow. Así, el workflow de CI
   conserva permisos de solo lectura y solo el de PR automático requiere
   permiso para crear PRs.

2. **Usar Compose como interfaz de validación y build.** Tras integrar
   `local-environment`, CI invocará sus servicios de tests y build para
   conservar el mismo entorno que el desarrollo local. Se agregarán allí los
   comandos necesarios para Ruff y ESLint. No se debe instalar dependencias de
   aplicación directamente en el runner. Antes de que Docker esté integrado,
   el check de build Docker no puede considerarse implementado.

3. **Mantener un único check de CI estable para branch protection.** Los pasos
   de lint, typecheck, tests y build deberán reportar fallo al check si alguno
   no pasa. La configuración de GitHub requerirá ese check en ambos branches
   protegidos; el nombre final se documentará para que coincida exactamente.

4. **Extender el mecanismo local de hooks existente.** Se conserva
   `.githooks/pre-commit` para whitespace, Ruff en el `.venv` del backend y
   ESLint en `node_modules` del frontend. El hook `commit-msg` valida
   Conventional Commits y un nuevo `pre-push` ejecuta las suites backend y
   frontend mediante Docker Compose. La guía indicará cómo activar
   `core.hooksPath`. El lint local requiere tener instaladas las dependencias de
   cada aplicación y los tests pre-push requieren Docker en ejecución; si no,
   commit o push se detienen con un error explícito. CI vuelve a comprobar los
   mensajes y las verificaciones del PR, ya que los hooks locales se pueden
   omitir.

5. **Usar `GITHUB_TOKEN` para PRs automáticos.** El workflow de publicación
   resolverá el destino por prefijo y creará un PR solo si no existe uno abierto
   para la rama origen. Los pushes posteriores actualizan la rama del PR ya
   existente. El PR generado conservará la estructura de la plantilla del
   repositorio. El token tendrá únicamente permisos de lectura de contenido y
   escritura de pull requests. GitHub deja en aprobación requerida los
   workflows `pull_request` generados por esas acciones; una persona con permiso
   de escritura deberá aprobarlos antes de que CI se ejecute. Se elige este
   comportamiento para evitar guardar un PAT o las credenciales de una GitHub
   App como secretos del repositorio.

6. **Configurar protecciones de forma explícita en GitHub.** La documentación
   enumerará los ajustes requeridos para `development` y `master`: exigir PR,
   requerir el check CI y rechazar pushes directos. Un administrador deberá
   aplicar y verificar esos ajustes en la configuración del repositorio.

## Risks / Trade-offs

- [La infraestructura Docker aún no está disponible en esta rama] → Integrar
  `local-environment` antes de habilitar el build y los tests Docker como
  checks requeridos.
- [Un check puede bloquear PRs si se requiere con un nombre distinto al
  reportado por GitHub] → Confirmar el nombre publicado por el workflow y
  documentar el mismo nombre en la configuración de branch protection.
- [La creación automática requiere permisos del token que pueden estar
  restringidos por la organización] → Solicitar o habilitar el permiso de
  creación de PRs y comprobar el workflow en una rama de prueba antes de
  depender de él.
- [Los tests Docker antes del push alargan el ciclo local y requieren Docker
  activo] → Informar claramente el requisito y la suite fallida; conservar las
  mismas pruebas en CI antes de integrar.
- [Los checks de un PR creado con `GITHUB_TOKEN` esperan aprobación manual] →
  Documentar y realizar la aprobación desde una cuenta con permiso de escritura;
  un check pendiente de aprobación nunca cuenta como exitoso.
- [La protección de ramas es configuración remota, no versionada junto al
  workflow] → Asignar su aplicación a un administrador y documentar cómo
  verificarla.

## Migration Plan

1. Desarrollar en `feature/ci-cd` la configuración de lint, workflows, hooks y
   documentación sin integrar ramas.
2. Después de integrar `feature/local-environment` en `development`, actualizar
   `feature/ci-cd` con esa base y conectar los comandos de CI a Compose.
3. Ejecutar y corregir las verificaciones Docker y validar los workflows,
   aprobando las ejecuciones de los PRs automáticos, antes de requerir sus
   checks o integrar `feature/ci-cd`.
4. Configurar y comprobar la protección de `development` y `master` con el
   nombre de check estable publicado por CI.
5. Si el pipeline bloquea contribuciones, corregir la causa o retirar
   temporalmente el check requerido desde la configuración de GitHub mientras
   se restaura CI; no habilitar pushes directos como mecanismo permanente.
