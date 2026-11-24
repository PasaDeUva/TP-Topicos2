# Proposal

## Why

La verificación de integración entre `identity-service`, `events-service` y `compras-service` se encontraba concentrada en un único script monolítico (`backend/verify_identity_integration.py`). Cualquier aserción intermedia fallida interrumpía la suite completa e impedía diagnosticar escenarios independientes de negocio (compras exitosas, fallidas, ciclo de vida de sesiones y resiliencia).

## What Changes

- **Escenarios aislados por servicio** dentro de `backend/events-service/scripts/verify_compose.py` y `backend/compras-service/scripts/verify_compose.py`: cada archivo contiene el código de sus escenarios (eventos: catálogo público, escritura protegida, propiedad/baja lógica, inventario y reservas; compras: autenticación, validación de entrada, idempotencia y propiedad) y reutiliza el arnés compartido.
- **Suite multiservicio en `backend/suite-e2e-backend/`** para validar la orquestación entre Identity, Events y Compras:
  - `harness/`: arnés compartido (Compose aislado, cliente HTTP, contexto, runner común y auditoría de secretos).
  - `scenarios/`: `test_compra_exitosa`, `test_compra_fallida` (evento inexistente/inactivo, cupo agotado), `test_session_lifecycle`, `test_resilience_and_logs` y `test_rollback`.
  - `run_e2e.py`: ejecutor con reporte por escenario, `--scenario` y `--rollback-ref`.
- **Compatibilidad y gobernanza**:
  - Eliminar el script monolítico `backend/verify_identity_integration.py` (su lógica se reparte entre los escenarios aislados y la suite multiservicio).
  - Actualizar `.github/workflows/ci.yml`: Ruff incluye `suite-e2e-backend`, cada `verify_compose.py` corre como paso propio y la suite multiservicio corre una sola vez.
  - Documentar la decisión en [ADR-0014](../../../docs/adr/0014-suite-e2e-backend.md).

## Capabilities

### New Capabilities
<!-- Ninguna capability nueva; se trata de una refactorización de infraestructura y pruebas internas (skip_specs: true). -->

### Modified Capabilities
<!-- Ninguna capability modificada a nivel de especificación de requisitos funcionales del producto. -->

## Impact

- **Código y pruebas**: Creación del paquete `backend/suite-e2e-backend/` y eliminación de `backend/verify_identity_integration.py`.
- **Scripts de integración**: `backend/compras-service/scripts/verify_compose.py` y `backend/events-service/scripts/verify_compose.py` pasan a contener sus escenarios aislados.
- **CI/CD**: `.github/workflows/ci.yml` en los pasos de lint y ejecución de pruebas E2E.
- **Dependencias**: Ninguna; se mantiene el uso exclusivo de la biblioteca estándar de Python sin requerir dependencias adicionales en el host.
