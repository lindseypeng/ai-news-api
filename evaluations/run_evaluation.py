import argparse
import json
from pathlib import Path

import requests

from evaluations.scoring import answer_matches

QUESTIONS_PATH = Path(__file__).with_name("questions.json")


def run_evaluation(base_url: str, minimum_accuracy: float = 0.0) -> int:
    cases = json.loads(QUESTIONS_PATH.read_text())
    retrieval_passed = 0
    answer_passed = 0
    end_to_end_passed = 0

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
        answer_correct = result["supported"] and answer_matches(
            case, result["answer"]
        )
        end_to_end_correct = retrieved_expected_source and answer_correct
        retrieval_passed += int(retrieved_expected_source)
        answer_passed += int(answer_correct)
        end_to_end_passed += int(end_to_end_correct)
        status = "PASS" if end_to_end_correct else "FAIL"
        print(
            f"{status} {case['id']}: {result['answer']} "
            f"(retrieval: {retrieved_expected_source}, answer: {answer_correct})"
        )

    total = len(cases)
    accuracy = end_to_end_passed / total
    print(f"\nRetrieval accuracy: {retrieval_passed}/{total} ({retrieval_passed / total:.1%})")
    print(f"Answer accuracy: {answer_passed}/{total} ({answer_passed / total:.1%})")
    print(f"End-to-end accuracy: {end_to_end_passed}/{total} ({accuracy:.1%})")
    print(f"Minimum required accuracy: {minimum_accuracy:.1%}")
    return 0 if accuracy >= minimum_accuracy else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8001")
    parser.add_argument(
        "--minimum-accuracy",
        type=float,
        default=0.0,
        help="Optional passing threshold from 0.0 to 1.0 (default: report only)",
    )
    args = parser.parse_args()
    if not 0.0 <= args.minimum_accuracy <= 1.0:
        parser.error("--minimum-accuracy must be between 0.0 and 1.0")
    raise SystemExit(run_evaluation(args.base_url, args.minimum_accuracy))
