"""
Subject channel routes - lists the subject portals shown in the Gallery
and their per-subject details.
"""
from fastapi import APIRouter, HTTPException

from prompts import get_available_subjects

router = APIRouter(prefix="/subjects", tags=["subjects"])


@router.get("")
async def get_subjects():
    """Get available subject channels for the Gallery"""
    subjects = get_available_subjects()
    subjects_list = list(subjects.values())
    return {
        "subjects": subjects_list,
        "total": len(subjects_list)
    }


@router.get("/{subject_id}")
async def get_subject(subject_id: str):
    """Get details for a specific subject"""
    subjects = get_available_subjects()
    if subject_id not in subjects:
        raise HTTPException(status_code=404, detail=f"Subject '{subject_id}' not found")
    return subjects[subject_id]
