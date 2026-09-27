# PageIndex Notes

Reference: [vectorless-rag.md](vectorless-rag.md) §3–5

## Core idea

Vector RAG asks *"what text looks like the question?"*
PageIndex asks *"where would an expert look to answer this question?"*

Instead of chunking + embedding a document, PageIndex builds a **hierarchical index**
(an enhanced table of contents) and has an LLM *navigate* it — no vector store, no
embedding similarity.

## Components

### 1. Tree Index

Built once per document (offline). Each node holds:

- `title` — section heading
- `summary` — short LLM-generated summary of the section's content
- `pages` — page range it spans
- `text` — full text, attached only at leaf nodes, read lazily (only when opened)
- `children` — subsections

Build steps:
1. Parse heading structure (PDF outlines, heading styles, or an LLM pass)
2. Summarize each node bottom-up
3. Persist as JSON — no vector DB needed

### 2. Navigation Agent

At query time the LLM sees **titles + summaries only** (never full text) at each level:

1. Look at the root's children → pick the branch most likely to hold the answer
2. Descend one level, repeat
3. On reaching a leaf, read its full text
4. If the text contains a cross-reference ("see Appendix B"), follow it and pull that
   section in too
5. Answer, citing the page ranges actually opened

### 3. Cross-reference following

The feature vector search structurally cannot do — "see Appendix B" has no embedding
relationship to Appendix B, but in a tree it's just another node to visit.

## Runnable sketch — key pieces

From the code in [vectorless-rag.md](vectorless-rag.md) §5:

- `Node` dataclass — id, title, summary, pages, text, children
- `mock_llm_choose(question, children)` — stand-in for the real LLM call; picks the
  best child by keyword overlap. **This is the only piece to swap for production** —
  replace with a real LLM call using:
  ```
  Question: {question}
  You are navigating a document's table of contents.
  Options (id | title | summary): ...
  Reply with the single id most likely to contain the answer, or NONE.
  ```
- `navigate(question, root)` — descends one level per reasoning step while children
  exist, then regex-scans the resulting text for "see Appendix X" and recursively
  pulls in referenced nodes.

### Adapting for a real document

1. Build the tree from the actual doc (extract headings → nest as `Node`s →
   LLM-summarize bottom-up)
2. Swap `mock_llm_choose` for a real LLM call
3. Keep the descend-then-follow-cross-refs shape — it's the core mechanism
4. Add backtracking — the sketch is greedy and never undoes a wrong turn; a wrong
   turn near the root is the main failure mode

## When to use it

**Good fit:** long, well-structured documents (annual reports, contracts, regulatory
manuals) where precision and traceability matter more than latency.
Cost: ~3–6 LLM calls per query vs. a millisecond vector lookup.

**Poor fit:** huge volumes of short, unstructured text (support tickets, chat logs) —
no hierarchy to navigate.

See §10 decision tree and Quick Reference Card in
[vectorless-rag.md](vectorless-rag.md) for picking between this and the other
vectorless flavors (agentic lexical search, structured retrieval, long-context/CAG)
or falling back to vector RAG.

## Open questions / next steps

- [ ] Build a real tree index from a PDF (extract outline, summarize bottom-up,
      persist as JSON) — Week's "what's next" item #2
- [ ] Add backtracking to the navigation loop
- [ ] Try coarse-to-fine hybrid: vector/BM25 picks the document, PageIndex picks
      the section within it
