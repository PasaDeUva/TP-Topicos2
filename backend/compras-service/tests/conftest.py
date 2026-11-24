import os
import uuid
from collections.abc import AsyncGenerator, Callable

import httpx
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.database import get_session
from app.events_client import EventsClient, get_events_client
from app.identity import current_customer
from app.main import app
from app.models import Base

TEST_DATABASE_URL = os.getenv(
    "COMPRAS_TEST_DATABASE_URL",
    "postgresql+psycopg://compras:compras@compras-db:5432/compras_test",
)
TEST_CUSTOMER_ID = uuid.UUID("00000000-0000-4000-8000-000000000002")

if "/compras_db" in TEST_DATABASE_URL:
    raise RuntimeError(
        "Refusing to run tests against development database 'compras_db'. "
        "Set COMPRAS_TEST_DATABASE_URL to a dedicated test database "
        "(e.g. compras_test)."
    )


async def _ensure_test_database_exists(db_url: str) -> None:
    """Asegura que la base de datos de test exista antes de conectar."""
    db_name = db_url.rsplit("/", 1)[-1].split("?")[0]
    for maint_db in ("postgres", "compras_db"):
        try:
            maint_url = db_url.rsplit("/", 1)[0] + f"/{maint_db}"
            engine_admin = create_async_engine(maint_url, isolation_level="AUTOCOMMIT")
            async with engine_admin.connect() as conn:
                res = await conn.execute(
                    text(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'")
                )
                if not res.scalar():
                    await conn.execute(text(f'CREATE DATABASE "{db_name}"'))
            await engine_admin.dispose()
            break
        except Exception:
            continue


@pytest_asyncio.fixture(scope="session")
async def engine():
    await _ensure_test_database_exists(TEST_DATABASE_URL)
    eng = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture()
async def session_factory(engine) -> Callable[[], AsyncSession]:
    """Cada solicitud HTTP usa su propia sesión, como en producción."""
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE compras"))
    return factory


@pytest_asyncio.fixture()
async def client(session_factory) -> AsyncGenerator[AsyncClient, None]:
    async def _override_session() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as s:
            yield s

    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[current_customer] = lambda: TEST_CUSTOMER_ID
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture()
async def eventos_simulados() -> AsyncGenerator[dict, None]:
    """Eventos falsos: `eventos` mapea id -> payload; `llamadas` cuenta consultas."""
    state: dict = {
        "eventos": {},
        "llamadas": 0,
        "modo": "normal",
        "correlation_ids": [],
        "reservas": {},
        "reservas_creadas": [],
        "reservas_confirmadas": [],
        "reservas_liberadas": [],
        "modo_reserva": "normal",
        "modo_confirmar": "normal",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        state["llamadas"] += 1
        state["correlation_ids"].append(request.headers.get("X-Correlation-Id"))
        if state["modo"] == "caido":
            raise httpx.ConnectError("events-service caído")
        if state["modo"] == "5xx":
            return httpx.Response(500)

        path = request.url.path
        # Confirmar reserva: POST .../reservas/{rid}/confirmar
        if path.endswith("/confirmar") and request.method == "POST":
            if state["modo_confirmar"] == "5xx":
                return httpx.Response(500)
            if state["modo_confirmar"] == "409":
                return httpx.Response(409, json={"detail": "reserva expirada"})
            parts = path.split("/")
            rid = parts[-2]
            state["reservas_confirmadas"].append(rid)
            return httpx.Response(200, json={"status": "confirmada"})

        # Liberar reserva: DELETE /eventos/{eid}/modalidades/{mid}/reservas/{rid}
        if "/reservas/" in path and request.method == "DELETE":
            rid = path.rsplit("/", 1)[-1]
            state["reservas_liberadas"].append(rid)
            return httpx.Response(200, json={"status": "liberada"})

        # Crear reserva: POST /eventos/{eid}/modalidades/{mid}/reservas
        if path.endswith("/reservas") and request.method == "POST":
            if state["modo_reserva"] == "5xx":
                return httpx.Response(500)
            if state["modo_reserva"] == "409":
                return httpx.Response(409, json={"detail": "sin disponibilidad"})
            rid = str(uuid.uuid4())
            state["reservas_creadas"].append(rid)
            return httpx.Response(201, json={"reserva_id": rid})

        # Consulta de evento: GET /eventos/{eid}
        evento_id = path.rsplit("/", 1)[-1]
        evento = state["eventos"].get(evento_id)
        if evento is None:
            return httpx.Response(404, json={"detail": "not found"})
        return httpx.Response(200, json=evento)

    transport = httpx.MockTransport(handler)

    def _client() -> EventsClient:
        return EventsClient("http://events", timeout=1.0, transport=transport)

    app.dependency_overrides[get_events_client] = _client
    yield state
    app.dependency_overrides.pop(get_events_client, None)


def evento_fake(
    *,
    activo: bool = True,
    modalidades: list[dict] | None = None,
) -> tuple[str, dict]:
    evento_id = str(uuid.uuid4())
    if modalidades is None:
        modalidades = [
            {"id": str(uuid.uuid4()), "nombre": "Campo General", "tipo": "general"}
        ]
    return evento_id, {
        "id": evento_id,
        "owner_id": str(uuid.uuid4()),
        "nombre": "Festival de Test",
        "descripcion": None,
        "venue": "Estadio Monumental",
        "fecha": "2027-03-15T20:00:00Z",
        "activo": activo,
        "creado_en": "2026-01-01T00:00:00Z",
        "modalidades": modalidades,
    }
