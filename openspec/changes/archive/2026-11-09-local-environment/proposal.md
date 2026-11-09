# Propuesta

## Why

El monorepo necesita un entorno local reproducible para ejecutar los proyectos
frontend y backend junto con PostgreSQL, sin instalar dependencias de aplicación
en el host.

## What Changes

- Agregar Docker Compose con servicios para frontend, backend y PostgreSQL.
- Configurar la comunicación del frontend con el backend mediante el proxy de Vite.
- Configurar persistencia local para PostgreSQL y healthcheck de disponibilidad.
- Documentar los comandos de ejecución y validación dentro de Docker.

## Capabilities

### New Capabilities

- Entorno local reproducible para los proyectos del monorepo.

### Modified Capabilities

Ninguna.

## Impact

Agrega archivos Docker y configuración de desarrollo local. No implementa
funcionalidades de negocio ni define todavía los microservicios reales.
