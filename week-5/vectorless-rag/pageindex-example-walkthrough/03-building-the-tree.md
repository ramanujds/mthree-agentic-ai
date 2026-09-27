# Step 2 — Building the Tree

> [Back to index](README.md) · Previous: [Environment Setup](02-environment-setup.md) · Next: [Talking to Ollama](04-talking-to-ollama.md)

## Goal

Parse `company_handbook.md`'s heading structure into a `Node` tree — no chunking, no LLM calls yet — and see, live, why the document's own top-level heading needs special handling.

## Why this matters

Every other RAG approach in this repo turns a document into a flat list of same-sized chunks. This one turns it into a tree that mirrors the document's *own* structure: an H1 is the root, each H2 is a section, each H3 under it is a sub-section. Nothing is split mid-sentence and nothing needs a chunk-size parameter, because the boundaries are the ones the document's author already chose.

## 1. Add the imports and the `Node` type

```python
import re
from dataclasses import dataclass, field
```

```python
@dataclass
class Node:
    id: str
    title: str
    summary: str = ""
    text: str = ""
    children: list["Node"] = field(default_factory=list)
```

A `Node` is deliberately plain: a title and summary for navigation, the raw `text` for when it's actually read, and `children` for descending further. `id` exists purely so the LLM has something short to answer with later — you'll see exactly why its shape matters in [Step 5](06-llm-navigation-decision.md).

## 2. A first (naive) parser

The plan: walk the file line by line, and whenever a line looks like a heading (`#`, `##`, `###`, ...), start a new `Node` at that heading's level, nested under whatever heading is currently open at a shallower level.

```python
def parse_markdown_tree(path: str) -> Node:
    """Turn a markdown file's heading structure into a tree. No chunking."""
    root = Node(id="0", title="Document")
    stack: list[tuple[int, Node]] = [(0, root)]
    buffer: list[str] = []

    def flush_text():
        stack[-1][1].text = "\n".join(buffer).strip()
        buffer.clear()

    with open(path) as f:
        for line in f:
            heading = re.match(r"^(#+)\s+(.*)", line)
            if heading:
                flush_text()
                level, title = len(heading.group(1)), heading.group(2).strip()
                node = Node(id=f"n{len(stack)}-{len(title)}-{title[:15]}", title=title)
                while stack[-1][0] >= level:
                    stack.pop()
                stack[-1][1].children.append(node)
                stack.append((level, node))
            else:
                buffer.append(line.rstrip())
    flush_text()
    return root
```

`stack` always holds the chain of currently-open headings, from the root down. Seeing a new heading pops anything at the same level or deeper (those sections are now closed), then nests the new node under whatever is left — that's the entire "hierarchy" logic. Text between headings accumulates in `buffer` and gets attached to whichever node was open (`flush_text`) right before the next heading starts.

Wire up a temporary way to see the tree, so you can check the structure before doing anything else with it:

```python
def main():
    root = parse_markdown_tree(DATA_FILE)

    def show(node, indent=0):
        print(" " * indent + f"{node.title} ({len(node.text)} chars)")
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

Output:

```
Document (0 chars)
  Company Handbook (0 chars)
    Remote Work Policy (211 chars)
    Vacation Policy (215 chars)
    Expense Reimbursement (232 chars)
    Onboarding (0 chars)
      Getting a laptop (139 chars)
      Setting up email (140 chars)
      Point of contact (135 chars)
      Internal tool access (107 chars)
    Appendix A: Team Exceptions (256 chars)
```

Look closely: there's an extra, meaningless `Document` node wrapping the real root, `Company Handbook`. That's because the file's own `# Company Handbook` heading was treated like any other heading — a *child* node — instead of naming the tree's root. It's a real bug: every navigation path later would start with a pointless extra hop.

## 3. Fix it: let the file's own H1 name the root

```python
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
```

The first time a level-1 heading is seen, it renames `root` in place and resets the stack to treat the root as already "open" at level 1 — every subsequent heading nests under it normally. Any *later* H1 (a document with more than one top-level heading) would still be treated as a new top-level sibling, which is the right behavior for a multi-chapter document.

## Try it

```bash
uv run main.py
```

Output:

```
Company Handbook (0 chars)
  Remote Work Policy (211 chars)
  Vacation Policy (215 chars)
  Expense Reimbursement (232 chars)
  Onboarding (0 chars)
    Getting a laptop (139 chars)
    Setting up email (140 chars)
    Point of contact (135 chars)
    Internal tool access (107 chars)
  Appendix A: Team Exceptions (256 chars)
```

No wrapper node. `Company Handbook` is the root, its five `##` sections are direct children, and the four `###` onboarding sub-sections nest correctly one level deeper. This is the actual navigable shape the rest of the app depends on.

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

import os
import re
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


def main():
    root = parse_markdown_tree(DATA_FILE)

    def show(node, indent=0):
        print(" " * indent + f"{node.title} ({len(node.text)} chars)")
        for child in node.children:
            show(child, indent + 2)

    show(root)


if __name__ == "__main__":
    main()
```

</details>

Note: `Node.id` is built from the stack depth, the title's length, and a truncated title (`f"n{len(stack)}-{len(title)}-{title[:15]}"`) — unique enough for Python code to work with today. It looks descriptive, which feels like a good thing. [Step 5](06-llm-navigation-decision.md) shows why it's actually a trap once an LLM has to reproduce it exactly.

## Common mistakes

| Symptom | Cause | Fix |
| --- | --- | --- |
| `FileNotFoundError` on `company_handbook.md` | `DATA_FILE` path is wrong, or the file wasn't created under `data/` | Confirm `data/company_handbook.md` exists relative to `main.py` |
| Every section shows `(0 chars)` | Regex `^(#+)\s+(.*)` isn't matching, or the file has no body text between headings | Check for a literal `#` followed by a space in each heading line |
| `Onboarding` sub-sections appear as siblings of `Onboarding`, not children | An `###` heading was written as `##` (wrong level) in the data file | Confirm heading levels in `company_handbook.md` match the walkthrough exactly |

Next: **[Talking to Ollama](04-talking-to-ollama.md)** — add the one function every later step depends on: a raw call to the local LLM.
