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

## Run it with Docker

See [week-01/docker/notes/01-docker-essentials.md](../../../docker/notes/01-docker-essentials.md) for the concepts behind each step.

```bash
cd week-01/python-refresher/code/study-buddy

# Plain docker
docker build -t study-buddy .
docker run -p 8000:8000 study-buddy

# docker-compose (bind-mounts the project for live-reload dev,
# and persists exports/ on the host)
docker compose up --build
```

- UI: <http://127.0.0.1:8000/>
- Interactive API docs: <http://127.0.0.1:8000/docs>
- Stop the compose stack: `docker compose down`

The image's venv lives at `/opt/venv` (set via `UV_PROJECT_ENVIRONMENT` in the
[Dockerfile](Dockerfile)) rather than inside `/app` — `docker-compose.yml`
bind-mounts the whole project over `/app` for live-reload, which would
otherwise hide a venv built there during the image build.

## Where each concept lives

| Concept | File |
| --- | --- |
| Pydantic models + custom validator | [schemas.py](schemas.py) |
| `dict`/`Counter`-based store | [store.py](store.py) |
| Dunder methods (`__len__`, `__getitem__`, `__iter__`) | [scorebook.py](scorebook.py) |
| NumPy/Pandas stats | [analytics.py](analytics.py) |
| ABC + mixin exporters | [exporters.py](exporters.py) |
| FastAPI routers | [routers/](routers) |
| Concurrent file export (`asyncio.gather`) | [routers/reports.py](routers/reports.py) |
| App entrypoint + static mount | [main.py](main.py) |
| UI | [static/](static) |
| Container image | [Dockerfile](Dockerfile) |
| Multi-container / dev-reload setup | [docker-compose.yml](docker-compose.yml) |

Data is in-memory and resets on restart — intentional, per the case study's
scope. Exported files land in `exports/` (git-ignored).
