# Week 7: Langfuse Observability and Prompt Management

This lab adapts the earlier `week-5/langfuse` exercises to the AI News API and
the current Langfuse Python SDK. Langfuse adds LLM-specific observability:
traces show inputs, outputs, latency, token usage, cost, errors, and the nested
steps that produced a result.

Langfuse is separate from PostgreSQL. PostgreSQL remains the source of truth for
news and vectors; Langfuse explains how the LLM portions of a request behaved.

## Teaching guide: what Langfuse does

Traditional application monitoring tells us whether an API request succeeded,
failed, or was slow. Langfuse adds visibility into the AI-specific parts of the
request: which prompt and model were used, what the model received and returned,
how many tokens it consumed, what it cost, and which intermediate steps led to
the result.

A useful way to explain the distinction is:

> PostgreSQL tells us what data we have. Langfuse tells us what the AI did with
> that data.

### Core concepts

| Concept | Meaning |
| --- | --- |
| Trace | One complete request or workflow, such as answering one news question. |
| Observation | One recorded step inside a trace. |
| Generation | An observation representing an LLM call, including its prompt, response, model, token usage, and cost. |
| Span | A timed operation such as retrieval, preprocessing, or orchestration. |
| Metadata | Application-specific context, such as article length, relevance, or topic count. |
| Tags | Labels used to group and filter related traces. |
| Prompt | A centrally stored, versioned instruction that can be changed independently of application code. |
| Score | A quality measurement attached to a trace or observation, from evaluation code, user feedback, or human review. |
| Session | A group of related traces, such as all turns in one conversation. |

### Minimum setup: two small code changes

At minimum, Langfuse tracing can be added with two small code changes:

```python
from langfuse import observe
from langfuse.openai import OpenAI  # replaces: from openai import OpenAI

client = OpenAI()


@observe(name="week-7-news-analysis")
def analyze_news(title: str, content: str):
    # Calls made with this client are traced automatically.
    return client.responses.create(
        model="gpt-4o-mini",
        input=f"Title: {title}\n\nContent: {content}",
    )
```

1. Replace the normal OpenAI import with Langfuse's instrumented OpenAI
   wrapper. This automatically records the model, input, output, token usage,
   latency, estimated cost, and errors.
2. Add `@observe()` to the business operation. The decorator creates a named
   parent observation that groups the work performed inside the function.

The OpenAI wrapper can create a trace by itself, so the decorator is not
strictly required. The decorator adds business meaning and becomes especially
useful when one operation contains multiple steps:

> One changed import gives us automatic model-call telemetry. One decorator
> organizes that telemetry under a named business workflow.

The credentials in `.env` are still required, but they are configuration rather
than changes to the application logic.

### Put multiple functions under one observed workflow

Make the business operation the decorated parent, then call child functions
from inside it. Langfuse propagates the active trace context automatically:

```python
from langfuse import observe


@observe(name="retrieve-news", as_type="retriever")
def retrieve_news(question: str):
    return ["Relevant article chunk"]


@observe(name="generate-answer", as_type="generation")
def generate_answer(question: str, contexts: list[str]):
    return "A grounded answer"


@observe(name="answer-news-question", as_type="chain")
def answer_news_question(question: str):
    contexts = retrieve_news(question)
    return generate_answer(question, contexts)
```

This produces one hierarchy:

```text
answer-news-question          <- parent business workflow
  -> retrieve-news            <- child observation
  -> generate-answer          <- child observation
```

There is no need to pass a trace ID between these synchronous functions. The
nesting comes from calling the decorated children while the decorated parent is
active. A regular, undecorated helper still runs under the parent, but it will
not appear as its own step. OpenAI calls made through the Langfuse wrapper do
appear automatically as generation children.

### What each Week 7 example demonstrates

#### `week-7-simple-summary`

This is the smallest observability example:

```text
Headline -> OpenAI -> Summary
```

Its trace shows the input headline, model, instructions, generated summary,
latency, token usage, estimated cost, and any OpenAI error. The teaching point
is that one trace lets us inspect an entire AI request instead of reconstructing
it from ordinary application logs.

#### `week-7-news-analysis`

This example represents a structured enrichment workflow:

