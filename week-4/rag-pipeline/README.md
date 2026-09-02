# End-to-End RAG Pipeline

This directory contains a complete implementation of a Retrieval-Augmented Generation (RAG) pipeline using PGVector, OpenAI embeddings, and a set of sample news articles bundled in `sample_data/` as the example dataset. This folder is self-contained: the sample data is committed here, so it doesn't depend on the main app's scraping/enrichment pipeline having been run.

## Project Structure

```text
rag-pipeline/
├── rag_chat.py                 # Interactive query interface
├── examples.py                 # Usage examples
├── build_vectordb.py           # Database setup script (run once)
├── README.md                   # This file
├── sample_data/                # Bundled sample news articles (NewsItem JSON)
└── rag/                        # Implementation package (no need to modify)
    ├── __init__.py     
    ├── config.py               # Configuration settings
    ├── rag_system.py           # Main orchestrator
    ├── vector_store.py         # PGVector interface
    ├── document_processor.py   # Document chunking
    └── embedding_service.py    # Embedding generation
```

## Architecture Overview

The RAG pipeline consists of the following components:

1. **Document Processing**: Load and chunk local news article JSON files
2. **Embedding Generation**: Create embeddings using OpenAI's text-embedding-3-small
3. **Vector Storage**: Store embeddings in PGVector database
4. **Similarity Search**: Query the database to find relevant chunks
5. **Response Generation**: Use retrieved context to generate answers with OpenAI

## Prerequisites

- Docker and Docker Compose installed
- OpenAI API key
- `uv` installed (this pipeline runs inside the main project's environment,
  it has no dependencies of its own)

## Dependencies

This pipeline's packages are declared in the root `pyproject.toml`/`uv.lock`
and installed automatically by `uv sync` (Setup step 1 below) — no manual
`uv add` needed. Beyond what the main app already required (`openai`,
`dotenv`), this pipeline specifically needs:

- `pgvector` — SQLAlchemy/psycopg integration for Postgres's `vector` type
- `psycopg[binary]` — the Postgres driver `vector_store.py` connects with
- `tiktoken` — token-based chunking in `document_processor.py`
- `tqdm` — progress bars in `embedding_service.py`

## Setup

1. From the project root, install dependencies and set up `.env` (skip if
   already done for the main app):
   ```bash
   uv sync
   cp .env.example .env   # fill in OPENAI_API_KEY
   ```

2. Start Postgres (pgvector-enabled) from the project root:
   ```bash
   docker compose up -d
   ```

3. `cd week-4/rag-pipeline` before running anything below.

## Usage

### Step 1: Build the Vector Database

First, populate the vector database with your local news articles:

```bash
uv run python build_vectordb.py
```

This will:
- Load every article JSON file from `sample_data/`
- Split each article into token-based chunks
- Generate embeddings for each chunk
- Store everything in PGVector

### Step 2: Query the System

Run the interactive query interface:

```bash
uv run python rag_chat.py
```

### Step 3: Explore Examples

Study the example scripts to understand different usage patterns:

```bash
uv run python examples.py
```

## Programmatic Usage

You can also use the RAG system in your own Python scripts:

```python
from rag import RAGSystem

# Initialize the system
rag = RAGSystem()

# Ask a question
response = rag.query("What is the Felony Bench and how does it evaluate AI models?")
print(response)

# Get more context
response_with_context = rag.query(
    "How does Cobalt let Kobo e-readers run apps?",
    show_context=True  # Shows the retrieved chunks
)
print(response_with_context)
```
