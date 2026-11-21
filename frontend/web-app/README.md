# Cliente web de acceso y cuenta

La aplicación permite registrar cuentas, iniciar sesión, consultar roles y solicitar el rol faltante. Compose conecta `/auth` y `/admin` con Identity mediante un proxy del mismo origen.

Una cuenta con rol administrador activo puede consultar los organizadores desde su cuenta y habilitar o deshabilitar cada rol. Si la operación no puede confirmarse, la interfaz consulta nuevamente el estado antes de mostrarlo. El acceso se comprueba también en Identity.

## Arranque local

Requisitos: Docker con Compose, Node.js 22 o superior y OpenSSL. Desde la raíz del repositorio, en PowerShell:

```powershell
$env:IDENTITY_WEB_CSRF_SECRET = openssl rand -hex 32
$env:WEB_APP_HOST_PORT = '15174'
$env:IDENTITY_HOST_PORT = '18002'
$env:IDENTITY_DB_HOST_PORT = '0'
$env:IDENTITY_WEB_ORIGINS = 'http://localhost:15174'
docker compose -p web-local up -d --build --wait web-app
```

Abrir `http://localhost:15174`. Conservar el mismo secreto al reiniciar los servicios: cambiarlo invalida los tokens CSRF existentes. En otros entornos, proporcionar un secreto aleatorio estable de al menos 32 bytes fuera del repositorio y configurar `IDENTITY_WEB_ORIGINS` con un único origen de frontend, sin barra final. Identity y el frontend pueden tener orígenes distintos, pero una instancia de Identity admite un solo origen de frontend para la sesión web. La excepción `IDENTITY_WEB_ALLOW_LOCAL_HTTP=true` solo admite orígenes de loopback en `IDENTITY_ENV=local`; para HTTPS utilizar `false` y un proxy TLS apropiado. El archivo Compose incluido está orientado a desarrollo local.

La cookie de renovación es HttpOnly y el JWT se mantiene en memoria. La coordinación entre pestañas requiere Web Locks, BroadcastChannel, almacenamiento local y un contexto seguro: HTTPS o localhost. Si la sesión vence, se revoca o una renovación queda con resultado desconocido, iniciar sesión nuevamente. Si el navegador no ofrece coordinación segura, la aplicación no inicia ni renueva la sesión.

### Identity en otro origen del mismo sitio

El proxy del mismo origen es el comportamiento predeterminado. Para conectar el navegador directamente a Identity, configurar `VITE_IDENTITY_ORIGIN` con su origen completo, por ejemplo `https://identity.example.com`, y configurar en Identity `IDENTITY_WEB_ORIGINS` con el origen único del frontend, por ejemplo `https://app.example.com`. Fuera de localhost se requiere HTTPS. La cookie `SameSite=Strict` limita esta configuración a orígenes del mismo sitio; para sitios distintos se requiere revisar el diseño. La variable `VITE_IDENTITY_ORIGIN` es pública y se incorpora al ejecutar Vite o al construir los archivos de producción; no debe contener secretos.

## Pruebas

Desde la raíz del repositorio:

```powershell
npm --prefix frontend/web-app ci
npm --prefix frontend/web-app test
npm --prefix frontend/web-app run lint
npm --prefix frontend/web-app run typecheck
npm --prefix frontend/web-app run build
npm --prefix frontend/web-app exec -- playwright install chromium
docker compose build backend-tests
docker compose run --rm backend-tests
docker compose run --rm --no-deps backend-tests python -m ruff check mock-service identity-service
```

Las pruebas de navegador usan un proyecto Compose aislado y crean cuentas de prueba en su propia base. Detener `web-local` antes de ejecutar las pruebas, que requieren los puertos 15174, 15443 y 18002 disponibles:

```powershell
docker compose -p web-local down
```

```powershell
$env:WEB_APP_HOST_PORT = '15174'
$env:IDENTITY_HOST_PORT = '18002'
$env:IDENTITY_DB_HOST_PORT = '0'
$env:IDENTITY_WEB_CSRF_SECRET = 'test-only-csrf-secret-for-isolated-browser-check'
$env:IDENTITY_WEB_ALLOW_LOCAL_HTTP = 'true'
$env:IDENTITY_WEB_ORIGINS = 'http://localhost:15174'
docker compose -p web-access-check-20261120 up -d --build --wait web-app
npm --prefix frontend/web-app run test:e2e
$env:IDENTITY_WEB_ALLOW_LOCAL_HTTP = 'false'
$env:IDENTITY_WEB_ORIGINS = 'https://localhost:15443'
docker compose -p web-access-check-20261120 up -d --wait web-app
$env:E2E_HTTPS = '1'
$env:E2E_COMPOSE_PROJECT = 'web-access-check-20261120'
npm --prefix frontend/web-app run test:e2e -- e2e/security.e2e.js
docker compose -p web-access-check-20261120 down --volumes --remove-orphans
```

La prueba HTTPS genera un certificado temporal autofirmado y lo acepta solo en su navegador de prueba. El comando final elimina los volúmenes del proyecto aislado indicado; no usar ese nombre de proyecto para datos que deban conservarse.

## Resultado de verificación

La verificación de este cambio ejecutó 36 pruebas del cliente web, 66 de Identity, 21 de Events, una del backend mock y una del frontend mock; también pasaron lint, typecheck y build de ambos frontends y Ruff de backend. Playwright pasó cuatro escenarios HTTP y uno HTTPS en Chromium; los escenarios HTTP también pasaron con frontend e Identity en puertos distintos. La prueba HTTPS se ejecuta por separado y se omite deliberadamente durante la ejecución HTTP.
