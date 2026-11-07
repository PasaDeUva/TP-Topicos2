---
name: conventional-commits
description: "Use when creating Git commits. Follow the basic Conventional Commits format."
---

# Conventional Commits

Use this format:

```text
<type>: <description>
```

Optionally include the affected area:

```text
<type>(<scope>): <description>
```

Common types:

- `feat`: nueva funcionalidad
- `fix`: corrección de un error
- `docs`: documentación
- `test`: pruebas
- `refactor`: reestructuración sin cambiar el comportamiento
- `chore`: mantenimiento

```text
feat: agregar registro de organizadores
fix(auth): corregir inicio de sesión
docs: actualizar instrucciones de instalación
```
