"""Embedding service for creating vector embeddings."""

from typing import List, Dict, Any
from openai import OpenAI
from tqdm import tqdm

from .config import OPENAI_API_KEY, EMBEDDING_MODEL, EMBEDDING_DIMENSIONS


class EmbeddingService:
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = EMBEDDING_MODEL
        self.dimensions = EMBEDDING_DIMENSIONS

    def create_embedding(self, text: str) -> List[float]:
        """Create embedding for a single text."""
        response = self.client.embeddings.create(
            model=self.model, input=text, dimensions=self.dimensions
        )
        return response.data[0].embedding

    def create_embeddings_batch(
        self, texts: List[str], batch_size: int = 100
    ) -> List[List[float]]:
        """
        Create embeddings for multiple texts in batches.
        OpenAI has a limit on batch size, so we process in chunks.
        """
        all_embeddings = []

        # Process in batches with progress bar
        for i in tqdm(range(0, len(texts), batch_size), desc="Creating embeddings"):
            batch = texts[i : i + batch_size]

            response = self.client.embeddings.create(
                model=self.model, input=batch, dimensions=self.dimensions
            )

            embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(embeddings)

        return all_embeddings

    def add_embeddings_to_chunks(
        self, chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Add embeddings to a list of chunks."""
        # Extract texts
        texts = [chunk["content"] for chunk in chunks]

        # Create embeddings
        print(f"Creating embeddings for {len(texts)} chunks...")
        embeddings = self.create_embeddings_batch(texts)

        # Add embeddings to chunks
        for chunk, embedding in zip(chunks, embeddings):
            chunk["embedding"] = embedding

        return chunks
