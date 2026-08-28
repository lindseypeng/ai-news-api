from datetime import datetime

from pydantic import BaseModel, ConfigDict, HttpUrl


class NewsItem(BaseModel):
    """Canonical news item shared across scraping, enrichment, storage and the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None

    # Populated by scrapers / normalization
    source: str
    source_id: str
    title: str
    url: HttpUrl
    author: str | None = None
    content: str | None = None
    scraped_at: datetime

    # Populated later by LLM enrichment
    summary: str | None = None
    tags: list[str] = []


class ArticleEnrichment(BaseModel):
    """Structured LLM output produced from an article's title and content."""

    summary: str
    tags: list[str]
