# Project

We are building an AI News API.

The application:
- collects news from external sources
- normalizes all sources into one NewsItem format
- enriches articles with an LLM
- stores data in PostgreSQL
- exposes both structured and semantic search through FastAPI

# Workflow

External Sources  
→ Scrapers  
→ Normalization  
→ LLM Enrichment  
→ PostgreSQL

From PostgreSQL, users can query data in two ways:

1. Structured API
   - filter news by fields such as source, topic or date
   - examples: GET /news, GET /news?topic=agents

2. Semantic / RAG API
   - chunk article content
   - create embeddings
   - store vectors with pgvector
   - retrieve relevant chunks with semantic search
   - optionally use an LLM to answer questions
   - examples: GET /search, POST /ask

The batch pipeline writes data.  
FastAPI reads and serves stored data.

# Technology

- Python
- Pydantic
- OpenAI API
- FastAPI
- SQLAlchemy
- PostgreSQL + pgvector
- Docker
- uv
- Render

# Project Structure

text ai-news-api/ ├── app/ │   ├── main.py                  # Start FastAPI │   ├── pipeline.py              # Run news processing pipeline │   ├── config.py                # Settings and environment variables │   ├── api/                     # HTTP endpoints │   ├── scrapers/                # Collect external news │   ├── agents/                  # LLM logic │   ├── services/                # Coordinate workflows │   ├── database/                # Store/query PostgreSQL │   └── schemas/                 # Shared data models ├── tests/ ├── Dockerfile ├── docker-compose.yml ├── render.yaml ├── .env.example ├── pyproject.toml └── README.md 

# Principles

- Keep the project simple and build incrementally.
- Use one canonical NewsItem schema.
- Keep scraping, LLM, database and API logic separate.
- The API should query stored data, not scrape during requests.
- Use PostgreSQL for both structured data and vector search.
- Do not add tools or frameworks unless they solve a clear requirement.
