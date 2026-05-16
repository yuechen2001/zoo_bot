from game.trivia_data import QUESTIONS

VALID_ANSWERS = {"A", "B", "C", "D"}


class TestTriviaData:
    def test_has_15_questions(self):
        assert len(QUESTIONS) == 15

    def test_each_question_has_required_fields(self):
        for i, q in enumerate(QUESTIONS):
            assert "q" in q, f"Question {i} missing 'q'"
            assert "options" in q, f"Question {i} missing 'options'"
            assert "answer" in q, f"Question {i} missing 'answer'"

    def test_each_question_has_4_options(self):
        for i, q in enumerate(QUESTIONS):
            assert (
                len(q["options"]) == 4
            ), f"Question {i} has {len(q['options'])} options, expected 4"

    def test_each_answer_is_valid(self):
        for i, q in enumerate(QUESTIONS):
            assert q["answer"] in VALID_ANSWERS, f"Question {i} has invalid answer '{q['answer']}'"

    def test_each_option_is_non_empty_string(self):
        for i, q in enumerate(QUESTIONS):
            for j, opt in enumerate(q["options"]):
                assert (
                    isinstance(opt, str) and opt.strip()
                ), f"Question {i} option {j} is empty or not a string"

    def test_each_question_text_is_non_empty(self):
        for i, q in enumerate(QUESTIONS):
            assert (
                isinstance(q["q"], str) and q["q"].strip()
            ), f"Question {i} has empty question text"

    def test_option_labels_match_a_b_c_d(self):
        for i, q in enumerate(QUESTIONS):
            labels = [opt[0] for opt in q["options"]]
            assert labels == [
                "A",
                "B",
                "C",
                "D",
            ], f"Question {i} options don't start with A, B, C, D"
