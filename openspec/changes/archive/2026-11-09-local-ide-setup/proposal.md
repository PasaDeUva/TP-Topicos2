# Proposal

## Why

El IDE no reconoce FastAPI ni las demás librerías de los servicios Python, ni los módulos de los proyectos frontend, porque las dependencias solo existen dentro de Docker. Con varios microservicios y aplicaciones, instalar paquetes en la raíz o en el Python del sistema mezclaría dependencias y ensuciaría el entorno del desarrollador.

## What Changes

- Documentar un venv por servicio (`backend/<servicio>/.venv`), usado solo para que el IDE resuelva imports; la ejecución y los tests siguen en Docker.
- Documentar la instalación de `node_modules` dentro de cada aplicación frontend (`frontend/<app>/node_modules`), usada solo para que el IDE resuelva React, Vite y TypeScript; nada se instala en la raíz.
- Documentar que cada servicio o aplicación se abre como su propia carpeta o proyecto en el IDE, para que detecte su `.venv` o su `node_modules`.
- Agregar un `.gitignore` en la raíz que excluya `.venv/`, `node_modules/` y los artefactos generados.
- Agregar `docs/local-development.md` con los pasos para Windows, macOS y Linux, independientes del editor, y enlazarlo desde el README.

## Capabilities

### New Capabilities

Ninguna. Es tooling de desarrollo y documentación, sin cambios de comportamiento de la plataforma.

### Modified Capabilities

Ninguna.

## Impact

Agrega `.gitignore` y `docs/local-development.md`, y actualiza el README. No agrega archivos específicos de un editor ni modifica el código o las dependencias de los servicios y las aplicaciones.
