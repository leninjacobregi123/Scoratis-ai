"""
Notebook routes: tree, create, rename, move, archive, delete, open.

A notebook is a student's container for study - it owns conversations and
the lessons generated from them, and nests inside other notebooks.

Two rules the nesting needs, enforced here rather than in the schema
because Postgres will not express them cheaply:

  - a notebook may not be moved inside itself or its own descendants,
    which would orphan the subtree into a cycle unreachable from any root
  - depth is capped, so a tree cannot be nested past what breadcrumbs and
    the sidebar can render

Deletion defaults to archiving. A notebook can hold hours of generated
courses, and the foreign keys are SET NULL precisely so removing the
folder never destroys the contents - but the safest delete is the one
that is reversible, so `DELETE` archives unless explicitly told not to.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_

from core.auth import get_current_user
from database import get_database
from models import Notebook, Conversation, Lesson, User, MAX_NOTEBOOK_DEPTH

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/notebooks", tags=["notebooks"])

MAX_NOTEBOOKS_PER_USER = 500


async def _owned_notebook(session, notebook_id: int, user: User) -> Notebook:
    """Fetch a notebook, 404ing for both missing AND other users' rows.

    Same reasoning as _owned_lesson: distinguishing the two would leak
    which notebook ids exist.
    """
    notebook = await session.get(Notebook, notebook_id)
    if not notebook or notebook.user_id != user.id:
        raise HTTPException(status_code=404, detail="Notebook not found")
    return notebook


async def _all_notebooks(session, user_id: int) -> list[Notebook]:
    rows = await session.execute(
        select(Notebook).where(Notebook.user_id == user_id).order_by(Notebook.name)
    )
    return list(rows.scalars().all())


def _descendant_ids(notebooks: list[Notebook], root_id: int) -> set[int]:
    """Every id beneath root_id, root included.

    Walks the in-memory list rather than issuing a recursive CTE - the
    whole tree is one student's own folders and is already loaded.
    """
    by_parent: dict[Optional[int], list[Notebook]] = {}
    for nb in notebooks:
        by_parent.setdefault(nb.parent_id, []).append(nb)

    found = {root_id}
    stack = [root_id]
    while stack:
        current = stack.pop()
        for child in by_parent.get(current, []):
            if child.id not in found:
                found.add(child.id)
                stack.append(child.id)
    return found


def _depth_of(notebooks: list[Notebook], notebook_id: Optional[int]) -> int:
    """How many levels down `notebook_id` sits. A root is depth 1."""
    if notebook_id is None:
        return 0
    by_id = {nb.id: nb for nb in notebooks}
    depth = 0
    seen: set[int] = set()
    current = notebook_id
    while current is not None and current not in seen:
        seen.add(current)
        depth += 1
        node = by_id.get(current)
        current = node.parent_id if node else None
    return depth


def _subtree_height(notebooks: list[Notebook], root_id: int) -> int:
    """Levels contained in the subtree, root counted as 1."""
    by_parent: dict[Optional[int], list[Notebook]] = {}
    for nb in notebooks:
        by_parent.setdefault(nb.parent_id, []).append(nb)

    height = 1
    frontier = [root_id]
    while frontier:
        nxt = [c.id for p in frontier for c in by_parent.get(p, [])]
        if not nxt:
            break
        height += 1
        frontier = nxt
    return height


async def _counts_for(session, notebook_ids: list[int]) -> dict[int, dict]:
    """Conversation and lesson counts per notebook, in two queries.

    Counting per notebook in a loop would be N+1 queries for a sidebar
    that renders on every page.
    """
    if not notebook_ids:
        return {}
    counts = {nid: {"conversations": 0, "lessons": 0} for nid in notebook_ids}

    convs = await session.execute(
        select(Conversation.notebook_id, func.count())
        .where(Conversation.notebook_id.in_(notebook_ids))
        .group_by(Conversation.notebook_id)
    )
    for nid, total in convs.all():
        counts[nid]["conversations"] = total

    lessons = await session.execute(
        select(Lesson.notebook_id, func.count())
        .where(Lesson.notebook_id.in_(notebook_ids))
        .group_by(Lesson.notebook_id)
    )
    for nid, total in lessons.all():
        counts[nid]["lessons"] = total

    return counts


@router.get("")
async def list_notebooks(
    include_archived: bool = Query(False),
    current_user: User = Depends(get_current_user),
):
    """The user's whole notebook tree, flat, with per-notebook counts.

    Returned flat rather than nested: the client needs random access by id
    for breadcrumbs and the move dialog anyway, and rebuilding the tree
    from parent_id is trivial there.
    """
    db = get_database()
    async with db.get_session() as session:
        notebooks = await _all_notebooks(session, current_user.id)
        if not include_archived:
            notebooks = [nb for nb in notebooks if nb.archived_at is None]
        counts = await _counts_for(session, [nb.id for nb in notebooks])
        return {
            "notebooks": [nb.to_dict(counts.get(nb.id)) for nb in notebooks],
            "max_depth": MAX_NOTEBOOK_DEPTH,
        }


@router.get("/recent")
async def most_recent_notebook(current_user: User = Depends(get_current_user)):
    """The notebook to resume into after sign-in.

    Returns null rather than 404 when the user has none - "you have no
    notebooks yet" is an ordinary first-run state, not an error, and the
    client shows the create screen.
    """
    db = get_database()
    async with db.get_session() as session:
        row = await session.execute(
            select(Notebook)
            .where(Notebook.user_id == current_user.id, Notebook.archived_at.is_(None))
            .order_by(
                Notebook.last_opened_at.desc().nullslast(),
                Notebook.created_at.desc(),
            )
            .limit(1)
        )
        notebook = row.scalar_one_or_none()
        return {"notebook": notebook.to_dict() if notebook else None}


@router.post("", status_code=201)
async def create_notebook(payload: dict, current_user: User = Depends(get_current_user)):
    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    if len(name) > 200:
        raise HTTPException(status_code=400, detail="name is too long (max 200 chars)")

    parent_id = payload.get("parent_id")
    db = get_database()
    async with db.get_session() as session:
        notebooks = await _all_notebooks(session, current_user.id)
        if len(notebooks) >= MAX_NOTEBOOKS_PER_USER:
            raise HTTPException(
                status_code=400,
                detail=f"You have reached the limit of {MAX_NOTEBOOKS_PER_USER} notebooks.",
            )

        if parent_id is not None:
            await _owned_notebook(session, parent_id, current_user)
            if _depth_of(notebooks, parent_id) >= MAX_NOTEBOOK_DEPTH:
                raise HTTPException(
                    status_code=400,
                    detail=f"Notebooks can only be nested {MAX_NOTEBOOK_DEPTH} levels deep.",
                )

        notebook = Notebook(
            user_id=current_user.id,
            parent_id=parent_id,
            name=name,
            description=(payload.get("description") or "").strip() or None,
            last_opened_at=datetime.now(timezone.utc),
        )
        session.add(notebook)
        await session.flush()
        result = notebook.to_dict({"conversations": 0, "lessons": 0})

    logger.info(f"Created notebook {result['id']} for user {current_user.id}")
    return result


@router.patch("/{notebook_id}")
async def update_notebook(
    notebook_id: int, payload: dict, current_user: User = Depends(get_current_user)
):
    """Rename, re-describe, move, or restore from the archive."""
    db = get_database()
    async with db.get_session() as session:
        notebook = await _owned_notebook(session, notebook_id, current_user)

        if "name" in payload:
            name = (payload.get("name") or "").strip()
            if not name:
                raise HTTPException(status_code=400, detail="name cannot be empty")
            if len(name) > 200:
                raise HTTPException(status_code=400, detail="name is too long (max 200 chars)")
            notebook.name = name

        if "description" in payload:
            notebook.description = (payload.get("description") or "").strip() or None

        if "archived" in payload:
            notebook.archived_at = (
                datetime.now(timezone.utc) if payload["archived"] else None
            )

        if "parent_id" in payload:
            new_parent = payload["parent_id"]
            if new_parent == notebook_id:
                raise HTTPException(
                    status_code=400, detail="A notebook cannot contain itself."
                )

            notebooks = await _all_notebooks(session, current_user.id)
            if new_parent is not None:
                await _owned_notebook(session, new_parent, current_user)
                # The cycle check: moving a notebook under its own
                # descendant would detach the whole subtree from every
                # root, leaving it unreachable in the UI and unfixable
                # without direct SQL.
                if new_parent in _descendant_ids(notebooks, notebook_id):
                    raise HTTPException(
                        status_code=400,
                        detail="A notebook cannot be moved inside one of its own sub-notebooks.",
                    )
                # Depth is about the whole subtree, not just this row: a
                # 3-level subtree moved under a 3-deep parent lands at 6.
                if _depth_of(notebooks, new_parent) + _subtree_height(
                    notebooks, notebook_id
                ) > MAX_NOTEBOOK_DEPTH:
                    raise HTTPException(
                        status_code=400,
                        detail=f"That move would nest deeper than {MAX_NOTEBOOK_DEPTH} levels.",
                    )
            notebook.parent_id = new_parent

        await session.flush()
        # updated_at is server-side (onupdate=now()), so flushing an UPDATE
        # expires it. Reading it back in to_dict() would then try to load
        # lazily and raise MissingGreenlet on the async engine - refresh
        # explicitly while there is still an awaitable context to do it in.
        await session.refresh(notebook)
        counts = await _counts_for(session, [notebook.id])
        return notebook.to_dict(counts.get(notebook.id))


@router.post("/{notebook_id}/open")
async def open_notebook(notebook_id: int, current_user: User = Depends(get_current_user)):
    """Mark a notebook as the one to resume into next sign-in."""
    db = get_database()
    async with db.get_session() as session:
        notebook = await _owned_notebook(session, notebook_id, current_user)
        notebook.last_opened_at = datetime.now(timezone.utc)
        await session.flush()
        await session.refresh(notebook)  # see update_notebook: onupdate expires updated_at
        return notebook.to_dict()


@router.get("/{notebook_id}/contents")
async def notebook_contents(
    notebook_id: int, current_user: User = Depends(get_current_user)
):
    """Everything filed directly in this notebook: sub-notebooks, chats, courses."""
    db = get_database()
    async with db.get_session() as session:
        notebook = await _owned_notebook(session, notebook_id, current_user)

        children = await session.execute(
            select(Notebook)
            .where(
                Notebook.user_id == current_user.id,
                Notebook.parent_id == notebook_id,
                Notebook.archived_at.is_(None),
            )
            .order_by(Notebook.name)
        )
        children = list(children.scalars().all())
        child_counts = await _counts_for(session, [c.id for c in children])

        conversations = await session.execute(
            select(Conversation)
            .where(Conversation.notebook_id == notebook_id)
            .order_by(Conversation.updated_at.desc())
        )
        lessons = await session.execute(
            select(Lesson)
            .where(Lesson.notebook_id == notebook_id)
            .order_by(Lesson.created_at.desc())
        )

        return {
            "notebook": notebook.to_dict(),
            "children": [c.to_dict(child_counts.get(c.id)) for c in children],
            "conversations": [
                {
                    "id": c.id,
                    "session_id": c.session_id,
                    "title": c.title,
                    "updated_at": c.updated_at.isoformat() if c.updated_at else None,
                }
                for c in conversations.scalars().all()
            ],
            "lessons": [
                l.to_dict(include_scenes=False) for l in lessons.scalars().all()
            ],
        }


@router.delete("/{notebook_id}")
async def delete_notebook(
    notebook_id: int,
    permanent: bool = Query(False),
    current_user: User = Depends(get_current_user),
):
    """Archive by default; delete for real only when explicitly asked.

    Even a permanent delete keeps the contents: the foreign keys are SET
    NULL, so conversations and lessons survive as unfiled and sub-notebooks
    are promoted to the top level. What is destroyed is the filing, not
    the student's work.
    """
    db = get_database()
    async with db.get_session() as session:
        notebook = await _owned_notebook(session, notebook_id, current_user)

        if not permanent:
            notebook.archived_at = datetime.now(timezone.utc)
            await session.flush()
            return {"id": notebook_id, "archived": True}

        notebooks = await _all_notebooks(session, current_user.id)
        child_count = sum(1 for nb in notebooks if nb.parent_id == notebook_id)
        counts = await _counts_for(session, [notebook_id])
        await session.delete(notebook)

    logger.info(f"Deleted notebook {notebook_id} for user {current_user.id}")
    return {
        "id": notebook_id,
        "deleted": True,
        "promoted_children": child_count,
        "unfiled": counts.get(notebook_id, {"conversations": 0, "lessons": 0}),
    }
