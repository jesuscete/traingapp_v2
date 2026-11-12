import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    activities,
    agent,
    analysis,
    auth,
    catalog,
    chat,
    goals,
    gym,
    integrations,
    internal,
    live,
    nutrition,
    profile,
    routine,
    sessions,
    stats,
)
from app.core.config import settings
from app.core.database import async_session_factory
from app.services import garmin_sync

logger = logging.getLogger(__name__)


async def _garmin_poller() -> None:
    """Sondeo periódico de Garmin (la API personal no tiene avisos push)."""
    interval = settings.garmin_poll_minutes * 60
    while True:
        await asyncio.sleep(interval)
        try:
            async with async_session_factory() as session:
                await garmin_sync.sync_all(session)
        except Exception:  # el sondeo no debe tumbar la API; se registra y se reintenta
            logger.exception("Fallo en el sondeo de Garmin")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    poller = (
        asyncio.create_task(_garmin_poller()) if settings.garmin_poll_minutes > 0 else None
    )
    yield
    if poller is not None:
        poller.cancel()
        with suppress(asyncio.CancelledError):
            await poller


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(gym.router)
app.include_router(sessions.router)
app.include_router(chat.router)
app.include_router(live.router)
app.include_router(routine.router)
app.include_router(catalog.router)
app.include_router(internal.router)
app.include_router(stats.router)
app.include_router(analysis.router)
app.include_router(agent.router)
app.include_router(nutrition.router)
app.include_router(activities.router)
app.include_router(goals.router)
app.include_router(integrations.router)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}
