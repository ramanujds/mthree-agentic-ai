# Step 6 — The Navigation Loop

> [Back to index](README.md) · Previous: [LLM Navigation Decision](06-llm-navigation-decision.md) · Next: [Grounded Answers and Wiring](08-grounded-answers-and-wiring.md)

## Goal

Call `llm_choose` repeatedly to descend the whole tree from root to leaf, then follow any "see Appendix X" cross-reference the leaf's text contains.

## Why this matters

`llm_choose` decides one level at a time; it has no idea how deep the tree is or when to stop. `navigate()` is the loop that turns single decisions into a full traversal — and cross-reference following is the one capability a vector-similarity retriever cannot replicate no matter how good its embeddings are: "see Appendix A" is a literal instruction to go read something else, and this app can just... do that, deterministically, every time.

## 1. Descend the tree, one level per turn

```python
def navigate(question: str, root: Node) -> tuple[list[str], list[tuple[str, str]]]:
    path, node = [root.title], root
    while node.children:
        nxt = llm_choose(question, node.children)
        if nxt is None:
            break
        node = nxt
        path.append(node.title)

    context = [(node.title, node.text)]
    return path, context
```

`while node.children` is the entire stopping condition: keep descending as long as the current node has somewhere further to go. `if nxt is None: break` handles the case from [Step 5](06-llm-navigation-decision.md) where the model isn't confident any child is relevant — rather than force a wrong turn, navigation just stops at the best node found so far, which is safer than guessing.

Wire it up:

```python
def main():
    root = parse_markdown_tree(DATA_FILE)
    summarize_tree(root)

    question = "How many days can I work remotely per week?"
    path, context = navigate(question, root)
    print(f"Q: {question}")
    print(f"Path: {' / '.join(path)}")
    for title, text in context:
        print(f"[{title}] {text}")


if __name__ == "__main__":
    main()
```

## Try it

```bash
uv run main.py
```

```
Q: How many days can I work remotely per week?
Path: Company Handbook / Remote Work Policy
[Remote Work Policy] Employees may work remotely up to 3 days per week, subject to manager
approval. Requests must be submitted at least 2 business days in advance
through the HR portal. For team-specific exceptions, see Appendix A.
```

The navigation correctly lands on `Remote Work Policy` — but look at the retrieved text: it says "see Appendix A", and nothing here does anything about that yet. A reader would follow that reference automatically; the code should too.

## 2. Follow cross-references

```python
def find_by_title(root: Node, title_fragment: str) -> Node | None:
    if title_fragment.lower() in root.title.lower():
        return root
    for child in root.children:
        if (hit := find_by_title(child, title_fragment)):
            return hit
    return None
```

```python
def navigate(question: str, root: Node) -> tuple[list[str], list[tuple[str, str]]]:
    path, node = [root.title], root
    while node.children:
        nxt = llm_choose(question, node.children)
        if nxt is None:
            break
        node = nxt
        path.append(node.title)

    context = [(node.title, node.text)]
    for ref in re.findall(r"see (Appendix \w+)", node.text, re.IGNORECASE):
        target = find_by_title(root, ref)
        if target:
            path.append(f"-> {target.title}")
            context.append((target.title, target.text))
    return path, context
```

`find_by_title` is a small recursive search over the *whole* tree (not just the current branch) — a cross-reference can point anywhere, so the lookup has to be global, unlike the strictly top-down descent in the main loop. `re.findall(r"see (Appendix \w+)", ...)` scans the leaf's own text for the reference pattern; every match found gets resolved and appended to both `path` (so the navigation trail shows it was followed) and `context` (so its text is available for the final answer).

## Try it

Same `main()`, no changes needed there:

```bash
uv run main.py
```

```
Q: How many days can I work remotely per week?
Path: Company Handbook / Remote Work Policy / -> Appendix A: Team Exceptions
[Remote Work Policy] Employees may work remotely up to 3 days per week, subject to manager
approval. Requests must be submitted at least 2 business days in advance
through the HR portal. For team-specific exceptions, see Appendix A.
[Appendix A: Team Exceptions] Sales team members may work remotely up to 5 days per week during Q4 to
support year-end client travel, with manager approval.

Engineers on the on-call rotation may work remotely full-time during
their on-call week, regardless of the standard 3-day limit.
```

`Path:` now shows the cross-reference being followed explicitly, and `context` carries both sections' text — everything the next step needs to answer questions that span the base policy *and* its exceptions.

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


def find_by_title(root: Node, title_fragment: str) -> Node | None:
    if title_fragment.lower() in root.title.lower():
        return root
    for child in root.children:
        if (hit := find_by_title(child, title_fragment)):
            return hit
    return None


def navigate(question: str, root: Node) -> tuple[list[str], list[tuple[str, str]]]:
    path, node = [root.title], root
    while node.children:
        nxt = llm_choose(question, node.children)
        if nxt is None:
            break
        node = nxt
        path.append(node.title)

    context = [(node.title, node.text)]
    for ref in re.findall(r"see (Appendix \w+)", node.text, re.IGNORECASE):
        target = find_by_title(root, ref)
        if target:
            path.append(f"-> {target.title}")
            context.append((target.title, target.text))
    return path, context


def main():
    root = parse_markdown_tree(DATA_FILE)
    summarize_tree(root)

    question = "How many days can I work remotely per week?"
    path, context = navigate(question, root)
    print(f"Q: {question}")
    print(f"Path: {' / '.join(path)}")
    for title, text in context:
        print(f"[{title}] {text}")


if __name__ == "__main__":
    main()
```

</details>

## Common mistakes

| Symptom | Cause | Fix |
| --- | --- | --- |
| Cross-reference never gets followed | Regex `r"see (Appendix \w+)"` doesn't match the document's actual phrasing | Confirm `company_handbook.md` says "see Appendix A" (case doesn't matter — `re.IGNORECASE` is set) |
| `find_by_title` returns the wrong node | Two sections share a substring in their titles (e.g. both contain "Appendix") | `find_by_title` does a substring match, not exact — fine for this small handbook, but a larger document would need a stricter check |
| Navigation loops forever | A cycle in cross-references (A refers to B, B refers back to A) | Not handled here — `context` would keep growing; a real implementation should track visited nodes |
| `Path:` stops at the root immediately | `llm_choose` returned `None` at the very first level | Expected if the question is genuinely ambiguous at the root — see [Step 5](06-llm-navigation-decision.md)'s common mistakes |

Next: **[Grounded Answers and Wiring](08-grounded-answers-and-wiring.md)** — turn `context` into an actual answer, and run all three questions end to end.
