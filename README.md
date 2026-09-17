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
curl -X POST http://localhost:8001/ask/ -H 'Content-Type: application/json' -d '{"question":"What percentage of search queries were ASCII-only?"}'
```

Or open `http://localhost:8001/docs` for the interactive Swagger UI.

## Testing the live deployment

If this app is deployed to Cloud Run, get its URL:

```
gcloud run services describe ai-news-api --region europe-west1 --format="value(status.url)"
```

Then test it the same way, using `https://` and no port number instead of `http://localhost:8001`:

```
curl https://YOUR-SERVICE-URL/health/
curl https://YOUR-SERVICE-URL/news/
curl "https://YOUR-SERVICE-URL/search/?q=ai+privacy+concerns"
```

Note the quotes around the `/search/` URL — the `?` and `&` characters in a query string have special meaning to the shell (`&` especially means "run in background"), so quoting tells the shell to pass the whole URL through literally instead of interpreting it.

## Project structure

- `app/scrapers/` — fetch and normalize data from external sources into `NewsItem`
- `app/agents/` — LLM calls: `news_agent.py` (summarization, tagging), `embedding_agent.py` (embeddings for semantic search)
- `app/services/` — pipeline stages: `ingestion.py` (scrape → save), `enrichment.py` (enrich → save), `indexing.py` (chunk → embed → save)
- `app/database/` — SQLAlchemy connection, models (`news_items`, `news_chunks`), and queries
- `app/schemas/` — shared Pydantic schemas (`NewsItem`, `SearchResult`)
- `app/api/routes/` — FastAPI endpoints: `news.py` (list/get articles), `search.py` (semantic search), `health.py`
- `week6/evaluations/` — fixed evaluation corpus, ground-truth questions, loader, and Week 6 RAG evaluation runner

See `week6/README.md` for grounded question answering and evaluation against
exact numeric, boolean, and short-text answers.
