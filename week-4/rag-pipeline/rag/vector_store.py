"""Vector store implementation using PGVector."""

import json
from typing import Any, Dict, List, Optional

import psycopg
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row

from .config import DATABASE_CONFIG, EMBEDDING_DIMENSIONS


class VectorStore:
    def __init__(self):
        self.conn = None
        self.connect()
        self.setup_database()

    def connect(self):
        """Establish connection to PostgreSQL database."""
        # Build connection string for psycopg3
        conn_str = (
            f"host={DATABASE_CONFIG['host']} "
            f"port={DATABASE_CONFIG['port']} "
            f"dbname={DATABASE_CONFIG['database']} "
            f"user={DATABASE_CONFIG['user']} "
            f"password={DATABASE_CONFIG['password']}"
        )
        self.conn = psycopg.connect(conn_str)
        self.conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        register_vector(self.conn)

    def setup_database(self):
        """Create the necessary tables and extensions."""
        with self.conn.cursor() as cur:
            # Create documents table
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS documents (
                    id SERIAL PRIMARY KEY,
                    content TEXT NOT NULL,
                    embedding vector({EMBEDDING_DIMENSIONS}),
                    metadata JSONB DEFAULT '{{}}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create index for similarity search using HNSW with inner product
            cur.execute("""
                CREATE INDEX IF NOT EXISTS documents_embedding_idx 
                ON documents USING hnsw (embedding vector_ip_ops)
            """)

            self.conn.commit()

    def add_document(
        self,
        content: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Add a single document to the vector store."""
        with self.conn.cursor() as cur:
            result = cur.execute(
                """
                INSERT INTO documents (content, embedding, metadata)
                VALUES (%s, %s, %s)
                RETURNING id
            """,
                (content, embedding, json.dumps(metadata or {})),
            )
            doc_id = result.fetchone()[0]
            self.conn.commit()
            return doc_id

    def add_documents(self, documents: List[Dict[str, Any]]):
        """Add multiple documents to the vector store in batch."""
        with self.conn.cursor() as cur:
            for doc in documents:
                cur.execute(
                    """
                    INSERT INTO documents (content, embedding, metadata)
                    VALUES (%s, %s, %s)
                """,
                    (
                        doc["content"],
                        doc["embedding"],
                        json.dumps(doc.get("metadata", {})),
                    ),
                )
            self.conn.commit()

    def similarity_search(
        self,
        query_embedding: List[float],
        k: int = 5,
        threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """Perform similarity search using inner product."""
        with self.conn.cursor(row_factory=dict_row) as cur:
            # Base query with similarity score using inner product
            query = """
                SELECT 
                    id,
                    content,
                    metadata,
                    -(embedding <#> %s::vector) as similarity,
                    created_at
                FROM documents
            """

            # Add threshold filter if specified
            if threshold is not None:
                query += f" WHERE -(embedding <#> %s::vector) >= {threshold}"

            # Order by similarity and limit (using inner product)
            query += " ORDER BY embedding <#> %s::vector LIMIT %s"

            # Execute query
            if threshold is not None:
                result = cur.execute(
                    query, (query_embedding, query_embedding, query_embedding, k)
                )
            else:
                result = cur.execute(query, (query_embedding, query_embedding, k))

            results = result.fetchall()

            # Convert to list of dicts with proper formatting
            return [
                {
                    "id": r["id"],
                    "content": r["content"],
                    "metadata": r["metadata"],
                    "similarity": float(r["similarity"]),
                    "created_at": r["created_at"].isoformat()
                    if r["created_at"]
                    else None,
                }
                for r in results
            ]

    def get_document_count(self) -> int:
        """Get the total number of documents in the store."""
        with self.conn.cursor() as cur:
            result = cur.execute("SELECT COUNT(*) FROM documents")
            return result.fetchone()[0]

    def clear_all_documents(self):
        """Delete all documents from the store."""
        with self.conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE documents RESTART IDENTITY")
            self.conn.commit()

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
