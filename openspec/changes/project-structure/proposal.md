# Proposal

## Why

El proyecto necesita una estructura de monorepo de microservicios que permita desarrollar backend y frontend de forma independiente y validar el workflow con código mínimo.

## What Changes

- Crear `frontend/` y `backend/` como categorías independientes del monorepo.
- Reservar dentro de cada categoría una carpeta independiente para cada microservicio o aplicación.
- Mantener abiertos la cantidad, los nombres definitivos y la relación entre los microservicios hasta definir los siguientes changes.
- Usar `mock-service/` y `mock-app/` únicamente como placeholders técnicos de esta estructura inicial.
- Agregar una implementación mínima en cada parte.
- Validar el flujo end-to-end con el mínimo código necesario.
- Usar FastAPI, SQLAlchemy y PostgreSQL en el backend.
- Usar React, Vite y TypeScript en el frontend.
- Preparar Docker como infraestructura del proyecto; su configuración queda para `local-environment`.

## Capabilities

### New Capabilities

Ninguna. El change valida la estructura del proyecto, no una funcionalidad de negocio.

### Modified Capabilities

Ninguna.

## Impact

Agrega la estructura inicial del monorepo, código mínimo de validación y la decisión de stack registrada en [ADR-0001](../../../docs/adr/0001-stack-inicial.md). No implementa funcionalidades del dominio ni define todavía microservicios concretos.
