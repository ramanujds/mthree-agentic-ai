"""In-memory data store for notes and scores (see notes/03-data-structures-deep-dive.md).

A plain dict keyed by id gives O(1) lookup/insert/delete while preserving
insertion order (regular dicts are ordered since Python 3.7) — good enough
for this case study; swap for a real DB later without changing the router
code, since routers only depend on this module's function signatures.
"""

import uuid
from collections import Counter
from datetime import datetime, timezone

from schemas import Note, NoteCreate, Score, ScoreCreate

_notes: dict[str, Note] = {}
_scores: dict[str, Score] = {}


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --- Notes -------------------------------------------------------------

def add_note(payload: NoteCreate) -> Note:
    note = Note(id=_new_id(), created_at=_now(), **payload.model_dump())
    _notes[note.id] = note
    return note


def list_notes(topic: str | None = None) -> list[Note]:
    notes = list(_notes.values())
    if topic:
        notes = [n for n in notes if n.topic.lower() == topic.lower()]
    return notes


def search_notes(query: str) -> list[Note]:
    q = query.lower()
    return [
        n for n in _notes.values()
        if q in n.content.lower() or q in n.topic.lower()
    ]


def topic_counts() -> list[tuple[str, int]]:
    counts = Counter(n.topic for n in _notes.values())
    return counts.most_common()


# --- Scores --------------------------------------------------------------

def add_score(payload: ScoreCreate) -> Score:
    score = Score(id=_new_id(), recorded_at=_now(), **payload.model_dump())
    _scores[score.id] = score
    return score


def list_scores(topic: str | None = None) -> list[Score]:
    scores = list(_scores.values())
    if topic:
        scores = [s for s in scores if s.topic.lower() == topic.lower()]
    return scores


def clear_all() -> None:
    """Testing/dev helper — wipe the store."""
    _notes.clear()
    _scores.clear()
