from sqlalchemy import Column, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY

from app.database.connection import Base


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
