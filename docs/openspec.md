# Cómo trabajar con OpenSpec

OpenSpec organiza el trabajo en cambios (*changes*) documentados antes de
implementarlos. Cada cambio vive en su propia carpeta y, al terminar, se archiva.

## Estructura

```text
openspec/
├── config.yaml                  # configuración y contexto del proyecto
├── specs/                       # comportamiento vigente del sistema
└── changes/
    ├── <change-activo>/         # cambio en desarrollo
    │   ├── .openspec.yaml
    │   ├── proposal.md          # por qué y qué cambia
    │   ├── design.md            # cómo se implementa
    │   ├── tasks.md             # checklist de implementación
    │   └── specs/               # deltas de comportamiento (opcional)
    └── archive/                 # cambios terminados
```

## Dos tipos de comandos

| Tipo | Dónde se escribe | Para qué |
|---|---|---|
| Comandos del agente (`/opsx-*`) | Chat de Copilot, OpenCode o Antigravity | Crear, implementar y archivar cambios. |
| Comandos del CLI (`openspec ...`) | Terminal | Consultar, validar y archivar. |

## Flujo de trabajo

1. **Explorar** una idea (opcional): `/opsx-explore`.
2. **Proponer** el cambio: `/opsx-propose <descripción>`. Genera `proposal.md`,
   `design.md`, `tasks.md` y, si corresponde, `specs/`.
3. **Commitear la propuesta** en una rama `feature/<nombre>`.
4. **Implementar** las tareas: `/opsx-apply <change>`. Cada tarea completada se
   marca como `- [x]` en `tasks.md`.
5. **Validar**: `openspec validate <change> --strict`.
6. **Archivar**: `/opsx-archive <change>`. Mueve el cambio a `archive/` y, si
   hay deltas, sincroniza `openspec/specs/`.
7. **Abrir el Pull Request** hacia `development`.

OpenSpec no crea Pull Requests ni ramas: eso se hace con Git.

## Comandos del CLI

| Comando | Qué hace |
|---|---|
| `openspec list` | Lista los cambios activos y su progreso. |
| `openspec list --specs` | Lista las specs vigentes. |
| `openspec status --change <change>` | Muestra los artifacts completos y pendientes. |
| `openspec show <change>` | Muestra un cambio o una spec. |
| `openspec validate <change> --strict` | Valida un cambio. |
| `openspec validate --all --strict` | Valida cambios y specs. |
| `openspec archive <change>` | Archiva un cambio y actualiza las specs. |
| `openspec new change <nombre>` | Crea un cambio vacío. |
| `openspec update` | Actualiza skills y prompts generados. |

## Cuándo un cambio lleva specs

Una spec describe **comportamiento verificable** del sistema.

- Si el cambio agrega o modifica comportamiento (por ejemplo, un entorno
  ejecutable o una API), debe incluir `specs/<capacidad>/spec.md` con
  `## ADDED Requirements`, `## MODIFIED Requirements`, etc.
- Si es tooling, documentación o estructura, se declara en `.openspec.yaml`:

  ```yaml
  schema: spec-driven
  skip_specs: true
  ```

Cada requisito debe usar `MUST` o `SHALL` y tener al menos un
`#### Scenario:`.

## Convenciones del proyecto

- Los artifacts se redactan en español y de forma concisa.
- Un cambio por rama `feature/<nombre>`, con el mismo nombre que el change.
- Las decisiones arquitectónicas van en [`docs/adr/`](adr/README.md) y se
  enlazan desde `proposal.md` o `design.md`.
- Los commits siguen Conventional Commits.
- Un cambio solo se archiva cuando todas sus tareas están completas y pasa
  `openspec validate --strict`.

## Instalar el CLI sin ensuciar el repositorio

El CLI de OpenSpec es una herramienta Node. No se instala dentro de
`backend/`, `frontend/` ni en la raíz del proyecto.

Con [fnm](https://github.com/Schniz/fnm) en Windows, activar Node en la sesión:

```powershell
fnm env --use-on-cd | Out-String | Invoke-Expression
```

Para activarlo en cada terminal nueva:

```powershell
Add-Content $PROFILE 'fnm env --use-on-cd | Out-String | Invoke-Expression'
```

Sin Node en el host, se puede ejecutar mediante Docker desde la raíz:

```powershell
docker run --rm -v "${PWD}:/workspace" -w /workspace node:22-alpine `
  sh -c "npm install --silent --global @fission-ai/openspec@latest >/dev/null && openspec validate --all --strict"
```

Las dependencias de la aplicación (FastAPI, React, PostgreSQL) se ejecutan
siempre dentro de Docker Compose. Ver el [README](../README.md).
