# Tasks

## 1. Configuración del repositorio

- [x] 1.1 Agregar `.gitignore` en la raíz con `.venv/`, `__pycache__/`, `.pytest_cache/`, `node_modules/` y `dist/`, y verificar con `git check-ignore -v backend/mock-service/.venv frontend/mock-app/node_modules` que ambos quedan ignorados.

## 2. Guía y verificación

- [x] 2.1 Crear `docs/local-development.md` con los pasos para Windows (PowerShell), macOS y Linux, independientes del editor, cubriendo el prerrequisito de Python 3.12 en el host, el venv de los servicios, `node_modules` de las aplicaciones, cómo abrir cada uno como proyecto y cómo seleccionar el intérprete manualmente en VS Code, y enlazarlo desde el README.
- [x] 2.2 Seguir la guía en Windows con VS Code: crear `backend/mock-service/.venv`, instalar `requirements.txt`, abrir `backend/mock-service` como carpeta y verificar que el IDE resuelva `from fastapi import FastAPI` en `app/main.py`. Registrar en la guía que macOS y Linux no fueron probados.
- [x] 2.3 Seguir la guía en Windows con VS Code: ejecutar `npm install` en `frontend/mock-app` con Node de `fnm`, abrir esa carpeta y verificar que el IDE resuelva `react` y `vite` en `src/App.tsx` y `vite.config.ts`.
- [x] 2.4 Verificar que `git status` no muestre `.venv` ni `node_modules` y que los tests sigan corriendo en Docker sin depender de ellos (`docker compose run --rm mock-service pytest`, disponible una vez integrado `local-environment`).
