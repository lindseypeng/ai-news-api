from sqlalchemy import text

from app.database.connection import Base, engine
from app.database.models import NewsChunkModel, NewsItemModel  # noqa: F401


def create_tables() -> None:
    """Enable pgvector and create all tables defined in the SQLAlchemy models."""
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    print("Tables to be created:")
    for table in Base.metadata.tables:
        print(f"- {table}")

    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    create_tables()
    print("Tables created successfully.")
