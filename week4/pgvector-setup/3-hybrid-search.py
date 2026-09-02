"""
Advanced Hybrid Search with pgvector

This file demonstrates advanced search capabilities combining:
- Semantic search using vector embeddings
- Keyword search using PostgreSQL's full-text search
- Reciprocal Rank Fusion (RRF) for result combination
- Flexible and strict keyword matching modes
- Metadata filtering
- Performance optimization with HNSW indexes

The implementation shows how to build a production-ready hybrid search system
that balances semantic understanding with precise keyword matching.
"""

import json
import os
from typing import List, Literal

import psycopg
from dotenv import load_dotenv
from openai import OpenAI
from pgvector.psycopg import register_vector

load_dotenv()

DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/postgres"
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class VectorStore:
    """
    A clean implementation of hybrid search combining semantic and keyword search
    using Reciprocal Rank Fusion (RRF).

    Supports two keyword search modes:
    - 'strict': All query terms must match (websearch_to_tsquery)
    - 'flexible': Any query terms can match (custom OR logic)
    """

    DEFAULT_LIMIT = 10
    DEFAULT_RRF_K = 2
    EMBEDDING_DIMENSIONS = 1536
    SEARCH_CONFIG = "english"
    MAX_SEARCH_RESULTS = 30

    def __init__(self):
        self.conn = psycopg.connect(DATABASE_URL)
        register_vector(self.conn)

    def get_embedding(self, text: str) -> List[float]:
        """Generate embeddings using OpenAI."""
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text,
            dimensions=self.EMBEDDING_DIMENSIONS,
        )
        return response.data[0].embedding

    def _build_metadata_filter(
        self, metadata_filter: dict = None
    ) -> tuple[str, str, dict]:
        """Build metadata filter using PostgreSQL's JSON containment operator."""
        if not metadata_filter:
            return "", "", {}

        where_clause = " WHERE metadata::jsonb @> %(metadata_filter)s::jsonb"
        and_clause = " AND metadata::jsonb @> %(metadata_filter)s::jsonb"
        params = {"metadata_filter": json.dumps(metadata_filter)}

        return where_clause, and_clause, params

    def search(
        self,
        query: str,
        semantic_weight: float = 1.0,
        full_text_weight: float = 1.0,
        keyword_mode: Literal["strict", "flexible"] = "flexible",
        rrf_k: int = DEFAULT_RRF_K,
        limit: int = DEFAULT_LIMIT,
        metadata_filter: dict = None,
    ) -> List[dict]:
        """
        Perform hybrid search combining semantic and keyword search.

        Args:
            query: Search query text
            semantic_weight: Weight for semantic search (0.0 to disable)
            full_text_weight: Weight for keyword search (0.0 to disable)
            keyword_mode: 'strict' (all terms must match) or 'flexible' (any terms can match)
            rrf_k: Smoothing constant for Reciprocal Rank Fusion
            limit: Maximum number of results to return
            metadata_filter: Optional dictionary of metadata key-value pairs to filter by

        Returns:
            List of search results with scores and metadata
        """

        # Use AND logic (all terms must match)
        if keyword_mode == "strict":
            tsquery_func = (
                f"websearch_to_tsquery('{self.SEARCH_CONFIG}', %(fts_query)s)"
            )
            fts_query = query

        # Use OR logic (any terms can match)
        elif keyword_mode == "flexible":
            tsquery_func = f"to_tsquery('{self.SEARCH_CONFIG}', %(fts_query)s)"
            # Convert websearch AND query to OR query inline
            with self.conn.cursor() as cur:
                cur.execute(
                    f"SELECT websearch_to_tsquery('{self.SEARCH_CONFIG}', %s)::text",
                    (query,),
                )
                result = cur.fetchone()[0]
                fts_query = (
                    result.replace(" & ", " | ") if result and result != "''" else "''"
                )
        else:
            raise ValueError("keyword_mode must be 'strict' or 'flexible'")

        query_embedding = self.get_embedding(query)
        metadata_where, metadata_and, metadata_params = self._build_metadata_filter(
            metadata_filter
        )

        with self.conn.cursor() as cur:
            sql_query = f"""
                WITH full_text AS (
                    SELECT 
                        id,
                        ts_rank_cd(fts, {tsquery_func}) as fts_score,
                        row_number() OVER (
                            ORDER BY 
                                ts_rank_cd(fts, {tsquery_func}) DESC,
                                length(content)
                        ) as rank_ix
                    FROM documents
                    WHERE fts @@ {tsquery_func}{metadata_and}
                    ORDER BY rank_ix
                    LIMIT least(%(limit)s, %(max_results)s) * 2
                ),
                semantic AS (
                    SELECT 
                        id,
                        row_number() OVER (ORDER BY embedding <#> %(query_embedding)s::vector) as rank_ix
                    FROM documents{metadata_where}
                    ORDER BY rank_ix
                    LIMIT least(%(limit)s, %(max_results)s) * 2
                )
                SELECT 
                    d.*,
                    ft.fts_score,
                    COALESCE(1.0 / (%(rrf_k)s + ft.rank_ix), 0.0) * %(full_text_weight)s as full_text_score,
                    COALESCE(1.0 / (%(rrf_k)s + s.rank_ix), 0.0) * %(semantic_weight)s as semantic_score,
                    (
                        COALESCE(1.0 / (%(rrf_k)s + ft.rank_ix), 0.0) * %(full_text_weight)s + 
                        COALESCE(1.0 / (%(rrf_k)s + s.rank_ix), 0.0) * %(semantic_weight)s
                    ) as combined_score
                FROM 
                    full_text ft
                    FULL OUTER JOIN semantic s ON ft.id = s.id
                    JOIN documents d ON COALESCE(ft.id, s.id) = d.id{metadata_where}
                ORDER BY combined_score DESC
                LIMIT least(%(limit)s, %(max_results)s)
            """

            params = {
                "fts_query": fts_query,
                "query_embedding": query_embedding,
                "limit": limit,
                "max_results": self.MAX_SEARCH_RESULTS,
                "rrf_k": rrf_k,
                "full_text_weight": full_text_weight,
                "semantic_weight": semantic_weight,
                **metadata_params,
            }

            cur.execute(sql_query, params)

            results = cur.fetchall()

            return [
                {
                    "id": r[0],
                    "content": r[1],
                    "metadata": r[2],
                    "embedding": r[3],
                    "fts": r[4],
                    "created_at": r[5],
                    "fts_raw_score": float(r[6]) if r[6] else 0.0,
                    "full_text_score": float(r[7]),
                    "semantic_score": float(r[8]),
                    "combined_score": float(r[9]),
                }
                for r in results
            ]

    def add_document(self, content: str, metadata: dict = None) -> int:
        """Add a document to the search index."""
        embedding = self.get_embedding(content)

        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO documents (content, metadata, embedding)
                VALUES (%s, %s, %s)
                RETURNING id
            """,
                (content, psycopg.types.json.Json(metadata or {}), embedding),
            )

            doc_id = cur.fetchone()[0]
            self.conn.commit()
            return doc_id

    def close(self):
        """Close database connection."""
        self.conn.close()


# =============================================================================
# TUTORIAL EXAMPLES
# =============================================================================


def insert_documents():
    """Insert sample documents for tutorial examples."""
    search_engine = VectorStore()
    try:
        documents = [
            {
                "content": "PostgreSQL is an advanced open-source relational database with powerful features for data management.",
                "metadata": {"category": "database", "type": "relational"},
            },
            {
                "content": "Vector databases enable similarity search by storing and querying high-dimensional embeddings.",
                "metadata": {"category": "database", "type": "vector"},
            },
            {
                "content": "To implement vector similarity search, you need to store document embeddings and compute distances.",
                "metadata": {"category": "implementation", "type": "tutorial"},
            },
            {
                "content": "Machine learning models transform text content into numerical vectors for semantic analysis.",
                "metadata": {"category": "AI", "type": "embedding"},
            },
            {
                "content": "pgvector is a PostgreSQL extension that adds vector similarity search capabilities to your database.",
                "metadata": {"category": "database", "type": "extension"},
            },
            {
                "content": "Hybrid search combines keyword matching with semantic similarity for better document retrieval results.",
                "metadata": {"category": "search", "type": "hybrid"},
            },
        ]

        print("Inserting documents...")
        for doc in documents:
            doc_id = search_engine.add_document(doc["content"], doc["metadata"])
            print(f"Inserted document {doc_id}: {doc['content'][:50]}...")
    finally:
        search_engine.close()


def compare_search_modes():
    """
    Tutorial: Compare strict vs flexible keyword search modes.

    Demonstrates the difference between:
    - Strict mode: All terms must match (good for precise queries)
    - Flexible mode: Any terms can match (good for conversational queries)
    """
    search_engine = VectorStore()
    try:
        print("\n--- Comparing Search Modes ---")
        print("=" * 60)

        # Test with a conversational query
        query = (
            "How can I implement vector similarity search in my PostgreSQL database?"
        )
        print(f"Query: {query}\n")

        # Test strict mode (websearch_to_tsquery)
        print("Strict Mode (all terms must match)")
        print("Uses websearch_to_tsquery - precise but restrictive")
        results = search_engine.search(
            query,
            semantic_weight=0.0,
            full_text_weight=1.0,
            keyword_mode="strict",
            limit=3,
        )

        for r in results:
            print(
                f"Raw FTS Score: {r['fts_raw_score']:.4f}, RRF Score: {r['full_text_score']:.4f} - {r['content'][:50]}..."
            )
        else:
            print("No results - query too restrictive")

        print()

        # Test flexible mode (OR-based search)
        print("Flexible Mode (any terms can match)")
        print("Uses custom OR logic - flexible and conversational")
        results = search_engine.search(
            query,
            semantic_weight=0.0,
            full_text_weight=1.0,
            keyword_mode="flexible",
            limit=3,
        )

        for r in results:
            print(
                f"Raw FTS Score: {r['fts_raw_score']:.4f}, RRF Score: {r['full_text_score']:.4f} - {r['content'][:50]}..."
            )

        print("\n" + "=" * 60)

    finally:
        search_engine.close()


def demonstrate_hybrid_search():
    """
    Tutorial: Show the power of combining semantic + keyword search.

    Compares:
    1. Pure semantic search (understanding context)
    2. Pure keyword search (exact term matching)
    3. Hybrid search (best of both worlds)
    """
    search_engine = VectorStore()
    try:
        print("\n--- Hybrid Search Demonstration ---")
        print("=" * 60)

        query = "database for storing vectors"
        print(f"Query: {query}\n")

        # Pure semantic search
        print("Semantic Only (understands context)")
        results = search_engine.search(
            query,
            semantic_weight=1.0,
            full_text_weight=0.0,
            keyword_mode="flexible",
            limit=3,
        )

        for i, r in enumerate(results, 1):
            print(f"{i}. Score: {r['semantic_score']:.4f} - {r['content'][:50]}...")

        print()

        # Pure keyword search
        print("Keyword Only (exact term matching)")
        results = search_engine.search(
            query,
            semantic_weight=0.0,
            full_text_weight=1.0,
            keyword_mode="flexible",
            limit=3,
        )

        for i, r in enumerate(results, 1):
            print(f"{i}. Score: {r['full_text_score']:.4f} - {r['content'][:50]}...")

        print()

        # Hybrid search
        print("Hybrid (semantic + keyword)")
        results = search_engine.search(
            query,
            semantic_weight=1.0,
            full_text_weight=1.0,
            keyword_mode="flexible",
            limit=3,
        )

        for i, r in enumerate(results, 1):
            print(f"{i}. Combined Score: {r['combined_score']:.4f}")
            print(f"   FTS Score: {r['full_text_score']:.4f}")
            print(f"   Semantic Score: {r['semantic_score']:.4f}")
            print(f"   Content: {r['content'][:50]}...")
            print()

        # Hybrid search with metadata filter
        print("Hybrid Search with Metadata Filter")
        print("Filtering for category='database'")
        results = search_engine.search(
            query,
            semantic_weight=1.0,
            full_text_weight=1.0,
            keyword_mode="flexible",
            limit=3,
            metadata_filter={"category": "database"},
        )

        for i, r in enumerate(results, 1):
            print(f"{i}. Combined Score: {r['combined_score']:.4f}")
            print(f"   FTS Score: {r['full_text_score']:.4f}")
            print(f"   Semantic Score: {r['semantic_score']:.4f}")
            print(f"   Content: {r['content'][:50]}...")
            print(f"   Metadata: {r['metadata']}")
            print()

        print("Note: Hybrid search provides the most balanced and relevant results")
        print("=" * 60)

    finally:
        search_engine.close()


def weight_tuning_example():
    """
    Tutorial: Show how to tune semantic vs keyword weights.

    Demonstrates how different weight combinations affect search results.
    """
    search_engine = VectorStore()
    try:
        print("\n--- Weight Tuning Example ---")
        print("=" * 60)

        query = "Natural language processing is the field of study that focuses on the interaction between computers and human language."
        print(f"Query: {query}\n")

        weight_configs = [
            (1.0, 2.0, "Keyword-heavy (precise matching)"),
            (2.0, 1.0, "Semantic-heavy (contextual understanding)"),
        ]

        for semantic_w, keyword_w, description in weight_configs:
            print(f"{description}")
            print(f"Weights: Semantic={semantic_w}, Keyword={keyword_w}")

            results = search_engine.search(
                query,
                semantic_weight=semantic_w,
                full_text_weight=keyword_w,
                keyword_mode="flexible",
                limit=3,
            )

            for r in results:
                print(f"Score: {r['combined_score']:.4f} - {r['content'][:45]}...")
            print()

        print("Weight tuning guidelines:")
        print("- Higher keyword weight → More precise, exact matches")
        print("- Higher semantic weight → More contextual, conceptual matches")
        print("=" * 60)

    finally:
        search_engine.close()


def main():
    # Uncomment to set up fresh data
    insert_documents()

    # Compare search modes
    compare_search_modes()

    # Demonstrate hybrid search
    demonstrate_hybrid_search()

    # Weight tuning example
    weight_tuning_example()


if __name__ == "__main__":
    main()
