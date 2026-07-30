from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from api.schemas import JournalCreate, JournalUpdate, FolderCreate, FolderUpdate
import backend.core.services as services

router = APIRouter()


@router.get("/journals")
async def get_journals(
    folder_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None)
):
    if not journal.title.strip() or not journal.content.strip():
        raise HTTPException(status_code=400, detail="Title and content are required")

    journal_id = await services.db.create_journal(
        title=journal.title.strip(),
        content=journal.content.strip(),
        tags=journal.tags,
        folder_id=journal.folder_id
    )
    return {"id": journal_id, "message": "Journal created successfully"}

@router.put("/journals/{journal_id}")
async def update_journal(journal_id: int, journal: JournalUpdate):
    await services.db.delete_journal(journal_id)
    return {"message": "Journal deleted successfully"}


@router.get("/folders")
async def get_folders():
    if not folder.name.strip():
        raise HTTPException(status_code=400, detail="Folder name is required")

    folder_id = await services.db.create_folder(
        name=folder.name.strip(),
        description=folder.description.strip() if folder.description else "",
        color=folder.color
    )
    return {"id": folder_id, "message": "Folder created successfully"}

@router.put("/folders/{folder_id}")
async def update_folder(folder_id: int, folder: FolderUpdate):
    await services.db.delete_folder(folder_id)
    return {"message": "Folder deleted successfully"}
