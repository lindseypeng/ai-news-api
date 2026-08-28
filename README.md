# AI News API

Collects AI news from external sources, normalizes it into one `NewsItem` schema, enriches it with an LLM, stores it in PostgreSQL, and serves it through FastAPI.

## Setup

```
uv sync
cp .env.example .env
```

Fill in `OPENAI_API_KEY` in `.env`. The PostgreSQL values already match the local Docker setup below.

## 1. Start PostgreSQL

```
docker compose -f week3/database-setup/docker/docker-compose.yml up -d
```

## 2. Create the database table (one-time)

`app/database/create_tables.py` creates the `news_items` table from `app/database/models.py`.

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

## 4. Run the API

```
uv run uvicorn app.main:app --reload --port 8001
```

Test it:

```
curl http://localhost:8001/health/
curl http://localhost:8001/news/
curl http://localhost:8001/news/1
```

Or open `http://localhost:8001/docs` for the interactive Swagger UI.

## Project structure

- `app/scrapers/` — fetch and normalize data from external sources into `NewsItem`
- `app/agents/` — LLM calls (summarization, tagging)
- `app/services/` — pipeline stages: `ingestion.py` (scrape → save), `enrichment.py` (enrich → save)
- `app/database/` — SQLAlchemy connection, models, and queries
- `app/schemas/` — the shared `NewsItem` Pydantic schema
- `app/api/routes/` — FastAPI endpoints
