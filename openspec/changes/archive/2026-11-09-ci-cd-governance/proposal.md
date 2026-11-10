# Proposal

## Why

El repositorio no tiene CI ni reglas de protección para `development` y
`master`, por lo que un PR no está obligado a pasar verificaciones y se pueden
integrar cambios sin revisión. También falta automatizar los PRs según Git Flow
y hacer cumplir de forma consistente las convenciones de contribución.

## What Changes

- Agregar CI para cada PR hacia `development` o `master`, con lint de Python y
  TypeScript, typecheck, tests y build de las imágenes Docker.
- Crear o actualizar automáticamente un PR al publicar una rama:
  `feature/*` y `bugfix/*` hacia `development`; `release/*` y `hotfix/*` hacia
  `master`.
- Proteger `development` y `master` para requerir PR y checks CI exitosos, sin
  permitir push directo.
- Enforzar Conventional Commits mediante hooks locales y validación en CI.
- Ejecutar Ruff y ESLint antes de cada commit con los entornos locales de cada
  aplicación, y ejecutar los tests backend y frontend con Docker Compose antes
  de cada push.
- Reutilizar el PR template y el hook pre-commit existentes, actualizándolos
  para reflejar las nuevas verificaciones y convenciones.
- Documentar la configuración de protección de ramas requerida en GitHub,
  que no se establece desde un workflow del repositorio.

## Capabilities

### New Capabilities

- `contribution-governance`: verificaciones CI, políticas de integración,
  creación automática de PRs y convenciones aplicadas a contribuciones.

### Modified Capabilities

Ninguna.

## Impact

Agrega workflows de GitHub Actions, configuración de Ruff y ESLint, validación
de commits y cambios a los hooks, el PR template y la documentación. La
protección efectiva de ramas requiere además configurar reglas en GitHub para
`development` y `master`. El build Docker depende de integrar primero los
Dockerfiles y Compose del change `local-environment`.
