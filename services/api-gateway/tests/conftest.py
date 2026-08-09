import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.redis import get_redis
from app.main import app


@pytest.fixture
def db_session_factory() -> async_sessionmaker[AsyncSession]:
    return factory


@pytest.fixture
def seed_catalog(db_session_factory: async_sessionmaker[AsyncSession]) -> None:
    from app.analytics.exercise_seed import EXERCISE_CATALOG_SEED
    from app.models import ExerciseCatalog

    async def run() -> None:
        async with db_session_factory() as session:
            for entry in EXERCISE_CATALOG_SEED:
                session.add(ExerciseCatalog(**entry))
            await session.commit()

    asyncio.run(run())




class FakeRedis:
    def __init__(self) -> None:
        self.lists: dict[str, list[str]] = defaultdict(list)

    async def lpush(self, name: str, value: str) -> int:
        self.lists[name].insert(0, value)
        return 1

    async def setex(self, name: str, time: int, value: str) -> int:
        self.lists[name] = [value]
        return 1

    async def get(self, name: str) -> str | None:
        values = self.lists.get(name)
        return values[0] if values else None

    async def delete(self, name: str) -> int:
        return 1 if self.lists.pop(name, None) is not None else 0


@pytest.fixture(autouse=True)
def _fake_redis() -> FakeRedis:
    fake = FakeRedis()
    app.dependency_overrides[get_redis] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_redis, None)

engine = create_async_engine(
    "sqlite+aiosqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

factory = async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture(autouse=True)
def _clean_db() -> Iterator[None]:
    async def reset() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(reset())
    yield


@pytest.fixture(scope="session")
def client() -> TestClient:
    async def init_db() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(init_db())

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
