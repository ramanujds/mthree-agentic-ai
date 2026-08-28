"""Score statistics via NumPy + Pandas (see notes/04-numpy-essentials.md
and notes/05-pandas-data-wrangling.md).
"""

import numpy as np
import pandas as pd

from schemas import ScoreStats, TopicStats
from scorebook import ScoreBook


def compute_score_stats(scorebook: ScoreBook) -> ScoreStats:
    if len(scorebook) == 0:
        return ScoreStats(
            overall_mean_percent=None,
            total_attempts=0,
            best_topic=None,
            worst_topic=None,
            by_topic=[],
        )

    df = pd.DataFrame(
        {
            "topic": [s.topic for s in scorebook],
            "percent": np.array(scorebook.percentages()),
        }
    )

    overall_mean = float(df["percent"].mean())

    per_topic = df.groupby("topic")["percent"].agg(["mean", "count"]).reset_index()
    per_topic = per_topic.sort_values("mean", ascending=False)

    best_row = per_topic.iloc[0]
    worst_row = per_topic.iloc[-1]

    by_topic = [
        TopicStats(topic=row["topic"], mean_percent=round(float(row["mean"]), 2), attempts=int(row["count"]))
        for _, row in per_topic.iterrows()
    ]

    return ScoreStats(
        overall_mean_percent=round(overall_mean, 2),
        total_attempts=len(scorebook),
        best_topic=str(best_row["topic"]),
        worst_topic=str(worst_row["topic"]),
        by_topic=by_topic,
    )
