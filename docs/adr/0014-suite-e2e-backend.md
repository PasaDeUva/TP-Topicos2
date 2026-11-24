# ADR-0014: Suite E2E y de integración multiservicio en backend

- Estado: Propuesto
- Fecha: 2026-11-23

## Contexto

La verificación de integración entre `identity-service`, `events-service` y `compras-service` se encontraba concentrada en un único script monolítico (`backend/verify_identity_integration.py`). Este script ejecutaba en una sola función secuencial todas las comprobaciones de autenticación, creación de eventos, compras, idempotencia, revocación de sesiones, resiliencia ante caídas de Identity y auditoría de bitácoras.

Este enfoque presentaba desventajas importantes:
1. Una falla en una aserción intermedia impedía ejecutar y diagnosticar los escenarios restantes.
2. Resultaba difícil agregar o extender casos de prueba específicos (por ejemplo, compras fallidas por conflicto de idempotencia, recursos inexistentes o autorizaciones denegadas).
3. El archivo residía suelto en la raíz de `backend/`, desalineado de la organización del resto de los servicios.

## Decisión

Se decide refactorizar la prueba de integración hacia una suite modular bajo `backend/suite-e2e-backend/`, organizada de la siguiente manera:

1. **Arnés de infraestructura (`backend/suite-e2e-backend/harness/`):**
   - Gestión de ciclo de vida del entorno Docker Compose aislado y temporal (`environment.py`).
   - Cliente HTTP y aserciones de respuesta (`client.py`).
   - Contexto compartido de ejecución con URLs, secretos y utilidades de ayuda (`context.py`).
   - Auditoría de seguridad de bitácoras para prevenir fuga de credenciales (`security.py`).

2. **Escenarios multiservicio (`backend/suite-e2e-backend/scenarios/`):**
   - Pruebas independientes para cada flujo de negocio o de infraestructura:
     - `test_auth_and_roles.py`: Registro, login, habilitación de organizadores y aislamiento de eventos por organizador (Identity + Events).
     - `test_compra_exitosa.py`: Compra válida, idempotencia exitosa, consulta de compras y correlación de IDs en bitácoras (Identity + Events + Compras).
     - `test_compra_fallida.py`: Conflictos de idempotencia con diferente carga útil, aislamiento entre clientes, compra sobre eventos inexistentes y accesos no autenticados (Identity + Events + Compras).
     - `test_session_lifecycle.py`: Revocación inmediata de tokens por logout y deshabilitación administrativa de organizadores (Identity + Events + Compras).
     - `test_resilience_and_logs.py`: Falla de token de servicio, indisponibilidad de Identity Service (503) y auditoría de no exposición de secretos en bitácoras (Identity + Events + Compras).
     - `test_rollback.py`: Validación opcional de reversión a revisiones previas si se suministra `--rollback-ref`.

3. **Ejecutor (`backend/suite-e2e-backend/run_e2e.py`):**
   - Ejecuta todos los escenarios de forma secuencial reportando el estado (`PASSED` / `FAILED`) y duración de cada uno.
   - Utiliza exclusivamente la biblioteca estándar de Python (sin dependencias externas en el host).
   - En caso de falla, captura y emite la bitácora redactada de los contenedores para facilitar el diagnóstico.
   - Admite filtro de escenarios individuales mediante `--scenario` y soporte de `--rollback-ref`.

4. **Compatibilidad:**
   - Se mantiene un archivo de compatibilidad en `backend/verify_identity_integration.py` que delega la ejecución al nuevo ejecutor para no romper herramientas existentes.
   - Se actualizan las referencias en `.github/workflows/ci.yml` y en los scripts delegadores de los servicios (`backend/compras-service/scripts/verify_compose.py` y `backend/events-service/scripts/verify_compose.py`).

## Consecuencias

### Positivas

- Diagnóstico claro e individualizado de cada flujo multiservicio.
- Facilidad para incorporar nuevos casos de prueba (ej. flujos de reservas, concurrencia o pagos) sin tocar la lógica de los demás.
- Separación limpia entre la orquestación de contenedores/red y las aserciones de negocio.
- Mantiene compatibilidad total con el pipeline de CI y las políticas de ejecución con la biblioteca estándar en el host.

### Negativas

- Mayor cantidad de archivos y estructura de carpetas en comparación con un script único.
- Requiere mantener la sincronización entre el contexto de prueba compartido y los requisitos de cada escenario.

## Alternativas consideradas

- **Mantener el script monolítico:** descartado por la falta de granularidad y la fragilidad ante fallos en cascada.
- **Migrar a Pytest directamente en el host:** descartado porque requeriría instalar dependencias de Python adicionales en el host/runner fuera del entorno de contenedores, contraviniendo el principio de usar la biblioteca estándar adoptado en ADR-0012.
