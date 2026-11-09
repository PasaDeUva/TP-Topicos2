# Desarrollo local y configuración del IDE

Esta guía explica cómo hacer que el IDE reconozca las dependencias de cada
servicio y aplicación, **sin instalar nada en la raíz del repositorio ni en el
Python del sistema**.

La ejecución y los tests siguen en Docker. Las dependencias que se instalan
aquí existen solo para que el editor resuelva imports y dé autocompletado.

## Cómo está organizado

Cada servicio y cada aplicación tiene sus propias dependencias:

```text
backend/
└── <servicio>/
    ├── .venv/              # entorno virtual (ignorado por git)
    └── requirements.txt
frontend/
└── <app>/
    ├── node_modules/       # dependencias (ignorado por git)
    └── package.json
```

No existe un entorno compartido en la raíz. Un entorno por proyecto evita
mezclar dependencias de servicios distintos.

## Prerrequisitos

- **Python 3.12** instalado en el host, la misma versión que usan los
  Dockerfiles. El venv debe crearse con esa versión explícita: `python` puede
  apuntar a otro intérprete; un venv creado con una versión distinta puede
  romper los paquetes con binarios compilados, como `pydantic`.
  - Windows: `py -3.12 --version`
  - macOS y Linux: `python3.12 --version`
- **Node.js** administrado con [fnm](https://github.com/Schniz/fnm), para no
  instalarlo globalmente.

## Servicios backend (Python)

Repetir para cada servicio dentro de `backend/`. El ejemplo usa `mock-service`.
`--prompt .` hace que la terminal muestre el nombre del servicio (`(mock-service)`)
en lugar de `(.venv)`, y `--clear` recrea el venv si ya existía.

**Windows (PowerShell):**

```powershell
cd backend\mock-service
py -3.12 -m venv --clear --prompt . .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Si PowerShell bloquea `Activate.ps1`, habilitar scripts para el usuario una sola vez:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

**macOS y Linux:**

```bash
cd backend/mock-service
python3.12 -m venv --clear --prompt . .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Comprobar que se creó con Python 3.12 y que las librerías cargan:

```bash
python -c "import sys, fastapi; print(sys.version.split()[0], fastapi.__version__)"
```

Para salir del venv: `deactivate`.

Si cambia `requirements.txt`, volver a ejecutar `python -m pip install -r requirements.txt` con el venv activo.

## Aplicaciones frontend (Node)

Repetir para cada aplicación dentro de `frontend/`. El ejemplo usa `mock-app`.

Con Node activo en la terminal:

```bash
cd frontend/mock-app
npm install
```

Si cambia `package.json`, volver a ejecutar `npm install`.

## Abrir el proyecto en el IDE

El IDE usa **un solo intérprete de Python por proyecto abierto**. Por eso cada
servicio o aplicación se abre como su propia carpeta, no desde la raíz del
repositorio:

```bash
code backend/mock-service
code frontend/mock-app
```

Abrir la raíz del repositorio deja los imports de los servicios sin resolver,
porque los entornos están dentro de cada carpeta.

### VS Code: seleccionar el intérprete

Al abrir `backend/mock-service`, VS Code suele detectar `.venv` por sí solo. Si
no lo hace:

1. Abrir la paleta de comandos (`Ctrl+Shift+P`, o `Cmd+Shift+P` en macOS).
2. Ejecutar **Python: Select Interpreter**.
3. Elegir **Enter interpreter path...** y seleccionar:
   - Windows: `.venv\Scripts\python.exe`
   - macOS y Linux: `.venv/bin/python`

Esta selección se hace una vez por carpeta. VS Code y Pylance usan ese
intérprete para resolver imports aunque el venv no esté activado en la
terminal.

Para el frontend no hace falta seleccionar nada: TypeScript usa el
`node_modules` y el `tsconfig.json` de la carpeta abierta.

## Cuándo activar el venv

No hace falta mantener el venv activado todo el tiempo.

- **VS Code:** basta con seleccionar el intérprete del venv una vez para el
  servicio; no depende del estado de activación de la terminal.
- **Terminal:** activarlo solo cuando se quieran ejecutar `python`, `pip`,
  `pytest` u otras herramientas localmente. Para instalar dependencias sin
  activarlo, ejecutar desde la carpeta del servicio y llamar directamente al
  Python del venv:

  **Windows (PowerShell):**

  ```powershell
  .venv\Scripts\python -m pip install -r requirements.txt
  ```

  **macOS y Linux:**

  ```bash
  .venv/bin/python -m pip install -r requirements.txt
  ```

- **Ejecución y tests del proyecto:** siguen en Docker Compose. El venv es para
  el análisis del IDE y tareas locales puntuales; no reemplaza los contenedores.

## Verificar que funciona

- En `backend/mock-service/app/main.py`, `from fastapi import FastAPI` no debe
  mostrar un error de import sin resolver.
- En `frontend/mock-app/src/App.tsx`, los imports de `react` no deben mostrar
  errores, y `vite.config.ts` debe reconocer `vite`.
- `git status` no debe listar `.venv/` ni `node_modules/`.

## Qué está probado

Esta guía se verificó en **Windows con VS Code**. Los comandos de macOS y Linux
son los equivalentes estándar y **no fueron probados**.
