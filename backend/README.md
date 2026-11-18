# Backend

Esta carpeta contiene los microservicios backend del monorepo. Cada servicio
tiene su propia subcarpeta, código, dependencias y tests.

## Servicios actuales

| Servicio | Carpeta | Compose |
|---|---|---|
| Mock service | [`mock-service/`](mock-service/) | `mock-service` |
| Identity service | [`identity-service/`](identity-service/) | `identity-service` |
| Events service | [`events-service/`](events-service/) | `events-service` |

Los nombres de Compose son los que se usan en `docker compose run`. Los
comandos son los mismos en Windows, macOS y Linux.

## Ejecutar tests de un servicio

Desde la raíz del repositorio:

```bash
docker compose run --rm mock-service pytest
docker compose run --rm backend-tests sh -c "cd events-service && pytest"
```

Para Identity, el runner de backend prepara la base de pruebas y permite
ejecutar solo su suite:

```bash
docker compose run --rm backend-tests sh -c 'cd identity-service && pytest'
```

## Ejecutar todos los tests del backend

El servicio `backend-tests` espera las instancias de Identity y Events, crea la
base de prueba de Identity si falta y ejecuta los tests de cada subcarpeta que
contenga `tests/`. Identity aplica sus migraciones al iniciar sus pruebas. Para
correr la suite completa:

```bash
docker compose run --rm backend-tests
```

Cada nuevo microservicio backend debe mantener sus tests dentro de su propia
carpeta y declarar sus dependencias en `requirements.txt` (o `requirements-dev.txt`) para que el runner
los incluya automáticamente.

Consultá las instrucciones específicas en
[`mock-service/README.md`](mock-service/README.md),
[`events-service/README.md`](events-service/README.md) e
[`identity-service/README.md`](identity-service/README.md).
