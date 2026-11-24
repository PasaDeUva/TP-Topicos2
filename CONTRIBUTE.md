# Guía de Contribución (CONTRIBUTE)

Esta guía describe el flujo de trabajo estándar para colaborar en el desarrollo de la plataforma **TP-Topicos2**, asegurando consistencia en el código, control de calidad y trazabilidad en los cambios.

---

## 1. Flujo de Ramas (Git Flow / Feature Branch Workflow)

El proyecto utiliza una estrategia basada en **Git Flow**:

### Estructura de Ramas

- **`master`:** Rama productiva y estable. Solo recibe código a través de ramas `release/*` o `hotfix/*`.
- **`development`:** Rama principal de integración y desarrollo activo. Aquí convergen las nuevas funcionalidades y correcciones antes de un lanzamiento.
- **`feature/<nombre-descriptivo>`:** Nuevas funcionalidades o requerimientos (por ejemplo: `feature/asientos-numerados`). Salen de `development` y se integran mediante Pull Request a `development`.
- **`bugfix/<nombre-descriptivo>`:** Correcciones de errores identificados en desarrollo. Salen de `development` y se integran a `development`.
- **`release/<version>`:** Preparación de una versión candidata para entrega. Sale de `development` y se integra a `master` y a `development`.
- **`hotfix/<nombre-descriptivo>`:** Correcciones críticas urgentes sobre `master`. Salen de `master` y se integran tanto a `master` como a `development`.

### Protección de Ramas en GitHub

Las ramas `development` y `master` están protegidas:
1. Ningún desarrollador ni administrador puede hacer `push` directo (`git push origin development` está bloqueado).
2. Todo cambio debe incorporarse obligatoriamente mediante un **Pull Request (PR)**.
3. El Pull Request requiere que el pipeline automatizado de **CI (`CI / checks`)** finalice en verde de forma obligatoria antes de permitir el merge.

---

## 2. Desarrollo Guiado por Especificaciones (Spec-Driven con OpenSpec)

Antes de implementar funcionalidades que alteren el comportamiento de la plataforma, se debe documentar el cambio utilizando **OpenSpec**:

```text
openspec/
├── config.yaml
├── specs/                 # Especificaciones vigentes (fuente de verdad)
└── changes/               # Propuestas de cambio en desarrollo
    └── archive/           # Cambios completados e históricos
```

### Ciclo de vida de un cambio:

1. **Explorar requerimientos:**
   ```text
   /opsx-explore
   ```
2. **Proponer el cambio:**
   ```text
   /opsx-propose
   ```
   Esto crea dentro de `openspec/changes/<nombre-cambio>/`:
   - `proposal.md`: Justificación, impacto y alcance.
   - `specs/`: Deltas de especificación funcional con escenarios Given/When/Then.
   - `design.md`: Decisiones de arquitectura y contratos de API.
   - `tasks.md`: Plan de tareas atómicas e incrementales.
3. **Implementar las tareas:**
   ```text
   /opsx-apply
   ```
4. **Sincronizar las especificaciones principales:**
   ```text
   /opsx-sync
   ```
5. **Archivar el cambio terminado:**
   ```text
   /opsx-archive
   ```

Si la propuesta introduce una decisión arquitectónica estructural, se debe registrar también un **ADR (Architecture Decision Record)** en [`docs/adr/`](docs/adr/README.md).

---

## 3. Estándar de Commits (Conventional Commits 1.0.0)

Todos los mensajes de commit deben seguir la especificación [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/):

```text
<tipo>[scope opcional][!]: <descripción en minúsculas y modo imperativo>

[cuerpo opcional explicando el porqué del cambio]

[footer(s) opcionales (ej: BREAKING CHANGE, Closes #123)]
```

### Tipos Permitidos:
- **`feat`:** Nueva funcionalidad para el usuario o servicio.
- **`fix`:** Corrección de un bug.
- **`test`:** Añadir o corregir pruebas automatizadas.
- **`refactor`:** Modificación de código que no añade funcionalidad ni corrige errores.
- **`docs`:** Cambios exclusivos en documentación (`README`, `docs/`, `CONTRIBUTE`, etc.).
- **`style`:** Formato, espacios en blanco, punto y coma (sin cambios de lógica).
- **`ci`:** Modificaciones a archivos de CI/CD (ej. GitHub Actions).
- **`chore`:** Mantenimiento general, actualización de tareas auxiliares o dependencias.
- **`build`:** Cambios que afectan el sistema de build o dependencias externas.
- **`perf`:** Mejoras de rendimiento.

