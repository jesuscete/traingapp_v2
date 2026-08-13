from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.security import verify_password
from app.crud import users
from app.models import User
from app.schemas.auth import EmailChangeIn, PasswordChangeIn, ProfileIn, UserOut

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=UserOut)
async def get_profile(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserOut:
    record = await users.get_by_id(session, current_user.id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return UserOut.model_validate(record)


@router.put("", response_model=UserOut)
async def update_profile(
    body: ProfileIn,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserOut:
    updated = await users.update_profile(session, current_user, body)
    return UserOut.model_validate(updated)


@router.put("/email", response_model=UserOut)
async def update_email(
    body: EmailChangeIn,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserOut:
    existing = await users.get_by_email(session, body.email)
    if existing is not None and existing.id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El email ya está registrado",
        )
    updated = await users.update_email(session, current_user, body.email)
    return UserOut.model_validate(updated)


@router.put("/password", response_model=UserOut)
async def update_password(
    body: PasswordChangeIn,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserOut:
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual no es correcta",
        )
    updated = await users.update_password(session, current_user, body.new_password)
    return UserOut.model_validate(updated)
