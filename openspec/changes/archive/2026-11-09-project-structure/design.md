# Design

## Decisions

- Mantener `frontend/` y `backend/` como categorías separadas dentro de la raíz.
- Mantener cada microservicio o aplicación aislado en una subcarpeta propia, con sus archivos de configuración y dependencias.
- No fijar todavía la cantidad, los nombres ni la relación entre los microservicios.
- Usar `backend/mock-service/` y `frontend/mock-app/` como proyectos mínimos de referencia hasta definir los servicios reales.
- Mantener el código mínimo enfocado en comprobar que el flujo de desarrollo funciona.
- Usar FastAPI, SQLAlchemy y PostgreSQL para el backend.
- Usar React, Vite y TypeScript para el frontend.
- Registrar la decisión en [ADR-0001](../../../docs/adr/0001-stack-inicial.md).

## Non-Goals

- Implementar funcionalidades del dominio.
- Implementar Docker Compose o CI en este change.
- Configurar Docker Compose o CI en este change.
