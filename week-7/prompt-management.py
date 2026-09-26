"""Create, retrieve, compile, and trace a managed Langfuse news prompt."""

import os

from dotenv import load_dotenv
from langfuse import get_client, observe
from langfuse.openai import openai

load_dotenv()

PROMPT_NAME = "ai-news-summary"
DEFAULT_MODEL = "gpt-4o-mini"


def require_credentials() -> None:
    required = ("OPENAI_API_KEY", "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY")
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise SystemExit(f"Set {', '.join(missing)} in .env before running this lab.")


def register_prompt():
    """Create a new prompt version and label it for production use."""

    return get_client().create_prompt(
        name=PROMPT_NAME,
        prompt=(
            "Summarize this AI news article in one concise sentence.\n\n"
            "Title: {{title}}\n\nArticle: {{content}}"
        ),
        config={"model": DEFAULT_MODEL, "temperature": 0.2},
        labels=["production"],
        tags=["week-7", "ai-news"],
        commit_message="Initial Week 7 AI news summary prompt",
    )


@observe(name="week-7-managed-prompt")
def summarize_with_managed_prompt(title: str, content: str) -> str:
    """Load the production prompt, compile its variables, and call OpenAI."""

    prompt = get_client().get_prompt(PROMPT_NAME, label="production")
    compiled_prompt = prompt.compile(title=title, content=content)
    config = prompt.config or {}

    response = openai.responses.create(
        model=config.get("model", DEFAULT_MODEL),
        temperature=config.get("temperature", 0.2),
        input=compiled_prompt,
        name="managed-news-summary",
        langfuse_prompt=prompt,
    )
    return response.output_text


def main() -> None:
    require_credentials()
    prompt = register_prompt()
    print(f"Created prompt '{prompt.name}' version {prompt.version}.")

    summary = summarize_with_managed_prompt(
        title="New benchmark measures reliability of AI agents",
        content=(
            "The benchmark evaluates whether agents choose the correct tools, "
            "recover from errors, and cite the evidence used in their answers."
        ),
    )
    print(f"Summary: {summary}")

    get_client().flush()
    print("Open Langfuse > Prompt Management and Tracing to inspect the result.")


if __name__ == "__main__":
    main()
