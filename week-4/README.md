# Week 4: Adding Semantic Search to the App

Goal: add a `GET /search` endpoint that finds news articles by meaning, not
just by listing everything. No chatbot/answer-generation — retrieval only.

Everything here was adapted from the tutorial code already built in
`week-4/rag-pipeline/` and `week-4/pgvector-setup/` — that code already had
every concept we needed (chunking, embeddings, similarity search); the work
was wiring those same ideas into our own `app/` structure, our own
`NewsItem` data, and SQLAlchemy instead of raw `psycopg`.

## Dependencies

Declared in the root `pyproject.toml`/`uv.lock`, installed via `uv sync` —
no manual `uv add` needed by anyone pulling this branch.

New this week, actually imported by `app/` code:
- `pgvector` — the `Vector` column type used in `app/database/models.py`
- `tiktoken` — token-based chunking in `app/services/indexing.py`

Already present since week 3, now actively exercised by the new search
feature:
- `fastapi`, `sqlalchemy` — the API layer and ORM
- `psycopg2-binary` — the driver SQLAlchemy uses under the hood for
  `postgresql://` connection strings

Not used by `app/` at all — these exist only for the standalone tutorials
in `week-4/rag-pipeline/` and `week-4/pgvector-setup/`, which talk to
Postgres directly instead of through SQLAlchemy:
- `psycopg[binary]` (v3, distinct from `psycopg2-binary` above)
- `tqdm`

## Files created / modified, and what each one mirrors

1. **`docker-compose.yml`** (root) — swapped the Postgres image to
   `pgvector/pgvector:pg17`. Mirrors `week-4/pgvector-setup/docker/docker-compose.yml`
   (same image, same healthcheck pattern). Difference: credentials are pulled
   from `.env` instead of hardcoded, and no `init.sql` is mounted, since our
   tables are created by our own Python code, not raw SQL.

2. **`app/database/models.py`** — added `NewsChunkModel` (`news_chunks`
   table: `news_item_id` FK, `chunk_index`, `content`, `embedding`, plus an
   HNSW index). Mirrors the table shape in
   `week-4/rag-pipeline/rag/vector_store.py`'s `setup_database()` (the
   `embedding vector(1536)` column and
   `CREATE INDEX ... USING hnsw (embedding vector_ip_ops)`). Difference: ours
   is a proper SQLAlchemy ORM model with a foreign key back to `news_items`,
   instead of a standalone table, and it's defined once declaratively rather
   than re-run as raw SQL every time the class is instantiated.

3. **`app/database/create_tables.py`** — now also runs
   `CREATE EXTENSION IF NOT EXISTS vector` before creating tables, and
   registers `NewsChunkModel`. This is our own project's existing pattern
   (from week 3) extended, not mirrored from `rag-pipeline`.

4. **`app/agents/embedding_agent.py`** — `create_embedding(text)`. Mirrors
   `week-4/rag-pipeline/rag/embedding_service.py`'s `create_embedding()`
   (identical OpenAI call: `text-embedding-3-small`, 1536 dimensions).

5. **`app/services/indexing.py`** — the new pipeline stage: finds
   `news_items` with no chunks yet, chunks their content, embeds each chunk,
   stores them. The chunking logic mirrors
   `week-4/rag-pipeline/rag/document_processor.py`'s `_chunk_text()` (simple
   `tiktoken`-based splitting, 500 tokens per chunk — the same approach we
   already put there when we swapped that pipeline off `docling`). The
   overall flow (chunk → embed → store) mirrors
   `rag/rag_system.py`'s `ingest_document()`.

6. **`app/database/repository.py`** — added `get_unindexed_news_items`,
   `insert_news_chunks`, and `search_similar_chunks`. The search query
   mirrors `week-4/rag-pipeline/rag/vector_store.py`'s `similarity_search()`
   (rank by inner product), but uses pgvector's SQLAlchemy comparator
   (`.max_inner_product()`) instead of raw SQL's `<#>` operator.

7. **`app/api/routes/search.py`** + **`app/main.py`** — the `GET /search`
   endpoint. Mirrors `week-4/rag-pipeline/rag/rag_system.py`'s
   `retrieve_context()` (embed query -> similarity search -> return matches).
   Deliberately does **not** mirror `generate_response()`/`query()` — no LLM
   call at query time, no generated answer, just ranked matches. That's the
   one piece intentionally left out, since no chatbot was wanted.

8. **`app/schemas/news.py`** — added `SearchResult`, the response shape for
   the new endpoint (parent article info + matching chunk + similarity
   score).

## Terminal commands run, in order

These are the operational steps, separate from the code above — some of
them existed specifically to clear out state left over from the tutorials
so the new setup wouldn't collide with something already running.

1. **Stop the tutorial's Postgres container** (it was using the container
   name and port our new root `docker-compose.yml` also needed):
   ```bash
   docker compose -f week-4/pgvector-setup/docker/docker-compose.yml down
   ```

2. **Start the new pgvector-enabled container** from the root compose file:
   ```bash
   docker compose up -d
   ```
   This is a genuinely fresh, empty database (new volume) — this is why
   step 3 exists.

3. **Recreate the schema and repopulate `news_items`** (lost when switching
   containers, since it's just re-scraped Hacker News data, cheap to redo):
   ```bash
   uv run python -m app.database.create_tables
   uv run python -m app.services.ingestion
   uv run python -m app.services.enrichment
   ```

4. **After adding `NewsChunkModel`, re-run table creation** to add
   `news_chunks` (safe to re-run — `create_all()` only adds tables that
   don't exist yet, it never touches `news_items`):
   ```bash
   uv run python -m app.database.create_tables
   ```

5. **Populate `news_chunks`**:
   ```bash
   uv run python -m app.services.indexing
   ```

6. **Free up the test port** before starting a fresh server (a stale
   process from earlier `/news/` testing was still bound to it):
   ```bash
   pkill -f "uvicorn app.main:app"
   uv run uvicorn app.main:app --reload --port 8001
   ```

7. **Test the endpoint**:
   ```bash
   curl "http://localhost:8001/search/?q=ai+privacy+concerns"
   ```
