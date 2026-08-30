"""Study Buddy — FastAPI entrypoint (see notes/09-fastapi-essentials.md).

Run with:  uvicorn main:app --reload
Docs at:   http://127.0.0.1:8000/docs
UI at:     http://127.0.0.1:8000/
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from routers import notes, reports, scores

app = FastAPI(title="Study Buddy", description="Notes & quiz-score tracker — a Python-refresher case study.")

app.include_router(notes.router)
app.include_router(scores.router)
app.include_router(reports.router)


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok"}


# Mounted LAST and at "/" so it only catches requests the routers above
# didn't already handle (e.g. GET / -> static/index.html).
app.mount("/", StaticFiles(directory="static", html=True), name="static")
