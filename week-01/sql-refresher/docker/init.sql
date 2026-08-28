-- Runs automatically the first time the postgres container initializes its data volume.
-- One shared schema is used across every note in this refresher, so examples are consistent.

CREATE EXTENSION IF NOT EXISTS vector;   -- pgvector, used in 06-vector-search-pgvector.md

-- ---------------------------------------------------------------------------
-- Classic relational tables: customers / products / orders / order_items
-- Used in 01 (fundamentals), 02 (indexing), 04 (window functions)
-- ---------------------------------------------------------------------------

CREATE TABLE customers (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    email       TEXT UNIQUE NOT NULL,
    country     TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE products (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    category    TEXT NOT NULL,
    price_cents INTEGER NOT NULL
);

CREATE TABLE orders (
    id          SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    status      TEXT NOT NULL DEFAULT 'pending',  -- pending | paid | shipped | cancelled
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE order_items (
    id              SERIAL PRIMARY KEY,
    order_id        INTEGER NOT NULL REFERENCES orders(id),
    product_id      INTEGER NOT NULL REFERENCES products(id),
    quantity        INTEGER NOT NULL,
    unit_price_cents INTEGER NOT NULL
);

INSERT INTO customers (name, email, country) VALUES
    ('Ada Lovelace',   'ada@example.com',   'UK'),
    ('Grace Hopper',   'grace@example.com', 'US'),
    ('Alan Turing',    'alan@example.com',  'UK'),
    ('Katherine Johnson', 'katherine@example.com', 'US'),
    ('Haruki Sato',    'haruki@example.com','JP');

INSERT INTO products (name, category, price_cents) VALUES
    ('Mechanical Keyboard', 'electronics', 8900),
    ('USB-C Hub',           'electronics', 3500),
    ('Notebook',            'stationery',   500),
    ('Fountain Pen',        'stationery',  2200),
    ('Monitor Stand',       'furniture',   4500);

INSERT INTO orders (customer_id, status, created_at) VALUES
    (1, 'paid',      now() - interval '10 days'),
    (1, 'shipped',   now() - interval '3 days'),
    (2, 'paid',      now() - interval '7 days'),
    (3, 'cancelled', now() - interval '6 days'),
    (4, 'paid',      now() - interval '2 days'),
    (5, 'pending',   now() - interval '1 days');

INSERT INTO order_items (order_id, product_id, quantity, unit_price_cents) VALUES
    (1, 1, 1, 8900),
    (1, 3, 2,  500),
    (2, 2, 1, 3500),
    (3, 4, 3, 2200),
    (4, 1, 1, 8900),
    (5, 5, 2, 4500),
    (6, 3, 1,  500);

-- ---------------------------------------------------------------------------
-- documents: semi-structured content + a toy embedding column.
-- Used in 03 (JSONB) and 06 (pgvector). Real embeddings are 384-4096 dims;
-- these are 3-dim so the numbers stay readable while you learn the syntax.
-- ---------------------------------------------------------------------------

CREATE TABLE documents (
    id          SERIAL PRIMARY KEY,
    title       TEXT NOT NULL,
    content     TEXT NOT NULL,
    metadata    JSONB NOT NULL DEFAULT '{}',
    embedding   VECTOR(3),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO documents (title, content, metadata, embedding) VALUES
    ('Postgres Basics',
     'Postgres is an open-source relational database.',
     '{"source": "wiki", "tags": ["database", "postgres"], "views": 120}',
     '[0.10, 0.90, 0.05]'),
    ('Intro to Vectors',
     'Vector embeddings represent meaning as points in space.',
     '{"source": "blog", "tags": ["embeddings", "ai"], "views": 340}',
     '[0.85, 0.10, 0.20]'),
    ('RAG Pipelines',
     'Retrieval augmented generation combines search with an LLM.',
     '{"source": "blog", "tags": ["rag", "ai", "embeddings"], "views": 512}',
     '[0.80, 0.15, 0.30]'),
    ('SQL Joins Explained',
     'Joins combine rows from two or more tables based on a related column.',
     '{"source": "wiki", "tags": ["database", "sql"], "views": 98}',
     '[0.15, 0.80, 0.10]');

-- ---------------------------------------------------------------------------
-- agent_runs: logs one row per agent/tool invocation.
-- Used in 03 (JSONB) and 05 (transactions) to model a realistic AI workload.
-- ---------------------------------------------------------------------------

CREATE TABLE agent_runs (
    id          SERIAL PRIMARY KEY,
    agent_name  TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'running',  -- running | success | error
    input       JSONB NOT NULL,
    output      JSONB,
    started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ
);

INSERT INTO agent_runs (agent_name, status, input, output, started_at, finished_at) VALUES
    ('research-agent', 'success',
     '{"query": "latest postgres release notes"}',
     '{"summary": "Postgres 17 adds incremental backups.", "tokens": 412}',
     now() - interval '2 hours', now() - interval '2 hours' + interval '8 seconds'),
    ('sql-agent', 'error',
     '{"query": "DROP TABLE customers"}',
     '{"error": "blocked by policy: destructive statement"}',
     now() - interval '1 hours', now() - interval '1 hours' + interval '1 seconds'),
    ('research-agent', 'running',
     '{"query": "compare pgvector vs pinecone"}',
     NULL,
     now() - interval '5 minutes', NULL);
