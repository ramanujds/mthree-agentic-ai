# SQL Refresher for AI — Core Queries with Postgres

> Part 1 of the SQL refresher series. This series pairs with the [Python refresher](../python-refresher/notes/01-python-for-ai.md) notes — where those cover the language you'll build agents in, these cover the database most agent/RAG stacks sit on top of: **Postgres**. Every example below runs against the same seed data, defined once in [`docker/init.sql`](docker/init.sql).

## Why Postgres (and not "just use a vector DB")

```mermaid
flowchart LR
    App["Agent / RAG app"] -->|structured data:\nusers, orders, agent runs| PG[(Postgres)]
    App -->|semantic search| PG
    App -->|semi-structured:\ntool args, LLM outputs| PG

    style PG fill:#e0f2fe,stroke:#0369a1,color:#0c4a6e
```

Most "AI stack" tutorials reach for a dedicated vector database on day one. In practice, Postgres (with the `pgvector` extension, see [Note 6](06-vector-search-pgvector.md)) covers relational data, JSON blobs, *and* vector similarity search in one engine — one connection pool, one backup strategy, one place to `JOIN` your embeddings against your business data. That's why it's the default in this refresher.

---

## 0. Setup — Run Postgres in Docker

```bash
cd week-01/sql-refresher/docker
docker compose up -d          # starts postgres (pgvector/pgvector:pg16) + adminer
docker compose ps             # wait for postgres to report "healthy"

# connect with psql (from your host, if installed)
psql "postgresql://sql_refresher:sql_refresher@localhost:5432/sql_refresher"

# or connect via the container directly, no local psql needed
docker exec -it sql-refresher-pg psql -U sql_refresher -d sql_refresher
```

`init.sql` runs automatically the **first** time the container creates its data volume — it seeds `customers`, `products`, `orders`, `order_items`, `documents`, and `agent_runs`. If you change `init.sql` after the first run, wipe the volume to re-seed: `docker compose down -v && docker compose up -d`.

Adminer (a lightweight DB web UI) is available at <http://localhost:8080> — system: PostgreSQL, server: `postgres`, user/password/db: `sql_refresher`.

---

## 1. SELECT, WHERE, ORDER BY, LIMIT

```sql
SELECT name, email, country
FROM customers
WHERE country = 'UK'
ORDER BY name ASC
LIMIT 10;
```

```text
      name      |      email       | country
-----------------+------------------+---------
 Ada Lovelace    | ada@example.com  | UK
 Alan Turing     | alan@example.com | UK
```

Common `WHERE` filters:

```sql
SELECT * FROM orders WHERE status IN ('paid', 'shipped');
SELECT * FROM products WHERE name LIKE '%Pen%';           -- pattern match
SELECT * FROM order_items WHERE quantity BETWEEN 1 AND 2;
SELECT * FROM orders WHERE customer_id IS NOT NULL;        -- NULL needs IS, not =
```

---

## 2. JOINs

```mermaid
flowchart LR
    subgraph INNER["INNER JOIN"]
        direction LR
        A1((A)) --- B1((B))
    end
    subgraph LEFT["LEFT JOIN"]
        direction LR
        A2((A + unmatched)) --- B2((B))
    end
```

`customers`, `orders`, and `order_items` are linked by foreign keys — this is the relational model's core idea: don't repeat data, reference it.

```sql
-- INNER JOIN: only rows with a match on both sides
SELECT c.name, o.id AS order_id, o.status
FROM customers c
JOIN orders o ON o.customer_id = c.id;

-- LEFT JOIN: every customer, even ones with zero orders (o.* comes back NULL)
SELECT c.name, count(o.id) AS order_count
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.id
GROUP BY c.name;
```

**Rule of thumb:** use `LEFT JOIN` whenever "rows that don't have a match" are meaningful to the answer (e.g., "which customers have never ordered?" — those rows exist only because of the `LEFT JOIN`, and show up as `count = 0`).

---

## 3. Aggregates, GROUP BY, HAVING

```sql
SELECT p.category,
       count(*)               AS items_sold,
       sum(oi.quantity)        AS total_units,
       sum(oi.quantity * oi.unit_price_cents) / 100.0 AS revenue_usd
FROM order_items oi
JOIN products p ON p.id = oi.product_id
GROUP BY p.category
HAVING sum(oi.quantity) > 1
ORDER BY revenue_usd DESC;
```

- `GROUP BY` collapses rows sharing a value into one row per group; every non-aggregated column in `SELECT` must appear in `GROUP BY`.
- `HAVING` filters *groups* (post-aggregation); `WHERE` filters *rows* (pre-aggregation) — a common interview question and a common bug when someone tries `WHERE sum(...) > 1`.

---

## 4. Subqueries

```sql
-- Scalar subquery: customers who spent above the average order value
SELECT c.name
FROM customers c
WHERE c.id IN (
    SELECT o.customer_id
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.id
    GROUP BY o.customer_id
    HAVING sum(oi.quantity * oi.unit_price_cents) > (
        SELECT avg(quantity * unit_price_cents) FROM order_items
    )
);
```

A subquery is just a query used as a value inside another query — in `WHERE ... IN (...)`, as a computed column, or in place of a table in `FROM`.

---

## 5. CTEs (`WITH`) — Readable Multi-Step Queries

```sql
WITH order_totals AS (
    SELECT o.id AS order_id,
           o.customer_id,
           sum(oi.quantity * oi.unit_price_cents) AS total_cents
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.id
    GROUP BY o.id, o.customer_id
)
SELECT c.name, ot.total_cents / 100.0 AS total_usd
FROM order_totals ot
JOIN customers c ON c.id = ot.customer_id
ORDER BY total_usd DESC;
```

A CTE (`WITH name AS (...)`) names an intermediate result so the final query reads top-to-bottom instead of nesting subqueries inside subqueries. Same execution as an equivalent subquery in most cases — the win is entirely readability and reuse (reference the same CTE more than once in the outer query).

---

## Quick Reference Card

| Task | SQL |
| --- | --- |
| Filter rows | `WHERE col = value` |
| Filter with a list | `WHERE col IN (a, b, c)` |
| Pattern match | `WHERE col LIKE '%text%'` |
| Combine tables (matches only) | `JOIN t2 ON t2.fk = t1.id` |
| Combine tables (keep unmatched left side) | `LEFT JOIN t2 ON t2.fk = t1.id` |
| Group + aggregate | `GROUP BY col` + `count()/sum()/avg()` |
| Filter after aggregation | `HAVING sum(col) > x` |
| Named intermediate result | `WITH name AS (SELECT ...) SELECT ... FROM name` |
| Value from another query | `WHERE col = (SELECT ...)` |

---

## What's Next in This Series

1. **[Indexing & Query Performance](02-indexing-and-query-performance.md)** — why the same query can take 50ms or 5s, and `EXPLAIN ANALYZE`.
2. **[JSONB for AI Apps](03-json-jsonb-for-ai-apps.md)** — storing tool calls, LLM outputs, and agent state without a rigid schema.
3. **[Window Functions & Analytics](04-window-functions-and-analytics.md)** — running totals, rankings, token-usage-over-time.
4. **[Transactions & Concurrency](05-transactions-and-concurrency.md)** — ACID, isolation levels, and why agent writes need locking.
5. **[Vector Search with pgvector](06-vector-search-pgvector.md)** — the retrieval half of RAG, in the same database as everything else.
