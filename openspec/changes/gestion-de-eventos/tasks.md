# Tasks: Implementación de Gestión de Eventos y Catálogo

## 1. Scaffolding, Base de Datos y Modelo de Datos (PR-1 Slice 1)

- [ ] 1.1 Crear estructura de directorios en `backend/events-service/`, archivo `Dockerfile` y `pyproject.toml` con dependencias (FastAPI, SQLAlchemy 2, Alembic, Pydantic v2, Psycopg3) y verificar build de Docker.
- [ ] 1.2 Configurar `compose.yaml` agregando los servicios `events-db` (PostgreSQL 16) y `events-service` con sus volúmenes y variables de entorno correspondientes.
- [ ] 1.3 Configurar Alembic y generar la migración inicial completa `0001_initial_schema.py` creando las tablas `eventos`, `modalidades`, `asientos`, `zonas` y `reservas`, verificando su ejecución exitosa.
- [ ] 1.4 Implementar los modelos ORM de SQLAlchemy en `app/models/` (`evento.py`, `modalidad.py`, `asiento.py`, `zona.py`, `reserva.py`) respetando constraints y relaciones.

## 2. Middleware de Bitácora y Operaciones del Organizador (PR-1 Slice 2)

- [ ] 2.1 Implementar el middleware HTTP en `app/middleware/logging.py` que capture `duration_ms`, propague `X-Correlation-Id` y emita registros JSON estructurados a stdout.
- [ ] 2.2 Configurar inyección de dependencias para extraer claims de headers `X-User-Id` y `X-User-Role` en `app/dependencies.py`.
- [ ] 2.3 Implementar esquemas DTO de Pydantic v2 para creación y consulta básica de eventos en `app/schemas/evento.py` y `app/schemas/modalidad.py`.
- [ ] 2.4 Implementar routers del organizador `POST /eventos` (borrador), `GET /eventos`, `GET /eventos/{id}` y `PUT /eventos/{id}` en `app/routers/eventos.py`.

## 3. Testing Automatizado y Validación de PR-1 (PR-1 Slice 3)

- [ ] 3.1 Implementar fixtures de base de datos de test y cliente HTTP en `tests/conftest.py`.
- [ ] 3.2 Desarrollar tests unitarios para modelos y schemas en `tests/test_models.py`.
- [ ] 3.3 Desarrollar tests para el middleware HTTP de bitácora en `tests/test_middleware.py` validando formato JSON y cabeceras de correlación.
- [ ] 3.4 Desarrollar tests de integración en `tests/test_eventos_crud.py` validando creación 201, edición libre en borrador, validaciones 422 y control de acceso (401/403).
- [ ] 3.5 Ejecutar la suite de tests en Docker (`pytest`) y verificar que el código de producción respete el umbral de ~600 líneas antes de cerrar el PR-1.

## 4. Ciclo de Vida y Catálogo Público (PR-2)

- [ ] 4.1 Implementar validaciones de publicación (completitud de venue, fechas, modalidades) y router `POST /eventos/{id}/publicar`.
- [ ] 4.2 Implementar routers de transición `POST /eventos/{id}/pausar` y `POST /eventos/{id}/despublicar` protegiendo compras existentes.
- [ ] 4.3 Implementar router público `GET /catalogo/eventos` con soporte de filtros (`fecha_desde`, `fecha_hasta`, `tipo_evento`), paginación y exclusión automática de eventos finalizados.
- [ ] 4.4 Implementar router público `GET /catalogo/eventos/{id}` calculando dinámicamente `venta_habilitada` y disponibilidad en tiempo real.
- [ ] 4.5 Desarrollar tests de integración en `tests/test_ciclo_de_vida.py` y `tests/test_catalogo.py` cubriendo transiciones de estado, ocultamiento y filtros de catálogo (100% pytest).
- [ ] 4.6 Ejecutar validación de tests y verificar métrica de ~600 líneas de código de producción para PR-2.

## 5. Contratos de Inventario y Concurrencia (PR-3)

- [ ] 5.1 Implementar servicio de inventario en `app/services/inventario.py` gestionando reservas con TTL de 10 minutos para modalidades numeradas y generales.
- [ ] 5.2 Implementar concurrencia pesimista (`SELECT FOR UPDATE`) para asientos numerados y updates condicionales atómicos para zonas generales (`UPDATE ... WHERE cupo_disponible >= n RETURNING id`).
- [ ] 5.3 Implementar routers de contrato `POST /eventos/{id}/reservar`, `POST /eventos/{id}/confirmar` y `POST /eventos/{id}/liberar`.
- [ ] 5.4 Desarrollar tests de concurrencia y sobreventa en `tests/test_concurrencia_inventario.py` simulando peticiones simultáneas sobre el mismo asiento o cupo y validando expiración TTL.
- [ ] 5.5 Ejecutar la suite integral de pruebas con pytest en Docker Compose y validar funcionamiento de punta a punta con cURL antes de cerrar el PR-3.

## Workflow follow-up

- Ejecutar `openspec validate` para confirmar integridad de todos los artefactos.
- Crear Pull Request en GitHub con la propuesta y especificaciones completas para revisión del equipo.
