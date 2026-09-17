import unittest

from evaluations.scoring import answer_matches


class AnswerMatchingTests(unittest.TestCase):
    def test_numeric_answer_ignores_explanation_and_unit(self):
        case = {"answer_type": "number", "expected_answer": "48%"}
        self.assertTrue(answer_matches(case, "48 percent of Gen Z travellers."))

    def test_numeric_answer_rejects_wrong_number(self):
        case = {"answer_type": "number", "expected_answer": "48%"}
        self.assertFalse(answer_matches(case, "43%"))

    def test_boolean_accepts_true_and_yes(self):
        case = {"answer_type": "boolean", "expected_answer": "true"}
        self.assertTrue(answer_matches(case, "True. Apps update over Wi-Fi."))
        self.assertTrue(answer_matches(case, "Yes, they do."))

    def test_boolean_rejects_opposite_answer(self):
        case = {"answer_type": "boolean", "expected_answer": "false"}
        self.assertFalse(answer_matches(case, "True"))

    def test_text_accepts_alias(self):
        case = {
            "answer_type": "text",
            "expected_answer": "Kobo Clara BW",
            "accepted_answers": ["Clara BW"],
        }
        self.assertTrue(answer_matches(case, "The only tested model is Clara BW."))


if __name__ == "__main__":
    unittest.main()
