# Tasks

## 1. Arnés compartido

- [x] 1.1 Implementar `context.py`, `environment.py` y `client.py` en `backend/suite-e2e-backend/harness/`, verificando que el entorno Compose levante y se resuelvan las URLs de los tres servicios.
- [x] 1.2 Implementar `security.py` (redacción y auditoría de secretos) y verificar el enmascarado de contraseñas, tokens de servicio y JWTs.
- [x] 1.3 Implementar `runner.py` (`run_scenarios`) y exportarlo desde `harness/__init__.py`, verificando que lo usen `run_e2e.py` y los `verify_compose.py`.

## 2. Escenarios aislados por servicio (dentro de `verify_compose.py`)

- [x] 2.1 Escribir en `backend/events-service/scripts/verify_compose.py` los escenarios de catálogo público, escritura protegida, propiedad/baja lógica e inventario/reservas, y verificar que el script pase.
- [x] 2.2 Escribir en `backend/compras-service/scripts/verify_compose.py` los escenarios de autenticación requerida, validación de entrada e idempotencia/propiedad, y verificar que el script pase.

## 3. Escenarios multiservicio (`suite-e2e-backend`)

- [x] 3.1 Implementar `scenarios/test_compra_exitosa.py` (compra, descuento de inventario, idempotencia sin doble consumo, correlation_id en logs).
- [x] 3.2 Implementar `scenarios/test_compra_fallida.py` (evento/modalidad inexistente, evento inactivo, cupo agotado sin persistir la compra).
- [x] 3.3 Implementar `scenarios/test_session_lifecycle.py` (logout con revocación inmediata y deshabilitación de organizador).
- [x] 3.4 Implementar `scenarios/test_resilience_and_logs.py` (token interservicio inválido, caída de Identity, cero filtraciones en logs).
- [x] 3.5 Implementar `scenarios/test_rollback.py` (reversión opcional con `--rollback-ref`).
- [x] 3.6 Implementar `run_e2e.py` y eliminar `backend/verify_identity_integration.py`, verificando que la suite completa pase y que no queden referencias.

## 4. Integración en CI y validación

- [x] 4.1 Actualizar `.github/workflows/ci.yml`: Ruff sobre `suite-e2e-backend`, un paso por cada `verify_compose.py` y un paso para `run_e2e.py`.
- [x] 4.2 Ejecutar Ruff sobre `backend` y verificar que no haya errores.
- [x] 4.3 Ejecutar `verify_compose.py` de events y compras y `run_e2e.py`, y comprobar que todos los escenarios pasen.
