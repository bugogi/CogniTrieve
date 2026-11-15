# test_result_report.py
"""결과 리포트(utils/result_report.py, pages/4_결과리포트.py) 테스트. DB/Gemini 호출 없음."""
import os
import unittest

os.environ.setdefault("SUPABASE_URL", "http://localhost")
os.environ.setdefault("SUPABASE_KEY", "dummy-key")

from streamlit.testing.v1 import AppTest

from test_step3_flow import CASE, STEP2_RESULT
from utils.result_report import (
    CROSS_CHECK_GUIDE,
    build_report,
    is_report_ready,
)

PAGE = "pages/4_결과리포트.py"

STEP1_RESULTS = {
    "persona": "자기 주도형",
    "total_score": 22,
    "color": "#10B981",
    "icon": "👑",
    "title": "자기 주도형 (Self-Directed)",
    "description": "페르소나 설명",
}

COMPLETED_STATE = {
    "consented": True,
    "session_id": "fake-session-id",
    "case_id": "course",
    "case": CASE,
    "step1_done": True,
    "step1_persona": "자기 주도형",
    "step1_total_score": 22,
    "step1_results": STEP1_RESULTS,
    "step2_done": True,
    "step2_result": STEP2_RESULT,
    "step3_done": True,
    "step3_done_reason": "finished",
    # 1번 퀴즈 오답 → 같은 문제 재제출 오답 → 새 퀴즈(2번) 정답
    "step3_history": [
        {"quiz_no": 1, "quiz_type": "개념 자기설명 작성", "is_correct": False},
        {"quiz_no": 1, "quiz_type": "개념 자기설명 작성", "is_correct": False},
        {"quiz_no": 2, "quiz_type": "개념 자기설명 작성", "is_correct": True},
    ],
    "acquired_keywords": ["포인터"],
}


class TestBuildReport(unittest.TestCase):
    def test_sections(self):
        report = build_report(COMPLETED_STATE)
        self.assertEqual(report["step1"]["persona"], "자기 주도형")
        self.assertEqual(report["step1"]["total_score"], 22)
        self.assertEqual(report["step1"]["max_score"], 25)
        self.assertEqual(report["step2"]["health_score"], 72)
        self.assertEqual(
            [c["label"] for c in report["step2"]["components"]],
            ["프롬프트 건전성", "자립도", "위험구간 감점"],
        )
        step3 = report["step3"]
        self.assertEqual(step3["quiz_count"], 2)  # 서로 다른 퀴즈 번호 수
        self.assertEqual(step3["submission_count"], 3)  # 같은 문제 재제출 포함
        self.assertEqual(step3["correct_count"], 1)
        self.assertEqual([r["결과"] for r in step3["rows"]], ["오답", "오답", "정답"])
        self.assertEqual([r["퀴즈"] for r in step3["rows"]], ["1번", "1번", "2번"])
        self.assertEqual(step3["done_reason_label"], "직접 마무리")
        self.assertEqual(step3["badges"], ["포인터"])
        self.assertEqual(report["cross_check"]["guide"], CROSS_CHECK_GUIDE)

    def test_correct_reason_label(self):
        state = {**COMPLETED_STATE, "step3_done_reason": "correct"}
        self.assertEqual(build_report(state)["step3"]["done_reason_label"], "정답으로 통과")

    def test_missing_components_and_step1_results_fallback(self):
        state = {
            **COMPLETED_STATE,
            "step1_results": None,
            "step2_result": {**STEP2_RESULT, "components": None},
        }
        report = build_report(state)
        self.assertEqual(report["step1"]["persona"], "자기 주도형")
        self.assertEqual(report["step1"]["total_score"], 22)
        self.assertEqual(report["step2"]["components"], [])

    def test_report_ready_only_after_step3_done(self):
        self.assertTrue(is_report_ready(COMPLETED_STATE))
        self.assertFalse(is_report_ready({**COMPLETED_STATE, "step3_done": False}))
        self.assertFalse(is_report_ready({}))


class TestReportPage(unittest.TestCase):
    def _run(self, state: dict) -> AppTest:
        at = AppTest.from_file(PAGE, default_timeout=30)
        for k, v in state.items():
            at.session_state[k] = v
        return at.run()

    def test_blocked_before_step3_done(self):
        at = self._run({**COMPLETED_STATE, "step3_done": False, "step3_done_reason": None})
        self.assertEqual(len(at.exception), 0)
        self.assertTrue(any("3단계 전이검증을 마친 뒤" in w.value for w in at.warning))
        self.assertEqual(len(at.dataframe), 0)

    def test_blocked_without_consent(self):
        at = self._run({})
        self.assertEqual(len(at.exception), 0)
        self.assertTrue(any("동의 및 케이스 선택" in w.value for w in at.warning))

    def test_renders_completed_report(self):
        at = self._run(COMPLETED_STATE)
        self.assertEqual(len(at.exception), 0)
        self.assertTrue(any(CROSS_CHECK_GUIDE == i.value for i in at.info))
        table = at.dataframe[0].value
        self.assertEqual(list(table["결과"]), ["오답", "오답", "정답"])
        self.assertEqual(list(table["퀴즈"]), ["1번", "1번", "2번"])
        markdown = "\n".join(m.value for m in at.markdown)
        self.assertIn("직접 마무리", markdown)
        self.assertIn("#포인터", markdown)
        self.assertIn("Health Score: **72 / 100점**", markdown)
        self.assertIn("푼 퀴즈 <b>2</b>개 · 제출 <b>3</b>회", markdown)

    def test_legacy_history_without_quiz_no(self):
        """quiz_no가 없는 이력(이번 변경 이전 세션)도 제출 수 기준으로 표시된다."""
        state = {
            **COMPLETED_STATE,
            "step3_history": [{"quiz_type": "개념 자기설명 작성", "is_correct": True}],
        }
        step3 = build_report(state)["step3"]
        self.assertEqual(step3["quiz_count"], 1)
        self.assertEqual(step3["rows"][0]["퀴즈"], "-")

    def test_llm_strings_are_escaped(self):
        state = {
            **COMPLETED_STATE,
            "step2_result": {**STEP2_RESULT, "target_concept": "<script>x</script>"},
            "acquired_keywords": ["<b>kw</b>"],
        }
        at = self._run(state)
        markdown = "\n".join(m.value for m in at.markdown)
        self.assertNotIn("<script>", markdown)
        self.assertIn("&lt;script&gt;", markdown)
        self.assertIn("#&lt;b&gt;kw&lt;/b&gt;", markdown)


if __name__ == "__main__":
    unittest.main()
