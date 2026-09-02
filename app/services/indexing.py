import tiktoken

from app.agents.embedding_agent import EMBEDDING_MODEL, create_embedding
from app.database.connection import SessionLocal
from app.database.repository import get_unindexed_news_items, insert_news_chunks

MAX_TOKENS_PER_CHUNK = 500

tokenizer = tiktoken.encoding_for_model(EMBEDDING_MODEL)


def _chunk_text(text: str, max_tokens: int = MAX_TOKENS_PER_CHUNK) -> list[str]:
    """Split text into chunks of at most max_tokens tokens each."""
    tokens = tokenizer.encode(text)
    return [
        tokenizer.decode(tokens[i : i + max_tokens])
        for i in range(0, len(tokens), max_tokens)
    ]


def run_indexing() -> None:
    db = SessionLocal()
    try:
        for item in get_unindexed_news_items(db):
            text_chunks = _chunk_text(item.content)

            chunks = [
                {"content": chunk_text, "embedding": create_embedding(chunk_text)}
                for chunk_text in text_chunks
            ]

            insert_news_chunks(db, item.id, chunks)
            print(f"Indexed: {item.title} ({len(chunks)} chunks)")
    finally:
        db.close()


if __name__ == "__main__":
    run_indexing()
