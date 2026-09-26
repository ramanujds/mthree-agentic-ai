# Step 4 — Document Summary Index Retriever

> [Back to index](README.md) · Previous: [BM25 Retriever](04-bm25-retriever.md) · Next: [Auto Merging Retriever](06-auto-merging-retriever.md)

## Goal

Build `03_document_summary_index_retriever.py`: retrieval that first picks a whole *document* using an LLM-generated summary, then hands back that document's real chunks — in both an LLM-based and an embedding-based flavor.

## Why this matters

Steps 2 and 3 both retrieve at the chunk level: split everything into small pieces, rank the pieces. `DocumentSummaryIndex` retrieves at the **document** level instead. At index time, it asks the LLM to summarize each document; at query time, a retriever compares the query against those summaries (not the raw chunks) to decide which whole document(s) are relevant — and only then returns that document's actual nodes.

This is a real, useful tradeoff when you have many large documents: comparing a query against 500 short summaries is far cheaper than comparing it against every chunk of every document, and it avoids a chunk winning a similarity match purely by luck while sitting inside an otherwise-irrelevant document. The cost is paid up front: building the index now makes one LLM call *per document* to generate its summary, which is why this step is noticeably slower to build than Steps 2 and 3.

Two retriever variants make that document-level decision differently:

| Retriever | How it decides | Tradeoff |
| --- | --- | --- |
| `DocumentSummaryIndexLLMRetriever` | Shows the LLM all summaries and asks it to choose | More accurate reasoning, slower and costlier per query |
| `DocumentSummaryIndexEmbeddingRetriever` | Compares the query's embedding to each summary's embedding | Cheaper, scales better to many documents |

Whichever one you use, both return nodes from the **original document**, never the summary text — the summary is only ever a filter, not something to hand to a user.

## 1. Scaffold the file

```python
"""
Document Summary Index Retriever.

DocumentSummaryIndex generates an LLM summary of each document at index
time. Retrieval then works at the document level: a query is matched
against summaries (not raw chunks) to decide which whole documents are
relevant, and only then are that document's real nodes returned.

Two retriever variants are shown:
  - DocumentSummaryIndexLLMRetriever: asks the LLM to choose relevant
    document(s) by reading all summaries. More accurate, slower/costlier.
  - DocumentSummaryIndexEmbeddingRetriever: embeds the query and compares
    it against summary embeddings. Cheaper, scales better to many docs.

Both return nodes from the ORIGINAL documents, never the summaries
themselves - summaries are only used to pick which document(s) to open.
"""

import os

from llama_index.core import DocumentSummaryIndex, Settings, SimpleDirectoryReader, get_response_synthesizer
from llama_index.core.indices.document_summary import (
    DocumentSummaryIndexEmbeddingRetriever,
    DocumentSummaryIndexLLMRetriever,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.environ.get("OLLAMA_LLM_MODEL", "llama3:8b")
EMBED_MODEL = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")


def main():
    print("Scaffold ready.")


if __name__ == "__main__":
    main()
```

Save this as `03_document_summary_index_retriever.py`. Look closely at that second import: both retriever classes come from `llama_index.core.indices.document_summary`, **not** `llama_index.core.retrievers` where every other retriever in this walkthrough lives. Guessing the "obvious" import path here is an easy way to hit an `ImportError` (see Common mistakes).

## 2. Build the DocumentSummaryIndex

```python
def build_index() -> DocumentSummaryIndex:
    Settings.llm = Ollama(model=LLM_MODEL, base_url=OLLAMA_BASE_URL, request_timeout=120.0)
    Settings.embed_model = OllamaEmbedding(model_name=EMBED_MODEL, base_url=OLLAMA_BASE_URL)

    # SimpleDirectoryReader loads each file as its own Document, so the
    # index has one summary per file: company_policy.txt, onboarding_faq.txt.
    documents = SimpleDirectoryReader(input_files=[
        os.path.join(DATA_DIR, "company_policy.txt"),
        os.path.join(DATA_DIR, "onboarding_faq.txt"),
    ]).load_data()

    splitter = SentenceSplitter(chunk_size=256, chunk_overlap=20)
    response_synthesizer = get_response_synthesizer(response_mode="tree_summarize", use_async=False)

    return DocumentSummaryIndex.from_documents(
        documents,
        transformations=[splitter],
        response_synthesizer=response_synthesizer,
        show_progress=True,
    )
```

`response_mode="tree_summarize"` tells the response synthesizer how to combine multiple chunks into one summary when a document has more than one — recursively merging partial summaries rather than concatenating everything into a single giant prompt. `show_progress=True` gives you a progress bar precisely because this step, unlike Steps 2 and 3, does real per-document LLM work at build time.

## 3. Print the generated summaries

Before even retrieving anything, inspect what got generated — this is the artifact retrieval will actually search over:

```python
def main():
    index = build_index()

    print("Generated summaries:")
    for doc_id in index.index_struct.doc_id_to_summary_id:
        summary = index.get_document_summary(doc_id)
        print(f"  [{doc_id[:8]}] {summary[:150]}...")
    print("-" * 60)
```

## 4. Retrieve with both variants

```python
    llm_retriever = DocumentSummaryIndexLLMRetriever(index, choice_top_k=1)
    embedding_retriever = DocumentSummaryIndexEmbeddingRetriever(index, similarity_top_k=1)

    question = "How many vacation days can be carried over to next year?"

    for name, retriever in [("LLM-based", llm_retriever), ("Embedding-based", embedding_retriever)]:
        nodes = retriever.retrieve(question)
        print(f"Q ({name}): {question}")
        for n in nodes:
            print(f"  file={n.node.metadata.get('file_name')} text: {n.node.get_content()[:120]}...")
        print("-" * 60)
```

