---
name: conventional-commits
description: "Use when creating, reviewing, or amending Git commits. Enforce Conventional Commits 1.0.0."
---

# Conventional Commits

Follow the Conventional Commits 1.0.0 specification.

```text
<type>[optional scope][optional !]: <description>

[optional body]

[optional footer(s)]
```

## Rules

- Every commit MUST start with a type, followed by an optional scope, an optional `!`, a colon, and a space.
- The type MUST be a noun. Use `feat` for a new feature and `fix` for a bug fix.
- A scope MAY be included in parentheses and MUST describe a section of the codebase.
- A short description MUST immediately follow the `: ` separator.
- A body MAY follow the description after one blank line. It may contain multiple paragraphs.
- Footers MAY follow the body after one blank line.
- Each footer MUST use `Token: value` or `Token #value`. Replace spaces in footer tokens with hyphens, except for `BREAKING CHANGE`.
- Breaking changes MUST be indicated with `!` before the colon or with the exact uppercase footer `BREAKING CHANGE: description`.
- `BREAKING-CHANGE` is equivalent to `BREAKING CHANGE` when used as a footer token.
- Types other than `feat` and `fix` are allowed. Common examples are `build`, `chore`, `ci`, `docs`, `perf`, `refactor`, `revert`, `style`, and `test`.

## Examples

```text
feat: agregar registro de organizadores
fix(auth): corregir inicio de sesión
docs: actualizar instrucciones de instalación
```

```text
feat(api)!: cambiar el contrato de autenticación
```

```text
fix(events): corregir publicación duplicada

La publicación repetida ahora es idempotente.

Closes: #42
BREAKING CHANGE: los clientes deben enviar un token válido
```
