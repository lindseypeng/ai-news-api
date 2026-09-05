"""Batch ingestion/enrichment entry point."""

from app.services.enrichment import run_enrichment
from app.services.indexing import run_indexing
from app.services.ingestion import run_ingestion


def run_pipeline() -> None:
    run_ingestion()
    run_enrichment()
    run_indexing()


if __name__ == "__main__":
    run_pipeline()
