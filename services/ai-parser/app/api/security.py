import hmac
from typing import Annotated

from fastapi import Header, HTTPException, status

from app.core.config import settings


async def verify_internal_token(
    x_internal_token: Annotated[str | None, Header()] = None,
) -> None:
    """Solo el api-gateway (que conoce el token interno) puede llamar a ai-parser."""
    if x_internal_token is None or not hmac.compare_digest(
        x_internal_token.encode(), settings.internal_token.encode()
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid internal token"
        )
