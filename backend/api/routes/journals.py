"""
Journal and folder routes - user notes and the folders they're organized
into. Bundled together (not two separate files) since they're the same
"notes management" feature area and each individually small.

Uses database.get_database()'s singleton directly, same pattern as
api/routes/health.py - see that file's docstring for why.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from api.schemas import JournalCreate, JournalUpdate, FolderCreate, FolderUpdate
from core.auth import get_current_user
from database import get_database
from models import User

router = APIRouter(tags=["journals"])


@router.get("/journals")
async def get_journals(
    folder_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
):
    """Get all journals with optional filtering"""
    db = get_database()
    return await db.get_journals(user_id=current_user.id, folder_id=folder_id, search_query=search)


@router.post("/journals", status_code=201)
async def create_journal(journal: JournalCreate, current_user: User = Depends(get_current_user)):
    """Create a new journal entry with embedding for RAG"""
    if not journal.title.strip() or not journal.content.strip():
        raise HTTPException(status_code=400, detail="Title and content are required")

    db = get_database()
    journal_id = await db.create_journal(
        title=journal.title.strip(),
        content=journal.content.strip(),
        user_id=current_user.id,
        tags=journal.tags,
        folder_id=journal.folder_id
    )
    return {"id": journal_id, "message": "Journal created successfully"}


@router.put("/journals/{journal_id}")
async def update_journal(journal_id: int, journal: JournalUpdate, current_user: User = Depends(get_current_user)):
    """Update a journal entry (re-generates embedding)"""
    db = get_database()
    success = await db.update_journal(
        journal_id,
        user_id=current_user.id,
        title=journal.title,
        content=journal.content,
        tags=journal.tags,
        folder_id=journal.folder_id
    )
    if not success:
        raise HTTPException(status_code=400, detail="No changes made")
    return {"message": "Journal updated successfully"}


@router.delete("/journals/{journal_id}")
async def delete_journal(journal_id: int, current_user: User = Depends(get_current_user)):
    """Delete a journal entry"""
    db = get_database()
    await db.delete_journal(journal_id, user_id=current_user.id)
    return {"message": "Journal deleted successfully"}


@router.get("/folders")
async def get_folders(current_user: User = Depends(get_current_user)):
    """Get all folders"""
    db = get_database()
    return await db.get_folders(user_id=current_user.id)


@router.post("/folders", status_code=201)
async def create_folder(folder: FolderCreate, current_user: User = Depends(get_current_user)):
    """Create a new folder"""
    if not folder.name.strip():
        raise HTTPException(status_code=400, detail="Folder name is required")

    db = get_database()
    folder_id = await db.create_folder(
        name=folder.name.strip(),
        user_id=current_user.id,
        description=folder.description.strip() if folder.description else "",
        color=folder.color
    )
    return {"id": folder_id, "message": "Folder created successfully"}


@router.put("/folders/{folder_id}")
async def update_folder(folder_id: int, folder: FolderUpdate, current_user: User = Depends(get_current_user)):
    """Update a folder"""
    db = get_database()
    success = await db.update_folder(
        folder_id,
        user_id=current_user.id,
        name=folder.name,
        description=folder.description,
        color=folder.color
    )
    if not success:
        raise HTTPException(status_code=400, detail="No changes made")
    return {"message": "Folder updated successfully"}


@router.delete("/folders/{folder_id}")
async def delete_folder(folder_id: int, current_user: User = Depends(get_current_user)):
    """Delete a folder"""
    db = get_database()
    await db.delete_folder(folder_id, user_id=current_user.id)
    return {"message": "Folder deleted successfully"}
