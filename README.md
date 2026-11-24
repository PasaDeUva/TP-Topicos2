# TP-Topicos2

Plataforma web de venta y gestión de entradas para eventos basada en una arquitectura de microservicios. El proyecto se desarrolla con un enfoque **spec-driven**: primero se documenta el comportamiento esperado y después se implementa.

---

## Tecnologías

- **Backend:** Python 3.12, FastAPI 0.115, SQLAlchemy 2.0 (asyncio / psycopg v3), Alembic 1.14, Pydantic v2.
- **Bases de datos:** PostgreSQL 16 (instancias y bases de datos aisladas por servicio).
- **Frontend:** React 19, TypeScript, Vite, Tailwind CSS.
- **Seguridad & Autenticación:** Claves asimétricas RSA (JWT RS256), cookies de sesión HttpOnly con protección CSRF (SameSite Strict), rotación de tokens y lista de revocación centralizada en Identity.
- **Infraestructura:** Docker & Docker Compose.
- **Especificaciones:** OpenSpec en Markdown.
- **Testing & Calidad:** Pytest, Playwright, Vitest, Ruff, ESLint, TypeScript Typecheck.

---

## Arquitectura y Servicios

El repositorio está estructurado como un monorepo que contiene tanto las aplicaciones frontend como los microservicios backend:

```text
TP-Topicos2/
├── backend/
│   ├── identity-service/   # Cuentas, roles, autenticación JWT/cookies y revocación de sesiones
│   ├── events-service/     # Catálogo de eventos, modalidades (general y numerada), inventario y reservas
│   └── compras-service/    # Registro y consulta de compras con idempotencia e integración con Identity y Events
├── frontend/
│   └── web-app/            # Aplicación web principal (autenticación, registro, panel de administración de organizadores)
├── docs/                   # Documentación técnica, consigna, glosario y ADRs (Architecture Decision Records)
└── openspec/               # Especificaciones OpenSpec (specs vigentes, cambios y archivo)
```

### Mapa de Microservicios y Puertos en Desarrollo

| Servicio / Contenedor | Puerto Host | Descripción | Base de datos |
|---|---|---|---|
| `identity-service` | `8002` | Autenticación, registro, gestión de roles y sesiones web | `identity_db` (puerto `5435`) |
| `events-service` | `8001` | Gestión de catálogo de eventos, modalidades, sectores, asientos y reservas | `events_db` (puerto `5433`) |
| `compras-service` | `8003` | Registro y consulta de compras de entradas con validación e idempotencia | `compras_db` (puerto `5436`) |
| `web-app` | `5174` | Aplicación web (React + Vite) con proxy integrado para `/auth` y `/admin` | N/A |

> **Nota:** Todos los puertos del host son parametrizables a través de variables de entorno (ver `.env.example`).

---

## Entorno Local con Docker

El entorno local se ejecuta con Docker Compose y no requiere instalar dependencias de frontend o backend en la máquina host. Los comandos son idénticos en Windows, macOS y Linux.

### Requisitos Previos

- **Windows y macOS:** [Docker Desktop](https://www.docker.com/products/docker-desktop/).
- **Linux:** [Docker Engine](https://docs.docker.com/engine/install/) con el plugin Docker Compose.

### Configuración de Variables de Entorno

Copiar el archivo de plantilla `.env.example` a `.env`:

```bash
cp .env.example .env
```

*(En Windows PowerShell: `Copy-Item .env.example .env`)*

El archivo `.env` ya contiene valores por defecto listos para desarrollo local, incluyendo las credenciales iniciales de administrador (`admin@example.com` / `local-admin-password`), secretos CSRF y tokens de comunicación entre microservicios.

### Iniciar todos los servicios

```bash
docker compose up --build
```

O en segundo plano:

```bash
docker compose up -d --build
```

### URLs y Documentación Interactiva

- **Aplicación Web:** <http://localhost:5174>
- **Identity API (Swagger UI):** <http://localhost:8002/docs>
- **Events API (Swagger UI):** <http://localhost:8001/docs>
- **Compras API (Swagger UI):** <http://localhost:8003/docs>

### Iniciar servicios individuales

Para levantar un microservicio específico junto con su base de datos dependiente:

```bash
# Iniciar Identity Service
docker compose up -d --build --wait identity-service

# Iniciar Events Service
docker compose up -d --build --wait events-service

# Iniciar Compras Service
docker compose up -d --build --wait compras-service

# Iniciar Web App
docker compose up -d --build --wait web-app
```

Cada servicio ejecuta automáticamente sus migraciones de base de datos pendientes (`alembic upgrade head`) al arrancar el contenedor.

### Detener el entorno

Para detener los contenedores conservando las bases de datos y las claves criptográficas:

```bash
docker compose down
```

Para detener y eliminar volúmenes asociados:

```bash
docker compose down -v
```

---

## Contribución y Desarrollo

Toda la información sobre el flujo de trabajo de desarrollo se encuentra centralizada en **[CONTRIBUTE.md](CONTRIBUTE.md)**:

- **Estrategia de ramas (Git Flow):** Uso de ramas `feature/*`, `bugfix/*`, `release/*` y `hotfix/*`, reglas de protección y Pull Requests.
- **Desarrollo Spec-Driven (OpenSpec):** Cómo documentar, proponer y sincronizar especificaciones (`/opsx-*`).
- **Convención de commits:** Reglas de [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/) y activación de los hooks de pre-commit (`git config core.hooksPath .githooks`).
- **Validación y Tests locales:** Comandos para ejecutar las suites de pruebas de backend (`backend-tests`), linters (`Ruff`, `ESLint`), scripts `verify_compose.py` y pruebas E2E con Playwright.
- **Pipeline de CI:** Explicación de los checks obligatorios ejecutados en GitHub Actions antes de cada merge.

Consultá **[CONTRIBUTE.md](CONTRIBUTE.md)** antes de realizar y enviar cambios al repositorio.

---

## Agentes de IA Soportados

El repositorio cuenta con configuraciones y sincronización automática de skills y workflows para:

- **Antigravity:** `.agents/skills/` y `.agents/workflows/`
- **OpenCode:** `.opencode/skills/` y `.opencode/commands/`
- **GitHub Copilot en VS Code:** `.github/skills/` y `.github/prompts/`

---

## Documentación Técnica

- [Consigna del trabajo práctico](docs/assignment/Trabajo-final-de-Tpicos-II---2026.pdf)
- [Guía de Contribución](CONTRIBUTE.md)
- [Cómo trabajar con OpenSpec](docs/openspec.md)
- [Desarrollo local y configuración del IDE](docs/local-development.md)
- [Glosario de términos de la plataforma](docs/glosario.md)
- [Decisiones arquitectónicas (ADRs)](docs/adr/README.md)
- [Estrategia de CI/CD y Hooks](docs/ci-cd.md)
- [Documentación de Backend](backend/README.md)
  - [Identity Service](backend/identity-service/README.md)
  - [Events Service](backend/events-service/README.md)
  - [Compras Service](backend/compras-service/README.md)
- [Documentación de Web App](frontend/web-app/README.md)

---

## Autores

- **Acosta Santiago** - 📧 [jorge.santiago.acosta@gmail.com](mailto:jorge.santiago.acosta@gmail.com)
- **Valoni Mercedes** - 📧 [valonimercedes@gmail.com](mailto:valonimercedes@gmail.com)
- **Rodrigo Ignacio Romero** - 📧 [rodrigoignacio932@gmail.com](mailto:rodrigoignacio932@gmail.com)
