# Tasks

## 1. Migraciones y Modelos de Base de Datos

- [ ] 1.1 Crear migración `0002_add_inventario.py` en `events-service` agregando `precio` y `cupo` a `modalidades`, y creando las tablas `sectores`, `asientos` y `reservas`; verificar aplicando `docker compose run --rm events-service alembic upgrade head` y `alembic check`.
- [ ] 1.2 Definir los modelos SQLAlchemy `Sector`, `Asiento` y `Reserva` en `app/models.py`, y actualizar `Modalidad` con las relaciones correspondientes; verificar con `pytest tests/test_eventos.py` tras actualizar fixtures.

## 2. Esquemas Pydantic y Validaciones

- [ ] 2.1 Actualizar `ModalidadIn`, `ModalidadOut` y definir `SectorIn`, `SectorOut`, `AsientoOut`, `ReservaOut` y `DisponibilidadOut` en `app/schemas.py`, validando obligatoriedad de `cupo` en general y `sectores` en numerado; verificar con tests unitarios de validación de esquemas.
- [ ] 2.2 Actualizar el conftest y generador de payloads `evento_payload` en `tests/conftest.py` para incluir precios y cupos por defecto; verificar que la suite existente corra sin fallos de validación.

## 3. Endpoints de Inventario y Reservas

- [ ] 3.1 Actualizar `POST /eventos` y `PUT /eventos/{id}` en `app/routers.py` para persistir sectores y asientos cuando la modalidad sea numerada; verificar mediante tests de creación y edición completa de eventos con sectores.
- [ ] 3.2 Implementar `GET /eventos/{id}/modalidades/{mid}/disponibilidad` en `app/routers.py` calculando cupos libres para general y asientos libres para numerado; verificar con tests automatizados de consulta de disponibilidad.
- [ ] 3.3 Implementar endpoints de ciclo de vida de reservas: `POST .../reservas`, `DELETE .../reservas/{id}` (liberación) y `POST .../reservas/{id}/confirmar` en `app/routers.py`; verificar con tests de reserva exitosa, 409 por falta de cupo/asiento ocupado, liberación y confirmación.

## 4. Pruebas de Integración y Regresión

- [ ] 4.1 Ejecutar suite completa de tests de `events-service` dentro del contenedor; verificar con `docker compose run --rm backend-tests pytest backend/events-service/tests`.
- [ ] 4.2 Documentar los nuevos contratos y modelos en `backend/events-service/README.md`; verificar que los ejemplos de requests coincidan con los schemas implementados.

## Workflow follow-up

- Ejecutar `openspec validate inventario-de-entradas --strict`.
- Abrir Pull Request hacia `development` integrando las dos specs acordadas (`inventario-de-entradas` y `concurrencia-de-reservas`).
