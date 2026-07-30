"""
Quiz Models
Auto-generated practice questions, tied to a subject and (optionally) the
documents/chunks the questions were drawn from, so a wrong answer can point
back at its source the same way chat citations do (see Chunk.to_citation_dict).
"""

from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import Integer, String, DateTime, Float, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB

from .base import Base

if TYPE_CHECKING:
    from .user import User


class Quiz(Base):
    __tablename__ = "quizzes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    topic: Mapped[str] = mapped_column(String(500), nullable=False)
    source_document_ids: Mapped[Optional[List[int]]] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship("User")
    questions: Mapped[List["QuizQuestion"]] = relationship(
        "QuizQuestion", back_populates="quiz", cascade="all, delete-orphan",
        order_by="QuizQuestion.order_index",
    )
    attempts: Mapped[List["QuizAttempt"]] = relationship(
        "QuizAttempt", back_populates="quiz", cascade="all, delete-orphan"
    )

    def to_dict(self, include_answers: bool = False) -> dict:
        return {
            "id": self.id,
            "subject": self.subject,
            "topic": self.topic,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "questions": [q.to_dict(include_answer=include_answers) for q in self.questions],
        }


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quiz_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[List[str]] = mapped_column(JSONB, nullable=False)
    correct_answer: Mapped[str] = mapped_column(String(500), nullable=False)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_chunk_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("chunks.id", ondelete="SET NULL"), nullable=True
    )

    quiz: Mapped["Quiz"] = relationship("Quiz", back_populates="questions")

    def to_dict(self, include_answer: bool = False) -> dict:
        data = {
            "id": self.id,
            "order_index": self.order_index,
            "question_text": self.question_text,
            "options": self.options,
            "source_chunk_id": self.source_chunk_id,
        }
        if include_answer:
            data["correct_answer"] = self.correct_answer
            data["explanation"] = self.explanation
        return data


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quiz_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    answers: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    completed_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    quiz: Mapped["Quiz"] = relationship("Quiz", back_populates="attempts")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "quiz_id": self.quiz_id,
            "score": self.score,
            "answers": self.answers,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
