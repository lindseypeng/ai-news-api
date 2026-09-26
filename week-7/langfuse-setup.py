"""Week 7 Langfuse tracing examples for the AI News API."""

import os

from dotenv import load_dotenv
from langfuse import get_client, observe, propagate_attributes
from langfuse.openai import openai
from pydantic import BaseModel, Field

load_dotenv()

MODEL = "gpt-4o-mini"


def require_credentials() -> None:
    """Fail early with a useful message instead of silently dropping traces."""

    required = ("OPENAI_API_KEY", "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY")
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise SystemExit(f"Set {', '.join(missing)} in .env before running this lab.")


class NewsAnalysis(BaseModel):
    """Structured analysis returned by the example workflow."""

    summary: str = Field(description="A concise one-sentence article summary")
    topics: list[str] = Field(description="Two or three topic labels")
    relevance: str = Field(description="AI relevance: low, medium, or high")


@observe(name="week-7-simple-summary")
def summarize_headline(headline: str) -> str:
    """Minimal example: the decorator and OpenAI wrapper create a trace."""

    response = openai.responses.create(
        model=MODEL,
        instructions="Summarize the AI news headline in one short sentence.",
        input=headline,
        name="summarize-headline",
        metadata={"example": "minimal"},
    )
    return response.output_text


@observe(name="week-7-news-analysis", as_type="chain")
def analyze_news(title: str, content: str) -> NewsAnalysis:
    """Business example: trace a structured news-enrichment workflow."""

    with propagate_attributes(
        tags=["week-7", "news-enrichment"],
        metadata={"content_length": len(content)},
    ):
        response = openai.responses.parse(
            model=MODEL,
            instructions=(
                "Analyze this news article. Return a one-sentence summary, "
                "two or three topic labels, and its relevance to AI."
            ),
            input=f"Title: {title}\n\nContent: {content}",
            text_format=NewsAnalysis,
            name="classify-news-article",
        )
        analysis = response.output_parsed

        get_client().update_current_span(
            metadata={
                "relevance": analysis.relevance,
                "topic_count": len(analysis.topics),
            },
            output=analysis.model_dump(),
        )
        return analysis


def main() -> None:
    require_credentials()

    headline = "Open-source agents learn to use tools more reliably"
    print("Minimal example:")
    print(summarize_headline(headline))

    print("\nStructured news analysis:")
    analysis = analyze_news(
        title=headline,
        content=(
            "A research team released a benchmark and training recipe for AI "
            "agents that call external tools. The reported results show fewer "
            "invalid calls and better recovery from tool errors."
        ),
    )
    print(analysis.model_dump_json(indent=2))

    # This is a short-lived script, so send queued observations before exit.
    get_client().flush()
    print("\nOpen Langfuse > Tracing to inspect both examples.")


if __name__ == "__main__":
    main()
