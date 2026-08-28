"""Scores + analytics endpoints (see notes/04, 05, 06, 08, 09)."""

from fastapi import APIRouter, Query

import store
from analytics import compute_score_stats
from schemas import Score, ScoreCreate, ScoreStats
from scorebook import ScoreBook

router = APIRouter(prefix="/scores", tags=["scores"])


@router.post("", response_model=Score, status_code=201)
def create_score(payload: ScoreCreate) -> Score:
    return store.add_score(payload)


@router.get("", response_model=list[Score])
def get_scores(topic: str | None = Query(default=None)) -> list[Score]:
    return store.list_scores(topic=topic)


@router.get("/stats", response_model=ScoreStats)
def get_score_stats() -> ScoreStats:
    scorebook = ScoreBook(store.list_scores())
    return compute_score_stats(scorebook)
