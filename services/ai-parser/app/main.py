from fastapi import Depends, FastAPI

from app.api import agent, parse, plan, review
from app.api.security import verify_internal_token
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
)

internal_only = [Depends(verify_internal_token)]
app.include_router(parse.router, dependencies=internal_only)
app.include_router(review.router, dependencies=internal_only)
app.include_router(plan.router, dependencies=internal_only)
app.include_router(agent.router, dependencies=internal_only)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}
