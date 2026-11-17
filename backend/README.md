# Backend

Esta carpeta contiene los microservicios backend del monorepo. Cada servicio
tiene su propia subcarpeta, código, dependencias y tests.

## Servicios actuales

| Servicio | Carpeta | Compose |
|---|---|---|
| Mock service | [`mock-service/`](mock-service/) | `mock-service` |
| Identity service | [`identity-service/`](identity-service/) | `identity-service` |

Los nombres de Compose son los que se usan en `docker compose run`. Los
comandos son los mismos en Windows, macOS y Linux.

## Ejecutar tests de un servicio

Desde la raíz del repositorio:

```bash
docker compose run --rm mock-service pytest
```

Para Identity, el runner de backend prepara la base de pruebas y permite
ejecutar solo su suite:

```bash
docker compose run --rm backend-tests sh -c 'cd identity-service && DATABASE_URL="$TEST_DATABASE_URL" alembic upgrade head && pytest'
```

## Ejecutar todos los tests del backend

El servicio `backend-tests` inicia la base de pruebas de Identity, aplica sus
migraciones y ejecuta los tests de cada subcarpeta que contenga `tests/`. Para
correr la suite completa:

```bash
docker compose run --rm backend-tests
```

Cada nuevo microservicio backend debe mantener sus tests dentro de su propia
carpeta y declarar sus dependencias en `requirements.txt` para que el runner
los incluya automáticamente.

Consultá las instrucciones específicas en
[`mock-service/README.md`](mock-service/README.md) e
[`identity-service/README.md`](identity-service/README.md).
