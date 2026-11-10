# Spec Delta

## Purpose

Establece verificaciones automáticas y reglas de integración para que los
cambios sigan Git Flow y las convenciones del repositorio antes de integrarse.

## ADDED Requirements

### Requirement: Pull requests are validated by CI
El repositorio SHALL ejecutar lint, typecheck, tests y build de imágenes Docker
en cada pull request dirigido a `development` o `master`. Si GitHub requiere
aprobación del workflow, CI SHALL esperar la aprobación de una persona con
permiso de escritura antes de ejecutar los checks. El check SHALL fallar si
alguna verificación falla.

#### Scenario: Pull request passes all checks
- **WHEN** se abre o actualiza un pull request hacia `development` o `master`
- **THEN** CI ejecuta lint, typecheck, tests y build Docker y marca el check
  como exitoso si todas las verificaciones pasan

#### Scenario: A required check fails
- **GIVEN** una o más verificaciones de CI fallan
- **WHEN** CI completa la ejecución para el pull request
- **THEN** el check queda fallido y el pull request no puede integrarse mientras
  ese check sea requerido

#### Scenario: Automatically created pull request awaits workflow approval
- **GIVEN** el workflow crea o actualiza un pull request usando `GITHUB_TOKEN`
- **WHEN** GitHub deja la ejecución de `pull_request` en aprobación requerida
- **THEN** CI espera que una persona con permiso de escritura apruebe los
  workflows antes de ejecutar los checks

### Requirement: Pull requests follow Git Flow branch targets
Al publicarse una rama de trabajo, el repositorio SHALL crear o actualizar un
pull request hacia la rama destino definida por Git Flow, sin duplicar PRs
abiertos para la misma rama de origen.

#### Scenario: Feature or bugfix branch is published
- **WHEN** se publica una rama `feature/*` o `bugfix/*`
- **THEN** se crea o actualiza un pull request hacia `development`

#### Scenario: Release or hotfix branch is published
- **WHEN** se publica una rama `release/*` o `hotfix/*`
- **THEN** se crea o actualiza un pull request hacia `master`

### Requirement: Integration branches require pull requests and passing checks
Las ramas `development` y `master` SHALL rechazar cambios directos y SHALL
requerir un pull request con los checks de CI exitosos antes de permitir la
integración.

#### Scenario: Change is proposed for an integration branch
- **WHEN** un colaborador intenta integrar cambios en `development` o `master`
- **THEN** la integración requiere un pull request y los checks CI requeridos
  exitosos

#### Scenario: Direct push is attempted
- **WHEN** un colaborador intenta publicar un cambio directamente en
  `development` o `master`
- **THEN** la protección de la rama rechaza el push

### Requirement: Contributions use Conventional Commits
Los commits del repositorio SHALL seguir Conventional Commits, y las
contribuciones SHALL validar ese formato localmente y en CI antes de integrarse.

#### Scenario: Commit subject follows the convention
- **WHEN** un commit usa un tipo válido, dos puntos y una descripción según
  Conventional Commits
- **THEN** la validación local y la validación CI lo aceptan

#### Scenario: Commit subject does not follow the convention
- **WHEN** un commit no usa el formato Conventional Commits
- **THEN** el hook local lo rechaza y CI marca la validación como fallida

### Requirement: Local hooks run lint before commit
El hook `pre-commit` SHALL ejecutar Ruff usando el entorno virtual local del
backend y ESLint usando las dependencias locales del frontend, y SHALL impedir
el commit si cualquiera de los linters falla o no puede ejecutarse.

#### Scenario: Local lint passes
- **WHEN** se intenta crear un commit y ambos linters terminan correctamente
- **THEN** el hook permite continuar con el commit

#### Scenario: Local lint fails or is unavailable
- **WHEN** se intenta crear un commit y un linter falla o no está disponible
- **THEN** el hook rechaza el commit e indica qué verificación debe corregirse

### Requirement: Local hook runs tests before push
El hook `pre-push` SHALL ejecutar los tests backend y frontend con Docker
Compose, y SHALL impedir el push si Docker no está disponible o cualquier suite
de tests falla.

#### Scenario: Docker tests pass before push
- **WHEN** se intenta hacer push y Docker Compose completa correctamente los
  tests backend y frontend
- **THEN** el hook permite continuar con el push

#### Scenario: Docker is unavailable or tests fail
- **WHEN** se intenta hacer push y Docker no está disponible o falla una suite
  de tests
- **THEN** el hook rechaza el push e informa el motivo

### Requirement: Pull requests use the repository template
Cada pull request SHALL usar la plantilla existente del repositorio, que
presenta la descripción del cambio y las verificaciones aplicables.

#### Scenario: Contributor opens a pull request
- **WHEN** se inicia un pull request en el repositorio
- **THEN** la plantilla existente se presenta con sus secciones y checklist
  actualizados para las verificaciones requeridas
