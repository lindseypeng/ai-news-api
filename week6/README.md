# Week 6: Deploying to Google Cloud Run

Goal: get the AI News API running live on the internet, with a database that
isn't on our laptop, and a weekly job that keeps it updated automatically —
no manual intervention required.

## 1. Update and test the Dockerfile locally

The original `Dockerfile` never installed dependencies at all (`COPY . .`
then `CMD ["python", "-m", "app.main"]`, which would just import the app and
exit immediately). Fixed it to install dependencies via `uv` and run
`uvicorn` as a persistent server on Cloud Run's injected `$PORT`.

Tested locally, against local Postgres, before touching any cloud service:
```bash
docker build -t ai-news-api .
docker compose up -d
docker run --rm -p 8080:8080 --network ai-news-api_default \
  -e DATABASE_URL="postgresql://postgres:postgres@db:5432/postgres" \
  -e OPENAI_API_KEY="..." \
  ai-news-api
curl http://localhost:8080/health/
```

## 2. Set up a Google Cloud project

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Click the project dropdown (top left) → **New Project** → name it → **Create**
3. Go to **Billing** → link a billing account to the project
4. Install the `gcloud` CLI locally, then:
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

## 3. Sign up for Supabase and create a Postgres project

This replaces local Docker Postgres for the deployed app.

