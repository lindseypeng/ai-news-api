from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY

from app.database.connection import Base

EMBEDDING_DIMENSIONS = 1536


class NewsItemModel(Base):
    """SQLAlchemy table definition, mirroring app/schemas/news.py's NewsItem."""

    __tablename__ = "news_items"
    __table_args__ = (
        UniqueConstraint("source", "source_id", name="uq_news_items_source_source_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Populated by scrapers / normalization
    source = Column(String, nullable=False)
    source_id = Column(String, nullable=False)
    title = Column(String, nullable=False)
    url = Column(String, nullable=False)
    author = Column(String, nullable=True)
    content = Column(Text, nullable=True)
    scraped_at = Column(DateTime(timezone=True), nullable=False)

    # Populated later by LLM enrichment
    summary = Column(Text, nullable=True)
    tags = Column(ARRAY(String), nullable=False, default=list)


class NewsChunkModel(Base):
    """A chunk of a news article's content, with its embedding for semantic search."""

    __tablename__ = "news_chunks"
    __table_args__ = (
        UniqueConstraint(
            "news_item_id", "chunk_index", name="uq_news_chunks_item_chunk_index"
        ),
        Index(
            "ix_news_chunks_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_ip_ops"},
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    news_item_id = Column(Integer, ForeignKey("news_items.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(EMBEDDING_DIMENSIONS), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
