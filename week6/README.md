# Week 6: Evaluating RAG Question Answering

Week 6 measures whether semantic retrieval plus an LLM can answer factual
questions from the news corpus. The evaluation uses deterministic questions
whose answers are explicitly present in the Week 4 sample articles.

## What is evaluated

The dataset in `evaluations/questions.json` contains:

- percentage and count questions with one exact numeric answer;
- true/false questions grounded in explicit article statements; and
- a short text question with a canonical answer and accepted alias.

Each case also records the expected source article's `source_id`. This metadata
helps diagnose retrieval failures, but it is not sent to the API and therefore
does not give the system the answer.

The Motorola sample is intentionally excluded. Its extracted `content` only
contains a Mastodon JavaScript notice, while its summary claims facts that are
not present in that content. Treating the summary as ground truth would hide a
data-quality problem rather than evaluate RAG faithfully.

## RAG answer flow

`POST /ask/` performs four steps:

1. Embed the question.
2. Retrieve the five most similar chunks from pgvector.
3. Ask the LLM to answer only from those chunks.
4. Return the answer, whether it is supported, and the retrieved citations.

Example:

```bash
curl -X POST http://localhost:8001/ask/ \
  -H 'Content-Type: application/json' \
  -d '{"question":"True or false: Cobalt replaces Kobo’s boot chain.","limit":5}'
```

## Run the evaluation

The configured Supabase database did not contain these older sample records, so
`evaluations/fixtures.json` contains a compact evaluation corpus derived from
the relevant sample articles. Load and index it once:

```bash
uv run python -m evaluations.load_fixtures
```

The loader is idempotent: it skips existing articles and chunks. It calls the
embedding API only for fixtures that are not indexed yet.

Start the API, then run:

```bash
uv run python -m evaluations.run_evaluation --base-url http://localhost:8001
```

The runner requires both retrieval of the expected source article and a correct
answer for an end-to-end pass. It reports retrieval accuracy, answer accuracy,
and combined end-to-end accuracy separately. A less-than-perfect result is
expected and useful: it shows whether failures come from retrieval or answer
generation. Scoring uses the first number for numeric answers, the leading
true/false or yes/no for booleans, and normalized text matching for short text
answers.

By default this is a reporting exercise, so a low score does not make the
command fail. To use the evaluation as a CI quality gate, set a threshold such
as 70%:

```bash
uv run python -m evaluations.run_evaluation \
  --base-url http://localhost:8001 \
  --minimum-accuracy 0.70
```

Several cases are deliberately non-trivial. For example, the OpenAI Felony
Bench question requires adding multiple table rows, while similar percentages
in the travel article test whether retrieval and generation select the right
number. These questions can legitimately fail; their answers are not hardcoded
into the API.

Run the scorer's offline tests without a database or OpenAI call:

```bash
uv run python -m unittest tests/test_evaluation_scoring.py
```

## Interpreting failures

- Wrong or irrelevant citations indicate a retrieval failure.
- Correct citations with a wrong answer indicate a generation failure.
- `supported: false` means the retrieved evidence was insufficient.
- A source article without the answer in its actual content indicates a data
  quality failure and should not be counted as a model failure.
