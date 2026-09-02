"""
SQLAlchemy Integration with pgvector

This file demonstrates how to use pgvector with SQLAlchemy ORM, showing:
- SQLAlchemy model definition with vector columns
- Type-safe document operations
- Metadata filtering
- Full-text search integration
- Proper session management
"""

import os
from typing import List, Optional

from dotenv import load_dotenv
from openai import OpenAI
from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Column,
    Computed,
    DateTime,
    Integer,
    String,
    create_engine,
    text,
)
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

# Database setup
DRIVER = "psycopg"
DATABASE_URL = f"postgresql+{DRIVER}://postgres:postgres@localhost:5432/postgres"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class Document(Base):
    __tablename__ = "documents_sqlalchemy"

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(String, nullable=False)
    metadata_json = Column("metadata", JSON)
    embedding = Column(Vector(1536))
    fts = Column(TSVECTOR, Computed("to_tsvector('english', content)", persisted=True))
    created_at = Column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )


def get_embedding(text: str) -> List[float]:
    """Generate embeddings using OpenAI."""
    response = client.embeddings.create(
        model="text-embedding-3-small", input=text, dimensions=1536
    )
    return response.data[0].embedding


class VectorStore:
    def __init__(self):
        self.session = SessionLocal()

    def add_document(self, content: str, metadata: Optional[dict] = None):
        """Add a document to the vector store."""
        embedding = get_embedding(content)

        doc = Document(
            content=content, metadata_json=metadata or {}, embedding=embedding
        )

        self.session.add(doc)
        self.session.commit()
        return doc.id

    def search(
        self, query: str, limit: int = 5, metadata_filter: Optional[dict] = None
    ):
        """Search for similar documents with optional metadata filtering."""
        query_embedding = get_embedding(query)

        # Base query
        query_obj = self.session.query(
            Document.id,
            Document.content,
            Document.metadata_json,
            (-Document.embedding.max_inner_product(query_embedding)).label(
                "similarity"
            ),
        )

        # Apply metadata filter if provided
        if metadata_filter:
            print(f"Applying metadata filter: {metadata_filter}")
            for key, value in metadata_filter.items():
                # Use PostgreSQL JSON operator ->> to extract text
                query_obj = query_obj.filter(
                    text(f"metadata->>'{key}' = :value")
                ).params(value=str(value))
                print(f"Filtering for {key}={value}")

        # Order by similarity (descending since higher similarity scores are better)
        results = query_obj.order_by(text("similarity DESC")).limit(limit).all()
        print(f"Found {len(results)} results")

        return [
            {
                "id": r.id,
                "content": r.content,
                "metadata": r.metadata_json,
                "similarity": r.similarity,
            }
            for r in results
        ]

    def delete_document(self, doc_id: int):
        """Delete a document by ID."""
        self.session.query(Document).filter(Document.id == doc_id).delete()
        self.session.commit()

    def close(self):
        """Close the database session."""
        self.session.close()


def insert_documents():
    """Insert a list of documents into the database."""
    store = VectorStore()
    try:
        print("Adding documents to vector store...")

        docs = [
            (
                "Python is a versatile programming language.",
                {"type": "programming", "language": "Python"},
            ),
            (
                "JavaScript runs in browsers and Node.js.",
                {"type": "programming", "language": "JavaScript"},
            ),
            (
                "Machine learning models can predict outcomes.",
                {"type": "AI", "category": "ML"},
            ),
            (
                "Docker containers package applications.",
                {"type": "devops", "tool": "Docker"},
            ),
            (
                "Kubernetes orchestrates container deployments.",
                {"type": "devops", "tool": "Kubernetes"},
            ),
        ]

        print("Inserting documents...")
        for doc in docs:
            doc_id = store.add_document(doc[0], doc[1])
            print(f"Inserted document {doc_id}: {doc[0][:50]}...")
    finally:
        store.close()


def search_documents(
    query: str, limit: int = 5, metadata_filter: Optional[dict] = None
):
    """Search for documents using vector similarity."""
    store = VectorStore()
    try:
        print(f"\n--- Searching for '{query}' ---")
        if metadata_filter:
            print(f"With metadata filter: {metadata_filter}")

        results = store.search(query, limit, metadata_filter)
        for r in results:
            print(f"Similarity: {r['similarity']:.4f} - {r['content']}")
            if metadata_filter:
                print(f"Metadata: {r['metadata']}")
    finally:
        store.close()


def create_tables():
    """Create tables in the database."""
    # Drop existing tables to ensure clean state
    Base.metadata.drop_all(bind=engine)
    # Create tables
    Base.metadata.create_all(bind=engine)


def main():
    # Create tables
    create_tables()

    # Insert documents
    insert_documents()

    # Search without filter
    search_documents(
        query="container technology",
        limit=5,
    )

    # Search with metadata filter
    search_documents(
        query="programming",
        limit=5,
        metadata_filter={
            "type": "programming",
        },
    )


if __name__ == "__main__":
    main()
