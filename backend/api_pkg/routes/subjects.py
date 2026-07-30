from fastapi import APIRouter, HTTPException
from typing import Optional, List
from prompts import get_available_subjects

router = APIRouter()

@router.get("/")
async def get_subjects():
    subjects = get_available_subjects()
    if subject_id not in subjects:
        raise HTTPException(status_code=404, detail=f"Subject '{subject_id}' not found")
    return subjects[subject_id]
