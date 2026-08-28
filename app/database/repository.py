from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.database.models import NewsItemModel
from app.schemas.news import NewsItem


def insert_news_item(db: Session, item: NewsItem) -> NewsItemModel | None:
    """Insert a NewsItem, skipping it if (source, source_id) already exists."""

    stmt = (
        pg_insert(NewsItemModel)
        .values(
            source=item.source,
            source_id=item.source_id,
            title=item.title,
            url=str(item.url),
            author=item.author,
            content=item.content,
            scraped_at=item.scraped_at,
            summary=item.summary,
            tags=item.tags,
        )
        .on_conflict_do_nothing(index_elements=["source", "source_id"])
        .returning(NewsItemModel)
    )

    row = db.execute(stmt).scalar_one_or_none()
    db.commit()
    return row


def get_unenriched_news_items(db: Session) -> list[NewsItemModel]:
    """Return news items that haven't been enriched yet."""
    return db.query(NewsItemModel).filter(NewsItemModel.summary.is_(None)).all()


def get_all_news_items(db: Session, limit: int = 50) -> list[NewsItemModel]:
    """Return the most recent news items, newest first."""
    return (
        db.query(NewsItemModel)
        .order_by(NewsItemModel.scraped_at.desc())
        .limit(limit)
        .all()
    )


def get_news_item(db: Session, item_id: int) -> NewsItemModel | None:
    """Return a single news item by id, or None if it doesn't exist."""
    return db.get(NewsItemModel, item_id)


def save_enrichment(db: Session, item_id: int, summary: str, tags: list[str]) -> NewsItemModel:
    """Update a news item's summary and tags after LLM enrichment."""
    row = db.get(NewsItemModel, item_id)
    row.summary = summary
    row.tags = tags
    db.commit()
    db.refresh(row)
    return row
