# Entorno local

## Requirements

### Requirement: Ejecución reproducible de los servicios

El repositorio DEBE poder iniciar el frontend, el backend y PostgreSQL mediante
un único comando de Docker Compose, sin instalar dependencias de aplicación en
el host.

#### Scenario: Levantar el entorno

- **WHEN** el desarrollador ejecuta `docker compose up --build`
- **THEN** Compose construye las imágenes e inicia los servicios `mock-app`,
  `mock-service` y `postgres`.

### Requirement: Comunicación frontend-backend

El frontend DEBE poder consultar el endpoint de salud del backend mediante la
ruta `/api/health`.

#### Scenario: Consultar la salud del backend desde el frontend

- **WHEN** la aplicación frontend solicita `/api/health`
- **THEN** Vite redirige la solicitud al servicio `mock-service` y la interfaz
  muestra el estado recibido.

### Requirement: Disponibilidad de PostgreSQL

PostgreSQL DEBE tener un volumen persistente y un healthcheck que permita
esperar su disponibilidad antes de iniciar el backend.

#### Scenario: Backend dependiente de la base de datos

- **WHEN** Compose inicia el entorno
- **THEN** `mock-service` espera que el healthcheck de PostgreSQL sea saludable.

### Requirement: Ejecución completa de tests backend

El entorno DEBE ofrecer un comando que ejecute los tests de todos los
microservicios backend que contengan una carpeta `tests/`.

#### Scenario: Ejecutar la suite backend

- **WHEN** el desarrollador ejecuta `docker compose run --rm backend-tests`
- **THEN** se ejecutan los tests de cada microservicio backend encontrado.
