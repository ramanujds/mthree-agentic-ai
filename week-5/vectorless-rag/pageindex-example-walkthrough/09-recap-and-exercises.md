# Step 8 — Recap and Exercises

> [Back to index](README.md) · Previous: [Grounded Answers and Wiring](08-grounded-answers-and-wiring.md)

## What you built

One script, from an empty folder: `main.py`, a vectorless RAG pipeline that parses a company handbook's own heading structure into a tree, has an LLM navigate it by title and summary alone, follows cross-references explicitly, and answers grounded in exactly the sections retrieved that way. No vector store, no embedding model, no third-party dependencies.

It should now match [../pageindex-example/main.py](../pageindex-example/main.py) exactly.

## Quick reference card

| Concept | Where it lives |
| --- | --- |
| Document structure as a tree | `Node` dataclass — title, summary, text, children |
| Heading-to-tree parsing | `parse_markdown_tree` — no chunk size, no overlap |
| One-time index-build cost | `summarize_tree`, bottom-up |
| Raw LLM connectivity | `ollama_chat` — one `POST` to `/api/chat`, `stream: False` |
| LLM makes one routing decision | `llm_choose` — titles/summaries only, id-based reply |
| Robust id extraction | `re.split` on whitespace or a pipe, first token, matched case-insensitively |
| Full traversal | `navigate` — descend while `node.children`, stop on `None` |
| Cross-reference resolution | `re.findall(r"see (Appendix \w+)", ...)` + `find_by_title` |
| Grounding enforcement | The two guardrail clauses inside `answer()`'s prompt |

## Gotchas reference

| Symptom | Cause | Fix |
| --- | --- | --- |
| Navigation silently stops one level too early | `llm_choose` returned `None` because no child summary was distinctive enough for the question | Tighten `summarize_tree`'s prompt, or add more specific section text |
| A reply like `n3-10-Onboarding` doesn't match any real id | Id scheme encodes something (stack depth, string length) the model has no reliable way to reproduce | Use plain sequential ids ([Step 5](06-llm-navigation-decision.md)) |
| A reply that echoes the whole option line back doesn't match the bare id | Comparing the full raw reply with `==` instead of extracting the first token | Split on whitespace/pipe and take the first token, not exact equality ([Step 5](06-llm-navigation-decision.md)) |
| The model answers confidently even when `context` is empty or irrelevant | No guardrail instruction in `answer()`'s prompt | Add "using ONLY the sections below" and "say so instead of guessing" ([Step 7](08-grounded-answers-and-wiring.md)) |
| Running the script twice re-does all the summarization work | Nothing caches the tree between runs | See Exercise 4 below |
| Cross-reference regex doesn't match | Document phrasing differs from "see Appendix X" | The pattern is intentionally narrow for this example — a real implementation would need a broader reference grammar |

## Discussion questions

1. `llm_choose` shows the LLM only a section's title and summary, never its full text, at every level except the leaf. What's the failure mode if a summary is misleading (accurate but pointing to the wrong conclusion), and how would you catch it?
2. `find_by_title` searches the *entire* tree for a cross-reference target, while the main descent only ever looks at the current node's direct children. Why is that asymmetry correct here, and when would it stop being correct (hint: what if two different chapters both had an "Appendix A")?
3. This app makes several sequential LLM calls per question (one per tree level navigated, one for the final answer) versus [../../rag-with-LlamaIndex/simple-rag-example](../../rag-with-LlamaIndex/simple-rag-example/README.md)'s one embed-and-lookup. At what corpus size or query volume would that latency difference start to matter in practice?
4. `navigate()` has no protection against a cross-reference cycle (Appendix A mentions Appendix B, which mentions Appendix A). What's the simplest change that would make it safe against that, without changing its two-tuple return type?
5. The guardrail clauses in `answer()`'s prompt are the entire defense against hallucination in this app. What's a scenario where a model might ignore them anyway, and what would you add to make grounding failures visible rather than silent?

## Exercises

Roughly ordered easiest to hardest:

1. **Change the questions.** Edit the `questions` list in `main()` to ask something the handbook doesn't cover at all (e.g. "What's the parental leave policy?") and observe whether the guardrail actually kicks in.
2. **Add a fourth section with its own cross-reference.** Add a new `## Security Policy` section that says "see Appendix B", plus an `## Appendix B` with real content, and confirm `navigate()` follows it without any code changes.
3. **Print the navigation decision at every level**, not just the final path — add a `print` inside `llm_choose` showing the full options list and the raw reply for each call, so you can watch every decision the model makes in real time.
4. **Cache the summarized tree.** Right now every run re-summarizes all nine sections. Serialize the tree to JSON after `summarize_tree` and reload it on the next run if the source file's mtime hasn't changed — this is the same "don't redo expensive work" idea as [../../rag-with-LlamaIndex/simple-rag-example-chromadb](../../rag-with-LlamaIndex/simple-rag-example-chromadb/README.md)'s persistence check, applied to summaries instead of embeddings.
5. **Add backtracking.** Right now a wrong turn near the root is permanent — `navigate()` has no way to say "that branch was wrong, try a different one." Change `llm_choose` to return a ranked list instead of one node, and have `navigate()` try the next-best option if the chosen leaf's text turns out not to actually answer the question.
6. **Rebuild `main.py` from a blank file, unaided.** The best test of whether the concepts stuck: close this walkthrough and rewrite it from memory, checking against [../pageindex-example/main.py](../pageindex-example/main.py) only at the end.

## What's next

Compare what you just built against [../../rag-with-LlamaIndex/simple-rag-example](../../rag-with-LlamaIndex/simple-rag-example/README.md) — the same policy/onboarding domain, answered by chunking and embedding instead of tree navigation. [../pageindex-example/README.md](../pageindex-example/README.md#benefit-over-the-llamaindex-example) lays out the concrete comparison; building both is the fastest way to feel where each approach wins. For the deeper conceptual background behind why tree navigation works (and where it doesn't), see [../vectorless-rag.md](../vectorless-rag.md) and [../pageindex-notes.md](../pageindex-notes.md).
