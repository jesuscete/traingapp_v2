from dataclasses import asdict
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.security import verify_password
from app.crud import users
from app.models import User
from app.schemas.auth import EmailChangeIn, PasswordChangeIn, ProfileIn, UserOut
from app.schemas.session import CamelModel
from app.services import account, onboarding

router = APIRouter(prefix="/profile", tags=["profile"])


class OnboardingStepOut(CamelModel):
    key: str
    label: str
    done: bool
    skipped: bool = False
    href: str | None = None


class OnboardingOut(CamelModel):
    complete: bool  # datos imprescindibles completos: no se muestra la bienvenida
    required: list[OnboardingStepOut]
    recommended: list[OnboardingStepOut]
    pending_recommended: int


@router.get("/onboarding", response_model=OnboardingOut)
async def get_onboarding(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> OnboardingOut:
    """Qué datos faltan (imprescindibles) y qué pasos recomendados quedan."""
    required = onboarding.required_steps(current_user)
    recommended = await onboarding.recommended_steps(session, current_user)
    return OnboardingOut(
        complete=all(s.done for s in required),
        required=[OnboardingStepOut(**asdict(s)) for s in required],
        recommended=[OnboardingStepOut(**asdict(s)) for s in recommended],
        pending_recommended=sum(1 for s in recommended if not s.done and not s.skipped),
    )


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


class AccountDeleteIn(CamelModel):
    password: str = Field(min_length=1, max_length=128)


@router.get("/export")
async def export_account(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    """Descarga de todos tus datos en JSON (sin contraseñas ni claves)."""
    data = await account.export_user(session, current_user)
    stamp = datetime.now(UTC).strftime("%Y%m%d")
    return JSONResponse(
        {"exportedAt": datetime.now(UTC).isoformat(), "data": data},
        headers={"Content-Disposition": f'attachment; filename="traingapp-{stamp}.json"'},
    )


@router.post("/delete", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    body: AccountDeleteIn,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Borra la cuenta y todos sus datos. Pide la contraseña para confirmar."""
    if not verify_password(body.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña no es correcta",
        )
    await account.delete_user(session, current_user)
