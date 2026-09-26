# Step 3 — BM25 Retriever

> [Back to index](README.md) · Previous: [Vector Index Retriever](03-vector-index-retriever.md) · Next: [Document Summary Index Retriever](05-document-summary-index-retriever.md)

## Goal

Build `02_bm25_retriever.py`: a keyword-based retriever with no embeddings and no LLM involved at all, and see how it ranks the same kind of question differently from Step 2's vector retriever.

## Why this matters

BM25 is TF-IDF's more practical successor. TF-IDF scores a term by how often it appears in a document (term frequency) times how rare it is across the whole corpus (inverse document frequency) — it rewards words that are common in *this* document but uncommon everywhere else. BM25 keeps that idea but fixes two of its rough edges:

- **Term frequency saturation** — a word appearing 20 times shouldn't score 20x higher than it appearing once; BM25's contribution from repeated terms flattens out.
- **Document length normalization** — a long document naturally contains more words, including more repeats, so raw counts are adjusted for length before comparing across documents.

None of this involves meaning at all — it's pure vocabulary overlap. That's exactly why `BM25Retriever` needs no `Settings.embed_model` and no `Settings.llm`: it builds its own term-frequency index directly from a list of nodes, with nothing else in the pipeline.

## 1. Add the BM25 dependency

`BM25Retriever` lives in its own package, separate from `llama-index-core`:

```bash
uv add "llama-index-retrievers-bm25>=0.5.0"
```

## 2. Scaffold the file

```python
"""
BM25 Retriever.

A keyword-based retriever: it ranks chunks by exact term overlap with the
query, not semantic similarity. BM25 improves on plain TF-IDF with term
frequency saturation (repeating a word doesn't linearly increase its
score forever) and document length normalization. No embeddings or LLM
are needed for retrieval itself, since this is pure lexical matching.
"""

import os

from llama_index.core import SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter
from llama_index.retrievers.bm25 import BM25Retriever

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def main():
    print("Scaffold ready.")


if __name__ == "__main__":
    main()
```

Save this as `02_bm25_retriever.py`. Notice there's no `Settings`, no `Ollama`, no `OllamaEmbedding` import at all — the first script in this walkthrough that doesn't need them.

## 3. Split documents into nodes directly

`BM25Retriever.from_defaults` takes a plain list of `nodes`, not an index. So this script has to chunk documents itself instead of letting `VectorStoreIndex.from_documents` do it implicitly:

```python
def build_retriever() -> BM25Retriever:
    documents = SimpleDirectoryReader(input_files=[
        os.path.join(DATA_DIR, "company_policy.txt"),
        os.path.join(DATA_DIR, "onboarding_faq.txt"),
    ]).load_data()

    splitter = SentenceSplitter(chunk_size=256, chunk_overlap=20)
    nodes = splitter.get_nodes_from_documents(documents)

    return BM25Retriever.from_defaults(nodes=nodes, similarity_top_k=2)
```

## 4. Query with keyword-heavy phrases

Vector search shines on paraphrased, natural-language questions. To see BM25 at its best, query with phrases that lift vocabulary straight out of the source text:

```python
def main():
    retriever = build_retriever()

    # Queries chosen to favor exact keyword overlap over semantic meaning.
    questions = [
        "reimbursement receipts 30 days",
        "onboarding buddy first day",
    ]

    for question in questions:
        nodes = retriever.retrieve(question)
        print(f"Q: {question}")
        for n in nodes:
            print(f"  score={n.score:.4f} file={n.node.metadata.get('file_name')}")
            print(f"  text: {n.node.get_content()[:120]}...")
        print("-" * 60)
```

## Try it

```bash
uv run 02_bm25_retriever.py
```

Expected output:

```
Q: reimbursement receipts 30 days
  score=1.1799 file=company_policy.txt
  text: Remote Work Policy
...
  score=0.1205 file=onboarding_faq.txt
  ...
------------------------------------------------------------
Q: onboarding buddy first day
  score=1.3101 file=onboarding_faq.txt
  ...
  score=0.1508 file=company_policy.txt
  ...
```

Both files are still short enough to be a single node each, so the printed preview shows the start of the file rather than the exact matched phrase — the score and file name are what confirm the match, not the truncated preview text.

## Checkpoint

<details>
<summary>Full <code>02_bm25_retriever.py</code></summary>

```python
"""
BM25 Retriever.

A keyword-based retriever: it ranks chunks by exact term overlap with the
query, not semantic similarity. BM25 improves on plain TF-IDF with term
frequency saturation (repeating a word doesn't linearly increase its
score forever) and document length normalization. No embeddings or LLM
are needed for retrieval itself, since this is pure lexical matching.
"""

import os

from llama_index.core import SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter
from llama_index.retrievers.bm25 import BM25Retriever

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def build_retriever() -> BM25Retriever:
    documents = SimpleDirectoryReader(input_files=[
        os.path.join(DATA_DIR, "company_policy.txt"),
        os.path.join(DATA_DIR, "onboarding_faq.txt"),
    ]).load_data()

    splitter = SentenceSplitter(chunk_size=256, chunk_overlap=20)
    nodes = splitter.get_nodes_from_documents(documents)

    return BM25Retriever.from_defaults(nodes=nodes, similarity_top_k=2)


def main():
    retriever = build_retriever()

    # Queries chosen to favor exact keyword overlap over semantic meaning.
    questions = [
        "reimbursement receipts 30 days",
        "onboarding buddy first day",
    ]

    for question in questions:
        nodes = retriever.retrieve(question)
        print(f"Q: {question}")
        for n in nodes:
            print(f"  score={n.score:.4f} file={n.node.metadata.get('file_name')}")
            print(f"  text: {n.node.get_content()[:120]}...")
        print("-" * 60)


if __name__ == "__main__":
    main()
```

This matches [../advanced-retrievers-examples/02_bm25_retriever.py](../advanced-retrievers-examples/02_bm25_retriever.py) exactly.

</details>

## Common mistakes

| Symptom | Cause | Fix |
| --- | --- | --- |
| `ModuleNotFoundError: No module named 'llama_index.retrievers.bm25'` | Skipped `uv add`, or added it but forgot `uv sync` | Confirm `llama-index-retrievers-bm25` is in `pyproject.toml`, then `uv sync` |
| A natural-language question returns weak or irrelevant matches | BM25 has no notion of synonyms or meaning — the query must share actual words with the text | Rephrase using the document's own vocabulary, or pair BM25 with a vector retriever (Step 7 does exactly this) |
| Install fails building a stemmer dependency | Missing platform build tools for `PyStemmer` | Re-run `uv sync`; if it persists, check for prebuilt wheels for your platform/Python version |

Next: **[Document Summary Index Retriever](05-document-summary-index-retriever.md)** — retrieval at the whole-document level instead of the chunk level.
