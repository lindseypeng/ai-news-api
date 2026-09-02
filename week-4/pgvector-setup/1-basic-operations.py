"""
Basic Vector Operations with pgvector

This file demonstrates fundamental vector operations using pgvector and OpenAI embeddings,
including document insertion and similarity search. It shows how to:
- Connect to PostgreSQL with pgvector
- Generate embeddings using OpenAI
- Insert documents with their embeddings
- Perform similarity search using inner product
"""

import os

import psycopg
from dotenv import load_dotenv
from openai import OpenAI
from pgvector.psycopg import register_vector

load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Database connection
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/postgres"


def get_embedding(text: str) -> list[float]:
    """Generate embeddings using OpenAI's text-embedding-3-small model."""
    response = client.embeddings.create(
        model="text-embedding-3-small", input=text, dimensions=1536
    )
    return response.data[0].embedding


def create_connection():
    """Create a database connection and register vector type."""
    conn = psycopg.connect(DATABASE_URL)
    register_vector(conn)
    return conn


def insert_document(conn, content: str, metadata: dict = None):
    """Insert a document with its embedding into the database."""
    embedding = get_embedding(content)

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO documents (content, metadata, embedding)
            VALUES (%s, %s, %s)
            RETURNING id
        """,
            (content, psycopg.types.json.Json(metadata or {}), embedding),
        )

        doc_id = cur.fetchone()[0]
        conn.commit()
        return doc_id


def search_similar_documents(conn, query: str, limit: int = 1):
    """Search for similar documents using inner product similarity."""
    query_embedding = get_embedding(query)

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, content, metadata, 
                   -(embedding <#> %s::vector) as similarity
            FROM documents
            ORDER BY embedding <#> %s::vector
            LIMIT %s
        """,
            (query_embedding, query_embedding, limit),
        )

        results = cur.fetchall()
        return results


def insert_documents():
    """Insert a list of documents into the database."""
    conn = create_connection()
    try:
        documents = [
            {
                "content": "Machine learning is a subset of artificial intelligence that enables systems to learn from data.",
                "metadata": {"category": "AI", "topic": "ML basics"},
            },
            {
                "content": "Deep learning uses neural networks with multiple layers to analyze data.",
                "metadata": {"category": "AI", "topic": "Deep Learning"},
            },
            {
                "content": "Natural language processing helps computers understand human language.",
                "metadata": {"category": "AI", "topic": "NLP"},
            },
            {
                "content": "Computer vision enables machines to interpret and understand visual information.",
                "metadata": {"category": "AI", "topic": "Computer Vision"},
            },
            {
                "content": "PostgreSQL is a powerful open-source relational database system.",
                "metadata": {"category": "Database", "topic": "PostgreSQL"},
            },
        ]

        print("Inserting documents...")
        for doc in documents:
            doc_id = insert_document(conn, doc["content"], doc["metadata"])
            print(f"Inserted document {doc_id}: {doc['content'][:50]}...")
    finally:
        conn.close()


def search_documents(query: str, limit: int = 1):
    """Search for documents using cosine similarity."""
    conn = create_connection()

    try:
        # Search for similar documents
        print(f"\nSearching for documents similar to: '{query}'")

        results = search_similar_documents(conn, query, limit)

        print("\nSearch Results:")
        for id, content, metadata, similarity in results:
            print(f"\nID: {id}")
            print(f"Similarity: {similarity:.4f}")
            print(f"Content: {content}")
            print(f"Metadata: {metadata}")

    finally:
        conn.close()


def main():
    # Create tables
    insert_documents()

    # Search for similar documents
    search_documents(query="What is neural network?")


if __name__ == "__main__":
    main()
