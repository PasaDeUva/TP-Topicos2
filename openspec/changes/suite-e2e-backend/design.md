# Design

## Context

Véase `proposal.md` y [ADR-0014: Suite E2E y de integración multiservicio en backend](../../docs/adr/0014-suite-e2e-backend.md).
El entorno de ejecución en el host y en CI no cuenta necesariamente con `pytest` instalado fuera de los contenedores Docker. Siguiendo las directrices de ADR-0012, las pruebas de verificación Compose deben depender únicamente de la biblioteca estándar de Python y ejecutarse contra contenedores reales levantados mediante `docker compose`.

## Goals / Non-Goals

**Goals:**
- Separar la lógica de infraestructura (Docker Compose, HTTP, logging, seguridad) de los casos de prueba de negocio.
- Crear módulos de prueba independientes para cada flujo multiservicio (autenticación y roles, compras exitosas, compras fallidas, ciclo de vida de sesiones y resiliencia).
- Mantener un tiempo de ejecución eficiente reutilizando el entorno Compose temporal para la secuencia de pruebas sin reconstruir contenedores por cada escenario individual.
- Emitir reportes comprensibles con indicación de estado (`PASSED`/`FAILED`), tiempos por escenario y bitácoras redactadas en caso de error.
- Preservar compatibilidad con scripts delegadores existentes y con el workflow de CI.

**Non-Goals:**
- No incluye pruebas de interfaz gráfica de usuario en navegador (Frontend E2E con herramientas como Playwright o Cypress).
- No reemplaza las pruebas unitarias y de integración in-process que corren dentro de `backend-tests` con pytest y mocks.

## Decisions

### 1. Estructura modular del paquete `backend/suite-e2e-backend/`
Se organiza el paquete en dos áreas funcionales:
- `backend/suite-e2e-backend/harness/`:
  - `client.py`: Wrapper sobre `urllib.request` con soporte de payloads JSON, headers de correlación, tokens Bearer y validación de códigos HTTP esperados.
  - `compose.py`: Envoltorio de comandos `docker compose` para levantar, detener, consultar puertos dinámicos y extraer logs estructurados.
  - `context.py`: Objeto `E2EContext` que mantiene la configuración, credenciales, URLs base dinámicas y referencias a entidades creadas durante el flujo.
  - `environment.py`: Administrador de contexto (`contextmanager`) que genera el directorio temporal, copia el código de los servicios, normaliza finales de línea a LF, levanta los contenedores con `--wait` y asegura la destrucción de volúmenes en `finally`.
  - `security.py`: Verificación de que ninguna contraseña, token de servicio o JWT se registre en texto plano en los logs de los contenedores.
- `backend/suite-e2e-backend/scenarios/`:
  - `test_auth_and_roles.py`: Registro y login de organizadores/clientes, habilitación por admin, y aislamiento de propiedad de eventos.
  - `test_compra_exitosa.py`: Compra válida, idempotencia exitosa, consulta de compras y trazabilidad de `X-Correlation-Id`.
  - `test_compra_fallida.py`: Conflicto de idempotencia (409), aislamiento entre clientes (404), compra sobre evento inexistente (404) y rechazo no autenticado (401).
  - `test_session_lifecycle.py`: Revocación inmediata por logout (401) y deshabilitación administrativa de organizadores (403).
  - `test_resilience_and_logs.py`: Token interservicio incorrecto (503), indisponibilidad de Identity (503) y auditoría de bitácoras sin filtraciones.
  - `test_rollback.py`: Verificación de compatibilidad con versiones previas ante `--rollback-ref`.

*Alternativa considerada:* Mantener un único script monolítico. Descartada por la imposibilidad de aislar fallos y la dificultad de mantenimiento.

### 2. Ejecución con biblioteca estándar en el host
Se implementa `run_e2e.py` utilizando únicamente módulos estándar (`urllib`, `subprocess`, `json`, `time`, `uuid`, `argparse`).
*Alternativa considerada:* Utilizar `pytest` en el host. Descartada porque requeriría dependencias externas en el entorno del runner de CI y del host local, violando la regla de reproducibilidad establecida en ADR-0012.

### 3. Ciclo de vida de Compose por suite
Levantar y reconstruir los contenedores para cada escenario individual penalizaría el tiempo de ejecución (varios minutos por corrida). Se adopta levantar el entorno Compose una sola vez al inicio de la suite y ejecutar secuencialmente los escenarios. Cada escenario opera con datos identificados unívocamente (emails con timestamp/UUID, IDs únicos y correlación propia) para evitar efectos colaterales.

### 4. Aislamiento respecto a `backend-tests`
`Dockerfile.tests` inspecciona subdirectorios en `backend/` ejecutando pytest en aquellos que posean una carpeta `tests/`. Al ubicar las pruebas en `backend/suite-e2e-backend/scenarios/` (sin subcarpeta `tests/`), el contenedor de tests unitarios ignora `suite-e2e-backend/` automáticamente sin necesidad de parches frágiles.

## Risks / Trade-offs

- **[Riesgo] Contaminación de estado entre escenarios en el Compose compartido:**
  *Mitigación:* Cada escenario utiliza identificadores y credenciales generados aleatoriamente (`uuid.uuid4()`), garantizando independencia entre pruebas.
- **[Riesgo] Fuga de credenciales en salidas de consola ante fallos:**
  *Mitigación:* Toda salida de logs de contenedor capturada en caso de error es filtrada mediante `redact_logs()` antes de imprimirse.
- **[Riesgo] Desincronización con scripts delegadores:**
  *Mitigación:* Mantener `backend/verify_identity_integration.py` como wrapper retrocompatible que ejecuta `run_e2e.main()`, y actualizar `verify_compose.py` en `events-service` y `compras-service`.
