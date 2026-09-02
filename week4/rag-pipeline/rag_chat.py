"""Interactive script to query the RAG system."""

import sys
from rag import RAGSystem


def print_separator():
    print("\n" + "=" * 60 + "\n")


def main():
    print("=== News RAG Query System ===\n")

    # Initialize RAG system
    print("Initializing RAG system...")
    try:
        rag = RAGSystem()
    except Exception as e:
        print(f"Error initializing RAG system: {str(e)}")
        sys.exit(1)

    # Check if database has documents
    doc_count = rag.vector_store.get_document_count()
    if doc_count == 0:
        print("No documents found in database. Please run build_vectordb.py first.")
        sys.exit(1)

    print(f"✅ RAG system ready! ({doc_count} documents in database)")
    print("\nExample questions you can ask:")
    print("- Why does the article argue that slow software is no longer necessary?")
    print("- How is social media influencing travel decisions among Gen Z?")
    print("- What is the Felony Bench and how does it evaluate AI models?")
    print("- What kind of device is the Motorola partnership initially focused on?")
    print("- How does Cobalt let Kobo e-readers run apps?")
    print("\nType 'quit' or 'exit' to stop, 'stats' for system statistics.")

    # Interactive query loop
    while True:
        print_separator()
        query = input("Your question: ").strip()

        if query.lower() in ["quit", "exit"]:
            print("\nGoodbye! 👋")
            break

        if query.lower() == "stats":
            stats = rag.get_stats()
            print(f"\nSystem Statistics:")
            print(f"- Total documents: {stats['total_documents']}")
            print(f"- Embedding model: {stats['embedding_model']}")
            print(f"- Embedding dimensions: {stats['embedding_dimensions']}")
            print(f"- Chat model: {stats['chat_model']}")
            continue

        if not query:
            print("Please enter a question.")
            continue

        try:
            # Query the system
            print("\nProcessing your query...")
            response = rag.query(query, show_context=False)

            print("\nResponse:")
            print(response)

            # Ask if user wants to see the retrieved context
            show_context = input("\nShow retrieved context? (y/n): ").strip().lower()
            if show_context == "y":
                context = rag.retrieve_context(query)
                print("\n📚 Retrieved Context:")
                for i, doc in enumerate(context, 1):
                    print(
                        f"\n{i}. Chunk {doc['metadata']['chunk_index'] + 1}/{doc['metadata']['total_chunks']} (Similarity: {doc['similarity']:.3f})"
                    )
                    print(f"   Preview: {doc['content'][:200]}...")

        except Exception as e:
            print(f"\nError processing query: {str(e)}")


if __name__ == "__main__":
    main()
