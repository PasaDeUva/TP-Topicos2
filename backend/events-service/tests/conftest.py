import os
import uuid
from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.database import get_session
from app.main import app
from app.models import Base

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://events:events@events-db:5432/events_test",
)

if "/events_db" in TEST_DATABASE_URL:
    raise RuntimeError(
        "Refusing to run tests against development database 'events_db'. "
        "Set TEST_DATABASE_URL to a dedicated test database (e.g. events_test)."
    )


async def _ensure_test_database_exists(db_url: str) -> None:
    """Asegura que la base de datos de test exista antes de conectar."""
    db_name = db_url.rsplit("/", 1)[-1].split("?")[0]
    for maint_db in ("postgres", "events_db"):
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
async def session(engine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
        await s.rollback()


@pytest_asyncio.fixture()
async def client(session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    app.dependency_overrides[get_session] = lambda: session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Payload factory helpers
# ---------------------------------------------------------------------------


def evento_payload(**overrides) -> dict:
    base = {
        "owner_id": str(uuid.uuid4()),
        "nombre": "Festival de Test",
        "venue": "Estadio Monumental",
        "fecha": "2027-03-15T20:00:00Z",
        "modalidades": [{"nombre": "Campo General", "tipo": "general"}],
    }
    base.update(overrides)
    return base
