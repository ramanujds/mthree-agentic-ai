"""Pydantic request/response models for Study Buddy (see notes/08-pydantic-structured-outputs.md)."""

from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class NoteCreate(BaseModel):
    topic: str = Field(..., min_length=1, max_length=100)
    content: str = Field(..., min_length=1, max_length=2000)


class Note(NoteCreate):
    id: str
    created_at: datetime


class ScoreCreate(BaseModel):
    topic: str = Field(..., min_length=1, max_length=100)
    score: int = Field(..., ge=0)
    max_score: int = Field(..., gt=0)

    @model_validator(mode="after")
    def score_within_bounds(self) -> "ScoreCreate":
        if self.score > self.max_score:
            raise ValueError("score cannot exceed max_score")
        return self


class Score(ScoreCreate):
    id: str
    recorded_at: datetime


class TopicStats(BaseModel):
    topic: str
    mean_percent: float
    attempts: int


class ScoreStats(BaseModel):
    overall_mean_percent: float | None
    total_attempts: int
    best_topic: str | None
    worst_topic: str | None
    by_topic: list[TopicStats]


class ExportResult(BaseModel):
    json_path: str
    csv_path: str
