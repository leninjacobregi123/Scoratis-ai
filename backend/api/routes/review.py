"""
Spaced-repetition review routes. See services/review_service.py for the
SM-2 scheduling algorithm.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_current_user, get_db
from models import ReviewItem, User
from services import review_service

router = APIRouter(prefix="/review", tags=["review"])


class GradeRequest(BaseModel):
    quality: int = Field(ge=0, le=5, description="SM-2 recall quality: 0=blackout, 5=perfect")


@router.get("/due")
async def get_due_reviews(
    subject: Optional[str] = None,
    limit: int = Query(50, le=200),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    items = await review_service.get_due_items(
        session, user_id=current_user.id, subject=subject, limit=limit
    )
    return {"due": [item.to_dict() for item in items]}


@router.post("/{item_id}/grade")
async def grade_review(
    item_id: int,
    request: GradeRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(
        select(ReviewItem).where(ReviewItem.id == item_id, ReviewItem.user_id == current_user.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Review item not found")

    item = await review_service.grade_review_item(session, item=item, quality=request.quality)
    return item.to_dict()
