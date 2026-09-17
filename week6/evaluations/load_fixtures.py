import json
from datetime import datetime, timezone
from pathlib import Path

from app.agents.embedding_agent import create_embedding
from app.database.connection import SessionLocal
from app.database.models import NewsChunkModel, NewsItemModel
from app.database.repository import insert_news_chunks, insert_news_item
from app.schemas.news import NewsItem
from app.services.indexing import _chunk_text

FIXTURES_PATH = Path(__file__).with_name("fixtures.json")


def load_fixtures() -> None:
    """Insert and index the fixed Week 6 evaluation corpus."""

    fixtures = json.loads(FIXTURES_PATH.read_text())
    db = SessionLocal()
    try:
        for fixture in fixtures:
            existing = (
                db.query(NewsItemModel)
                .filter_by(source=fixture["source"], source_id=fixture["source_id"])
                .one_or_none()
            )
            if existing is None:
                item = NewsItem(
                    **fixture,
                    scraped_at=datetime.now(timezone.utc),
                    summary=None,
                    tags=["week-6-evaluation"],
                )
                existing = insert_news_item(db, item)
                print(f"Inserted fixture: {fixture['title']}")
            else:
                print(f"Fixture already present: {fixture['title']}")

            has_chunks = (
                db.query(NewsChunkModel.id)
                .filter_by(news_item_id=existing.id)
                .first()
                is not None
            )
            if has_chunks:
                print("  Already indexed")
                continue

            chunks = [
                {"content": text, "embedding": create_embedding(text)}
                for text in _chunk_text(existing.content)
            ]
            insert_news_chunks(db, existing.id, chunks)
            print(f"  Indexed {len(chunks)} chunk(s)")
    finally:
        db.close()


if __name__ == "__main__":
    load_fixtures()
