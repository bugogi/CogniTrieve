# test_logic_step3.py
import unittest
from unittest.mock import patch
from utils.logic_step3 import generate_adaptive_quiz, verify_answer

class TestLogicStep3(unittest.TestCase):
    @patch('utils.logic_step3.call_gemini_api')
    def test_generate_adaptive_quiz_success(self, mock_call_api):
        # Mock a successful JSON response
        mock_call_api.return_value = (
            '{"quiz_type": "에러 원인 분석", '
            '"dynamic_question": "퀵 정렬의 최악 시간복잡도가 발생하는 경우를 설명하세요.", '
            '"expected_keywords": ["오름차순", "피벗", "정렬된"]}'
        )
        
        result = generate_adaptive_quiz("퀵 정렬", "통째로 구현해줘")
        self.assertEqual(result["quiz_type"], "에러 원인 분석")
        self.assertEqual(result["dynamic_question"], "퀵 정렬의 최악 시간복잡도가 발생하는 경우를 설명하세요.")
        self.assertEqual(result["expected_keywords"], ["오름차순", "피벗", "정렬된"])
        
    @patch('utils.logic_step3.call_gemini_api')
    def test_generate_adaptive_quiz_missing_or_invalid_fields(self, mock_call_api):
        # Mock an invalid response
        mock_call_api.return_value = '{"invalid_field": "값"}'
        
        result = generate_adaptive_quiz("메모리 누수", "")
        self.assertEqual(result["quiz_type"], "핵심 로직 주석")  # Default value
        self.assertEqual(result["dynamic_question"], "'메모리 누수'의 동작 원리와 왜 중요한지 50자 이내로 핵심을 서술해 보세요.")  # Default value
        self.assertEqual(result["expected_keywords"], ["메모리 누수"])  # Default value
        
    @patch('utils.logic_step3.call_gemini_api')
    def test_generate_adaptive_quiz_json_decode_error(self, mock_call_api):
        # Mock JSON decode error raw response
        mock_call_api.return_value = "This is not JSON text"
        
        result = generate_adaptive_quiz("재귀 함수", "에러 해결법 알려줘")
        self.assertEqual(result["quiz_type"], "핵심 로직 주석")
        self.assertEqual(result["dynamic_question"], "'재귀 함수'의 동작 원리와 왜 중요한지 50자 이내로 핵심을 서술해 보세요.")
        self.assertEqual(result["expected_keywords"], ["재귀 함수"])

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
