from app.agents.news_agent import enrich_article
from app.database.connection import SessionLocal
from app.database.repository import get_unenriched_news_items, save_enrichment


def run_enrichment() -> None:
    db = SessionLocal()
    try:
        for row in get_unenriched_news_items(db):
            if not row.content:
                continue

            enrichment = enrich_article(row.title, row.content)
            save_enrichment(db, row.id, summary=enrichment.summary, tags=enrichment.tags)

            print(f"Enriched: {row.title}")
    finally:
        db.close()


if __name__ == "__main__":
    run_enrichment()
