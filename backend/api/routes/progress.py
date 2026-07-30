"""
Per-subject progress dashboard routes.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_current_user, get_db
from models import SubjectProgress, User

router = APIRouter(prefix="/progress", tags=["progress"])


@router.get("")
async def get_all_progress(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(
        select(SubjectProgress)
        .where(SubjectProgress.user_id == current_user.id)
        .order_by(SubjectProgress.last_active_at.desc())
    )
    rows = result.scalars().all()
    return {"subjects": [r.to_dict() for r in rows]}


@router.get("/{subject}")
async def get_subject_progress(
    subject: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(
        select(SubjectProgress).where(
            SubjectProgress.user_id == current_user.id, SubjectProgress.subject == subject
        )
    )
    progress = result.scalar_one_or_none()
    if not progress:
        raise HTTPException(status_code=404, detail="No progress recorded for this subject yet")
    return progress.to_dict()
