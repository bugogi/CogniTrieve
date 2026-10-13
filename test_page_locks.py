# test_page_locks.py
"""DB/Gemini 호출 없이, 세션 상태에 따른 1·2단계 잠금 렌더링 분기만 검증한다.
AppTest는 실제 Streamlit 스크립트를 그대로 실행하므로 st.secrets/환경변수에 의존하는
get_client() 초기화가 모듈 임포트 시점에 실패하지 않도록 더미 SUPABASE_URL/KEY를
먼저 세팅해 둔다(실제 네트워크 호출은 어떤 테스트에서도 트리거하지 않는다)."""
import os
import unittest

os.environ.setdefault("SUPABASE_URL", "http://localhost")
os.environ.setdefault("SUPABASE_KEY", "dummy-key")

from streamlit.testing.v1 import AppTest

CASE_SELF_REPORT = {
    "case_id": "course",
    "learning_type": "수강",
    "output_type": None,
    "questions": ["문항1", "문항2", "문항3", "문항4", "문항5"],
    "hotspot_primary": 1,
    "hotspot_secondary": 2,
    "hotspot_tier": {"primary": "최고위험", "secondary": "위험"},
    "concept_vocabulary": None,
}

STEP2_RESULT = {
    "health_score": 72,
    "components": None,
    "risk_highlight": "",
    "analysis_summary": "요약",
    "target_concept": "포인터",
}


class TestStep1Lock(unittest.TestCase):
    def _make(self, extra: dict):
        at = AppTest.from_file("pages/1_사전진단.py")
        state = {
            "consented": True,
            "session_id": "fake-session-id",
            "case_id": "course",
            "case": CASE_SELF_REPORT,
            **extra,
        }
        for k, v in state.items():
            at.session_state[k] = v
        at.run()
        return at

    def test_unlocked_shows_survey_form(self):
        at = self._make({})
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(at.radio), 5)

    def test_locked_hides_form_and_shows_notice(self):
        at = self._make({
            "step1_done": True,
            "step1_persona": "자기 주도형",
            "step1_total_score": 20,
            "step1_results": {
                "persona": "자기 주도형",
                "total_score": 20,
                "color": "#10B981",
                "icon": "🌟",
                "title": "자기 주도형",
                "description": "설명",
            },
        })
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(at.radio), 0)
        notices = [i.value for i in at.info]
        self.assertTrue(any("이미 제출했습니다" in n for n in notices))


class TestStep2Lock(unittest.TestCase):
    def _make(self, extra: dict):
        at = AppTest.from_file("pages/2_로그분석.py")
        state = {
            "consented": True,
            "session_id": "fake-session-id",
            "case_id": "course",
            "case": CASE_SELF_REPORT,
            "step1_done": True,
            "step1_persona": "자기 주도형",
            **extra,
        }
        for k, v in state.items():
            at.session_state[k] = v
        at.run()
        return at

    def test_no_result_yet_shows_input_form(self):
        at = self._make({})
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(at.text_area), 1)
        labels = [b.label for b in at.button]
        self.assertIn("⚡ Gemini AI 교차 분석 시작", labels)

    def test_result_pending_save_hides_form_shows_retry_button(self):
        at = self._make({"step2_result": STEP2_RESULT, "step2_done": False})
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(at.text_area), 0)
        labels = [b.label for b in at.button]
        self.assertIn("🔁 결과 저장 재시도", labels)
        self.assertNotIn("🎯 3단계: 적응형 전이 검증(퀴즈) 시작", labels)

    def test_locked_shows_readonly_result_and_next_step_button(self):
        at = self._make({"step2_result": STEP2_RESULT, "step2_done": True})
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(at.text_area), 0)
        labels = [b.label for b in at.button]
        self.assertIn("🎯 3단계: 적응형 전이 검증(퀴즈) 시작", labels)
        notices = [i.value for i in at.info]
        self.assertTrue(any("이미 제출했습니다" in n for n in notices))

    def test_entering_without_step1_done_is_blocked(self):
        at = self._make({"step1_done": False})
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(at.text_area), 0)
        warnings = [w.value for w in at.warning]
        self.assertTrue(any("1단계 사전진단을 완료" in w for w in warnings))


if __name__ == "__main__":
    unittest.main()
