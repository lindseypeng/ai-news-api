# Week 6: Deploying to Google Cloud Run

Goal: get the AI News API running live on the internet, with a database that
isn't on our laptop, and a weekly job that keeps it updated automatically —
no manual intervention required.

Almost all of this work is cloud infrastructure configuration (via `gcloud`),
not code — one small `Dockerfile` fix aside, everything below happened
outside git, directly against Google Cloud and Supabase.

## Cloud resources created (not files — these live in GCP/Supabase, not git)

- **Supabase Postgres project** — replaces local Docker Postgres for the
  deployed app. Uses the **session pooler** connection (not the direct
  connection), because Supabase's direct connection is IPv6-only on the free
  tier, and Cloud Run's outbound networking is IPv4.
- **Secret Manager secrets**: `openai-api-key`, `database-url` — the deployed
  app reads these as env vars (`OPENAI_API_KEY`, `DATABASE_URL`), same names
  it already expected locally via `.env`.
- **Cloud Run Service**: `ai-news-api` — the actual deployed API, built
  straight from the `Dockerfile` via Cloud Build.
- **Cloud Run Job**: `ai-news-pipeline` — same container image as the
  Service, but overridden to run `python -m app.pipeline` instead of
  `uvicorn`, then exit. This is the batch/cron counterpart to the always-on
  API — Cloud Run Jobs are a different resource type built for "run once,
  then stop," not for serving requests.
- **Cloud Scheduler job**: `ai-news-pipeline-weekly` — triggers the Job every
  Sunday via HTTP against the Cloud Run Admin API.

## Code change

**`Dockerfile`** — the previous version never installed dependencies at all
(`COPY . .` then `CMD ["python", "-m", "app.main"]`, which would just import
the app and exit immediately). The new version installs `uv`, runs
`uv sync --frozen --no-dev` in its own cached layer, and runs
`uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}` as a persistent
server listening on Cloud Run's injected `$PORT`.

## Terminal commands run, in order

1. **Test the Docker image locally first**, before touching any cloud
   resources — confirms the image builds and the app actually serves
   requests:
   ```bash
   docker build -t ai-news-api .
   docker compose up -d
   docker run --rm -p 8080:8080 --network ai-news-api_default \
     -e DATABASE_URL="postgresql://postgres:postgres@db:5432/postgres" \
     -e OPENAI_API_KEY="..." \
     ai-news-api
   curl http://localhost:8080/health/
   ```

2. **Set up Supabase**, then update `.env`'s `DATABASE_URL` to the session
   pooler connection string, with `?sslmode=require` appended. Test it before
   relying on it:
   ```bash
   uv run python -c "
   import os
   from dotenv import load_dotenv
   load_dotenv()
   from sqlalchemy import create_engine, text
   engine = create_engine(os.getenv('DATABASE_URL'))
   with engine.connect() as conn:
       print(conn.execute(text('SELECT version()')).scalar())
   "
   ```

3. **Create the tables on Supabase** (also enables the `vector` extension —
   `app/database/create_tables.py` already runs
   `CREATE EXTENSION IF NOT EXISTS vector` itself):
   ```bash
   uv run python -m app.database.create_tables
   ```

4. **Create the two secrets** in Secret Manager (via Console or
   `gcloud secrets create`), then grant the Cloud Run runtime service account
   access to read them:
   ```bash
   gcloud secrets add-iam-policy-binding openai-api-key \
     --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
     --role="roles/secretmanager.secretAccessor"

   gcloud secrets add-iam-policy-binding database-url \
     --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
     --role="roles/secretmanager.secretAccessor"
   ```

5. **Deploy the API**:
   ```bash
   gcloud run deploy ai-news-api \
     --source . \
     --region europe-west1 \
     --allow-unauthenticated \
     --min-instances 0 \
     --max-instances 1 \
     --cpu 1 \
     --memory 512Mi \
     --set-secrets OPENAI_API_KEY=openai-api-key:latest,DATABASE_URL=database-url:latest
   ```
   Test it:
   ```bash
   curl https://YOUR-SERVICE-URL/health/
   curl https://YOUR-SERVICE-URL/news/
   ```

6. **Create the Cloud Run Job**, reusing the same image the Service just
   built, overriding the command to run the batch pipeline instead:
   ```bash
   # Get the image the deployed Service is using
   gcloud run services describe ai-news-api --region europe-west1 \
     --format="value(spec.template.spec.containers[0].image)"

   gcloud run jobs create ai-news-pipeline \
     --image PASTE_IMAGE_HERE \
     --region europe-west1 \
     --set-secrets OPENAI_API_KEY=openai-api-key:latest,DATABASE_URL=database-url:latest \
     --command python \
     --args="-m,app.pipeline" \
     --max-retries 0 \
     --task-timeout 900
   ```

