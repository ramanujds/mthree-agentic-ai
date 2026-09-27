# Step 4 — Summarizing Sections

> [Back to index](README.md) · Previous: [Talking to Ollama](04-talking-to-ollama.md) · Next: [LLM Navigation Decision](06-llm-navigation-decision.md)

## Goal

Walk the tree bottom-up once and ask the LLM for a short summary of every section. This is this app's entire "index build" step — the one-time cost paid before any question is asked.

## Why this matters

In vector RAG, the equivalent one-time cost is embedding every chunk. Here, it's asking the LLM to compress every section down to a sentence. The reason this has to happen bottom-up (children before parents) is that a section with no text of its own — like `Onboarding`, which is just a heading with four sub-sections under it — has nothing to summarize *except* its children's titles. Summarizing a parent before its children would mean summarizing an empty string.

This summary is the **only thing** the LLM sees when deciding, later, which branch to descend into — not the full text. That's deliberate: showing full section text at every level of every decision would make navigation as expensive as just reading the whole document, defeating the purpose. A good one-sentence summary is what makes cheap, shallow decisions at each level possible.

## 1. Write `summarize_tree`

```python
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
```

The recursive call happens *first*, so by the time `basis` is computed for a parent, every child already has a `.summary` — though `basis` here actually falls back to child *titles* (not summaries) when a node has no text of its own, which is simpler and works fine for a tree this shallow. `basis[:1500]` caps how much text is sent per call; a real multi-hundred-page document's leaf sections would need this cap far more than the two-sentence sections in this example do.

## 2. Wire it up and print the result

```python
def main():
    root = parse_markdown_tree(DATA_FILE)
    summarize_tree(root)

    def show(node, indent=0):
        label = f"{node.title} -> {node.summary!r}" if node.summary else node.title
        print(" " * indent + label)
        for child in node.children:
            show(child, indent + 2)

    show(root)


if __name__ == "__main__":
    main()
```

## Try it

```bash
uv run main.py
```

This makes nine LLM calls (one per section with text or children), so it'll take a few seconds. Because it's a live model, your exact wording will differ from this — what matters is that every section gets a short, on-topic summary:

```
Company Handbook -> 'Company policies for remote work, vacation, expenses, and onboarding.'
  Remote Work Policy -> 'Remote work allowed up to 3 days per week with approval.'
  Vacation Policy -> 'Employees accrue 18 days of paid vacation, with carryover limit.'
  Expense Reimbursement -> 'Employees can be reimbursed for business expenses with receipts.'
  Onboarding -> 'Basic setup and access to laptop and internal tools.'
    Getting a laptop -> 'New hires receive laptop on first day, IT delivers or contacts it-support.'
    Setting up email -> 'Email account created before start date with setup instructions.'
    Point of contact -> 'Onboarding buddy contacts you on your first day.'
    Internal tool access -> 'Access granted within 24 hours of start date.'
  Appendix A: Team Exceptions -> 'Remote work allowed for sales and engineers during certain periods.'
```

Notice `Onboarding`'s summary is about setup and access in general — built entirely from its children's titles, since `Onboarding` itself has no body text of its own.

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
                node = Node(id=f"n{len(stack)}-{len(title)}-{title[:15]}", title=title)
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


def main():
    root = parse_markdown_tree(DATA_FILE)
    summarize_tree(root)

    def show(node, indent=0):
        label = f"{node.title} -> {node.summary!r}" if node.summary else node.title
        print(" " * indent + label)
        for child in node.children:
            show(child, indent + 2)

    show(root)


if __name__ == "__main__":
    main()
```

</details>

## Common mistakes

| Symptom | Cause | Fix |
| --- | --- | --- |
| `Onboarding`'s summary is empty | The `for child in node.children: summarize_tree(child)` recursive call was placed after computing `basis` instead of before | Recursion must happen first — a parent needs its children summarized before it can fall back to them |
| Every summary is a generic restatement of the whole document | `basis[:1500]` sliced across multiple sections' text by accident | Confirm `node.text` holds only that section's own text, not the whole file (check [Step 2](03-building-the-tree.md)'s `flush_text`) |
| This step takes much longer than expected | Normal for the first call in a session (model load), or a very slow machine | Later steps reuse the same warm model and are faster |

Next: **[LLM Navigation Decision](06-llm-navigation-decision.md)** — use these summaries to have the LLM actually choose a branch, and watch a real bug in how it replies.
