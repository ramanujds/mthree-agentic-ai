# Step 5 — LLM Navigation Decision

> [Back to index](README.md) · Previous: [Summarizing Sections](05-summarizing-sections.md) · Next: [The Navigation Loop](07-the-navigation-loop.md)

## Goal

Have the LLM pick which child section is most likely to answer a question, using only titles and summaries — and inspect the raw decision before trusting it with anything.

## Why this matters

This is the single most important step in the whole walkthrough, and the one most likely to bite you if you skip straight to a "final" version. The plan sounds simple: show the LLM a numbered list of `id | title | summary` options, ask it to reply with the winning `id`, and match that reply against the ids. In practice, an instruction like "reply with ONLY the id" is a *request*, not a guarantee — the model can and will reply with something close-but-not-exact, and if your matching logic assumes exactness, navigation silently breaks. You're about to watch that happen twice, for two different reasons, and fix both.

## 1. First attempt: match the LLM's reply against the id, exactly

```python
def llm_choose(question: str, children: list[Node]) -> Node | None:
    """Ask the LLM which child section to descend into -- titles/summaries only."""
    options = "\n".join(f"{c.id} | {c.title} | {c.summary}" for c in children)
    prompt = (
        f"Question: {question}\n"
        "You are navigating a document's table of contents.\n"
        f"Options (id | title | summary):\n{options}\n"
        "Reply with ONLY the id most likely to contain the answer, or NONE."
    )
    choice = ollama_chat(prompt).strip()
    print(f"  (raw LLM reply: {choice!r})")  # temporary -- see exactly what comes back
    return next((c for c in children if c.id == choice), None)
```

Try it against the tree's current ids (still the `n{depth}-{len}-{title[:15]}` scheme from Steps 2–4):

```python
def main():
    root = parse_markdown_tree(DATA_FILE)
    summarize_tree(root)

    question = "How do I get a laptop as a new hire?"
    choice = llm_choose(question, root.children)
    print(f"Q: {question}")
    print(f"Chosen: {choice.title if choice else None}")


if __name__ == "__main__":
    main()
```

## Try it

```bash
uv run main.py
```

A real run of this produced:

```
  (raw LLM reply: 'n3-10-Onboarding')
Q: How do I get a laptop as a new hire?
Chosen: None
```

The actual id for `Onboarding` is `n2-10-Onboarding` (depth 2, not 3) — the model got extremely close, close enough that a human skimming the options list would recognize what it meant, but not exact. Because the id encodes a detail (`len(stack)`) with no semantic meaning to the model, it has nothing reliable to *copy* — it's reconstructing a string that merely looks like the right shape, and gets one digit wrong. `Chosen: None` means navigation would silently stop right here, with no error and no obvious sign anything went wrong.

## 2. The id scheme is the real problem — make ids trivial to copy

The fix isn't smarter matching. It's giving the model an id so simple there's nothing to get wrong: a plain sequential number, assigned once per node as the tree is built.

```python
import itertools
```

```python
def parse_markdown_tree(path: str) -> Node:
    """Turn a markdown file's heading structure into a tree. No chunking."""
    ids = itertools.count(1)
    root = Node(id="0", title="Document")
    stack: list[tuple[int, Node]] = [(0, root)]
    buffer: list[str] = []
    seen_h1 = False

    def flush_text():
        stack[-1][1].text = "\n".join(buffer).strip()
        buffer.clear()

    with open(path) as f:
        for line in f:
            heading = re.match(r"^(#+)\s+(.*)", line)
            if heading:
                flush_text()
                level, title = len(heading.group(1)), heading.group(2).strip()
                if level == 1 and not seen_h1:
                    # the document's own H1 names the root instead of nesting under it
                    root.title = title
                    stack = [(1, root)]
                    seen_h1 = True
                    continue
                # short sequential ids -- an LLM can copy "3" back verbatim far
                # more reliably than a string it has to reproduce exactly
                node = Node(id=str(next(ids)), title=title)
                while stack[-1][0] >= level:
                    stack.pop()
                stack[-1][1].children.append(node)
                stack.append((level, node))
            else:
                buffer.append(line.rstrip())
    flush_text()
    return root
```

## Try it

Same `main()` as before, still with the exact-match `llm_choose`:

```bash
uv run main.py
```

A real run of this produced:

```
  (raw LLM reply: '4 | Onboarding | Setting up laptop and email for internal tool access.')
Q: How do I get a laptop as a new hire?
Chosen: None
```

Progress and a new problem, both visible in one line. The id is now correct — `4` really is `Onboarding`'s id — but the model didn't reply with just `4`; it echoed the *entire option line* back, id and all. `choice.strip()` doesn't help, because the extra text is in the middle of the string, not the edges. Exact-match id comparison is too strict for a model that treats "reply with ONLY X" as a strong suggestion rather than a hard constraint.

## 3. Exact match is still too strict — extract just the id token

```python
def llm_choose(question: str, children: list[Node]) -> Node | None:
    """Ask the LLM which child section to descend into -- titles/summaries only."""
    options = "\n".join(f"{c.id} | {c.title} | {c.summary}" for c in children)
    prompt = (
        f"Question: {question}\n"
        "You are navigating a document's table of contents.\n"
        f"Options (id | title | summary):\n{options}\n"
        "Reply with ONLY the id most likely to contain the answer, or NONE."
    )
    raw = ollama_chat(prompt).strip()
    # the model sometimes echoes the whole "id | title | summary" line back
    # instead of just the id -- take the first token, matched case-insensitively
    choice = re.split(r"[\s|]", raw, maxsplit=1)[0] if raw else raw
    return next((c for c in children if c.id.lower() == choice.lower()), None)
```

