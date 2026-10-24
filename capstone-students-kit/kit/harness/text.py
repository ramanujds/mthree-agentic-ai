"""Tokenisation, a hashing 'embedding', BM25 and rank fusion. Pure standard library."""
from __future__ import annotations
import hashlib, math, re
from collections import Counter

STOP = set("a an the of to in on for and or is are was were be been by with at as it its this that from what who how when which can do does did "
           "must may should would will if than then so such not no into over per each any all".split())
_TOKEN = re.compile(r"[a-z0-9$%][a-z0-9$%.,:'-]*[a-z0-9%]|[a-z0-9]", re.I)


def _stem(w: str) -> str:
    for suf in ("ing", "ed", "es", "s"):
        if len(w) > len(suf) + 3 and w.endswith(suf):
            return w[: -len(suf)]
    return w


def tokenize(text: str, keep_stop: bool = False) -> list[str]:
    toks = []
    for m in _TOKEN.findall(text.lower()):
        m = m.strip(".,:'-")
        if not m:
            continue
        if not keep_stop and m in STOP:
            continue
        toks.append(_stem(m))
    return toks


def count_tokens(text: str) -> int:
    """Rough LLM-token estimate (~1.3 tokens per word). Used for budgets and *simulated* cost."""
    return max(1, int(len(text.split()) * 1.3)) if text.strip() else 0


class HashingEmbedder:
    """Deterministic 'dense' embedding via the hashing trick (unigrams + bigrams). No model download, no cost.
    It is lexical, not truly semantic - discuss that trade-off in your write-up."""

    def __init__(self, dim: int = 512):
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        v = [0.0] * self.dim
        toks = tokenize(text)
        feats = toks + [a + "_" + b for a, b in zip(toks, toks[1:])]
        for f in feats:
            h = int(hashlib.md5(f.encode()).hexdigest(), 16)
            v[h % self.dim] += 1.0 if (h >> 64) & 1 else -1.0
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / n for x in v]

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))  # vectors are already L2-normalised


class BM25:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b

    def fit(self, docs: list[list[str]]) -> "BM25":
        self.docs = docs
        self.N = len(docs)
        self.avgdl = sum(len(d) for d in docs) / max(1, self.N)
        df = Counter()
        for d in docs:
            df.update(set(d))
        self.idf = {t: math.log(1 + (self.N - n + 0.5) / (n + 0.5)) for t, n in df.items()}
        self.tf = [Counter(d) for d in docs]
        return self

    def scores(self, query_tokens: list[str]) -> list[float]:
        out = []
        for i, d in enumerate(self.docs):
            s, dl = 0.0, len(d) or 1
            for t in query_tokens:
                f = self.tf[i].get(t, 0)
                if f:
                    s += self.idf.get(t, 0) * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
            out.append(s)
        return out


def rrf(rank_lists: list[list], k: int = 60) -> list[tuple]:
    """Reciprocal Rank Fusion. Each rank list is an ordered list of ids. Returns [(id, score)] best first."""
    sc: dict = {}
    for rl in rank_lists:
        for r, i in enumerate(rl):
            sc[i] = sc.get(i, 0.0) + 1.0 / (k + r + 1)
    return sorted(sc.items(), key=lambda x: -x[1])


def extractive_summary(messages: list[dict], max_words: int = 40) -> str:
    """Tiny free 'summariser': the first sentence of each message, trimmed. Plug in a real LLM summariser later if you want."""
    out = []
    for m in messages:
        first = (m.get("content") or "").split(".")[0].strip()
        if first:
            out.append(f"{m.get('role', '?')}: {first}")
    return " | ".join(out)[: max_words * 7]
