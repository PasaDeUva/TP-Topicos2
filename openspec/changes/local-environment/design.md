# Diseño

## Decisiones

- Usar Docker Compose como punto de entrada del entorno local.
- Ejecutar el backend FastAPI en el servicio `mock-service`.
- Ejecutar la aplicación React/Vite en el servicio `mock-app`.
- Ejecutar PostgreSQL en el servicio `postgres` con un volumen nombrado.
- Usar el proxy de Vite para que el navegador consuma `/api/health` y Vite
  enrute la solicitud hacia `http://mock-service:8000/health`.
- Esperar a que PostgreSQL esté saludable antes de iniciar `mock-service`.

La decisión de infraestructura se documenta en
[ADR-0002](../../../docs/adr/0002-entorno-local-docker-compose.md).

## Non-Goals

- Implementar funcionalidades del dominio.
- Definir los nombres o límites de los microservicios reales.
- Configurar CI/CD o despliegue productivo.
