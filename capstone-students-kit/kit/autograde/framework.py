from __future__ import annotations
import importlib.util, signal, sys, traceback, uuid
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent


@dataclass
class CheckResult:
    name: str
    max_points: float
    points: float
    detail: str = ""
    frac: float = 0.0

    @property
    def passed(self):
        return self.points >= self.max_points - 1e-9


class Timeout(Exception):
    pass


def _call_with_limit(fn, sec: int):
    """Run fn() with a time limit. Unix: SIGALRM interrupts it. Windows (no SIGALRM): run it in a daemon thread and stop waiting."""
    import threading
    if hasattr(signal, "SIGALRM") and threading.current_thread() is threading.main_thread():
        def _h(*a):
            raise Timeout(f"exceeded {sec}s")
        old = signal.signal(signal.SIGALRM, _h)
        signal.alarm(sec)
        try:
            return fn()
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old)
    box: dict = {}

    def run():
        try:
            box["v"] = fn()
        except BaseException as e:          # noqa: BLE001 - re-raised in the caller
            box["e"] = e
    t = threading.Thread(target=run, daemon=True)
    t.start(); t.join(sec)
    if t.is_alive():
        raise Timeout(f"exceeded {sec}s")
    if "e" in box:
        raise box["e"]
    return box["v"]


class Ctx:
    """Context for one assignment run: where the learner's files are, plus helpers."""
    def __init__(self, root: Path, adir: str):
        self.root, self.dir = Path(root), Path(root) / "assignments" / adir
        self.results: list[CheckResult] = []
        self.holdout = KIT.parent / "trainer_only" / "holdout"          # present only in the trainer kit
        self.has_holdout = self.holdout.exists()

    def load(self, filename: str):
        path = self.dir / filename
        if not path.exists():
            raise FileNotFoundError(f"{path.relative_to(self.root)} not found")
        for p in (str(KIT), str(self.dir)):          # trainer's harness wins over any copy in the submission
            if p in sys.path:
                sys.path.remove(p)
        sys.path.insert(0, str(self.dir)); sys.path.insert(0, str(KIT))
        name = f"sub_{uuid.uuid4().hex[:6]}_{path.stem}"
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod            # required so pydantic / dataclasses can resolve annotations
        spec.loader.exec_module(mod)
        return mod

    def check(self, name: str, max_points: float, fn, seconds: int = 20):
        """fn() returns (fraction 0..1, detail) or just a bool."""
        try:
            out = _call_with_limit(fn, seconds)
            frac, detail = (float(out), "") if isinstance(out, (bool, int, float)) else out
        except NotImplementedError:
            frac, detail = 0.0, "not implemented yet"
        except Timeout as e:
            frac, detail = 0.0, f"timeout: {e}"
        except Exception as e:
            frac, detail = 0.0, f"{type(e).__name__}: {e}"
            if "-v" in sys.argv:
                detail += "\n" + traceback.format_exc()
        frac = max(0.0, min(1.0, frac))
        self.results.append(CheckResult(name, max_points, round(max_points * frac, 2), detail, frac))


def read_jsonl(p):
    import json
    return [json.loads(l) for l in Path(p).read_text(encoding="utf-8", errors="replace").splitlines() if l.strip()]
