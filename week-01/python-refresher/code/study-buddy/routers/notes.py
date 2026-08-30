"""Notes endpoints (see notes/09-fastapi-essentials.md)."""

from fastapi import APIRouter, Query

import store
from schemas import Note, NoteCreate

router = APIRouter(prefix="/notes", tags=["notes"])


@router.post("", response_model=Note, status_code=201)
def create_note(payload: NoteCreate) -> Note:
    return store.add_note(payload)


@router.get("", response_model=list[Note])
def get_notes(topic: str | None = Query(default=None)) -> list[Note]:
    return store.list_notes(topic=topic)


@router.get("/search", response_model=list[Note])
def search_notes(q: str = Query(default="", description="Search term")) -> list[Note]:
    if not q.strip():
        return []
    return store.search_notes(q)


@router.get("/topic-counts")
def get_topic_counts() -> list[dict]:
    return [{"topic": topic, "count": count} for topic, count in store.topic_counts()]
