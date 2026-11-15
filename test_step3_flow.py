# test_step3_flow.py
"""3단계 제출 흐름(잠금·재시도·완료) 테스트. DB/Gemini 호출 없이 AppTest로 페이지를
실행한다 — 퀴즈는 세션에 미리 넣어 생성 호출을 피하고, save_step3_response는 patch한다.
(test_page_locks.py와 같은 이유로 더미 SUPABASE_URL/KEY를 먼저 세팅한다.)"""
import os
import unittest
from unittest.mock import patch

os.environ.setdefault("SUPABASE_URL", "http://localhost")
os.environ.setdefault("SUPABASE_KEY", "dummy-key")

from streamlit.testing.v1 import AppTest

PAGE = "pages/3_전이검증.py"
SAVE = "utils.db_handler.save_step3_response"

SUBMIT_LABEL = "🚀 정답 검증 및 제출"
NEW_QUIZ_LABEL = "🔄 새로운 퀴즈 출제"
FINISH_LABEL = "🏁 여기서 마무리"
REPORT_LABEL = "📄 결과 리포트 보기"

CASE = {
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
    "components": {"prompt_soundness": 70, "autonomy": 80, "risk_deduction": 66},
    "risk_highlight": "",
    "analysis_summary": "요약",
    "target_concept": "포인터",
}

QUIZ = {
    "quiz_type": "개념 자기설명 작성",
    "dynamic_question": "포인터가 무엇인지 1문장으로 설명하세요",
    "expected_keywords": ["주소"],
}

WRONG = "변수의 값을 복사합니다"
RIGHT = "메모리 주소를 저장하는 변수입니다"


def make_app(extra: dict | None = None) -> AppTest:
    at = AppTest.from_file(PAGE, default_timeout=30)
    state = {
        "consented": True,
        "session_id": "fake-session-id",
        "case_id": "course",
        "case": CASE,
        "step1_done": True,
        "step1_persona": "자기 주도형",
        "step2_done": True,
        "step2_result": STEP2_RESULT,
        "step3_quiz": dict(QUIZ),
        "last_target_concept": "포인터",
        **(extra or {}),
    }
    for k, v in state.items():
        at.session_state[k] = v
    return at


def button(at: AppTest, label: str):
    matches = [b for b in at.button if b.label == label]
    if not matches:
        raise AssertionError(f"버튼 없음: {label!r} (있는 버튼: {[b.label for b in at.button]})")
    return matches[0]


def answer_box(at: AppTest):
    return at.text_input[0]


def _page_text(at: AppTest) -> str:
    """오류·안내·마크다운 등 화면의 텍스트 요소를 한 문자열로 모은다."""
    elements = [*at.error, *at.info, *at.success, *at.warning, *at.markdown]
    return "\n".join(str(e.value) for e in elements)


def submit(at: AppTest, answer: str) -> AppTest:
    answer_box(at).input(answer)
    button(at, SUBMIT_LABEL).click()
    return at.run()


class TestSubmitLock(unittest.TestCase):
    def test_wrong_answer_locks_immediately(self):
        """버그 A 회귀: 제출 한 번 만에 입력창·제출 버튼이 잠겨 보여야 한다."""
        with patch(SAVE) as save:
            at = make_app().run()
            submit(at, WRONG)
            self.assertEqual(len(at.exception), 0)
            self.assertEqual(save.call_count, 1)
            self.assertFalse(save.call_args.kwargs["is_correct"])
            self.assertTrue(answer_box(at).disabled)
            self.assertTrue(button(at, SUBMIT_LABEL).disabled)
            self.assertTrue(any("키워드 판정 보완 필요" in e.value for e in at.error))

    def test_locked_quiz_cannot_be_resubmitted(self):
        with patch(SAVE) as save:
            at = make_app().run()
            submit(at, WRONG)
            button(at, SUBMIT_LABEL).click()
            at.run()
            self.assertEqual(save.call_count, 1)

    def test_empty_answer_warns_without_lock_or_save(self):
        with patch(SAVE) as save:
            at = make_app().run()
            submit(at, "   ")
            save.assert_not_called()
            self.assertFalse(answer_box(at).disabled)
            self.assertTrue(any("답변을 먼저 입력" in w.value for w in at.warning))

    def test_save_failure_keeps_quiz_open_and_retry_saves_again(self):
        with patch(SAVE, side_effect=RuntimeError("db down")) as save:
            at = make_app().run()
            submit(at, RIGHT)
            self.assertEqual(save.call_count, 1)
            self.assertFalse(answer_box(at).disabled)
            self.assertFalse(button(at, SUBMIT_LABEL).disabled)
            self.assertTrue(any("저장" in e.value for e in at.error))
            self.assertEqual(at.session_state["acquired_keywords"], [])

            save.side_effect = None
            button(at, SUBMIT_LABEL).click()
            at.run()
            self.assertEqual(save.call_count, 2)
            self.assertTrue(answer_box(at).disabled)

    def test_wrong_then_new_quiz_reopens_empty_input(self):
        with patch(SAVE):
            at = make_app().run()
            submit(at, WRONG)
            # 새 퀴즈 생성(Gemini) 호출은 patch로 대체한다
            with patch("utils.logic_step3.generate_adaptive_quiz", return_value=dict(QUIZ)):
                button(at, NEW_QUIZ_LABEL).click()
                at.run()
            self.assertEqual(len(at.exception), 0)
            self.assertEqual(at.session_state["step3_attempt"], 1)
            self.assertFalse(answer_box(at).disabled)
            self.assertEqual(answer_box(at).value, "")


