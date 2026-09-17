import argparse
import json
from pathlib import Path

import requests

from evaluations.scoring import answer_matches

QUESTIONS_PATH = Path(__file__).with_name("questions.json")


def run_evaluation(base_url: str) -> int:
    cases = json.loads(QUESTIONS_PATH.read_text())
    passed = 0

    for case in cases:
        response = requests.post(
            f"{base_url.rstrip('/')}/ask/",
            json={"question": case["question"], "limit": 5},
            timeout=60,
        )
        response.raise_for_status()
        result = response.json()
        retrieved_expected_source = any(
            citation["source_id"] == case["source_id"]
            for citation in result["citations"]
        )
        correct = (
            retrieved_expected_source
            and result["supported"]
            and answer_matches(case, result["answer"])
        )
        passed += int(correct)
        status = "PASS" if correct else "FAIL"
        print(
            f"{status} {case['id']}: {result['answer']} "
            f"(source retrieved: {retrieved_expected_source})"
        )

    print(f"\nAccuracy: {passed}/{len(cases)} ({passed / len(cases):.1%})")
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8001")
    args = parser.parse_args()
    raise SystemExit(run_evaluation(args.base_url))
