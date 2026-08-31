# test_logic_step2.py
import unittest
from unittest.mock import patch
from utils.logic_step2 import analyze_student_log, calculate_health_score

# 레거시 경로(A/C만 남음 — B는 3-b에서 diff/AST 비교 경로로 전환) fixture
CASE_LEGACY = {"case_id": "assignment_C", "output_type": "C"}

# 신규 경로(D/수강/시험대비) fixture
CASE_SELF_REPORT = {"case_id": "course", "output_type": None}
CASE_DESIGN = {"case_id": "assignment_D", "output_type": "D"}

# 신규 경로(B=코드, diff/AST 비교) fixture
CASE_CODE = {"case_id": "assignment_B", "output_type": "B"}


class TestLogicStep2Legacy(unittest.TestCase):
    @patch('utils.logic_step2.call_gemini_api')
    def test_analyze_student_log_success(self, mock_call_api):
        mock_call_api.return_value = (
            '{"health_score": 75, '
            '"risk_highlight": "이 에러 알아서 고쳐줘", '
            '"analysis_summary": "의존형 지시어가 발견되었습니다.", '
            '"target_concept": "시간 복잡도"}'
        )

        result = analyze_student_log(CASE_LEGACY, "일부 로그 내용")
        self.assertEqual(result["health_score"], 75)
        self.assertEqual(result["risk_highlight"], "이 에러 알아서 고쳐줘")
        self.assertEqual(result["analysis_summary"], "의존형 지시어가 발견되었습니다.")
        self.assertEqual(result["target_concept"], "시간 복잡도")
        self.assertNotIn("components", result)

    @patch('utils.logic_step2.call_gemini_api')
    def test_analyze_student_log_missing_keys(self, mock_call_api):
        mock_call_api.return_value = (
            '{"risk_highlight": "이 에러 알아서 고쳐줘", '
            '"analysis_summary": "의존형 지시어가 발견되었습니다."}'
        )

        result = analyze_student_log(CASE_LEGACY, "일부 로그 내용")
        self.assertEqual(result["health_score"], 50)  # Default value
        self.assertEqual(result["target_concept"], "데이터 구조 기초")  # Default value

    def test_analyze_student_log_empty_input(self):
        with self.assertRaises(ValueError):
            analyze_student_log(CASE_LEGACY, "   ")


class TestLogicStep2SelfReport(unittest.TestCase):
    @patch('utils.logic_step2.call_gemini_api')
    def test_self_report_path_combines_components(self, mock_call_api):
        mock_call_api.return_value = (
            '{"prompt_soundness": 40, '
            '"risk_deduction": 35, '
            '"risk_highlight": "그대로 써줘", '
            '"analysis_summary": "요약", '
            '"target_concept": "핵심 개념"}'
        )
        self_report = {"adoption_choice": "일부 수정", "revision_count": 2}

        result = analyze_student_log(CASE_SELF_REPORT, "일부 로그 내용", self_report)

        # autonomy = 50(일부 수정) + min(2*5, 20) = 60
        self.assertEqual(result["components"], {
            "prompt_soundness": 40,
            "autonomy": 60,
            "risk_deduction": 35,
        })
        self.assertEqual(result["health_score"], calculate_health_score(result["components"]))
        self.assertEqual(result["health_score"], 45)  # round((40+60+35)/3) = round(45) = 45

    @patch('utils.logic_step2.call_gemini_api')
    def test_self_report_path_missing_keys_uses_fallback(self, mock_call_api):
        mock_call_api.return_value = '{"risk_highlight": "", "analysis_summary": "요약"}'
        self_report = {"adoption_choice": "전면 재작업", "revision_count": 0}

        result = analyze_student_log(CASE_DESIGN, "일부 로그 내용", self_report)

        self.assertEqual(result["components"]["prompt_soundness"], 50)
        self.assertEqual(result["components"]["risk_deduction"], 50)
        self.assertEqual(result["components"]["autonomy"], 80)
        self.assertEqual(result["target_concept"], "핵심 학습 개념 미도출")

    def test_self_report_path_requires_self_report(self):
        with self.assertRaises(ValueError):
            analyze_student_log(CASE_SELF_REPORT, "일부 로그 내용", None)


class TestLogicStep2CodeCompare(unittest.TestCase):
    @patch('utils.logic_step2.code_compare.calculate_autonomy_score')
    @patch('utils.logic_step2.call_gemini_api')
    def test_code_compare_path_combines_components(self, mock_call_api, mock_autonomy):
        mock_call_api.return_value = (
            '{"prompt_soundness": 60, '
            '"risk_deduction": 70, '
            '"risk_highlight": "", '
            '"analysis_summary": "요약", '
            '"target_concept": "재귀"}'
        )
        mock_autonomy.return_value = 20
        code_pair = {"ai_code": "def f(): pass", "student_code": "def f(): pass"}

        result = analyze_student_log(CASE_CODE, "일부 로그 내용", code_pair=code_pair)

        mock_autonomy.assert_called_once_with("def f(): pass", "def f(): pass")
        self.assertEqual(result["components"], {
            "prompt_soundness": 60,
            "autonomy": 20,
            "risk_deduction": 70,
        })
        self.assertEqual(result["health_score"], 50)  # round((60+20+70)/3) = 50

    def test_code_compare_path_requires_code_pair(self):
        with self.assertRaises(ValueError):
            analyze_student_log(CASE_CODE, "일부 로그 내용", code_pair=None)


class TestCalculateHealthScore(unittest.TestCase):
    def test_equal_weighting_matches_spec_example(self):
        # AI_INSTRUCTIONS.md 예시: health_score:35 = (40+30+35)/3
        components = {"prompt_soundness": 40, "autonomy": 30, "risk_deduction": 35}
        self.assertEqual(calculate_health_score(components), 35)


if __name__ == "__main__":
    unittest.main()
