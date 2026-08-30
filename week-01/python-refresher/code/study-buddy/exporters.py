"""Report exporters — ABC + mixin (see notes/06-oop-deep-dive.md, sections 1-2).

ReportExporter defines the contract every format must satisfy. Adding a new
format (e.g. Markdown) means adding one new subclass — the export endpoint
in routers/reports.py never needs to change.
"""

import csv
import io
import json
from abc import ABC, abstractmethod

from schemas import Note, ScoreStats


class LoggingMixin:
    """Adds a .log() method to anything that mixes it in."""

    def log(self, message: str) -> None:
        print(f"[{self.__class__.__name__}] {message}")


class ReportExporter(ABC):
    @abstractmethod
    def render(self, notes: list[Note], stats: ScoreStats) -> str:
        ...

    @abstractmethod
    def file_extension(self) -> str:
        ...


class JSONExporter(ReportExporter, LoggingMixin):
    def render(self, notes: list[Note], stats: ScoreStats) -> str:
        self.log(f"rendering JSON report ({len(notes)} notes)")
        payload = {
            "notes": [n.model_dump(mode="json") for n in notes],
            "stats": stats.model_dump(mode="json"),
        }
        return json.dumps(payload, indent=2)

    def file_extension(self) -> str:
        return "json"


class CSVExporter(ReportExporter, LoggingMixin):
    def render(self, notes: list[Note], stats: ScoreStats) -> str:
        self.log(f"rendering CSV report ({len(notes)} notes)")
        buffer = io.StringIO()
        writer = csv.writer(buffer)

        writer.writerow(["== NOTES =="])
        writer.writerow(["id", "topic", "content", "created_at"])
        for note in notes:
            writer.writerow([note.id, note.topic, note.content, note.created_at.isoformat()])

        writer.writerow([])
        writer.writerow(["== TOPIC STATS =="])
        writer.writerow(["topic", "mean_percent", "attempts"])
        for row in stats.by_topic:
            writer.writerow([row.topic, row.mean_percent, row.attempts])

        writer.writerow([])
        writer.writerow(["overall_mean_percent", stats.overall_mean_percent])
        writer.writerow(["total_attempts", stats.total_attempts])
        writer.writerow(["best_topic", stats.best_topic])
        writer.writerow(["worst_topic", stats.worst_topic])

        return buffer.getvalue()

    def file_extension(self) -> str:
        return "csv"


EXPORTERS: dict[str, ReportExporter] = {
    "json": JSONExporter(),
    "csv": CSVExporter(),
}
