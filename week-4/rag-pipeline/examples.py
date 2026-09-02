"""Example usage of the RAG system."""

from rag import RAGSystem


def example_basic_query():
    """Basic example of querying the RAG system."""
    print("=== Basic Query Example ===\n")

    # Initialize RAG system
    rag = RAGSystem()

    # Simple query
    question = "What is the Felony Bench and how does it evaluate AI models?"
    response = rag.query(question)

    print(f"Question: {question}")
    print(f"Response: {response}")


def example_with_context():
    """Example showing retrieved context."""
    print("\n=== Query with Context Example ===\n")

    # Initialize RAG system
    rag = RAGSystem()

    # Query with context display
    question = "Why does the article argue that slow software is no longer necessary?"
    response = rag.query(question, show_context=True)

    print(f"Question: {question}")
    print(f"Response: {response}")


def example_custom_parameters():
    """Example with custom retrieval parameters."""
    print("\n=== Custom Parameters Example ===\n")

    # Initialize RAG system
    rag = RAGSystem()

    # Query with custom parameters
    question = "How is social media influencing travel decisions among Gen Z?"

    # Retrieve more documents with lower threshold
    response = rag.query(
        question,
        k=10,  # Retrieve top 10 chunks instead of default 5
        threshold=0.5,  # Lower similarity threshold
        show_context=False,
    )

    print(f"Question: {question}")
    print(f"Response: {response}")


def example_direct_retrieval():
    """Example of using retrieval without generation."""
    print("\n=== Direct Retrieval Example ===\n")

    # Initialize RAG system
    rag = RAGSystem()

    # Just retrieve relevant chunks
    query = "Kobo e-readers running apps"
    context = rag.retrieve_context(query, k=3)

    print(f"Query: {query}")
    print(f"Found {len(context)} relevant chunks:\n")

    for i, doc in enumerate(context, 1):
        print(
            f"{i}. Chunk {doc['metadata']['chunk_index'] + 1} (Similarity: {doc['similarity']:.3f})"
        )
        print(f"   Content: {doc['content'][:150]}...\n")


def example_batch_queries():
    """Example of processing multiple queries."""
    print("\n=== Batch Queries Example ===\n")

    # Initialize RAG system
    rag = RAGSystem()

    # Multiple questions
    questions = [
        "What kind of device is the Motorola partnership initially focused on?",
        "How does Cobalt let Kobo e-readers run apps?",
        "What is the Felony Bench measuring?",
    ]

    for i, question in enumerate(questions, 1):
        print(f"Question {i}: {question}")
        response = rag.query(question)
        print(f"Response: {response[:200]}...\n")  # Show first 200 chars
        print("-" * 50 + "\n")


def main():
    """Run all examples."""
    print("RAG System Examples\n")

    # Check if database has documents
    rag = RAGSystem()
    if rag.vector_store.get_document_count() == 0:
        print("No documents in database. Please run build_vectordb.py first.")
        return

    # Run examples
    example_basic_query()
    example_with_context()
    example_custom_parameters()
    example_direct_retrieval()
    example_batch_queries()


if __name__ == "__main__":
    main()
