# Tasks

## 1. Arnés de infraestructura E2E

- [ ] 1.1 Completar los módulos de arnés `context.py` y `environment.py` en `backend/suite-e2e-backend/harness/`, verificando que se inicialice el entorno Compose y se resuelvan las URLs de los tres servicios.
- [ ] 1.2 Implementar utilidades de redacción de secretos y auditoría de logs en `backend/suite-e2e-backend/harness/security.py`, verificando que los patrones de contraseñas, tokens de servicio y JWTs sean enmascarados correctamente.

## 2. Escenarios multiservicio desacoplados

- [ ] 2.1 Implementar `backend/suite-e2e-backend/scenarios/test_auth_and_roles.py` con el flujo de registro, login, aprobación administrativa y validación de aislamiento de eventos por organizador (Identity + Events).
- [ ] 2.2 Implementar `backend/suite-e2e-backend/scenarios/test_compra_exitosa.py` con el flujo de compra válida, idempotencia con clave repetida, consulta de compras del cliente y trazabilidad de correlation_id en logs (Identity + Events + Compras).
- [ ] 2.3 Implementar `backend/suite-e2e-backend/scenarios/test_compra_fallida.py` con los escenarios de fallo: conflicto de idempotencia (409), aislamiento de compra ajena (404), compra de evento inexistente (404) y rechazo no autenticado (401).
- [ ] 2.4 Implementar `backend/suite-e2e-backend/scenarios/test_session_lifecycle.py` con la revocación inmediata de sesión por logout (401) y deshabilitación administrativa de organizadores (403).
- [ ] 2.5 Implementar `backend/suite-e2e-backend/scenarios/test_resilience_and_logs.py` con la degradación ante token interservicio inválido (503), indisponibilidad de Identity (503) y auditoría de cero filtraciones en logs.
- [ ] 2.6 Implementar `backend/suite-e2e-backend/scenarios/test_rollback.py` con la verificación opcional de compatibilidad con versiones previas ante `--rollback-ref`.

## 3. Ejecutor E2E y compatibilidad

- [ ] 3.1 Implementar `backend/suite-e2e-backend/run_e2e.py` con reporte de ejecución individual por escenario, cálculo de tiempos y volcado de logs redactados ante fallas.
- [ ] 3.2 Refactorizar `backend/verify_identity_integration.py` para que actúe como shim compatible invocando a `run_e2e.py`.
- [ ] 3.3 Actualizar `backend/compras-service/scripts/verify_compose.py` y `backend/events-service/scripts/verify_compose.py` para invocar la nueva suite E2E.

## 4. Integración en CI y validación general

- [ ] 4.1 Actualizar `.github/workflows/ci.yml` para incluir `backend/suite-e2e-backend` en el paso de Ruff y ejecutar `backend/suite-e2e-backend/run_e2e.py` en el paso E2E.
- [ ] 4.2 Ejecutar el linter de Ruff sobre todo el paquete `backend/suite-e2e-backend` y verificar ausencia de errores de formato o sintaxis.
- [ ] 4.3 Ejecutar la suite E2E completa mediante `python backend/suite-e2e-backend/run_e2e.py` y comprobar que todos los escenarios pasen exitosamente.
