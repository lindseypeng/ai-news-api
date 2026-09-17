from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


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


class SearchResult(BaseModel):
    """A single semantic search hit: a matching chunk and its parent article."""

    news_item_id: int
    title: str
    url: HttpUrl
    chunk_content: str
    similarity: float


class AskRequest(BaseModel):
    """A question to answer from semantically retrieved news chunks."""

    question: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=10)


class AnswerCitation(BaseModel):
    """Article and chunk used to support an answer."""

    news_item_id: int
    source_id: str
    title: str
    url: HttpUrl
    chunk_content: str


class GroundedAnswer(BaseModel):
    """Structured answer generated only from retrieved context."""

    answer: str
    supported: bool


class AskResponse(BaseModel):
    """Grounded answer plus the retrieved evidence used to generate it."""

    question: str
    answer: str
    supported: bool
    citations: list[AnswerCitation]
