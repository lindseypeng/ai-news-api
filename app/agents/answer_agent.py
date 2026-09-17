from openai import OpenAI

from app.schemas.news import GroundedAnswer

ANSWER_MODEL = "gpt-4o-mini"

client = OpenAI()


def answer_from_context(question: str, contexts: list[str]) -> GroundedAnswer:
    """Answer a question using only retrieved article chunks."""

    numbered_context = "\n\n".join(
        f"[{index}] {context}" for index, context in enumerate(contexts, start=1)
    )
    response = client.responses.parse(
        model=ANSWER_MODEL,
        instructions=(
            "Answer only from the supplied context. Do not use outside knowledge. "
            "For a numeric question, return only the number and requested unit. "
            "For a true/false question, start the answer with 'true' or 'false'. "
            "If the context does not contain enough evidence, set supported to false "
            "and answer 'Not enough information'."
        ),
        input=f"Question: {question}\n\nContext:\n{numbered_context}",
        text_format=GroundedAnswer,
    )
    return response.output_parsed
