# ADR-0002: Entorno local con Docker Compose

- Estado: Aceptado
- Fecha: 2026-11-09

## Contexto

El monorepo contiene proyectos independientes y debe poder ejecutarse sin
instalar sus dependencias en el entorno del desarrollador. El backend también
necesita una instancia local de PostgreSQL para los próximos cambios.

## Decisión

Usar Docker Compose como punto de entrada del entorno local, con servicios
separados para frontend, backend y PostgreSQL. El frontend utilizará el proxy
de Vite para comunicarse con el backend mediante `/api`.

## Consecuencias

### Positivas

- El entorno de desarrollo es reproducible.
- Las dependencias quedan aisladas dentro de los contenedores.
- Los servicios se comunican mediante nombres de servicio de Docker.

### Negativas

- El desarrollo requiere Docker Desktop (Windows y macOS) o Docker Engine con Compose (Linux).
- El primer arranque puede tardar mientras se construyen las imágenes.
- Se agrega configuración de infraestructura antes de implementar el dominio.

## Alternativas consideradas

- Instalar dependencias directamente en el host: se descarta para mantener el
  entorno aislado y reproducible.
- Ejecutar todos los procesos en un único contenedor: se descarta porque oculta
  los límites entre frontend, backend y base de datos.
