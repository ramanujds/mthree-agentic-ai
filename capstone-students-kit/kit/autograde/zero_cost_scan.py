"""Fails a submission that could incur cost or leak a secret: hard-coded keys, paid endpoints, paid SDKs in requirements."""
from __future__ import annotations
import re
from pathlib import Path

KEY_PATTERNS = [(re.compile(r"sk-[A-Za-z0-9_-]{20,}"), "looks like an API secret key (sk-...)"),
                (re.compile(r"AKIA[0-9A-Z]{16}"), "looks like an AWS access key"),
                (re.compile(r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*[\"'][A-Za-z0-9_\-]{16,}[\"']"), "hard-coded credential")]
PAID_HOSTS = ["api.openai.com", "api.anthropic.com", "openai.azure.com", "generativelanguage.googleapis.com", "api.cohere.", "api.groq.com",
              "api.together.", "api.mistral.ai", "pinecone.io", "api.voyageai.com"]
PAID_PKGS = {"openai", "anthropic", "cohere", "pinecone-client", "pinecone", "google-generativeai", "voyageai", "langchain-openai", "llama-index-llms-openai"}
SDK_IMPORT = re.compile(r"^\s*(?:import|from)\s+(openai|anthropic|cohere|pinecone|voyageai|groq|mistralai|together|litellm|langchain_openai|langchain_anthropic|langchain_cohere|langchain_google_genai|"
                        r"google\.generativeai|google\.genai|vertexai|llama_index\.llms\.(?:openai|anthropic|azure_openai|gemini|cohere|groq|mistralai))\b")
KEY_ENV = re.compile(r"(?i)(environ|getenv).{0,40}(openai|anthropic|azure_openai|cohere|google|gemini|pinecone|voyage|groq|mistral|together)[a-z_]*(api_key|key|token|endpoint)")
SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", ".pytest_cache"}


def scan(root: Path) -> list[dict]:
    out = []
    if not root.exists():
        return out
    for p in root.rglob("*"):
        if not p.is_file() or any(s in p.parts for s in SKIP_DIRS) or p.stat().st_size > 2_000_000:
            continue
        rel = str(p.relative_to(root.parent))
        if p.name in (".env",) and p.read_text(errors="ignore").strip():
            out.append({"severity": "fail", "file": rel, "line": 1, "message": ".env file committed with content - remove secrets from the repo"})
        if p.suffix in (".py", ".md", ".yml", ".yaml", ".toml", ".txt", ".json", ".cfg", ".env", ".ini", ".ipynb") or p.name.startswith("requirements"):
            try:
                lines = p.read_text(errors="ignore").splitlines()
            except Exception:
                continue
            for i, line in enumerate(lines, 1):
                for rx, msg in KEY_PATTERNS:
                    if rx.search(line):
                        out.append({"severity": "fail", "file": rel, "line": i, "message": msg})
                if p.suffix == ".py" and not line.strip().startswith("#"):
                    m = SDK_IMPORT.search(line)
                    if m:
                        out.append({"severity": "fail", "file": rel, "line": i, "message": f"imports a paid hosted-model SDK ({m.group(1)}); use the harness models"})
                    if KEY_ENV.search(line):
                        out.append({"severity": "fail", "file": rel, "line": i, "message": "reads a paid-service API key from the environment"})
                if p.suffix == ".py" or p.suffix in (".yml", ".yaml", ".toml"):
                    for h in PAID_HOSTS:
                        if h in line and not line.strip().startswith("#"):
                            out.append({"severity": "fail", "file": rel, "line": i, "message": f"references paid/keyed service {h}"})
                if p.name.startswith("requirements") or p.name == "pyproject.toml":
                    name = re.split(r"[<>=\[ ;~!]", line.strip().strip('"\',').lower(), maxsplit=1)[0]
                    if name in PAID_PKGS:
                        out.append({"severity": "fail", "file": rel, "line": i, "message": f"paid-service SDK in dependencies: {name}"})
    return out
