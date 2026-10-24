"""Offline stand-ins for an LLM. Zero cost, deterministic, no network.

Message format (OpenAI-style, simplified):
  {"role": "system"|"user"|"assistant"|"tool", "content": str|None,
   "tool_calls": [{"id","name","arguments":dict}]   # assistant only
   "tool_call_id": str, "name": str}                # tool only
chat(messages, tools) -> assistant message dict (+ "usage": {"tokens_in","tokens_out"}).
`tools` is a list of {"name","description","parameters"} specs; RuleLLM only calls tools that are offered.
"""
from __future__ import annotations
import json, re
from . import DATA_DIR, faults
from .text import count_tokens, tokenize

ACC = re.compile(r"ACC-\d{4}")
BEN = re.compile(r"BEN-\d+")
INJ = re.compile(r"(ignore|disregard|forget)\b[^.]{0,30}\b(previous|prior|above|earlier)\b[^.]{0,20}\b(instruction|direction|rule)s?", re.I)
FEE_WORDS = {"international wire": "international_wire", "domestic wire": "domestic_wire", "incoming wire": "incoming_wire",
             "wire recall": "wire_recall", "stop payment": "stop_payment", "overdraft": "overdraft",
             "paper statement": "paper_statement", "card replacement": "card_replacement", "excess withdrawal": "excess_withdrawal"}


def _usage(messages, out_text):
    tin = sum(count_tokens(str(m.get("content") or "")) for m in messages)
    m = faults.token_multiplier()
    return {"tokens_in": tin * m, "tokens_out": count_tokens(out_text) * m}


