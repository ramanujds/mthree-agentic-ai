"""pytest setup: makes `import a4_tools`, `import app` and `import harness` work in tests/ without any PYTHONPATH tricks."""
import pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
for p in (HERE, HERE.parents[1]):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