Notice the LLM retriever's parameter is `choice_top_k`, not `similarity_top_k` — it's picking among a small number of discrete choices (documents) by having the LLM reason over them, not ranking by a similarity score, so the parameter name reflects that difference.

## Try it

```bash
uv run 03_document_summary_index_retriever.py
```

Expected shape of the output (the exact summary wording is LLM-generated and may differ slightly between runs, but should describe the same two topics):

```
Generated summaries:
  [5c89ae60] The provided text appears to be a collection of company policies, outlining rules and guidelines for employees. Specifically, it covers remote work, v...
  [fa17d835] This text appears to be a collection of frequently asked questions (FAQs) related to the process of onboarding new hires. It provides answers to commo...
------------------------------------------------------------
Q (LLM-based): How many vacation days can be carried over to next year?
  file=company_policy.txt text: Remote Work Policy
...
------------------------------------------------------------
Q (Embedding-based): How many vacation days can be carried over to next year?
  file=company_policy.txt text: Remote Work Policy
...
------------------------------------------------------------
```

Both variants agree here because there are only two candidate documents and the question is unambiguous — the real difference between them shows up as your corpus grows into dozens or hundreds of documents.

## Checkpoint

<details>
<summary>Full <code>03_document_summary_index_retriever.py</code></summary>

```python
"""
Document Summary Index Retriever.

DocumentSummaryIndex generates an LLM summary of each document at index
time. Retrieval then works at the document level: a query is matched
against summaries (not raw chunks) to decide which whole documents are
relevant, and only then are that document's real nodes returned.

Two retriever variants are shown:
  - DocumentSummaryIndexLLMRetriever: asks the LLM to choose relevant
    document(s) by reading all summaries. More accurate, slower/costlier.
  - DocumentSummaryIndexEmbeddingRetriever: embeds the query and compares
    it against summary embeddings. Cheaper, scales better to many docs.

Both return nodes from the ORIGINAL documents, never the summaries
themselves - summaries are only used to pick which document(s) to open.
"""

import os

from llama_index.core import DocumentSummaryIndex, Settings, SimpleDirectoryReader, get_response_synthesizer
from llama_index.core.indices.document_summary import (
    DocumentSummaryIndexEmbeddingRetriever,
    DocumentSummaryIndexLLMRetriever,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.environ.get("OLLAMA_LLM_MODEL", "llama3:8b")
EMBED_MODEL = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")


def build_index() -> DocumentSummaryIndex:
    Settings.llm = Ollama(model=LLM_MODEL, base_url=OLLAMA_BASE_URL, request_timeout=120.0)
    Settings.embed_model = OllamaEmbedding(model_name=EMBED_MODEL, base_url=OLLAMA_BASE_URL)

    # SimpleDirectoryReader loads each file as its own Document, so the
    # index has one summary per file: company_policy.txt, onboarding_faq.txt.
    documents = SimpleDirectoryReader(input_files=[
        os.path.join(DATA_DIR, "company_policy.txt"),
        os.path.join(DATA_DIR, "onboarding_faq.txt"),
    ]).load_data()

    splitter = SentenceSplitter(chunk_size=256, chunk_overlap=20)
    response_synthesizer = get_response_synthesizer(response_mode="tree_summarize", use_async=False)

    return DocumentSummaryIndex.from_documents(
        documents,
        transformations=[splitter],
        response_synthesizer=response_synthesizer,
        show_progress=True,
    )


def main():
    index = build_index()

    print("Generated summaries:")
    for doc_id in index.index_struct.doc_id_to_summary_id:
        summary = index.get_document_summary(doc_id)
        print(f"  [{doc_id[:8]}] {summary[:150]}...")
    print("-" * 60)

    llm_retriever = DocumentSummaryIndexLLMRetriever(index, choice_top_k=1)
    embedding_retriever = DocumentSummaryIndexEmbeddingRetriever(index, similarity_top_k=1)

    question = "How many vacation days can be carried over to next year?"

    for name, retriever in [("LLM-based", llm_retriever), ("Embedding-based", embedding_retriever)]:
        nodes = retriever.retrieve(question)
        print(f"Q ({name}): {question}")
        for n in nodes:
            print(f"  file={n.node.metadata.get('file_name')} text: {n.node.get_content()[:120]}...")
        print("-" * 60)


if __name__ == "__main__":
    main()
```

This matches [../advanced-retrievers-examples/03_document_summary_index_retriever.py](../advanced-retrievers-examples/03_document_summary_index_retriever.py) exactly.

</details>

## Common mistakes

| Symptom | Cause | Fix |
| --- | --- | --- |
| `ImportError: cannot import name 'DocumentSummaryIndexEmbeddingRetriever' from 'llama_index.core.retrievers'` | Guessed the same import path used for `VectorIndexRetriever` / `BM25Retriever` | Import from `llama_index.core.indices.document_summary` instead |
| Building the index takes noticeably longer than Steps 2-3 | `DocumentSummaryIndex.from_documents` calls the LLM once per document to generate its summary | Expected — `show_progress=True` shows exactly where the time goes; scales with document count |
| Both retriever variants always return the same document | Only two candidate documents in this corpus, and the question is unambiguous | Expected here; the LLM-based vs. embedding-based distinction matters most once you have many more documents |

Next: **[Auto Merging Retriever](06-auto-merging-retriever.md)** — chunking a long document hierarchically instead of flatly.
