# test_ui_copy.py
"""화면 문구 회귀 테스트: 6개 케이스로 일반화된 뒤에도 CS(assignment_B) 전용 문구나
정리 대상이던 표현이 화면에 다시 나타나지 않는지 확인한다. DB/Gemini 호출 없음."""
import os
import re
import unittest

os.environ.setdefault("SUPABASE_URL", "http://localhost")
os.environ.setdefault("SUPABASE_KEY", "dummy-key")

from streamlit.testing.v1 import AppTest

from test_page_locks import CASE_SELF_REPORT, STEP2_RESULT
from test_step3_flow import make_app as make_step3_app

FORBIDDEN = ["CS 개념", "CS 핵심", "CS 뱃지", "CS 역량", "메타 CS", "컴퓨터공학", "뱃지", "진증", "(완료)", "(진행 중)"]


def _visible_text(at: AppTest) -> str:
    elements = [*at.markdown, *at.info, *at.success, *at.warning, *at.error, *at.caption, *at.title]
    texts = [str(e.value) for e in elements]
    texts += [str(getattr(w, "placeholder", "") or "") for w in at.text_input]
    texts += [b.label for b in at.button]
    # <style> 블록(CSS 주석 포함)은 화면에 보이지 않으므로 검사 대상에서 뺀다
    return re.sub(r"<style>.*?</style>", "", "\n".join(texts), flags=re.S)


class TestStep2Copy(unittest.TestCase):
    def _run(self, extra: dict) -> AppTest:
        at = AppTest.from_file("pages/2_로그분석.py", default_timeout=30)
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
        return at.run()

    def test_input_form_has_no_cs_specific_copy(self):
        at = self._run({})
        self.assertEqual(len(at.exception), 0)
        text = _visible_text(at)
        for word in FORBIDDEN:
            self.assertNotIn(word, text)
        self.assertIn("(코딩 과제 예시)", text)  # 예제 로그는 코딩 예시임을 밝힌다

    def test_result_has_generic_concept_copy_and_growth_label(self):
        at = self._run({"step2_result": STEP2_RESULT, "step2_done": True})
        self.assertEqual(len(at.exception), 0)
        text = _visible_text(at)
        for word in FORBIDDEN:
            self.assertNotIn(word, text)
        self.assertIn("3단계 퀴즈용 핵심 개념 추출", text)
        self.assertIn("무의식적으로 AI에 기대는 순간이 보여요", text)  # 72점 → 중간 구간 라벨
        self.assertNotIn("위험:", text)


class TestStep3Copy(unittest.TestCase):
    def test_quiz_page_has_no_cs_specific_copy(self):
        at = make_step3_app().run()
        self.assertEqual(len(at.exception), 0)
        text = _visible_text(at)
        for word in FORBIDDEN:
            self.assertNotIn(word, text)
        self.assertIn("검증 대상 핵심 개념", text)
        self.assertIn("나의 획득 배지 보관함", text)


if __name__ == "__main__":
    unittest.main()
