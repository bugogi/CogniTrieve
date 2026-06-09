# test_logic_step2.py
import unittest
from unittest.mock import patch
from utils.logic_step2 import analyze_student_log

class TestLogicStep2(unittest.TestCase):
    @patch('utils.logic_step2.call_gemini_api')
    def test_analyze_student_log_success(self, mock_call_api):
        # Mock successful JSON response
        mock_call_api.return_value = (
            '{"health_score": 75, '
            '"risk_highlight": "이 에러 알아서 고쳐줘", '
            '"analysis_summary": "의존형 지시어가 발견되었습니다.", '
            '"target_concept": "시간 복잡도"}'
        )
        
        result = analyze_student_log("일부 로그 내용")
        self.assertEqual(result["health_score"], 75)
        self.assertEqual(result["risk_highlight"], "이 에러 알아서 고쳐줘")
        self.assertEqual(result["analysis_summary"], "의존형 지시어가 발견되었습니다.")
        self.assertEqual(result["target_concept"], "시간 복잡도")
        
    @patch('utils.logic_step2.call_gemini_api')
    def test_analyze_student_log_missing_keys(self, mock_call_api):
        # Mock JSON response missing health_score and target_concept
        mock_call_api.return_value = (
            '{"risk_highlight": "이 에러 알아서 고쳐줘", '
            '"analysis_summary": "의존형 지시어가 발견되었습니다."}'
        )
        
        result = analyze_student_log("일부 로그 내용")
        self.assertEqual(result["health_score"], 50)  # Default value
        self.assertEqual(result["target_concept"], "데이터 구조 기초")  # Default value
        
    def test_analyze_student_log_empty_input(self):
        with self.assertRaises(ValueError):
            analyze_student_log("   ")

if __name__ == "__main__":
    unittest.main()
