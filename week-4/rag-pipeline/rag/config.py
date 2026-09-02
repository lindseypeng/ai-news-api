"""Configuration settings for the RAG pipeline."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
DATABASE_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "postgres",
    "user": "postgres",
    "password": "postgres",
}

# OpenAI configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
CHAT_MODEL = "gpt-4o-mini"

# Document processing
RAG_PIPELINE_DIR = Path(__file__).resolve().parents[1]
NEWS_DATA_DIR = RAG_PIPELINE_DIR / "sample_data"
MAX_TOKENS_PER_CHUNK = 500

# Vector search
TOP_K_RESULTS = 5
SIMILARITY_THRESHOLD = 0.3
