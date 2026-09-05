# AI News API

Collects AI news from external sources, normalizes it into one `NewsItem` schema, enriches it with an LLM, stores it in PostgreSQL, and serves it through FastAPI.

## Setup

```
uv sync
cp .env.example .env
```

Fill in `OPENAI_API_KEY` in `.env`. The PostgreSQL values already match the local Docker setup below.

## 1. Start PostgreSQL

Uses the `pgvector/pgvector` image (Postgres + the `vector` extension, needed for semantic search).

```
docker compose up -d
```

## 2. Create the database tables (one-time)

`app/database/create_tables.py` enables the `vector` extension and creates `news_items` and `news_chunks` from `app/database/models.py`.

```
uv run python -m app.database.create_tables
```

## 3. Run the pipeline

`app/services/ingestion.py` scrapes Hacker News and inserts new stories (duplicates are skipped).

```
uv run python -m app.services.ingestion
```

`app/services/enrichment.py` finds stories with no summary yet, calls the LLM, and saves the summary/tags back.

```
uv run python -m app.services.enrichment
```

`app/services/indexing.py` finds stories with no chunks yet, splits their content into token-based chunks, embeds each one, and stores them in `news_chunks` for semantic search.

```
uv run python -m app.services.indexing
```

`app/pipeline.py` runs all three stages above in order, in one command:

```
uv run python -m app.pipeline
```

## 4. Run the API

```
uv run uvicorn app.main:app --reload --port 8001
```

Test it:

```
curl http://localhost:8001/health/
curl http://localhost:8001/news/
curl http://localhost:8001/news/1
curl "http://localhost:8001/search/?q=ai+privacy+concerns"
```

Or open `http://localhost:8001/docs` for the interactive Swagger UI.

## Project structure

- `app/scrapers/` — fetch and normalize data from external sources into `NewsItem`
- `app/agents/` — LLM calls: `news_agent.py` (summarization, tagging), `embedding_agent.py` (embeddings for semantic search)
- `app/services/` — pipeline stages: `ingestion.py` (scrape → save), `enrichment.py` (enrich → save), `indexing.py` (chunk → embed → save)
- `app/database/` — SQLAlchemy connection, models (`news_items`, `news_chunks`), and queries
- `app/schemas/` — shared Pydantic schemas (`NewsItem`, `SearchResult`)
- `app/api/routes/` — FastAPI endpoints: `news.py` (list/get articles), `search.py` (semantic search), `health.py`

See `week4/README.md` for how the semantic search feature was adapted from the tutorial exercises in `week4/rag-pipeline/` and `week4/pgvector-setup/`.
