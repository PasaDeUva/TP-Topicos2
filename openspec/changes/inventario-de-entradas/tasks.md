# Tasks

## 1. Migraciones y Modelos de Base de Datos

- [ ] 1.1 Crear migración `0002_add_inventario.py` en `backend/events-service/alembic/versions/` agregando `precio` y `cupo` a `modalidades` (con backfill acotado exclusivamente a modalidades generales de migración 0001 fijando `precio = 0.00` y `cupo = 0`), y creando las tablas `sectores`, `asientos` y `reservas` con columnas `expira_en` y restricción de unicidad global `uq_reservas_idempotency_key` sobre `idempotency_key`; verificar aplicando `docker compose run --rm events-service alembic upgrade head` y `docker compose run --rm events-service alembic check`.
- [ ] 1.2 Definir los modelos SQLAlchemy `Sector`, `Asiento` y `Reserva` en `backend/events-service/app/models.py`, actualizando `Modalidad` con `ON DELETE RESTRICT` en reservas; verificar importación y metadatos con `pytest tests/test_eventos.py`.

## 2. Esquemas Pydantic y Validaciones

- [ ] 2.1 Actualizar `ModalidadIn` (incorporando `id: UUID | None = None` para preservar identidades en `PUT`), `ModalidadOut` y definir `SectorIn`, `SectorOut`, `AsientoOut`, `ReservaOut` y `DisponibilidadOut` en `backend/events-service/app/schemas.py`, validando obligatoriedad de `precio >= 0` y `cupo >= 0` en general (permitiendo conservar o editar modalidades generales migradas sin cupo) y `sectores` con tarifas en numerado; verificar con tests de validación en `tests/test_eventos.py`.
- [ ] 2.2 Actualizar el conftest y generador de payloads `evento_payload` en `backend/events-service/tests/conftest.py` para incluir precios y cupos por defecto; verificar que la suite existente corra sin fallos de validación.

## 3. Endpoints de Inventario y Reservas

- [ ] 3.1 Actualizar `POST /eventos` y `PUT /eventos/{id}` en `backend/events-service/app/routers.py` para actualizar modalidades identificadas por `id` conservando sus entidades hijas, y rechazar con 409 Conflict si una modalidad omitida posee reservas en cualquier estado (`activa`, `confirmada` o `liberada`); verificar con tests de creación y edición en `tests/test_eventos.py`.
- [ ] 3.2 Implementar `GET /eventos/{id}/modalidades/{mid}/disponibilidad` en `backend/events-service/app/routers.py` respondiendo `200 {"disponibles": n}`; verificar con tests automatizados de disponibilidad en `tests/test_inventario.py`.
- [ ] 3.3 Implementar endpoints de ciclo de vida de reservas: `POST .../reservas` (201 con cabecera `Idempotency-Key`, unicidad global en base de datos y reconciliación ante colisiones concurrentes), `DELETE .../reservas/{id}` (200 con status liberada y 409 si ya estaba liberada/confirmada) y `POST .../reservas/{id}/confirmar` (200 idempotente y 409 si liberada/expirada) en `backend/events-service/app/routers.py`; verificar con tests de ciclo de vida en `tests/test_inventario.py`.

## 4. Pruebas de Integración y Regresión

- [ ] 4.1 Ejecutar suite completa de tests de `events-service` dentro del contenedor; verificar con `docker compose run --rm backend-tests pytest events-service/tests`.
- [ ] 4.2 Documentar los nuevos contratos y modelos en `backend/events-service/README.md`; verificar que los ejemplos de requests y respuestas (`{"status": "..."}`, `{"disponibles": ...}`) coincidan con los schemas implementados.

## Workflow follow-up

- Ejecutar `openspec validate inventario-de-entradas --strict`.
- Ambos changes (`inventario-de-entradas` y `concurrencia-de-reservas`) se implementan y verifican de forma conjunta bajo la misma migración `0002_add_inventario.py`.