```text
Article -> Structured LLM analysis -> Summary + topics + relevance
```

The model must return predictable fields rather than unrestricted prose. The
trace also records news-specific metadata such as content length, topic count,
and relevance. This demonstrates how Langfuse combines technical telemetry with
the business context needed to understand application behavior.

#### `week-7-managed-prompt`

This example stores the summarization prompt in Langfuse rather than treating
it as an anonymous string embedded permanently in Python:

```text
Versioned Langfuse prompt
          -> compile title and content
          -> OpenAI generation
          -> trace linked to the exact prompt version
```

Prompt management lets a team compare versions, assign a `production` label,
change prompts without deploying code, and roll back when a new version performs
poorly. Linking traces to prompt versions makes it possible to measure which
version produced each result.

### How it maps to the AI News API

The grounded-answer endpoint follows this workflow:

```text
POST /ask
  -> create a query embedding
  -> retrieve relevant PostgreSQL chunks
  -> generate an answer grounded in those chunks
```

Langfuse can reveal whether a bad answer came from the model, the supplied
context, an unexpected prompt version, or another observed step. Over time,
teams can use these traces to investigate errors, latency, token costs, and
quality regressions instead of treating the LLM as a black box.

## What is wired into the application

The OpenAI clients in `app/agents/` use Langfuse's drop-in OpenAI wrapper. Once
the optional Langfuse credentials are set, the existing enrichment, embedding,
semantic search, and grounded-answer calls produce observations automatically.
Without Langfuse credentials, the API continues to use OpenAI normally.

This folder contains two standalone learning exercises based on the original
lab:

- `langfuse-setup.py` demonstrates a minimal observed call and a nested,
  structured news-analysis workflow.
- `prompt-management.py` creates a versioned prompt, fetches its `production`
  version, compiles template variables, and links the OpenAI generation to that
  exact prompt version.

The older PydanticAI example is intentionally not copied because this project
does not use PydanticAI, and adding it would introduce a framework solely for a
demo.

## Setup

1. Install the locked dependencies:

   ```bash
   uv sync
   ```

2. Create a free project at <https://cloud.langfuse.com> and copy its API keys.

3. In `.env`, set:

   ```dotenv
   OPENAI_API_KEY=your_openai_api_key
   LANGFUSE_PUBLIC_KEY=pk-lf-...
   LANGFUSE_SECRET_KEY=sk-lf-...
   LANGFUSE_BASE_URL=https://cloud.langfuse.com
   ```

`LANGFUSE_BASE_URL` above selects the EU cloud region. Use the base URL shown by
your Langfuse project if it lives in another region.

## Lab 1: tracing

Run:

```bash
uv run python week-7/langfuse-setup.py
```

Then open **Tracing** in Langfuse. You should see:

1. `week-7-simple-summary`, containing one OpenAI generation; and
2. `week-7-news-analysis`, containing the structured generation plus tags and
   news-specific metadata.

The script calls `flush()` because it exits immediately. The FastAPI server is
long-running, so the SDK sends its batched events in the background.

## Lab 2: prompt management

Run:

```bash
uv run python week-7/prompt-management.py
```

The script creates a new version of `ai-news-summary` each time it runs, labels
that version `production`, retrieves it through the SDK, compiles `{{title}}`
and `{{content}}`, and sends it to OpenAI. Inspect both **Prompt Management**
and **Tracing** in Langfuse. Edit the production prompt in the UI and rerun the
script to see prompt changes without changing application code.

## Observe the real API

After the labs, run the normal application and call `/ask/`:

```bash
uv run uvicorn app.main:app --reload --port 8001
curl -X POST http://localhost:8001/ask/ \
  -H 'Content-Type: application/json' \
  -d '{"question":"What percentage of search queries were ASCII-only?"}'
```

The trace will include the query embedding and grounded answer generation.

## Optional: self-host the Langfuse UI

For a completely local UI and trace store, follow Langfuse's official Docker
Compose guide and set `LANGFUSE_BASE_URL=http://localhost:3000`. Keep that stack
separate from this repository's PostgreSQL Compose file: modern Langfuse needs
multiple supporting services and significantly more resources than this API.
