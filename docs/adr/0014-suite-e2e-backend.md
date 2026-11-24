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

Se separan las verificaciones de caja negra en dos niveles, ambos sobre un Compose aislado y con biblioteca estándar de Python:

1. **Escenarios aislados por servicio (`backend/<servicio>/scripts/verify_compose.py`):**
   - El código de los escenarios vive dentro de cada `verify_compose.py` y solo ejercita endpoints y reglas propias del servicio (ADR-0012).
   - `events-service`: catálogo público, escritura protegida (401/403), propiedad y baja lógica, inventario y reservas.
   - `compras-service`: autenticación requerida (401/403), validación de entrada (422/403), idempotencia y propiedad de compras.
   - Identity interviene solo como emisor de tokens y events-service solo como fuente de datos; no se valida orquestación.

2. **Escenarios multiservicio (`backend/suite-e2e-backend/scenarios/`):** validan la orquestación entre servicios.
   - `test_compra_exitosa.py`: compra, descuento de inventario en events, idempotencia sin doble consumo y trazabilidad de `X-Correlation-Id`.
   - `test_compra_fallida.py`: evento/modalidad inexistente, evento inactivo y cupo agotado propagados desde events sin persistir la compra.
   - `test_session_lifecycle.py`: revocación por logout y deshabilitación de organizador.
   - `test_resilience_and_logs.py`: token interservicio inválido, caída de Identity (503) y cero filtraciones en logs.
   - `test_rollback.py`: reversión opcional con `--rollback-ref`.

3. **Arnés compartido (`backend/suite-e2e-backend/harness/`):** ciclo de vida de Compose (`environment.py`), cliente HTTP (`client.py`), contexto con helpers `ensure_*` (`context.py`), runner común (`runner.py`) y auditoría de secretos (`security.py`). Los `verify_compose.py` lo importan agregando la carpeta al `sys.path`.

4. **Ejecución y compatibilidad:**
   - `run_e2e.py` ejecuta los escenarios multiservicio, con `--scenario` y `--rollback-ref`.
   - El script monolítico `backend/verify_identity_integration.py` se elimina; su lógica queda repartida entre los escenarios aislados de cada servicio y la suite multiservicio.
   - CI ejecuta cada `verify_compose.py` como paso propio y `run_e2e.py` una sola vez; no hay escenarios duplicados entre niveles.
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
