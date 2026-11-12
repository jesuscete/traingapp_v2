import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import User
from app.schemas.activity import ActivityDetailOut, ImportResultOut
from app.services import activity_import

router = APIRouter(prefix="/activities", tags=["activities"])


@router.post("/import", response_model=ImportResultOut)
async def import_activity(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    filename: Annotated[str, Query(min_length=5, max_length=200)],
    force: bool = False,
) -> ImportResultOut:
    """Importa un archivo FIT, GPX o TCX enviado como cuerpo binario (uno por petición).

    `force=true` importa aunque haya una sesión del mismo deporte a la misma hora.
    """
    data = await request.body()
    if not data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Archivo vacío"
        )
    result = await activity_import.import_file(session, current_user, filename, data, force=force)
    return ImportResultOut.model_validate(result, from_attributes=True)


@router.get("/{session_id}", response_model=ActivityDetailOut)
async def activity_detail(
    session_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ActivityDetailOut:
    """Series temporales, vueltas, zonas y parciales de una actividad importada."""
    found = await activity_import.activity_detail(session, current_user.id, session_id)
    if found is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    record, stream = found
    summary = (record.details or {}).get("activity")
    return ActivityDetailOut(
        session_id=record.id,
        discipline=record.discipline,
        summary=summary if isinstance(summary, dict) else None,
        samples=stream.samples if stream else {},
        laps=stream.laps if stream else [],
    )