7. **Run the Job manually once**, to actually seed the database (a scheduled
   trigger only handles *future* runs — it doesn't backfill existing empty
   data):
   ```bash
   gcloud run jobs execute ai-news-pipeline --region europe-west1
   ```
   Verify real rows landed, not just "the job said success":
   ```bash
   uv run python -c "
   import os
   from dotenv import load_dotenv
   load_dotenv()
   from sqlalchemy import create_engine, text
   engine = create_engine(os.getenv('DATABASE_URL'))
   with engine.connect() as conn:
       print('news_items:', conn.execute(text('SELECT count(*) FROM news_items')).scalar())
       print('news_chunks:', conn.execute(text('SELECT count(*) FROM news_chunks')).scalar())
   "
   ```
   Note: `gcloud run jobs execute` returns as soon as the execution *starts*,
   not when it *finishes* — check
   `gcloud run jobs executions describe EXECUTION_NAME --region europe-west1`
   for `status.conditions[].type: Completed` before assuming it's done.

8. **Enable the Cloud Scheduler API** (new APIs aren't enabled by default —
   the Console showed "no access" until this ran):
   ```bash
   gcloud services enable cloudscheduler.googleapis.com
   ```

9. **Grant the service account permission to invoke the Job** (separate from
   Secret Manager access — this specifically lets it trigger executions):
   ```bash
   gcloud run jobs add-iam-policy-binding ai-news-pipeline \
     --region europe-west1 \
     --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
     --role="roles/run.invoker"
   ```

10. **Create the Scheduler job**, targeting the Cloud Run Admin API's "run"
    endpoint for this Job:
    ```bash
    gcloud scheduler jobs update http ai-news-pipeline-weekly \
      --location europe-west1 \
      --oauth-service-account-email=PROJECT_NUMBER-compute@developer.gserviceaccount.com
    ```
    **Important gotcha we hit**: this must use `--oauth-service-account-email`
    (OAuth2), not `--oidc-service-account-email` (OIDC). OIDC is correct for
    triggering a Cloud Run *Service's* own URL, but the Cloud Run Admin API
    (`run.googleapis.com`, used to trigger a *Job*) requires a plain OAuth2
    access token instead. Using OIDC here silently fails with a `401
    UNAUTHENTICATED` — visible only by checking Cloud Logging directly:
    ```bash
    gcloud logging read 'resource.type="cloud_scheduler_job"' --freshness=10d --format=json
    ```
    `gcloud scheduler jobs describe` alone only showed an unhelpful
    `status.code: 2` — the actual `401`/`UNAUTHENTICATED` reason only showed
    up in the logs.

11. **Test the full chain manually before trusting the weekly schedule**:
    ```bash
    gcloud scheduler jobs run ai-news-pipeline-weekly --location europe-west1
    gcloud run jobs executions list --job ai-news-pipeline --region europe-west1
    ```
    A new execution name appearing confirms Scheduler successfully triggered
    the Job — not just that Scheduler *tried*.

## Testing the live deployment

Get the deployed URL, then hit it directly — same endpoints as local dev,
just `https://` with no port instead of `http://localhost:8001`:
```bash
gcloud run services describe ai-news-api --region europe-west1 --format="value(status.url)"

curl https://YOUR-SERVICE-URL/health/
curl https://YOUR-SERVICE-URL/news/
curl "https://YOUR-SERVICE-URL/search/?q=ai+privacy+concerns"
```
(Quote the `/search/` URL — `?` and `&` in a query string have special
meaning to the shell, `&` especially, since it means "run in background.")

Confirmed working end to end: `scraped_at` timestamps on returned articles
matched the exact time the scheduled pipeline run had just finished,
proving the data was genuinely fresh, not cached or fake.

## Security considerations

The service was deployed with `--allow-unauthenticated`, so anyone with the
URL can call every endpoint, with two different implications:

- **SQL injection: not a risk here.** Every query in `app/database/repository.py`
  goes through SQLAlchemy's ORM (`.filter()`, `.query()`, `pg_insert().values()`),
  which parameterizes all values automatically. User input (`q`, `item_id`)
  is never concatenated into a raw SQL string anywhere in this codebase.
- **Cost abuse: a real, unresolved risk.** `OPENAI_API_KEY` itself never
  leaves the server (it's only used inside `embedding_agent.py`/`news_agent.py`),
  so it can't be stolen through this API. But `/search/` calls
  `create_embedding()` — a real, billed OpenAI call — on *every* request,
  with no auth and no rate limit. Anyone can run up the OpenAI bill just by
  hammering the public `/search/` URL. `/news/` and `/health/` don't call
  OpenAI, so they're comparatively low-risk (aside from ordinary Cloud Run
  compute cost, capped somewhat by `--max-instances 1`).

  Not yet implemented, worth considering later: a simple API key required
  on `/search/` (separate from the OpenAI key), rate limiting, or a billing
  alert/cap on the OpenAI account as a cheaper stopgap.

## Why the pipeline runs as a Job, not through the API's main.py

`app/main.py`'s FastAPI app is meant to stay alive indefinitely, answering
requests. `app/pipeline.py`'s `run_pipeline()` is a batch job — it runs once
and exits. These are deliberately two different Cloud Run resource types
(Service vs. Job) for exactly this reason, matching the original project
principle: *"The batch pipeline writes data. FastAPI reads and serves stored
data."*

## Re-running the pipeline is safe

`run_pipeline()` never touches table creation or schema — only
`create_tables.py` does that, run once manually. Every stage
(`ingestion`/`enrichment`/`indexing`) only processes what's new or missing
(`ON CONFLICT DO NOTHING`, `WHERE summary IS NULL`, absence-of-chunks
checks), so the weekly trigger adds new articles without duplicating or
re-processing anything already done.
