# TP-Topicos2

Plataforma web de venta y gestión de entradas para eventos. El proyecto se desarrolla con un enfoque **spec-driven**: primero se documenta el comportamiento esperado y después se implementa.

## Tecnologías

- **Backend:**
- **Base de datos:** 
- **Frontend:**
- **Infraestructura:** 
- **Especificaciones:** OpenSpec en Markdown.

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

Para instalar el CLI en Windows:

```powershell
irm https://openspec.dev/cli/install.ps1 | iex
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

Los commits siguen Conventional Commits:

```text
<tipo>: <descripción>
<tipo>(<scope>): <descripción>
```

Tipos habituales: `feat`, `fix`, `docs`, `test`, `refactor` y `chore`.

Ejemplos:

```text
feat(identity): agregar registro de organizadores
fix(events): corregir publicación de eventos
docs: actualizar instrucciones de instalación
```

## Autores

- **Acosta Santiago** - 📧 [jorge.santiago.acosta@gmail.com](mailto:jorge.santiago.acosta@gmail.com)
- **Valoni Mercedes** - 📧 [valonimercedes@gmail.com](mailto:valonimercedes@gmail.com)
- **Rodrigo Ignacio Romero** - 📧 [rodirgoignacioromero96@gmail.com](mailto:rodirgoignacioromero96@gmail.com)