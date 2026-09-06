# test_logic_step3.py
import unittest
from unittest.mock import patch
from utils.logic_step3 import generate_adaptive_quiz, verify_answer

CASE_B = {"case_id": "assignment_B", "learning_type": "과제", "output_type": "B", "concept_vocabulary": ["재귀", "시간복잡도"]}
CASE_A = {"case_id": "assignment_A", "learning_type": "과제", "output_type": "A", "concept_vocabulary": ["논지", "논거"]}
CASE_C = {"case_id": "assignment_C", "learning_type": "과제", "output_type": "C", "concept_vocabulary": ["뉴턴제2법칙"]}
CASE_D = {"case_id": "assignment_D", "learning_type": "과제", "output_type": "D", "concept_vocabulary": ["브랜드컨셉"]}
CASE_COURSE = {"case_id": "course", "learning_type": "수강", "output_type": None, "concept_vocabulary": ["능동적부호화", "자기설명"]}
CASE_EXAM_PREP = {"case_id": "exam_prep", "learning_type": "시험 대비", "output_type": None, "concept_vocabulary": ["인출연습"]}
CASE_NO_VOCAB = {"case_id": "assignment_B", "learning_type": "과제", "output_type": "B", "concept_vocabulary": []}


class TestLogicStep3(unittest.TestCase):
    @patch('utils.logic_step3.call_gemini_api')
    def test_generate_adaptive_quiz_success(self, mock_call_api):
        # Mock a successful JSON response (B 케이스 허용 목록 내 값)
        mock_call_api.return_value = (
            '{"quiz_type": "에러 로그 원인 작성", '
            '"dynamic_question": "퀵 정렬의 최악 시간복잡도가 발생하는 경우를 설명하세요?", '
            '"expected_keywords": ["오름차순", "피벗", "정렬된"]}'
        )

        result = generate_adaptive_quiz("퀵 정렬", "통째로 구현해줘", CASE_B)
        self.assertEqual(result["quiz_type"], "에러 로그 원인 작성")
        self.assertEqual(result["dynamic_question"], "퀵 정렬의 최악 시간복잡도가 발생하는 경우를 설명하세요?")
        self.assertEqual(result["expected_keywords"], ["오름차순", "피벗", "정렬된"])

    @patch('utils.logic_step3.call_gemini_api')
    def test_generate_adaptive_quiz_invalid_quiz_type_falls_back_to_first_allowed(self, mock_call_api):
        # B의 허용 목록에 없는 quiz_type이 오면 목록의 첫 번째 항목으로 폴백
        mock_call_api.return_value = '{"invalid_field": "값"}'

        result = generate_adaptive_quiz("메모리 누수", "", CASE_B)
        self.assertEqual(result["quiz_type"], "함수 주석 작성")  # B 허용 목록의 첫 항목
        self.assertEqual(
            result["dynamic_question"],
            "'메모리 누수'이 하는 일을 주석 한 줄로 설명한다면?",
        )
        self.assertEqual(result["expected_keywords"], CASE_B["concept_vocabulary"])

    @patch('utils.logic_step3.call_gemini_api')
    def test_generate_adaptive_quiz_json_decode_error(self, mock_call_api):
        # Mock JSON decode error raw response
        mock_call_api.return_value = "This is not JSON text"

        result = generate_adaptive_quiz("재귀 함수", "에러 해결법 알려줘", CASE_C)
        self.assertEqual(result["quiz_type"], "수식 도출 근거 작성")  # C의 유일한 허용 quiz_type
        self.assertEqual(
            result["dynamic_question"],
            "'재귀 함수'이 어떤 원리에서 도출되었는지 1문장으로 설명한다면?",
        )
        self.assertEqual(result["expected_keywords"], CASE_C["concept_vocabulary"])

    @patch('utils.logic_step3.call_gemini_api')
    def test_generate_adaptive_quiz_type_a(self, mock_call_api):
        mock_call_api.return_value = '{}'
        result = generate_adaptive_quiz("핵심 논거", "", CASE_A)
        self.assertEqual(result["quiz_type"], "문단 핵심 논거 요약 작성")

    @patch('utils.logic_step3.call_gemini_api')
    def test_generate_adaptive_quiz_type_d(self, mock_call_api):
        mock_call_api.return_value = '{}'
        result = generate_adaptive_quiz("컨셉 발상", "", CASE_D)
        self.assertEqual(result["quiz_type"], "아이디어 근거 작성")

    @patch('utils.logic_step3.call_gemini_api')
    def test_generate_adaptive_quiz_course_uses_learning_type(self, mock_call_api):
        # output_type이 None인 course는 learning_type("수강")으로 분기해야 한다
        mock_call_api.return_value = '{}'
        result = generate_adaptive_quiz("능동적부호화", "", CASE_COURSE)
        self.assertEqual(result["quiz_type"], "개념 자기설명 작성")

    @patch('utils.logic_step3.call_gemini_api')
    def test_generate_adaptive_quiz_exam_prep_uses_learning_type(self, mock_call_api):
        # output_type이 None인 exam_prep은 learning_type("시험 대비")으로 분기해야 한다
        mock_call_api.return_value = '{}'
        result = generate_adaptive_quiz("인출연습", "", CASE_EXAM_PREP)
        self.assertEqual(result["quiz_type"], "오답 원인 재설명 작성")

    @patch('utils.logic_step3.call_gemini_api')
    def test_generate_adaptive_quiz_unknown_case_raises(self, mock_call_api):
        mock_call_api.return_value = '{}'
        unknown_case = {"case_id": "x", "learning_type": "알수없음", "output_type": "Z"}
        with self.assertRaises(ValueError):
            generate_adaptive_quiz("개념", "", unknown_case)

    @patch('utils.logic_step3.call_gemini_api')
    def test_generate_adaptive_quiz_empty_target_concept_uses_concept_vocabulary(self, mock_call_api):
        mock_call_api.return_value = '{}'
        result = generate_adaptive_quiz("", "", CASE_B)
        self.assertIn(CASE_B["concept_vocabulary"][0], result["dynamic_question"])

    @patch('utils.logic_step3.call_gemini_api')
    def test_generate_adaptive_quiz_empty_target_concept_no_vocabulary_uses_generic_default(self, mock_call_api):
        mock_call_api.return_value = '{}'
        result = generate_adaptive_quiz("", "", CASE_NO_VOCAB)
        self.assertIn("핵심 학습 개념", result["dynamic_question"])

    @patch('utils.logic_step3.call_gemini_api')
    def test_generate_adaptive_quiz_expected_keywords_fallback_no_vocabulary(self, mock_call_api):
        mock_call_api.return_value = '{}'
        result = generate_adaptive_quiz("메모리 누수", "", CASE_NO_VOCAB)
        self.assertEqual(result["expected_keywords"], ["메모리 누수"])

    def test_verify_answer_exact_match(self):
        # Exact match (even with whitespace / case differences)
        self.assertTrue(verify_answer("시간복잡도", ["시간복잡도"]))
        self.assertTrue(verify_answer("time complexity", ["Time Complexity"]))

    def test_verify_answer_whitespace_insensitive(self):
        # White spaces in student answer or keywords should not affect the result
        self.assertTrue(verify_answer("시 간 복 잡 도", ["시간 복잡도"]))
        self.assertTrue(verify_answer("timecomplexity", ["Time Complexity"]))
        self.assertTrue(verify_answer("  time  complexity  ", ["time complexity"]))
        self.assertTrue(verify_answer("\t시간복잡도\n", ["시  간  복  잡  도"]))

    def test_verify_answer_case_insensitive(self):
        # Case differences should not affect the result
        self.assertTrue(verify_answer("BiGo notation", ["bigo"]))
        self.assertTrue(verify_answer("HEAP OVERFLOW", ["heap overflow"]))

    def test_verify_answer_multiple_keywords(self):
        # Should return True if any of the keywords are present
        keywords = ["오름차순", "pivot", "worst case"]
        self.assertTrue(verify_answer("피벗(pivot)을 잘못 잡으면 정렬 속도가 느려집니다.", keywords))
        self.assertTrue(verify_answer("최악의 경우(Worst Case)에는 느립니다.", keywords))
        self.assertTrue(verify_answer("오름 차 순 정렬", keywords))
        self.assertFalse(verify_answer("아무 키워드도 안 들어간 답변", keywords))

    def test_verify_answer_edge_cases(self):
        # Empty inputs, None values, or empty lists
        self.assertFalse(verify_answer("", ["키워드"]))
        self.assertFalse(verify_answer("답변", []))
        self.assertFalse(verify_answer(None, ["키워드"]))
        self.assertFalse(verify_answer("답변", None))
        self.assertFalse(verify_answer("   ", ["   "]))

if __name__ == "__main__":
    unittest.main()