Instead of trusting the whole reply to be exactly the id, this takes only the first whitespace-or-pipe-delimited token — which is the id whether the model replies `4`, `4 | Onboarding`, or the entire line. The case-insensitive compare is a small bonus safety margin for the `NONE` case.

## Try it

Drop the temporary debug print from `main()` (it did its job) and run again:

```python
def main():
    root = parse_markdown_tree(DATA_FILE)
    summarize_tree(root)

    question = "How do I get a laptop as a new hire?"
    choice = llm_choose(question, root.children)
    print(f"Q: {question}")
    print(f"Chosen: {choice.title if choice else None}")


if __name__ == "__main__":
    main()
```

```bash
uv run main.py
```

```
Q: How do I get a laptop as a new hire?
Chosen: Onboarding
```

Correct, and robust to however much extra text the model decides to add.

## Checkpoint

<details>
<summary>Full <code>main.py</code></summary>

```python
"""
PageIndex-style vectorless RAG example.

No vector database, no embeddings, no RAG framework: the document is parsed
into a hierarchical tree (title + LLM summary + text per section), and the
LLM navigates that tree directly -- descending one heading level at a time,
then following any "see Appendix X" cross-reference -- instead of a
similarity search over chunks. Only stdlib + a local Ollama endpoint.
"""

import itertools
import json
import os
import re
import urllib.request
from dataclasses import dataclass, field

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.environ.get("OLLAMA_LLM_MODEL", "llama3:8b")
DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "company_handbook.md")


@dataclass
class Node:
    id: str
    title: str
    summary: str = ""
    text: str = ""
    children: list["Node"] = field(default_factory=list)


def ollama_chat(prompt: str) -> str:
    payload = {
        "model": LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }
    req = urllib.request.Request(
        f"{OLLAMA_BASE_URL}/api/chat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())["message"]["content"].strip()


def parse_markdown_tree(path: str) -> Node:
    """Turn a markdown file's heading structure into a tree. No chunking."""
    ids = itertools.count(1)
    root = Node(id="0", title="Document")
    stack: list[tuple[int, Node]] = [(0, root)]
    buffer: list[str] = []
    seen_h1 = False

    def flush_text():
        stack[-1][1].text = "\n".join(buffer).strip()
        buffer.clear()

    with open(path) as f:
        for line in f:
            heading = re.match(r"^(#+)\s+(.*)", line)
            if heading:
                flush_text()
                level, title = len(heading.group(1)), heading.group(2).strip()
                if level == 1 and not seen_h1:
                    # the document's own H1 names the root instead of nesting under it
                    root.title = title
                    stack = [(1, root)]
                    seen_h1 = True
                    continue
                # short sequential ids -- an LLM can copy "3" back verbatim far
                # more reliably than a string it has to reproduce exactly
                node = Node(id=str(next(ids)), title=title)
                while stack[-1][0] >= level:
                    stack.pop()
                stack[-1][1].children.append(node)
                stack.append((level, node))
            else:
                buffer.append(line.rstrip())
    flush_text()
    return root


def summarize_tree(node: Node) -> None:
    """Bottom-up, one-time LLM pass: give every section a short summary."""
    for child in node.children:
        summarize_tree(child)
    basis = node.text or " / ".join(c.title for c in node.children)
    if basis:
        node.summary = ollama_chat(
            "Summarize this document section in under 12 words. "
            f"Reply with only the summary, no preamble:\n\n{basis[:1500]}"
        )


def llm_choose(question: str, children: list[Node]) -> Node | None:
    """Ask the LLM which child section to descend into -- titles/summaries only."""
    options = "\n".join(f"{c.id} | {c.title} | {c.summary}" for c in children)
    prompt = (
        f"Question: {question}\n"
        "You are navigating a document's table of contents.\n"
        f"Options (id | title | summary):\n{options}\n"
        "Reply with ONLY the id most likely to contain the answer, or NONE."
    )
    raw = ollama_chat(prompt).strip()
    # the model sometimes echoes the whole "id | title | summary" line back
    # instead of just the id -- take the first token, matched case-insensitively
    choice = re.split(r"[\s|]", raw, maxsplit=1)[0] if raw else raw
    return next((c for c in children if c.id.lower() == choice.lower()), None)


def main():
    root = parse_markdown_tree(DATA_FILE)
    summarize_tree(root)

    question = "How do I get a laptop as a new hire?"
    choice = llm_choose(question, root.children)
    print(f"Q: {question}")
    print(f"Chosen: {choice.title if choice else None}")


if __name__ == "__main__":
    main()
```

</details>

## Common mistakes

| Symptom | Cause | Fix |
| --- | --- | --- |
| `Chosen: None` even after switching to sequential ids | Still comparing with `==` instead of extracting the first token | Confirm `llm_choose` splits on whitespace/pipe and takes the first token, not a raw equality check |
| Sequential ids collide across a large document | Multiple `parse_markdown_tree` calls, each starting a fresh `itertools.count(1)` | Build the tree once and reuse it — don't re-parse per question |
| The model sometimes answers a question with the wrong section entirely | Summaries are too vague or too similar to distinguish sections | Tighten the summarization prompt in [Step 4](05-summarizing-sections.md), or add a sentence of section-specific detail |
| `NONE` is chosen even when a section is clearly relevant | The model is being conservative given ambiguous phrasing | Expected sometimes — this is exactly what [Step 6](07-the-navigation-loop.md)'s `if nxt is None: break` exists to handle gracefully |

Next: **[The Navigation Loop](07-the-navigation-loop.md)** — use `llm_choose` repeatedly to descend the whole tree, then follow cross-references.
