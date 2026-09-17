import re


def normalize_text(value: str) -> str:
    """Normalize punctuation, case, and whitespace for deterministic comparison."""

    return " ".join(re.sub(r"[^a-z0-9.%]+", " ", value.lower()).split())


def extract_number(value: str) -> str | None:
    """Return the first integer or decimal in an answer."""

    match = re.search(r"-?\d+(?:\.\d+)?", value.replace(",", ""))
    return match.group(0) if match else None


def extract_boolean(value: str) -> str | None:
    """Return a leading true/false or yes/no answer in canonical form."""

    match = re.match(r"\s*(true|false|yes|no)\b", value, flags=re.IGNORECASE)
    first_word = match.group(1).lower() if match else ""
    if first_word in {"true", "yes"}:
        return "true"
    if first_word in {"false", "no"}:
        return "false"
    return None


def answer_matches(case: dict, actual_answer: str) -> bool:
    """Score one answer according to the case's declared answer type."""

    expected = case["expected_answer"]
    answer_type = case["answer_type"]
    if answer_type == "number":
        return extract_number(actual_answer) == extract_number(expected)
    if answer_type == "boolean":
        return extract_boolean(actual_answer) == extract_boolean(expected)

    acceptable = [expected, *case.get("accepted_answers", [])]
    actual = normalize_text(actual_answer)
    return any(normalize_text(answer) in actual for answer in acceptable)
