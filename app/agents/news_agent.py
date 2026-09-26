from langfuse.openai import OpenAI

from app.schemas.news import ArticleEnrichment

client = OpenAI()


def enrich_article(title: str, content: str) -> ArticleEnrichment:
    """Summarize an article and extract topic tags using the OpenAI API."""

    response = client.responses.parse(
        model="gpt-4o",
        instructions=(
            "You are a news analyst. Given an article's title and content, "
            "write a concise 1-2 sentence summary and list 3-5 tags."
        ),
        input=f"Title: {title}\n\nContent:\n{content}",
        text_format=ArticleEnrichment,
    )

    return response.output_parsed
