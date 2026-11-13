import asyncio
import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import get_session
from app.main import app
from app.models import Base

TEST_DATABASE_URL = "postgresql+psycopg://events:events@events-db:5432/events_db"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def engine():
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
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
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