class TestStep3Completion(unittest.TestCase):
    def test_correct_answer_completes_step3_and_locks_everything(self):
        with patch(SAVE) as save:
            at = make_app().run()
            submit(at, RIGHT)
            self.assertEqual(len(at.exception), 0)
            self.assertTrue(save.call_args.kwargs["is_correct"])
            self.assertTrue(at.session_state["step3_done"])
            self.assertEqual(at.session_state["step3_done_reason"], "correct")
            self.assertEqual(at.session_state["acquired_keywords"], ["포인터"])
            self.assertEqual(
                at.session_state["step3_history"],
                [{"quiz_type": QUIZ["quiz_type"], "is_correct": True}],
            )
            self.assertTrue(answer_box(at).disabled)
            self.assertTrue(button(at, SUBMIT_LABEL).disabled)
            self.assertTrue(button(at, NEW_QUIZ_LABEL).disabled)
            self.assertTrue(button(at, FINISH_LABEL).disabled)
            self.assertTrue(any("3단계를 완료했습니다" in s.value for s in at.success))
            self.assertFalse(button(at, REPORT_LABEL).disabled)

    def test_locked_new_quiz_click_is_ignored(self):
        with patch(SAVE):
            at = make_app().run()
            submit(at, RIGHT)
            button(at, NEW_QUIZ_LABEL).click()
            at.run()
            self.assertEqual(at.session_state["step3_attempt"], 0)
            self.assertEqual(at.session_state["step3_quiz"], QUIZ)

    def test_finish_disabled_until_a_submission_is_saved(self):
        with patch(SAVE):
            at = make_app().run()
            self.assertTrue(button(at, FINISH_LABEL).disabled)
            button(at, FINISH_LABEL).click()
            at.run()
            self.assertFalse(at.session_state["step3_done"])

            submit(at, WRONG)
            self.assertFalse(button(at, FINISH_LABEL).disabled)
            self.assertFalse(button(at, NEW_QUIZ_LABEL).disabled)

    def test_finish_after_wrong_answer_completes_and_locks(self):
        with patch(SAVE):
            at = make_app().run()
            submit(at, WRONG)
            button(at, FINISH_LABEL).click()
            at.run()
            self.assertEqual(len(at.exception), 0)
            self.assertTrue(at.session_state["step3_done"])
            self.assertEqual(at.session_state["step3_done_reason"], "finished")
            self.assertEqual(at.session_state["acquired_keywords"], [])
            self.assertTrue(button(at, NEW_QUIZ_LABEL).disabled)
            self.assertTrue(button(at, FINISH_LABEL).disabled)
            self.assertTrue(any("3단계를 마무리했습니다" in i.value for i in at.info))
            self.assertFalse(button(at, REPORT_LABEL).disabled)

    def test_wrong_feedback_hidden_after_finish(self):
        """회귀: 마무리 완료 상태에서는 이전 오답 피드백 문구가 화면에 없어야 한다."""
        with patch(SAVE):
            at = make_app().run()
            submit(at, WRONG)
            self.assertIn("다시 시도해 볼까요?", _page_text(at))  # 마무리 전에는 오답 피드백이 보임

            button(at, FINISH_LABEL).click()
            at.run()
            text = _page_text(at)
            self.assertNotIn("키워드 판정 보완 필요", text)
            self.assertNotIn("다시 시도해 볼까요?", text)
            self.assertIn("3단계를 마무리했습니다", text)

    def test_correct_feedback_kept_after_correct_completion(self):
        with patch(SAVE):
            at = make_app().run()
            submit(at, RIGHT)
            self.assertTrue(any("정답입니다" in s.value for s in at.success))

    def test_report_button_hidden_before_completion(self):
        with patch(SAVE):
            at = make_app().run()
            submit(at, WRONG)
            self.assertNotIn(REPORT_LABEL, [b.label for b in at.button])

    def test_save_failure_does_not_count_toward_finish(self):
        with patch(SAVE, side_effect=RuntimeError("db down")):
            at = make_app().run()
            submit(at, WRONG)
            self.assertEqual(at.session_state["step3_history"], [])
            self.assertTrue(button(at, FINISH_LABEL).disabled)


if __name__ == "__main__":
    unittest.main()
