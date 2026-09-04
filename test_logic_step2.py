# test_logic_step2.py
import unittest
from unittest.mock import patch
from utils.comparison import math_compare
from utils.logic_step2 import analyze_student_log, calculate_health_score

# None/"A"/"B"/"C"/"D" 다섯 값 중 무엇에도 해당하지 않는 output_type은 실제
# 케이스에는 존재하지 않지만(3-d 완료로 전부 신규 경로로 전환됨), cases 테이블에
# 잘못된 값이 들어간 경우를 조기에 드러내기 위해 디스패처가 명시적으로
# ValueError를 던진다 — 아래 fixture는 그 안전망을 확인하는 용도다.
CASE_UNKNOWN_FALLBACK = {"case_id": "hypothetical", "output_type": "UNKNOWN"}

# 신규 경로(D/수강/시험대비) fixture
CASE_SELF_REPORT = {"case_id": "course", "output_type": None}
CASE_DESIGN = {"case_id": "assignment_D", "output_type": "D"}

# 신규 경로(B=코드, diff/AST 비교) fixture
CASE_CODE = {"case_id": "assignment_B", "output_type": "B"}

# 신규 경로(A=텍스트, 임베딩 유사도+문장 재구성 비율) fixture
CASE_TEXT = {"case_id": "assignment_A", "output_type": "A"}

# 신규 경로(C=물리, 수식 동치 판정+전개 단계 수 비율) fixture
CASE_MATH = {"case_id": "assignment_C", "output_type": "C"}


class TestLogicStep2UnknownOutputType(unittest.TestCase):
    def test_unknown_output_type_raises_value_error(self):
        # 어떤 신규 경로 분기에도 해당하지 않으면(cases 테이블 오타 등을 가정),
        # 조용히 실패하는 대신 명시적으로 ValueError를 던져야 한다. 어느 분기에도
        # 걸리지 않으므로 Gemini API도 호출되지 않는다(mock 불필요).
        with self.assertRaises(ValueError):
            analyze_student_log(CASE_UNKNOWN_FALLBACK, "일부 로그 내용")

    def test_analyze_student_log_empty_input(self):
        with self.assertRaises(ValueError):
            analyze_student_log(CASE_UNKNOWN_FALLBACK, "   ")


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


class TestLogicStep2TextCompare(unittest.TestCase):
    @patch('utils.logic_step2.text_compare.calculate_autonomy_score')
    @patch('utils.logic_step2.call_gemini_api')
    def test_text_compare_path_combines_components(self, mock_call_api, mock_autonomy):
        mock_call_api.return_value = (
            '{"prompt_soundness": 55, '
            '"risk_deduction": 65, '
            '"risk_highlight": "", '
            '"analysis_summary": "요약", '
            '"target_concept": "핵심 논거"}'
        )
        mock_autonomy.return_value = 40
        text_pair = {"ai_text": "AI 초안 텍스트", "student_text": "학생 최종 제출문"}

        result = analyze_student_log(CASE_TEXT, "일부 로그 내용", text_pair=text_pair)

        mock_autonomy.assert_called_once_with("AI 초안 텍스트", "학생 최종 제출문")
        self.assertEqual(result["components"], {
            "prompt_soundness": 55,
            "autonomy": 40,
            "risk_deduction": 65,
        })
        self.assertEqual(result["health_score"], 53)  # round((55+40+65)/3) = round(53.33) = 53

    def test_text_compare_path_requires_text_pair(self):
        with self.assertRaises(ValueError):
            analyze_student_log(CASE_TEXT, "일부 로그 내용", text_pair=None)


class TestLogicStep2MathCompare(unittest.TestCase):
    @patch('utils.logic_step2.math_compare.calculate_autonomy_score')
    @patch('utils.logic_step2.call_gemini_api')
    def test_math_compare_path_combines_components(self, mock_call_api, mock_autonomy):
        mock_call_api.return_value = (
            '{"prompt_soundness": 50, '
            '"risk_deduction": 80, '
            '"risk_highlight": "", '
            '"analysis_summary": "요약", '
            '"target_concept": "뉴턴 제2법칙"}'
        )
        mock_autonomy.return_value = 35
        math_pair = {
            "ai_final_formula": "F = m*a",
            "student_final_formula": "F = m*a",
            "ai_solution_text": "F = m*a",
            "student_solution_text": "F = m*a",
        }
        self_report = {"adoption_choice": "일부 수정", "revision_count": 0}

        result = analyze_student_log(
            CASE_MATH, "일부 로그 내용", self_report=self_report, math_pair=math_pair
        )

        mock_autonomy.assert_called_once_with("F = m*a", "F = m*a", "F = m*a", "F = m*a")
        self.assertEqual(result["components"], {
            "prompt_soundness": 50,
            "autonomy": 35,
            "risk_deduction": 80,
        })
        self.assertEqual(result["health_score"], 55)  # round((50+35+80)/3) = round(55) = 55

    @patch('utils.logic_step2.math_compare.calculate_autonomy_score')
    @patch('utils.logic_step2.call_gemini_api')
    def test_math_compare_path_falls_back_to_self_report_on_parse_failure(
        self, mock_call_api, mock_autonomy
    ):
        mock_call_api.return_value = (
            '{"prompt_soundness": 50, '
            '"risk_deduction": 50, '
            '"risk_highlight": "", '
            '"analysis_summary": "요약", '
            '"target_concept": "뉴턴 제2법칙"}'
        )
        mock_autonomy.side_effect = math_compare.MathParsingError("한글 혼입으로 파싱 실패")
        math_pair = {
            "ai_final_formula": "F = m*a",
            "student_final_formula": "뉴턴 제2법칙에 의해 F=ma이다",
            "ai_solution_text": "F = m*a",
            "student_solution_text": "F = m*a",
        }
        self_report = {"adoption_choice": "전면 재작업", "revision_count": 3}

        result = analyze_student_log(
            CASE_MATH, "일부 로그 내용", self_report=self_report, math_pair=math_pair
        )

        # autonomy = 80(전면 재작업) + min(3*5, 20) = 95
        self.assertEqual(result["components"]["autonomy"], 95)

    def test_math_compare_path_requires_math_pair(self):
        with self.assertRaises(ValueError):
            analyze_student_log(
                CASE_MATH,
                "일부 로그 내용",
                self_report={"adoption_choice": "일부 수정", "revision_count": 0},
                math_pair=None,
            )

    def test_math_compare_path_requires_self_report_for_fallback(self):
        math_pair = {
            "ai_final_formula": "F = m*a",
            "student_final_formula": "F = m*a",
            "ai_solution_text": "F = m*a",
            "student_solution_text": "F = m*a",
        }
        with self.assertRaises(ValueError):
            analyze_student_log(CASE_MATH, "일부 로그 내용", self_report=None, math_pair=math_pair)


class TestCalculateHealthScore(unittest.TestCase):
    def test_equal_weighting_matches_spec_example(self):
        # AI_INSTRUCTIONS.md 예시: health_score:35 = (40+30+35)/3
        components = {"prompt_soundness": 40, "autonomy": 30, "risk_deduction": 35}
        self.assertEqual(calculate_health_score(components), 35)


if __name__ == "__main__":
    unittest.main()