### Ejemplos Válidos:
```text
feat(events): implementar control de concurrencia y expiracion por ttl
fix(identity): corregir validacion de tokens revocados
docs: agregar archivo CONTRIBUTE.md con guia de desarrollo
feat(compras)!: cambiar contrato de respuesta en registro de compras
```

*(Nota: Cambios incompatibles hacia atrás deben llevar `!` antes de los dos puntos o `BREAKING CHANGE:` en el pie).*

### Activación del Hook de Pre-commit

El repositorio incluye validaciones automáticas para impedir commits que no cumplan este formato. Configurar el hook local una sola vez tras clonar:

```bash
git config core.hooksPath .githooks
```

---

## 4. Pruebas y Validación Local (Tests)

Antes de abrir un Pull Request, es requisito obligatorio ejecutar y pasar todas las pruebas y validaciones localmente.

### A. Pruebas Unitarias e Integración de Backend

El contenedor `backend-tests` prepara automáticamente las bases de datos de prueba (`identity_test`, `events_test`, `compras_test`):

```bash
# Correr toda la suite de pruebas del backend
docker compose run --rm backend-tests

# Correr pruebas de un microservicio específico
docker compose run --rm backend-tests sh -c "cd identity-service && pytest -v"
docker compose run --rm backend-tests sh -c "cd events-service && pytest -v"
docker compose run --rm backend-tests sh -c "cd compras-service && pytest -v"
```

### B. Linters y Chequeo Estático de Tipos

```bash
# Backend (Ruff)
docker compose run --rm --no-deps backend-tests python -m ruff check identity-service events-service compras-service

# Frontend web-app (ESLint y TypeScript)
docker compose run --rm web-app npm run lint
docker compose run --rm web-app npm run typecheck
```

### C. Verificaciones de Caja Negra en Compose Aislado

Cada microservicio cuenta con un script de validación que instancia un entorno Docker efímero para certificar la integración real:

```bash
python backend/identity-service/scripts/verify_compose.py
python backend/events-service/scripts/verify_compose.py
python backend/compras-service/scripts/verify_compose.py
```

### D. Pruebas E2E de Frontend (Playwright)

```bash
npm --prefix frontend/web-app test:e2e
```

---

## 5. Integración Continua (CI Pipeline)

Al abrir o actualizar un Pull Request hacia `development` o `master`, GitHub Actions ejecuta automáticamente el workflow configurado en [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

El pipeline valida secuencialmente:
1. **Target Mapping:** Verifica que la rama origen apunte a la rama destino correcta según Git Flow.
2. **Commit Linter:** Valida que cada commit del branch cumpla con Conventional Commits.
3. **Compose Config:** Comprueba la sintaxis y variables de `compose.yaml`.
4. **Construcción de Imágenes:** Compila las imágenes de Docker de todos los servicios.
5. **Migraciones:** Aplica y comprueba drift en las bases de datos de test (`alembic upgrade head && alembic check`).
6. **Tests de Backend:** Ejecuta `pytest` sobre `identity-service`, `events-service` y `compras-service`.
7. **Linter de Backend:** Ejecuta `ruff check`.
8. **Frontend Checks:** Ejecuta `npm test`, `npm run lint` y `npm run typecheck` en `web-app`.
9. **E2E Integration Test:** Ejecuta la prueba de integración end-to-end con Identity real y microservicios.

> ⚠️ Si cualquiera de estos pasos falla, el Pull Request quedará bloqueado y no podrá integrarse hasta corregir las observaciones.

---

## 6. Proceso para Crear un Pull Request

1. Actualizar la rama base:
   ```bash
   git checkout development
   git pull origin development
   ```
2. Crear la rama de trabajo:
   ```bash
   git checkout -b feature/nombre-de-la-funcionalidad
   ```
3. Trabajar en los cambios asegurando commits atómicos y claros.
4. Ejecutar las pruebas y linters locales descritos en la sección 4.
5. Hacer push de la rama a GitHub:
   ```bash
   git push origin feature/nombre-de-la-funcionalidad
   ```
6. Crear el Pull Request en GitHub seleccionando `development` como rama base.
7. Describir los cambios realizados, referenciar tareas o issues relacionados y esperar la aprobación del CI y la revisión del equipo.
