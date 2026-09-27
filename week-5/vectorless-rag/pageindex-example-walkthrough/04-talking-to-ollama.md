# Step 3 — Talking to Ollama

> [Back to index](README.md) · Previous: [Building the Tree](03-building-the-tree.md) · Next: [Summarizing Sections](05-summarizing-sections.md)

## Goal

Add one function, `ollama_chat`, that sends a prompt to the local Ollama server and returns the model's reply as a plain string. Every remaining step in this app — summarizing, navigating, answering — is built entirely on top of this one function.

## Why this matters

Every other example in this repo's RAG series reaches an LLM through a framework client (`llama_index.llms.ollama.Ollama`, for instance), which hides the actual HTTP request being made. This app makes that request directly: Ollama exposes a plain HTTP API, and a chat completion is nothing more than a `POST` with a JSON body and a JSON response. Seeing that directly is worth the few extra lines — it's also exactly why this app can get away with zero third-party dependencies: `urllib.request` (stdlib) is enough to talk to any local HTTP service.

## 1. Add the imports

```python
import json
import os
import re
import urllib.request
from dataclasses import dataclass, field
```

## 2. Write `ollama_chat`

```python
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
```

`stream: False` matters: Ollama's default is to stream the response back as a sequence of partial JSON objects, one per token. That's the right shape for a typical chat UI, but this app just wants one complete string back per call — setting `stream: False` makes Ollama do the buffering for you and return a single JSON object instead of a stream you'd otherwise have to reassemble yourself.

## 3. Smoke-test it before building anything on top of it

Temporarily replace `main()`'s body:

```python
def main():
    print(ollama_chat("Reply with exactly the words: Ollama is working."))


if __name__ == "__main__":
    main()
```

## Try it

```bash
uv run main.py
```

Expected output (the model may not follow "exactly" to the letter — that inexactness is itself worth noticing, and comes back in [Step 5](06-llm-navigation-decision.md)):

```
Ollama is working.
```

If you see this, every later step's LLM calls will work the same way — same function, different prompts.

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


def main():
    print(ollama_chat("Reply with exactly the words: Ollama is working."))


if __name__ == "__main__":
    main()
```

</details>

## Common mistakes

| Symptom | Cause | Fix |
| --- | --- | --- |
| `URLError: [Errno 61] Connection refused` | Ollama isn't running | Start it, then re-run |
| `json.decoder.JSONDecodeError` | `stream` left as the default (`True`) or omitted | Confirm `"stream": False` is in the payload |
| `KeyError: 'message'` | Wrong endpoint (`/api/generate` instead of `/api/chat`) or a malformed payload | Confirm the URL is `{OLLAMA_BASE_URL}/api/chat` and the payload has a `messages` list |
| Request hangs for a long time on first call | Ollama is loading the model into memory | Expected once per session; increase `timeout` if it's genuinely too short for your machine |

Next: **[Summarizing Sections](05-summarizing-sections.md)** — use `ollama_chat` to give every section a short summary, the one-time cost of building this index.
