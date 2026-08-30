"""Report export endpoint — concurrent file writes (see notes/07-async-concurrency.md, section 3)."""

import asyncio
from pathlib import Path

import aiofiles
from fastapi import APIRouter

import store
from analytics import compute_score_stats
from exporters import CSVExporter, JSONExporter
from schemas import ExportResult
from scorebook import ScoreBook

router = APIRouter(prefix="/reports", tags=["reports"])

EXPORT_DIR = Path(__file__).resolve().parent.parent / "exports"


async def _write_file(path: Path, content: str) -> None:
    async with aiofiles.open(path, "w") as f:
        await f.write(content)


@router.post("/export", response_model=ExportResult)
async def export_report() -> ExportResult:
    EXPORT_DIR.mkdir(exist_ok=True)

    notes = store.list_notes()
    stats = compute_score_stats(ScoreBook(store.list_scores()))

    json_content = JSONExporter().render(notes, stats)
    csv_content = CSVExporter().render(notes, stats)

    json_path = EXPORT_DIR / "report.json"
    csv_path = EXPORT_DIR / "report.csv"

    # Both files are written concurrently, not one after another — the point
    # of this endpoint. Time it (or add a log line) to see them interleave.
    await asyncio.gather(
        _write_file(json_path, json_content),
        _write_file(csv_path, csv_content),
    )

    return ExportResult(json_path=str(json_path), csv_path=str(csv_path))
