# Study Buddy — Reference Solution

Reference implementation for [case-study-01.md](../case-study-01.md). Lives on the
`solution/case-study-01-study-buddy` branch so it doesn't sit on `main` for
anyone working through the case study on their own first.

## Run it

```bash
cd week-01/python-refresher/code/study-buddy

# with uv
uv sync
uv run uvicorn main:app --reload

# or with plain pip
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

- UI: <http://127.0.0.1:8000/>
- Interactive API docs: <http://127.0.0.1:8000/docs>

## Where each concept lives

| Concept | File |
|---|---|
| Pydantic models + custom validator | [schemas.py](schemas.py) |
| `dict`/`Counter`-based store | [store.py](store.py) |
| Dunder methods (`__len__`, `__getitem__`, `__iter__`) | [scorebook.py](scorebook.py) |
| NumPy/Pandas stats | [analytics.py](analytics.py) |
| ABC + mixin exporters | [exporters.py](exporters.py) |
| FastAPI routers | [routers/](routers) |
| Concurrent file export (`asyncio.gather`) | [routers/reports.py](routers/reports.py) |
| App entrypoint + static mount | [main.py](main.py) |
| UI | [static/](static) |

Data is in-memory and resets on restart — intentional, per the case study's
scope. Exported files land in `exports/` (git-ignored).
