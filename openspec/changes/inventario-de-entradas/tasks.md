# Tasks

## 1. Migraciones y Modelos de Base de Datos

- [ ] 1.1 Crear migración `0002_add_inventario.py` en `backend/events-service/alembic/versions/` agregando `precio` y `cupo` a `modalidades`, y creando las tablas `sectores`, `asientos` y `reservas` con columna `expira_en`; verificar aplicando `docker compose run --rm events-service alembic upgrade head` y `docker compose run --rm events-service alembic check`.
- [ ] 1.2 Definir los modelos SQLAlchemy `Sector`, `Asiento` y `Reserva` en `backend/events-service/app/models.py`, actualizando `Modalidad` con `ON DELETE RESTRICT` en reservas; verificar importación y metadatos con `pytest tests/test_eventos.py`.

## 2. Esquemas Pydantic y Validaciones

- [ ] 2.1 Actualizar `ModalidadIn`, `ModalidadOut` y definir `SectorIn`, `SectorOut`, `AsientoOut`, `ReservaOut` y `DisponibilidadOut` en `backend/events-service/app/schemas.py`, validando obligatoriedad de `precio` y `cupo` en general y `sectores` con tarifas en numerado; verificar con tests de validación en `tests/test_eventos.py`.
- [ ] 2.2 Actualizar el conftest y generador de payloads `evento_payload` en `backend/events-service/tests/conftest.py` para incluir precios y cupos por defecto; verificar que la suite existente corra sin fallos de validación.

## 3. Endpoints de Inventario y Reservas

- [ ] 3.1 Actualizar `POST /eventos` y `PUT /eventos/{id}` en `backend/events-service/app/routers.py` para persistir sectores y asientos en numeradas, e implementar el guard 409 ante intentos de eliminar modalidades con reservas activas o confirmadas; verificar con tests de creación y edición en `tests/test_eventos.py`.
- [ ] 3.2 Implementar `GET /eventos/{id}/modalidades/{mid}/disponibilidad` en `backend/events-service/app/routers.py` respondiendo `200 {"disponibles": n}`; verificar con tests automatizados de disponibilidad en `tests/test_inventario.py`.
- [ ] 3.3 Implementar endpoints de ciclo de vida de reservas: `POST .../reservas` (201), `DELETE .../reservas/{id}` (200 con status liberada y 409 si ya estaba liberada/confirmada) y `POST .../reservas/{id}/confirmar` (200 idempotente y 409 si liberada/expirada) en `backend/events-service/app/routers.py`; verificar con tests de ciclo de vida en `tests/test_inventario.py`.

## 4. Pruebas de Integración y Regresión

- [ ] 4.1 Ejecutar suite completa de tests de `events-service` dentro del contenedor; verificar con `docker compose run --rm backend-tests pytest backend/events-service/tests`.
- [ ] 4.2 Documentar los nuevos contratos y modelos en `backend/events-service/README.md`; verificar que los ejemplos de requests y respuestas (`{"status": "..."}`, `{"disponibles": ...}`) coincidan con los schemas implementados.

## Workflow follow-up

- Ejecutar `openspec validate inventario-de-entradas --strict`.
- Abrir Pull Request hacia `development` integrando las dos specs acordadas (`inventario-de-entradas` y `concurrencia-de-reservas`).
