# Step 7 — Grounded Answers and Wiring

> [Back to index](README.md) · Previous: [The Navigation Loop](07-the-navigation-loop.md) · Next: [Recap and Exercises](09-recap-and-exercises.md)

## Goal

Turn `navigate()`'s retrieved sections into an actual answer, then wire everything together into the finished `main()` that asks all three questions.

## Why this matters

Retrieval and generation are two separate steps, and it's worth keeping them separate in your head even though they run back to back: `navigate()`'s only job is finding the right text; `answer()`'s only job is answering *from* that text. The prompt in `answer()` is where grounding actually gets enforced — nothing before this point stops the model from ignoring the retrieved sections and answering from its own memorized knowledge instead. If navigation ever comes up empty (a bug, an unanswerable question, a document that genuinely doesn't cover something), an ungrounded model will still confidently produce something that *sounds* right. That's not hypothetical: earlier in this exact build, before the [Step 5](06-llm-navigation-decision.md) id-matching fix was in place, a broken `llm_choose` caused navigation to stop at the root with no real section text — and the model answered anyway:

```
Q: How do I get a laptop as a new hire?
Path: Company Handbook
A: According to the [Company Handbook], new hires are provided with a
company-issued laptop as part of their onboarding process.
(Section: Onboarding and Technology)
```

There is no "Onboarding and Technology" section anywhere in `company_handbook.md`. The model invented a plausible-sounding citation because it was never told it was allowed to say "I don't know." The instruction you're about to add exists specifically to prevent that.

## 1. Write `answer`

```python
def answer(question: str, context: list[tuple[str, str]]) -> str:
    grounding = "\n\n".join(f"[{title}]\n{text}" for title, text in context)
    prompt = (
        "Answer the question using ONLY the sections below. Cite the section "
        "title(s) you used. If the sections don't contain the answer, say so "
        f"instead of guessing.\n\nSections:\n{grounding}\n\nQuestion: {question}"
    )
    return ollama_chat(prompt)
```

The "using ONLY the sections below" and "if the sections don't contain the answer, say so instead of guessing" clauses are doing the actual grounding work. Neither one is enforced by anything else in this code — they're the entire defense against the hallucination shown above, and they're cheap insurance even after fixing the underlying navigation bug, since a *different* future bug (or a genuinely unanswerable question) could produce empty context again.

## 2. Wire it into `main()` and ask all three questions

```python
def main():
    root = parse_markdown_tree(DATA_FILE)
    summarize_tree(root)

    questions = [
        "How many days can I work remotely per week?",
        "How do I get a laptop as a new hire?",
        "Can the sales team work remotely more than the standard policy allows?",
    ]

    for question in questions:
        path, context = navigate(question, root)
        response = answer(question, context)
        print(f"Q: {question}")
        print(f"Path: {' / '.join(path)}")
        print(f"A: {response}")
        print("-" * 60)


if __name__ == "__main__":
    main()
```

The third question is the one this whole example is built around: the answer requires both `Remote Work Policy` (the 3-day cap) and `Appendix A` (the sales exception), connected only by the cross-reference `navigate()` follows automatically.

## Try it

```bash
uv run main.py
```

This makes roughly a dozen LLM calls total (9 for summarization, 1–2 per question for navigation, 1 per question for the answer), so it takes a while. Wording will vary run to run since every reply comes from a live model — what should stay consistent is which sections each `Path:` resolves to, and that every answer is actually grounded in retrieved text rather than invented. A real run produced:

```
Q: How many days can I work remotely per week?
Path: Company Handbook / Remote Work Policy / -> Appendix A: Team Exceptions
A: I used the [Remote Work Policy] section to answer this question.

According to the policy, employees may work remotely up to 3 days per week, subject to manager approval.
------------------------------------------------------------
Q: How do I get a laptop as a new hire?
Path: Company Handbook / Onboarding / Getting a laptop
A: According to the section "Getting a laptop", new hires receive a laptop on their first day, shipped by the IT department.
------------------------------------------------------------
Q: Can the sales team work remotely more than the standard policy allows?
Path: Company Handbook / Appendix A: Team Exceptions
A: According to [Appendix A: Team Exceptions], Sales team members may work remotely up to 5 days per week during Q4 to support year-end client travel, with manager approval. This implies that the sales team can work remotely more than the standard policy allows, specifically up to 5 days per week during Q4.
------------------------------------------------------------
```

Notice the third question's `Path:` goes straight to `Appendix A` without visiting `Remote Work Policy` first — the navigation summaries were distinctive enough that the model picked the right leaf directly. Either path (direct, or via the cross-reference) is a correct outcome; what matters is that the answer is grounded in real section text either way.

## Checkpoint

This matches [../pageindex-example/main.py](../pageindex-example/main.py) exactly.

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


def answer(question: str, context: list[tuple[str, str]]) -> str:
    grounding = "\n\n".join(f"[{title}]\n{text}" for title, text in context)
    prompt = (
        "Answer the question using ONLY the sections below. Cite the section "
        "title(s) you used. If the sections don't contain the answer, say so "
        f"instead of guessing.\n\nSections:\n{grounding}\n\nQuestion: {question}"
    )
    return ollama_chat(prompt)


def main():
    root = parse_markdown_tree(DATA_FILE)
    summarize_tree(root)

    questions = [
        "How many days can I work remotely per week?",
        "How do I get a laptop as a new hire?",
        "Can the sales team work remotely more than the standard policy allows?",
    ]

    for question in questions:
        path, context = navigate(question, root)
        response = answer(question, context)
        print(f"Q: {question}")
        print(f"Path: {' / '.join(path)}")
        print(f"A: {response}")
        print("-" * 60)


if __name__ == "__main__":
    main()
```

</details>

## Common mistakes

| Symptom | Cause | Fix |
| --- | --- | --- |
| Answer cites a section that isn't in `context` | The guardrail clause was dropped from the `answer()` prompt | Confirm the "using ONLY the sections below" and "say so instead of guessing" clauses are both present |
| Answer to the sales-team question ignores the 3-day standard policy | Navigation went straight to `Appendix A` without visiting `Remote Work Policy`, so `context` only has the exception, not the baseline | Not actually wrong — the model has the exception's own text, which already states the number; if you want both sections guaranteed, force a root-level visit before descending |
| Script is slow every single run, not just the first | Summarization runs on every `uv run main.py`, since nothing caches the tree | Expected in this example — see [Step 9](09-recap-and-exercises.md)'s exercises for adding a cache |
| `KeyError` or crash mid-way through the three questions | An HTTP call to Ollama timed out or failed transiently | Re-run; consider raising `timeout` in `ollama_chat` if it happens consistently |

Next: **[Recap and Exercises](09-recap-and-exercises.md)**.
