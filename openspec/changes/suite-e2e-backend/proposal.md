# Proposal

## Why

La verificación de integración entre `identity-service`, `events-service` y `compras-service` se encontraba concentrada en un único script monolítico (`backend/verify_identity_integration.py`). Cualquier aserción intermedia fallida interrumpía la suite completa e impedía diagnosticar escenarios independientes de negocio (compras exitosas, fallidas, ciclo de vida de sesiones y resiliencia).

## What Changes

- **Suite modular bajo `backend/suite-e2e-backend/`**:
  - `backend/suite-e2e-backend/harness/`: Módulos de infraestructura reutilizables para gestión del ciclo de vida de Docker Compose aislado (`environment.py`), cliente HTTP estándar (`client.py`), contexto compartido (`context.py`), utilidades de orquestación (`compose.py`) y auditoría de no exposición de secretos (`security.py`).
  - `backend/suite-e2e-backend/scenarios/`: Escenarios de prueba multiservicio desacoplados:
    - `test_auth_and_roles.py`: Registro, login, aprobación de organizadores por admin y aislamiento de propiedad de eventos.
    - `test_compra_exitosa.py`: Compra válida con token cliente, idempotencia repetida, consulta de compras y correlación de IDs en logs estructurados.
    - `test_compra_fallida.py`: Conflicto de idempotencia por payload alterado (409), aislamiento de compras entre clientes (404), compra sobre evento inexistente (404) y rechazo de compras no autenticadas (401).
    - `test_session_lifecycle.py`: Revocación inmediata de sesión por logout e invalidación de token (401), y deshabilitación administrativa de organizadores (403).
    - `test_resilience_and_logs.py`: Token interservicio incorrecto (503), indisponibilidad de Identity (503) y auditoría de bitácoras sin filtración de secretos.
    - `test_rollback.py`: Soporte opcional de verificación de rollback si se especifica `--rollback-ref`.
  - `backend/suite-e2e-backend/run_e2e.py`: Ejecutor CLI con reporte detallado por escenario, captura de bitácoras redactadas ante errores y soporte de ejecución selectiva con `--scenario`.
- **Compatibilidad y gobernanza**:
  - Mantener `backend/verify_identity_integration.py` como envoltorio compatible que invoca el nuevo ejecutor.
  - Actualizar los scripts de verificación de servicios (`backend/compras-service/scripts/verify_compose.py` y `backend/events-service/scripts/verify_compose.py`).
  - Actualizar `.github/workflows/ci.yml` para ejecutar la nueva suite e incluirla en el linter Ruff.
  - Documentar la arquitectura en [ADR-0014: Suite E2E y de integración multiservicio en backend](../../docs/adr/0014-suite-e2e-backend.md).

## Capabilities

### New Capabilities
<!-- Ninguna capability nueva; se trata de una refactorización de infraestructura y pruebas internas (skip_specs: true). -->

### Modified Capabilities
<!-- Ninguna capability modificada a nivel de especificación de requisitos funcionales del producto. -->

## Impact

- **Código y pruebas**: Creación del paquete `backend/suite-e2e-backend/`, preservando compatibilidad de `backend/verify_identity_integration.py`.
- **Scripts de integración**: `backend/compras-service/scripts/verify_compose.py` y `backend/events-service/scripts/verify_compose.py`.
- **CI/CD**: `.github/workflows/ci.yml` en los pasos de lint y ejecución de pruebas E2E.
- **Dependencias**: Ninguna; se mantiene el uso exclusivo de la biblioteca estándar de Python sin requerir dependencias adicionales en el host.
