"""Main RAG system that orchestrates the entire pipeline."""

from typing import Any, Dict, List

from openai import OpenAI

from .config import CHAT_MODEL, OPENAI_API_KEY, SIMILARITY_THRESHOLD, TOP_K_RESULTS
from .document_processor import DocumentProcessor
from .embedding_service import EmbeddingService
from .vector_store import VectorStore


class RAGSystem:
    def __init__(self):
        self.vector_store = VectorStore()
        self.embedding_service = EmbeddingService()
        self.document_processor = DocumentProcessor()
        self.chat_client = OpenAI(api_key=OPENAI_API_KEY)

    def ingest_document(self, source: str):
        """Process and store a document in the vector database."""
        # Process document into chunks
        chunks = self.document_processor.process_document(source)

        # Add embeddings
        chunks_with_embeddings = self.embedding_service.add_embeddings_to_chunks(chunks)

        # Store in vector database
        print("Storing chunks in vector database...")
        self.vector_store.add_documents(chunks_with_embeddings)

        # Print statistics
        stats = self.document_processor.get_chunk_stats(chunks)
        print("\nIngestion complete!")
        print(f"Total chunks: {stats['total_chunks']}")
        print(f"Average tokens per chunk: {stats['avg_tokens_per_chunk']:.1f}")
        print(f"Total documents in store: {self.vector_store.get_document_count()}")

    def retrieve_context(
        self, query: str, k: int = None, threshold: float = None
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant context for a query."""
        # Use defaults if not specified
        k = k or TOP_K_RESULTS
        threshold = threshold or SIMILARITY_THRESHOLD

        # Create embedding for query
        query_embedding = self.embedding_service.create_embedding(query)

        # Search for similar documents
        results = self.vector_store.similarity_search(
            query_embedding=query_embedding, k=k, threshold=threshold
        )

        return results

    def generate_response(self, query: str, context: List[Dict[str, Any]]) -> str:
        """Generate a response using the retrieved context."""
        # Prepare context for prompt
        context_texts = []
        for i, doc in enumerate(context, 1):
            context_texts.append(
                f"[Document {i}] (Similarity: {doc['similarity']:.3f})\n{doc['content']}"
            )

        combined_context = "\n\n---\n\n".join(context_texts)

        # Create system prompt
        system_prompt = """You are a helpful AI assistant that answers questions based on the provided context. 
        Use the context to answer the user's question accurately and comprehensively. 
        If the context doesn't contain enough information to fully answer the question, say so.
        Always cite which document(s) you're using for your answer."""

        # Create messages
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Context:\n{combined_context}\n\nQuestion: {query}",
            },
        ]

        # Generate response
        response = self.chat_client.chat.completions.create(
            model=CHAT_MODEL, messages=messages, temperature=0.7, max_tokens=1000
        )

        return response.choices[0].message.content

    def query(
        self,
        question: str,
        k: int = None,
        threshold: float = None,
        show_context: bool = False,
    ) -> str:
        """
        Main query method that combines retrieval and generation.
        Args:
            question: The user's question
            k: Number of documents to retrieve (default: TOP_K_RESULTS)
            threshold: Similarity threshold (default: SIMILARITY_THRESHOLD)
            show_context: Whether to include retrieved context in response

        Returns:
            The generated response
        """
        # Retrieve relevant context
        print("Searching for relevant context...")
        context = self.retrieve_context(question, k=k, threshold=threshold)

        if not context:
            return "I couldn't find any relevant information to answer your question."

        print(f"Found {len(context)} relevant chunks")

        # Generate response
        print("Generating response...")
        response = self.generate_response(question, context)

        if show_context:
            # Append context information
            context_info = "\n\n**Retrieved Context:**\n"
            for i, doc in enumerate(context, 1):
                context_info += f"\n{i}. (Similarity: {doc['similarity']:.3f}) {doc['content'][:200]}..."
            response += context_info

        return response

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the RAG system."""
        return {
            "total_documents": self.vector_store.get_document_count(),
            "embedding_model": self.embedding_service.model,
            "embedding_dimensions": self.embedding_service.dimensions,
            "chat_model": CHAT_MODEL,
        }