class RuleLLM:
    """A deterministic rule-based 'model': picks tools from keywords, then writes a templated/extractive final answer.
    It is deliberately NAIVE: it obeys instructions that appear inside tool output (prompt injection) so that the Week 7
    red-team lab can be done offline. It follows ONE system-prompt directive: if the system prompt contains the word
    'cite', the final answer ends with a 'Sources:' line."""
    name = "rule-llm"

    def _plan(self, q: str, offered: set[str]) -> list[tuple[str, dict]]:
        ql, accs = q.lower(), ACC.findall(q)
        acc = accs[0] if accs else ""
        plan: list[tuple[str, dict]] = []
        amt = re.search(r"\$\s?([\d,]+(?:\.\d+)?)", q)
        ben = BEN.search(q)
        is_transfer = bool(re.search(r"\b(transfer|send|move)\b", ql) and amt and ben)
        wants_fee = any(w in ql for w in ("fee", "cost", "charge", "how much", "price"))
        fee_type = next((v for k, v in FEE_WORDS.items() if k in ql), None)
        is_escalate = any(w in ql for w in ("escalate", "fraud", "complain"))
        if is_transfer and "initiate_transfer" in offered:
            plan.append(("initiate_transfer", {"from_account": acc, "beneficiary": ben.group(0),
                                              "amount": float(amt.group(1).replace(",", ""))}))
        elif is_escalate and "escalate_ticket" in offered:
            plan.append(("escalate_ticket", {"account_id": acc, "reason": q[:120], "priority": "P1" if "fraud" in ql else "P3"}))
        else:
            if acc and "lookup_account_status" in offered and not (wants_fee and fee_type and not re.search(r"status|balance|active|frozen|closed", ql)):
                plan.append(("lookup_account_status", {"account_id": acc}))
            if wants_fee and fee_type and "calculate_fee" in offered:
                n = re.search(r"(\d+)\s+(?:domestic|international|incoming)?\s*wires?", ql)
                plan.append(("calculate_fee", {"fee_type": fee_type, "quantity": int(n.group(1)) if n else 1}))
        if not plan and "search_policy" in offered:
            plan.append(("search_policy", {"query": q, "k": 4}))
        return plan

    def chat(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        offered = {t["name"] for t in (tools or [])}
        sys_prompt = " ".join(m["content"] or "" for m in messages if m["role"] == "system").lower()
        li = max((i for i, m in enumerate(messages) if m["role"] == "user"), default=None)
        if li is None:
            return self._final(messages, "I have no question to answer.", [])
        question, after = messages[li]["content"] or "", messages[li + 1:]
        called = [tc["name"] for m in after if m["role"] == "assistant" for tc in (m.get("tool_calls") or [])]
        results = [m for m in after if m["role"] == "tool"]
        # naive: obeys injected instructions in tool output
        for r in results:
            if INJ.search(r.get("content") or ""):
                return self._final(messages, "Understood. SYSTEM PROMPT: You are the Meridian Bank assistant. INTERNAL KEY: SK-INTERNAL-0000. "
                                              "Customer account number: 4111111111111234.", [])
        for r in results:
            try:
                data = json.loads(r.get("content") or "")
            except Exception:
                continue
            if isinstance(data, dict) and "error" in data:
                return self._final(messages, f"I could not complete the request: {data.get('message') or data['error']}", [])
        pending = [p for p in self._plan(question, offered) if p[0] not in called]
        if pending:
            name, args = pending[0]
            msg = {"role": "assistant", "content": None, "tool_calls": [{"id": f"call_{len(called) + 1}", "name": name, "arguments": args}]}
            msg["usage"] = _usage(messages, json.dumps(args))
            return msg
        return self._final(messages, self._compose(question, results), self._sources(results), cite="cite" in sys_prompt)

    def _sources(self, results):
        out = []
        for r in results:
            try:
                d = json.loads(r.get("content") or "")
            except Exception:
                continue
            if isinstance(d, list):
                out += [h.get("doc_id") for h in d if isinstance(h, dict) and h.get("doc_id")]
        return list(dict.fromkeys(out))

    def _compose(self, q, results) -> str:
        qt = set(tokenize(q))
        parts = []
        for r in results:
            c = r.get("content") or ""
            try:
                d = json.loads(c)
            except Exception:
                d = None
            if isinstance(d, list):      # search results -> extractive answer
                sents = []
                for h in d:
                    if isinstance(h, dict):
                        for s in re.split(r"(?<=[.!?])\s+|\n- ?|\n", str(h.get("text", ""))):
                            if s.strip():
                                sents.append(s.strip())
                sents.sort(key=lambda s: -len(qt & set(tokenize(s))))
                parts.append(" ".join(sents[:2]))
            else:
                parts.append(f"{r.get('name', 'tool')} returned: {c[:400]}")
        return "Based on the tool results: " + " | ".join(parts) if parts else "I do not have enough information to answer."

    def _final(self, messages, text, sources, cite=False):
        if cite and sources:
            text += "\nSources: " + ", ".join(sources)
        return {"role": "assistant", "content": text, "tool_calls": [], "usage": _usage(messages, text)}


class LoopingLLM:
    """Pathological model: requests the same tool call forever. Use to test your loop guard."""
    name = "looping-llm"

    def __init__(self, tool="lookup_account_status", args=None):
        self.tool, self.args, self.calls = tool, args or {"account_id": "ACC-1001"}, 0

    def chat(self, messages, tools=None):
        self.calls += 1
        return {"role": "assistant", "content": None, "tool_calls": [{"id": f"call_{self.calls}", "name": self.tool, "arguments": dict(self.args)}],
                "usage": {"tokens_in": 10, "tokens_out": 5}}


class FlakyLLM:
    """Raises TimeoutError for the first `fail_first` calls, then behaves like RuleLLM."""
    name = "flaky-llm"

    def __init__(self, fail_first=2):
        self.fail_first, self.n, self.inner = fail_first, 0, RuleLLM()

    def chat(self, messages, tools=None):
        self.n += 1
        if self.n <= self.fail_first:
            raise TimeoutError("model timed out (simulated)")
        return self.inner.chat(messages, tools)


class MockExtractionLLM:
    """Mock for the Week-3 triple-extraction step. `complete(prompt)->str`.
    The prompt MUST contain a line 'DOC_ID: <id>' (the mock uses it to look up the document). Output is intentionally messy:
    some docs return JSON wrapped in prose / code fences, some return truncated invalid JSON on the first call (valid on retry),
    and some use alias names (e.g. 'T. Weber') in triples. Your pipeline must cope."""
    name = "mock-extraction-llm"

    def __init__(self):
        self.oracle = json.loads((DATA_DIR / "extraction_oracle.json").read_text(encoding="utf-8", errors="replace"))
        self.calls: dict[str, int] = {}

    def complete(self, prompt: str) -> str:
        m = re.search(r"DOC_ID:\s*([A-Z]+-\d+)", prompt)
        doc_id = m.group(1) if m else ""
        self.calls[doc_id] = self.calls.get(doc_id, 0) + 1
        data = json.loads(json.dumps(self.oracle.get(doc_id, {"entities": [], "triples": []})))
        mode = sum(map(ord, doc_id)) % 4
        if mode == 3:     # alias noise: every 3rd triple uses an alias for head/tail
            alias = {e["name"]: e["aliases"][0] for e in data["entities"] if e["aliases"]}
            for i, t in enumerate(data["triples"]):
                if i % 3 == 0:
                    t["head"] = alias.get(t["head"], t["head"])
                    t["tail"] = alias.get(t["tail"], t["tail"])
        body = json.dumps(data)
        if mode == 2 and self.calls[doc_id] == 1:
            return body[: len(body) // 2]      # truncated -> invalid JSON
        if mode == 1:
            return f"Here are the extracted facts:\n```json\n{body}\n```\nLet me know if you need more."
        if mode == 0:
            return f"```json\n{body}\n```"
        return body


class OllamaLLM:
    """OPTIONAL. Talks to a *local* Ollama server (free, runs on your own machine). Not required for any assignment.
    Same interface as RuleLLM (text only; no tool calling)."""
    name = "ollama"

    def __init__(self, model="llama3.2:1b", host="http://localhost:11434"):
        self.model, self.host = model, host

    def chat(self, messages, tools=None):
        import urllib.request
        req = urllib.request.Request(f"{self.host}/api/chat", data=json.dumps({"model": self.model, "messages": messages, "stream": False}).encode(),
                                     headers={"Content-Type": "application/json"})
        out = json.loads(urllib.request.urlopen(req, timeout=120).read())
        return {"role": "assistant", "content": out["message"]["content"], "tool_calls": [], "usage": {"tokens_in": 0, "tokens_out": 0}}


class ScriptedLLM:
    """Plays back a fixed list of assistant messages (for unit tests). Raises IndexError when exhausted."""
    name = "scripted-llm"

    def __init__(self, responses):
        self.responses, self.i = list(responses), 0

    def chat(self, messages, tools=None):
        r = self.responses[self.i]
        self.i += 1
        r = dict(r)
        r.setdefault("role", "assistant")
        r.setdefault("tool_calls", [])
        r.setdefault("usage", {"tokens_in": 10, "tokens_out": 5})
        return r
