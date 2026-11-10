# Mock Service

Servicio backend mínimo basado en FastAPI. Funciona como placeholder hasta que
se definan los microservicios reales del dominio.

## Endpoint

```text
GET /health
```

Respuesta esperada:

```json
{"status":"ok"}
```

## Tests

Los tests se ejecutan dentro del contenedor del servicio desde la raíz del
repositorio (mismo comando en Windows, macOS y Linux):

```bash
docker compose run --rm mock-service pytest
```

Este comando ejecuta únicamente los tests de `mock-service`. No ejecuta los
tests de otros servicios.

## Ejecución

Para iniciar el entorno completo:

```bash
docker compose up --build
```

El servicio queda disponible en
<http://localhost:8000/health>.
