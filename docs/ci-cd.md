# Hooks y CI/CD

Activá los hooks una vez por clon:

```bash
git config core.hooksPath .githooks
```

- **Antes del commit:** whitespace, Ruff en el `.venv` del backend y ESLint en
  las dependencias locales del frontend. `commit-msg` valida Conventional
  Commits.
- **Antes del push:** `pre-push` corre los tests backend y frontend con Docker
  Compose. Docker debe estar iniciado y el hook bloquea el push si falla una
  suite o falta `compose.yaml`.
- **Al publicar una rama:** se crea un PR a `development` para `feature/*` y
  `bugfix/*`, o a `master` para `release/*` y `hotfix/*`. Los pushes siguientes
  reutilizan el PR abierto de esa rama.
- **En cada PR a `development` o `master`:** GitHub Actions valida commits,
  lint, typecheck, tests y build Docker en el check `CI / checks`.

Los PRs creados por el workflow usan `GITHUB_TOKEN`. En **Settings → Actions →
General → Workflow permissions**, habilitá **Allow GitHub Actions to create and
approve pull requests** para que el workflow pueda crearlos. GitHub también
puede dejar sus ejecuciones en espera hasta que alguien con permiso de escritura
las apruebe.
Para exigir los checks y bloquear pushes directos, un administrador debe
configurar un ruleset para `development` y `master`. Ver [protección de ramas
en GitHub](../README.md#proteccion-de-ramas-en-github).

## Excepción: omitir hooks

Usalo solo si es necesario: estos comandos omiten las validaciones locales de
esa operación. Ejecutá después las comprobaciones omitidas antes de abrir o
actualizar el PR.

```bash
git commit --no-verify -m "tipo: descripción"
git push --no-verify
```

Esto no omite los checks de GitHub Actions ni las reglas de protección remotas.
