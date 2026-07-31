"""
Quiz routes: generate, fetch, submit. See services/quiz_service.py for the
LLM-generation and scoring logic.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.auth import get_current_user, get_db
from models import Quiz, QuizQuestion, User
from services import quiz_service, review_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/quizzes", tags=["quizzes"])


class QuizGenerateRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=500)
    num_questions: int = Field(default=5, ge=1, le=15)


class QuizSubmitRequest(BaseModel):
    answers: dict  # {"<question_id>": "<selected option text>"}


async def _get_owned_quiz(session: AsyncSession, quiz_id: int, user_id: int) -> Quiz:
    result = await session.execute(
        select(Quiz)
        .options(selectinload(Quiz.questions))
        .where(Quiz.id == quiz_id, Quiz.user_id == user_id)
    )
    quiz = result.scalar_one_or_none()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return quiz


@router.post("/generate")
async def generate_quiz(
    request: QuizGenerateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    try:
        quiz = await quiz_service.generate_quiz(
            session,
            user_id=current_user.id,
            topic=request.topic.strip(),
            num_questions=request.num_questions,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return quiz.to_dict(include_answers=False)


@router.get("")
async def list_quizzes(
    limit: int = Query(20, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Quiz)
        .where(Quiz.user_id == current_user.id)
        .order_by(Quiz.created_at.desc())
        .limit(limit)
    )

    result = await session.execute(stmt)
    quizzes = result.scalars().all()
    return {"quizzes": [{"id": q.id, "topic": q.topic,
                          "created_at": q.created_at.isoformat() if q.created_at else None} for q in quizzes]}


@router.get("/{quiz_id}")
async def get_quiz(
    quiz_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    quiz = await _get_owned_quiz(session, quiz_id, current_user.id)
    return quiz.to_dict(include_answers=False)


@router.post("/{quiz_id}/submit")
async def submit_quiz(
    quiz_id: int,
    request: QuizSubmitRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    quiz = await _get_owned_quiz(session, quiz_id, current_user.id)

    attempt = await quiz_service.submit_quiz_attempt(
        session, quiz=quiz, user_id=current_user.id, answers=request.answers
    )

    missed_ids = attempt.answers.get("missed_question_ids", [])
    missed_questions = [q for q in quiz.questions if q.id in missed_ids]
    await review_service.seed_from_missed_quiz_questions(
        session, user_id=current_user.id, questions=missed_questions
    )

    return {
        "attempt": attempt.to_dict(),
        "quiz": quiz.to_dict(include_answers=True),
    }
