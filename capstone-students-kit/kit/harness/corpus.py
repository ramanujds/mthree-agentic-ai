from __future__ import annotations
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Doc:
    doc_id: str
    title: str
    status: str
    effective: str
    text: str                      # body without front matter
    meta: dict = field(default_factory=dict)
    sections: list[tuple[str, str]] = field(default_factory=list)   # (heading, body)


def load_corpus(corpus_dir) -> list[Doc]:
    docs = []
    for p in sorted(Path(corpus_dir).glob("*.md")):
        raw = p.read_text(encoding="utf-8")
        meta, body = {}, raw
        m = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.S)
        if m:
            for line in m.group(1).splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()
            body = m.group(2)
        sections, cur_h, cur = [], "", []
        for line in body.splitlines():
            if line.startswith("## "):
                if cur_h or "".join(cur).strip():
                    sections.append((cur_h, "\n".join(cur).strip()))
                cur_h, cur = line[3:].strip(), []
            else:
                cur.append(line)
        sections.append((cur_h, "\n".join(cur).strip()))
        docs.append(Doc(meta.get("doc_id", p.stem), meta.get("title", p.stem), meta.get("status", "current"),
                        meta.get("effective", ""), body.strip(), meta, sections))
    return docs
