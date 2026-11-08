# TP-Topicos2

Plataforma web de venta y gestión de entradas para eventos. El proyecto se desarrolla con un enfoque **spec-driven**: primero se documenta el comportamiento esperado y después se implementa.

## Tecnologías

- **Backend:** FastAPI y SQLAlchemy.
- **Base de datos:** PostgreSQL.
- **Frontend:** React, Vite y TypeScript.
- **Infraestructura:** Docker.
- **Especificaciones:** OpenSpec en Markdown.

## Estructura

```text
frontend/    # aplicaciones frontend, una carpeta por proyecto
└── mock-app/ # aplicación React independiente de ejemplo
backend/     # microservicios backend, una carpeta por servicio
└── mock-service/ # servicio FastAPI independiente de ejemplo
```

## Documentación

- [Consigna del trabajo práctico](docs/assignment/Trabajo-final-de-Tpicos-II---2026.pdf)

## Agentes soportados

El repositorio incluye workflows para:

- **OpenCode:** `.opencode/skills/` y `.opencode/commands/`.
- **Antigravity:** `.agents/skills/` y `.agents/workflows/`.
- **GitHub Copilot en VS Code:** `.github/skills/` y `.github/prompts/`.

Cada integrante puede usar el agente que prefiera. Las skills oficiales de OpenSpec se mantienen en la ruta específica de cada herramienta.

## OpenSpec

OpenSpec organiza el trabajo en:

```text
openspec/
├── config.yaml
├── specs/                 # comportamiento vigente
└── changes/               # cambios en desarrollo
    └── archive/           # cambios terminados
```

Para instalar el CLI:

**Windows (PowerShell):**

```powershell
irm https://openspec.dev/cli/install.ps1 | iex
```

**macOS y Linux:**

```bash
curl -fsSL https://openspec.dev/cli/install.sh | bash
```

**Alternativamente, con npm (todos los sistemas):**

```bash
npm install -g @fission-ai/openspec@latest
```

Para inicializar o actualizar el proyecto:

```powershell
openspec init --tools "opencode,antigravity,github-copilot"
```

## Workflow de trabajo

1. **Explorar** una idea o problema:

   ```text
   /opsx-explore
   ```

2. **Proponer** un cambio:

   ```text
   /opsx-propose
   ```

   La propuesta crea `proposal.md`, `specs/`, `design.md` y `tasks.md` dentro de `openspec/changes/`.

3. **Aplicar** las tareas aprobadas:

   ```text
   /opsx-apply
   ```

4. **Sincronizar** las especificaciones vigentes:

   ```text
   /opsx-sync
   ```

5. **Archivar** el cambio terminado:

   ```text
   /opsx-archive
   ```

Los nombres pueden aparecer como skills, prompts o workflows según el agente. También se pueden invocar directamente por nombre, por ejemplo `openspec-apply-change`.

## Git Flow y commits

Usamos Git Flow para las ramas:

```text
feature/<nombre>
bugfix/<nombre>
release/<version>
hotfix/<nombre>
```

Los commits siguen [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/):

```text
<type>[optional scope][optional !]: <description>

[optional body]

[optional footer(s)]
```

`feat` se usa para nuevas funcionalidades y `fix` para correcciones. También se permiten otros tipos como `build`, `chore`, `ci`, `docs`, `perf`, `refactor`, `revert`, `style` y `test`.

Ejemplos:

```text
feat(identity): agregar registro de organizadores
fix(events): corregir publicación de eventos
docs: actualizar instrucciones de instalación
feat(api)!: cambiar el contrato de autenticación
```

Los cambios incompatibles deben marcarse con `!` antes de los dos puntos o con el footer `BREAKING CHANGE: descripción`.

## Autores

- **Acosta Santiago** - 📧 [jorge.santiago.acosta@gmail.com](mailto:jorge.santiago.acosta@gmail.com)
- **Valoni Mercedes** - 📧 [valonimercedes@gmail.com](mailto:valonimercedes@gmail.com)
- **Rodrigo Ignacio Romero** - 📧 [rodrigoignacio932@gmail.com](mailto:rodrigoignacio932@gmail.com)