# test_admin_page.py
"""관리자 뷰 페이지 스모크 테스트. fetch_admin_rows를 fixture로 바꿔 DB 없이 렌더링하고,
학생 답변·로그 원문이 화면 어디에도 나오지 않는지 확인한다(test_page_locks.py와 같은
이유로 더미 SUPABASE_URL/KEY를 먼저 세팅한다)."""
import os
import unittest
from unittest.mock import patch

os.environ.setdefault("SUPABASE_URL", "http://localhost")
os.environ.setdefault("SUPABASE_KEY", "dummy-key")

import streamlit as st
from streamlit.testing.v1 import AppTest

from test_admin_metrics import SECRET_ANSWER, _raw

PAGE = "pages/9_관리자.py"
SECRET_RISK_HIGHLIGHT = "그냥 전부 짜줘 제출해야 함"


def _raw_with_leaky_columns() -> dict:
    """DB 조회가 실수로 민감 컬럼을 더 가져오더라도 화면에 안 나오는지 보기 위한 fixture."""
    raw = _raw()
    for row in raw["step2_responses"]:
        row["risk_highlight"] = SECRET_RISK_HIGHLIGHT
        row["analysis_summary"] = SECRET_RISK_HIGHLIGHT
    return raw


def _rendered_text(at: AppTest) -> str:
    """렌더링된 모든 요소(proto)를 문자열로 이어붙인다(차트 데이터·표 포함)."""
    chunks = []

    def walk(node):
        proto = getattr(node, "proto", None)
        if proto is not None:
            chunks.append(str(proto))
        children = getattr(node, "children", None) or {}
        for child in children.values():
            walk(child)

    walk(at._tree)
    for df in at.dataframe:
        chunks.append(df.value.to_csv())
    return "\n".join(chunks)


class TestAdminPage(unittest.TestCase):
    def setUp(self):
        st.cache_data.clear()

    def _run(self, raw: dict) -> AppTest:
        with patch("utils.db_handler.fetch_admin_rows", return_value=raw):
            at = AppTest.from_file(PAGE, default_timeout=30)
            at.run()
        return at

    def test_renders_with_fixture(self):
        at = self._run(_raw())
        self.assertEqual(len(at.exception), 0)
        metrics = {m.label: m.value for m in at.metric}
        self.assertEqual(metrics["전체 세션"], "6")
        self.assertEqual(metrics["완료 세션 (1~3단계)"], "2")
        self.assertEqual(metrics["첫 퀴즈 정답률 (주 지표)"], "50%")
        self.assertEqual(metrics["세션당 평균 제출 횟수 (보조 지표)"], "1.50회")

    def test_no_raw_text_rendered(self):
        at = self._run(_raw_with_leaky_columns())
        self.assertEqual(len(at.exception), 0)
        rendered = _rendered_text(at)
        self.assertIn("2026-11-14 01:00 KST", rendered)  # 렌더링 내용이 실제로 수집됐는지 확인
        self.assertNotIn(SECRET_ANSWER, rendered)
        self.assertNotIn(SECRET_RISK_HIGHLIGHT, rendered)

    def test_renders_with_empty_data(self):
        at = self._run({})
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(at.info), 1)  # "완료 세션이 없습니다" 안내

    def test_fetch_failure_shows_error(self):
        with patch("utils.db_handler.fetch_admin_rows", side_effect=RuntimeError("boom")):
            at = AppTest.from_file(PAGE, default_timeout=30)
            at.run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(at.error), 1)


if __name__ == "__main__":
    unittest.main()