1. Go to [supabase.com](https://supabase.com) → **Sign up** (GitHub, Google, or email)
2. Click **New Project** → pick an organization, name it, set a database
   password (save this — it's needed for the connection string), pick a
   region → **Create new project**
3. Wait a minute or two for it to provision
4. Go to **Project Settings → Database → Connection Pooling**, copy the
   **session pooler** connection string (not the direct connection — that's
   IPv6-only on the free tier, and Cloud Run's outbound networking is IPv4)
5. Paste it into `.env`'s `DATABASE_URL`, filling in the real password, and
   append `?sslmode=require`

Test the connection before relying on it:
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

## 4. Create the tables on Supabase

`app/database/create_tables.py` also enables the `vector` extension itself
(`CREATE EXTENSION IF NOT EXISTS vector`), so no separate manual step is
needed for that.
```bash
uv run python -m app.database.create_tables
```

## 5. Store secrets in Google Secret Manager

1. In Cloud Console, go to **Security → Secret Manager → Create Secret**
2. Name it `openai-api-key`, paste in the OpenAI key value, **Create**
3. Repeat for `database-url`, using the Supabase connection string
4. Grant the Cloud Run runtime service account access to both:
   ```bash
   gcloud secrets add-iam-policy-binding openai-api-key \
     --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
     --role="roles/secretmanager.secretAccessor"

   gcloud secrets add-iam-policy-binding database-url \
     --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
     --role="roles/secretmanager.secretAccessor"
   ```
   (Find `PROJECT_NUMBER` via `gcloud projects describe YOUR_PROJECT_ID --format="value(projectNumber)"`.)

## 6. Deploy the API to Cloud Run

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
Builds straight from the `Dockerfile` via Cloud Build and produces a live
HTTPS URL. Test it:
```bash
curl https://YOUR-SERVICE-URL/health/
curl https://YOUR-SERVICE-URL/news/
```

## 7. Create a Cloud Run Job for the batch pipeline

Same container image as the Service, but overridden to run
`python -m app.pipeline` instead of `uvicorn`, then exit — the batch/cron
counterpart to the always-on API. Cloud Run Jobs are a different resource
type, built for "run once, then stop," not for serving requests.
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

Run it manually once to actually seed the database — a scheduled trigger
only handles *future* runs, it doesn't backfill existing empty data:
```bash
gcloud run jobs execute ai-news-pipeline --region europe-west1
```
Verify real rows landed, not just "the job said success" (note: `execute`
returns as soon as the job *starts*, not when it *finishes* — check
`gcloud run jobs executions describe EXECUTION_NAME --region europe-west1`
for `status.conditions[].type: Completed` first):
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

## 8. Set up Cloud Scheduler to trigger the Job weekly

```bash
gcloud services enable cloudscheduler.googleapis.com

gcloud run jobs add-iam-policy-binding ai-news-pipeline \
  --region europe-west1 \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/run.invoker"

gcloud scheduler jobs create http ai-news-pipeline-weekly \
  --location europe-west1 \
  --schedule="0 3 * * 0" \
  --uri="https://europe-west1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/YOUR_PROJECT_ID/jobs/ai-news-pipeline:run" \
  --http-method=POST \
  --oauth-service-account-email=PROJECT_NUMBER-compute@developer.gserviceaccount.com
```

**Gotcha hit here**: this must use `--oauth-service-account-email` (OAuth2),
not `--oidc-service-account-email` (OIDC). OIDC is correct for triggering a
Cloud Run *Service's* own URL, but the Cloud Run Admin API
(`run.googleapis.com`, used to trigger a *Job*) requires a plain OAuth2
token instead. Using OIDC here silently failed with `401 UNAUTHENTICATED` —
only visible by checking Cloud Logging directly, since
`gcloud scheduler jobs describe` alone just showed an unhelpful
`status.code: 2`:
```bash
gcloud logging read 'resource.type="cloud_scheduler_job"' --freshness=10d --format=json
```

Tested the full chain manually before trusting the weekly schedule:
```bash
gcloud scheduler jobs run ai-news-pipeline-weekly --location europe-west1
gcloud run jobs executions list --job ai-news-pipeline --region europe-west1
```
A new execution name appearing confirms Scheduler actually triggered the
Job — not just that Scheduler *tried*.

## 9. Test the live deployment end-to-end

```bash
gcloud run services describe ai-news-api --region europe-west1 --format="value(status.url)"

curl https://YOUR-SERVICE-URL/health/
curl https://YOUR-SERVICE-URL/news/
curl "https://YOUR-SERVICE-URL/search/?q=ai+privacy+concerns"
```
(Quote the `/search/` URL — `?` and `&` have special meaning to the shell.)

Confirmed working: `scraped_at` timestamps on returned articles matched the
exact time the scheduled pipeline run had just finished, proving the data
was genuinely fresh, not cached or fake.

## 10. Security considerations

The service was deployed with `--allow-unauthenticated`, so anyone with the
URL can call every endpoint:

- **SQL injection: not a risk here.** Every query in
  `app/database/repository.py` goes through SQLAlchemy's ORM, which
  parameterizes all values automatically. User input is never concatenated
  into a raw SQL string anywhere in this codebase.
- **Cost abuse: a real, unresolved risk.** `OPENAI_API_KEY` never leaves the
  server, so it can't be stolen through this API. But `/search/` triggers a
  real, billed OpenAI call on *every* request, with no auth and no rate
  limit — anyone can run up the OpenAI bill just by hammering the public
  URL. Not yet implemented, worth considering later: a simple API key on
  `/search/`, rate limiting, or a billing alert/cap on the OpenAI account.

## Why the pipeline runs as a Job, not through the API's main.py

`app/main.py`'s FastAPI app is meant to stay alive indefinitely, answering
requests. `app/pipeline.py`'s `run_pipeline()` is a batch job — it runs once
and exits. These are deliberately two different Cloud Run resource types
(Service vs. Job), matching the original project principle: *"The batch
pipeline writes data. FastAPI reads and serves stored data."*

## Re-running the pipeline is safe

`run_pipeline()` never touches table creation or schema — only
`create_tables.py` does that, run once manually. Every stage
(`ingestion`/`enrichment`/`indexing`) only processes what's new or missing
(`ON CONFLICT DO NOTHING`, `WHERE summary IS NULL`, absence-of-chunks
checks), so the weekly trigger adds new articles without duplicating or
re-processing anything already done.
