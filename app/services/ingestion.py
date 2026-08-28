from app.database.connection import SessionLocal
from app.database.repository import insert_news_item
from app.scrapers.hackernews import scrape_top_stories


def run_ingestion() -> None:
    news_items = scrape_top_stories()

    db = SessionLocal()
    try:
        for item in news_items:
            row = insert_news_item(db, item)
            if row:
                print(f"Inserted: {row.title}")
            else:
                print(f"Skipped (already exists): {item.title}")
    finally:
        db.close()


if __name__ == "__main__":
    run_ingestion()
