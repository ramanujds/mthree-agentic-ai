"""ScoreBook — wraps a list of scores as a native-feeling collection.

Demonstrates dunder methods (__len__, __getitem__, __iter__, __repr__) from
notes/06-oop-deep-dive.md, section 3 — the same pattern behind
torch.utils.data.Dataset (len(dataset), dataset[i], for x in dataset).
"""

from schemas import Score


class ScoreBook:
    def __init__(self, scores: list[Score]):
        self._scores = scores

    def __len__(self) -> int:
        return len(self._scores)

    def __getitem__(self, idx):
        return self._scores[idx]

    def __iter__(self):
        return iter(self._scores)

    def __repr__(self) -> str:
        return f"ScoreBook({len(self)} scores)"

    def by_topic(self, topic: str) -> "ScoreBook":
        return ScoreBook([s for s in self._scores if s.topic.lower() == topic.lower()])

    def topics(self) -> set[str]:
        return {s.topic for s in self._scores}

    def percentages(self) -> list[float]:
        return [100.0 * s.score / s.max_score for s in self._scores]
