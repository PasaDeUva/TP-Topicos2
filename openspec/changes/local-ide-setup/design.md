# Design

## Context

Los servicios Python y las aplicaciones frontend se ejecutan y prueban en Docker, pero el editor corre en el host y necesita las dependencias para resolver imports y dar autocompletado. Cada microservicio tiene su propio `requirements.txt`, y el `Dockerfile` de `mock-service` usa Python 3.12. Cada aplicación frontend tiene su propio `package.json` (`mock-app` usa React 19, Vite y TypeScript). OpenSpec ya no compite por el entorno: es una herramienta Node, instalada con `fnm` en el perfil del usuario.

## Goals / Non-Goals

**Goals:**

- Que el IDE reconozca FastAPI y el resto de las dependencias en cada servicio.
- Que el IDE reconozca React, Vite y los tipos de TypeScript en cada aplicación frontend.
- No instalar nada en la raíz del repositorio ni en el Python del sistema.
- Que agregar un servicio o una aplicación nueva siga el mismo procedimiento.

**Non-Goals:**

- Reemplazar Docker para ejecutar, probar o desplegar.
- Agregar archivos específicos de un editor (`.code-workspace`, `.vscode/`).
- Usar Dev Containers.

## Decisions

- **Un venv por servicio, en `backend/<servicio>/.venv`.** Refleja el aislamiento real de dependencias entre microservicios. Se descarta un único venv en la raíz porque mezclaría dependencias de servicios distintos.
- **`node_modules` por aplicación, en `frontend/<app>/node_modules`.** Se instala con `npm install` dentro de la carpeta de la aplicación, con Node administrado por `fnm`, y el servidor de TypeScript lo resuelve desde ahí. Se descarta un `package.json` en la raíz porque convertiría el monorepo en un workspace de npm y mezclaría dependencias.
- **Abrir cada servicio o aplicación como su propia carpeta o proyecto del IDE.** Los IDEs detectan el `.venv` o el `node_modules` de la carpeta abierta y resuelven los imports desde su raíz. Es la opción portable: no depende del editor. Se descarta un workspace multi-root porque `.code-workspace` es un formato exclusivo de VS Code y el equipo no usa necesariamente el mismo editor; se descarta `python.analysis.extraPaths` porque admite un solo intérprete y su ruta cambia según el sistema operativo.
- **Sin archivos de configuración de editor en el repositorio.** La configuración queda en la guía, no en `.vscode/`.
- **Mismas `requirements.txt` y `package.json` que Docker, y Python 3.12**, para evitar divergencias entre el IDE y el contenedor. Python 3.12 debe estar instalado en el host para crear el venv; la guía lo indica como prerrequisito y advierte sobre el entorno `base` de conda.
- **Guía por sistema operativo en `docs/local-development.md`**, con variantes para PowerShell y bash/zsh, y la selección manual del intérprete en VS Code.

## Risks / Trade-offs

- [El venv o `node_modules` pueden desactualizarse respecto de `requirements.txt` o `package.json`] -> la guía indica reinstalar con `pip install -r requirements.txt` o `npm install` al cambiar dependencias.
- [Quien abre la raíz del repositorio ve imports sin resolver, porque el IDE usa un solo intérprete por proyecto] -> la guía indica abrir la carpeta del servicio o de la aplicación.
- [La autodetección de `.venv` depende del IDE] -> la guía indica cómo seleccionar el intérprete manualmente en VS Code.
- [Solo se verifica en VS Code sobre Windows] -> la guía registra que macOS y Linux no fueron probados.
- [`node_modules` instalado en el host puede diferir del de la imagen Docker] -> se usa solo para el IDE; la ejecución y los tests siguen en Docker.
