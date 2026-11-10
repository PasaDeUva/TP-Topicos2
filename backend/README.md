# Backend

Esta carpeta contiene los microservicios backend del monorepo. Cada servicio
tiene su propia subcarpeta, código, dependencias y tests.

## Servicios actuales

| Servicio | Carpeta | Compose |
|---|---|---|
| Mock service | [`mock-service/`](mock-service/) | `mock-service` |

Los nombres de Compose son los que se usan en `docker compose run`. Los
comandos son los mismos en Windows, macOS y Linux.

## Ejecutar tests de un servicio

Desde la raíz del repositorio:

```bash
docker compose run --rm mock-service pytest
```

Para otro microservicio, se utiliza su nombre en Compose:

```bash
docker compose run --rm otro-servicio pytest
```

## Ejecutar todos los tests del backend

El servicio `backend-tests` busca cada subcarpeta de `backend/` que contenga
`tests/` y ejecuta sus tests. Para correr la suite completa:

```bash
docker compose run --rm backend-tests
```

Cada nuevo microservicio backend debe mantener sus tests dentro de su propia
carpeta y declarar sus dependencias en `requirements.txt` para que el runner
los incluya automáticamente.

El servicio `mock-service` está documentado en
[`mock-service/README.md`](mock-service/README.md).
