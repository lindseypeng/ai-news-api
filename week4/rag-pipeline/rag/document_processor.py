"""Document processor for loading and chunking local news article JSON files."""

import json
from pathlib import Path
from typing import Any, Dict, List

import tiktoken

from .config import EMBEDDING_MODEL, MAX_TOKENS_PER_CHUNK


class DocumentProcessor:
    def __init__(self):
        self.tokenizer = tiktoken.encoding_for_model(EMBEDDING_MODEL)

    def process_document(self, source: str) -> List[Dict[str, Any]]:
        """
        Process all NewsItem JSON files in a local directory into chunks.
        Returns list of chunks with metadata.
        """
        input_dir = Path(source)
        json_files = sorted(input_dir.glob("*.json"))
        print(f"Found {len(json_files)} articles in: {input_dir}")

        processed_chunks = []

        for filepath in json_files:
            article = json.loads(filepath.read_text(encoding="utf-8"))
            title = article.get("title", "")
            content = article.get("content") or ""

            if not content:
                continue

            full_text = f"{title}\n\n{content}"
            text_chunks = self._chunk_text(full_text, MAX_TOKENS_PER_CHUNK)

            for i, chunk_text in enumerate(text_chunks):
                processed_chunks.append(
                    {
                        "content": chunk_text,
                        "metadata": {
                            "chunk_index": i,
                            "total_chunks": len(text_chunks),
                            "source": filepath.name,
                            "title": title,
                            "url": article.get("url"),
                        },
                    }
                )

        print(f"Created {len(processed_chunks)} chunks")
        return processed_chunks

    def _chunk_text(self, text: str, max_tokens: int) -> List[str]:
        """Split text into chunks of at most max_tokens tokens each."""
        tokens = self.tokenizer.encode(text)
        return [
            self.tokenizer.decode(tokens[i : i + max_tokens])
            for i in range(0, len(tokens), max_tokens)
        ]

    def get_chunk_stats(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get statistics about the processed chunks."""
        total_tokens = 0

        for chunk in chunks:
            tokens = self.tokenizer.encode(chunk["content"])
            total_tokens += len(tokens)

        return {
            "total_chunks": len(chunks),
            "total_tokens": total_tokens,
            "avg_tokens_per_chunk": total_tokens / len(chunks) if chunks else 0,
        }
