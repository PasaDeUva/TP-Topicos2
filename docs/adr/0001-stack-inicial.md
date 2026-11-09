# ADR-0001: Stack inicial del proyecto

- Estado: Aceptado
- Fecha: 2026-11-08

## Contexto

El monorepo necesita un stack mínimo para validar el desarrollo independiente de frontend y backend.

## Decisión

- Backend: FastAPI, SQLAlchemy y PostgreSQL.
- Frontend: React, Vite y TypeScript.
- Infraestructura: Docker.

## Consecuencias

### Positivas

- Permite separar el desarrollo de frontend y backend.
- Define una base común para las siguientes etapas.
- Mantiene una tecnología de persistencia preparada para el backend.

### Negativas

- Agrega dependencias y configuración inicial antes de implementar funcionalidades del dominio.
- Requiere mantener herramientas de frontend y backend coordinadas.

## Alternativas consideradas

- Mantener el stack sin definir: se descarta porque impide implementar el código mínimo de validación.
- Usar otro framework de backend o frontend: se descarta para este bootstrap.
