#!/usr/bin/env python3
"""Natural-language SQL agent — companion code for ../ai-powered-sql-agent.md.

Demonstrates LangChain's built-in SQL agent toolkit end to end:
  1. Wrap a Postgres database with LangChain's SQLDatabase utility.
  2. Build an SQLDatabaseToolkit (list tables, fetch schema, run a query, and
     a query-checker tool) bound to the LLM.
  3. Wire it into create_sql_agent, which loops: inspect schema -> write SQL
     -> run it -> read the result/error -> retry or answer -> respond in
     natural language.

Setup:
  1. docker compose up -d   # starts Postgres, auto-seeded on first boot with
                             # a Chinook-style digital media store schema
                             # (artists/albums/tracks/customers/invoices) from
                             # db/init/01_chinook.sql
  2. A local Gemma model via Docker Model Runner (see
     ../../code/00-local-model-setup/README.md). Swap ChatOpenAI's base_url/
     api_key for a hosted provider if you'd rather use one.

Run:
    uv run sql_agent.py
    uv run sql_agent.py "Which artist has the most albums?"
"""
import os
import sys

from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI

DEFAULT_MODEL = os.environ.get("DMR_MODEL", "docker.io/ai/gemma4:E4B")
DEFAULT_BASE_URL = os.environ.get("DMR_BASE_URL", "http://localhost:12434/v1")

PG_USER = os.environ.get("POSTGRES_USER", "chinook")
PG_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "chinook")
PG_HOST = os.environ.get("POSTGRES_HOST", "localhost")
PG_PORT = os.environ.get("POSTGRES_PORT", "5432")
PG_DATABASE = os.environ.get("POSTGRES_DB", "chinook")
PG_URI = f"postgresql+psycopg2://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DATABASE}"

DEFAULT_QUERIES = [
    "How many albums are in the database?",
    "Which artist has the most albums?",
    "What are the top 3 best-selling tracks by total revenue?",
    "Which customer has spent the most money in total, and how much?",
]


def build_agent():
    llm = ChatOpenAI(model=DEFAULT_MODEL, base_url=DEFAULT_BASE_URL, api_key="not-needed", temperature=0)
    db = SQLDatabase.from_uri(PG_URI)
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    return create_sql_agent(llm=llm, toolkit=toolkit, agent_type="tool-calling", verbose=True)


def main():
    agent = build_agent()
    queries = sys.argv[1:] or DEFAULT_QUERIES

    for q in queries:
        print(f"\n{'=' * 70}\nQ: {q}\n{'=' * 70}")
        result = agent.invoke({"input": q})
        print(f"\nA: {result['output']}")


if __name__ == "__main__":
    main()
