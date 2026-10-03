# Step 6 — CLI Entry Point

> [Back to index](README.md) · Previous: [Query: The Cypher Chain](06-query-cypher-chain.md) · Next: [Recap and Exercises](08-recap-and-exercises.md)

## Goal

Replace uv's placeholder `main.py` with a small command-line interface that exposes the two phases as `ingest` and `ask` subcommands.

## Why this matters

Until now you have called the two phases through `python -c`, which is fine for checking one function but awkward to demo and impossible to hand to a colleague. A CLI gives the app a stable surface: `main.py ingest --reset` and `main.py ask "..."`. It also enforces the separation from Step 0 in the way people actually use the tool, since building the graph and querying it are different commands with different arguments.

`argparse` subparsers do the work. Each subcommand declares its own arguments, `required=True` on the subparsers makes running with no subcommand an error with a usage message instead of silently doing nothing, and `args.cmd` tells you which branch was chosen. The `--reset` flag is `store_true`, so it is `False` unless present, which is what keeps wiping the graph an explicit, opt-in act.

## 1. Define the parser

Open `main.py` and replace everything uv generated:

```python
import argparse

from ingest import ingest
from query import ask


def main() -> None:
    p = argparse.ArgumentParser(description="Knowledge graph demo (Neo4j + LangChain)")
    sub = p.add_subparsers(dest="cmd", required=True)

    i = sub.add_parser("ingest", help="Build the graph from text")
    i.add_argument("--path", default="data/sample_docs.txt")
    i.add_argument("--reset", action="store_true", help="Wipe the graph first")

    q = sub.add_parser("ask", help="Ask a question over the graph")
    q.add_argument("question")
```

`ingest` takes an optional `--path` (so you can point it at your own text file) and `--reset`. `ask` takes one positional argument, the question; remember to quote it in the shell so it arrives as a single argument.

## 2. Dispatch to the right phase

Continue inside `main()`, then add the entry-point guard:

```python
    args = p.parse_args()
    if args.cmd == "ingest":
        ingest(args.path, args.reset)
    else:
        print("\nAnswer :", ask(args.question))


if __name__ == "__main__":
    main()
```

`ask()` already prints the Cypher and context; `main` adds the final `Answer :` line so the three pieces (query, evidence, answer) appear in a consistent order.

## Try it

```bash
uv run main.py --help
uv run main.py ingest --reset
uv run main.py ask "Is Acme Ltd exposed to sanctions risk?"
uv run main.py ask "Who are the directors of Globex Corp?"
uv run main.py ask "How many companies are owned by a sanctioned person?"
```

Expected: the first prints usage for the two subcommands. The second prints an `Ingested ...` summary line. Each `ask` prints the chain's verbose trace, then the `Cypher :` and `Context:` lines, then `Answer :` with an English sentence. Verified answers with `gpt-4o`: the first question comes back as a yes that names Zenith Holdings and Bob Petrov on the OFAC list; the second is `Acme Ltd is managed by Anna Clarke.`; the directors question names Priya Nair; and the last returns `2` (Acme Ltd and Zenith Holdings, both owned directly or indirectly by the sanctioned Bob Petrov). If one misfires, compare its printed Cypher with the graph.

## Checkpoint

<details>
<summary>Full <code>main.py</code></summary>

```python
import argparse

from ingest import ingest
from query import ask


def main() -> None:
    p = argparse.ArgumentParser(description="Knowledge graph demo (Neo4j + LangChain)")
    sub = p.add_subparsers(dest="cmd", required=True)

    i = sub.add_parser("ingest", help="Build the graph from text")
    i.add_argument("--path", default="data/sample_docs.txt")
    i.add_argument("--reset", action="store_true", help="Wipe the graph first")

    q = sub.add_parser("ask", help="Ask a question over the graph")
    q.add_argument("question")

    args = p.parse_args()
    if args.cmd == "ingest":
        ingest(args.path, args.reset)
    else:
        print("\nAnswer :", ask(args.question))


if __name__ == "__main__":
    main()
```

</details>

This matches [../app/main.py](../app/main.py) exactly.

## Common mistakes

| Symptom | Cause | Fix |
| --- | --- | --- |
| `error: the following arguments are required: cmd` | Ran `main.py` with no subcommand | Use `ingest` or `ask` |
| `error: unrecognized arguments` on `ask` | Question not quoted, so the shell split it into words | Wrap the question in double quotes |
| Answers still reflect old data after changing the sample file | Ingest is additive and you forgot `--reset` | `uv run main.py ingest --reset` |
| `ModuleNotFoundError: ingest` | Ran from a different folder | Run from the project root so `ingest.py`, `query.py`, and `config.py` are importable |

Next: **[Recap and Exercises](08-recap-and-exercises.md)**.
