from openai import OpenAI

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536

client = OpenAI()


def create_embedding(text: str) -> list[float]:
    """Generate an embedding vector for a piece of text using the OpenAI API."""

    response = client.embeddings.create(
        model=EMBEDDING_MODEL, input=text, dimensions=EMBEDDING_DIMENSIONS
    )

    return response.data[0].embedding
