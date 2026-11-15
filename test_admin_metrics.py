# test_admin_metrics.py
"""관리자 뷰 집계 로직(utils/admin_metrics.py) 단위 테스트. DB 호출 없음."""
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd

from utils.admin_metrics import (
    FUNNEL_STAGES,
    KST,
    UNKNOWN_PERSONA_LABEL,
    build_frames,
    build_session_summary,
    case_counts,
    first_quiz_per_session,
    format_kst,
    funnel_counts,
    health_score_histogram,
    mask_answers,
    overview,
    pearson_r,
    persona_distribution,
    recent_completed_table,
    scatter_data,
    short_id,
    step3_by_case,
    step3_overview,
    to_kst,
)

SECRET_ANSWER = "포인터는 메모리 주소를 담는 변수라서 직접 접근이 가능합니다"

CASES = [
    {"case_id": "case_x", "learning_type": "과제", "output_type": "B"},
    {"case_id": "case_y", "learning_type": "수강", "output_type": None},
    {"case_id": "case_z", "learning_type": "시험 대비", "output_type": None},
]


def _ts(hour: int, minute: int = 0) -> str:
    return f"2026-11-13T{hour:02d}:{minute:02d}:00.123456+00:00"


def _raw() -> dict:
    """세션 4개:
    s-complete-1: 1·2·3단계 완료, 3단계 2회 시도(첫 시도 오답, 둘째 정답)
    s-complete-2: 1·2·3단계 완료, 3단계 1회(정답), persona 없음
    s-stop-at-2 : 1·2단계까지만
    s-only-1    : 1단계까지만
    s-no-step2  : 1·3단계만(2단계 없음) — 비정상 경로, 완료로 세면 안 됨
    s-created   : 세션만 생성
    """
    sessions = [
        {"session_id": sid, "anon_id": anon, "case_id": case, "created_at": _ts(1)}
        for sid, anon, case in [
            ("s-complete-1", "anon-a", "case_x"),
            ("s-complete-2", "anon-a", "case_y"),
            ("s-stop-at-2", "anon-b", "case_x"),
            ("s-only-1", "anon-b", "case_x"),
            ("s-no-step2", "anon-c", "case_y"),
            ("s-created", "anon-c", "case_x"),
        ]
    ]
    step1 = [
        {"id": 1, "session_id": "s-complete-1", "case_id": "case_x", "total_score": 10, "persona": "효율 중심형", "created_at": _ts(2)},
        {"id": 2, "session_id": "s-complete-2", "case_id": "case_y", "total_score": 20, "persona": None, "created_at": _ts(2)},
        {"id": 3, "session_id": "s-stop-at-2", "case_id": "case_x", "total_score": 15, "persona": "방어형", "created_at": _ts(2)},
        {"id": 4, "session_id": "s-only-1", "case_id": "case_x", "total_score": 5, "persona": "맹목적 의존형", "created_at": _ts(2)},
        {"id": 5, "session_id": "s-no-step2", "case_id": "case_y", "total_score": 12, "persona": "방어형", "created_at": _ts(2)},
    ]
    step2 = [
        {"id": 1, "session_id": "s-complete-1", "case_id": "case_x", "health_score": "40.5", "created_at": _ts(3)},
        {"id": 2, "session_id": "s-complete-2", "case_id": "case_y", "health_score": 100, "created_at": _ts(3)},
        {"id": 3, "session_id": "s-stop-at-2", "case_id": "case_x", "health_score": 70, "created_at": _ts(3)},
    ]
    step3 = [
        # 같은 created_at이어도 id가 작은 쪽이 "첫 퀴즈"
        {"id": 11, "session_id": "s-complete-1", "case_id": "case_x", "quiz_type": "에러 로그 원인 작성",
         "student_answer": "두 번째 답변", "is_correct": True, "matched_keyword": "포인터", "created_at": _ts(15, 30)},
        {"id": 10, "session_id": "s-complete-1", "case_id": "case_x", "quiz_type": "함수 주석 작성",
         "student_answer": SECRET_ANSWER, "is_correct": False, "matched_keyword": None, "created_at": _ts(15, 30)},
        {"id": 12, "session_id": "s-complete-2", "case_id": "case_y", "quiz_type": "개념 자기설명 작성",
         "student_answer": "짧은 답", "is_correct": True, "matched_keyword": "회상", "created_at": _ts(16)},
        {"id": 13, "session_id": "s-no-step2", "case_id": "case_y", "quiz_type": "개념 자기설명 작성",
         "student_answer": "x", "is_correct": True, "matched_keyword": "x", "created_at": _ts(16)},
    ]
    return {
        "cases": CASES,
        "sessions": sessions,
        "step1_responses": step1,
        "step2_responses": step2,
        "step3_responses": step3,
    }


def _summary():
    frames = build_frames(_raw())
    return frames, build_session_summary(frames)


class TestKstConversion(unittest.TestCase):
    def test_utc_offset_string_crosses_midnight(self):
        result = to_kst(pd.Series(["2026-11-13T15:30:00+00:00"]))
        self.assertEqual(result.iloc[0], datetime(2026, 11, 14, 0, 30, tzinfo=KST))

    def test_z_suffix_and_microseconds(self):
        result = to_kst(pd.Series(["2026-11-13T00:00:00Z", "2026-11-13T00:00:00.654321+00:00"]))
        self.assertEqual(result.iloc[0].hour, 9)
        self.assertEqual(result.iloc[1].microsecond, 654321)

    def test_none_becomes_nat(self):
        result = to_kst(pd.Series([None, "2026-11-13T00:00:00+00:00"]))
        self.assertTrue(pd.isna(result.iloc[0]))
        self.assertEqual(format_kst(result.iloc[0]), "-")
        self.assertEqual(format_kst(result.iloc[1]), "2026-11-13 09:00 KST")

    def test_frames_created_at_is_kst(self):
        frames = build_frames(_raw())
        ts = frames["step3_responses"]["created_at"].iloc[0]
        self.assertEqual(ts.utcoffset().total_seconds(), 9 * 3600)


class TestMasking(unittest.TestCase):
    def test_answer_replaced_by_length(self):
        masked = mask_answers([{"id": 1, "student_answer": "  가나다  "}])
        self.assertNotIn("student_answer", masked[0])
        self.assertEqual(masked[0]["answer_length"], 3)

    def test_none_and_empty_answers(self):
        masked = mask_answers([{"student_answer": None}, {"student_answer": ""}, {}])
        self.assertEqual([m["answer_length"] for m in masked], [0, 0, 0])

    def test_input_rows_not_mutated(self):
        rows = [{"student_answer": SECRET_ANSWER}]
        mask_answers(rows)
        self.assertIn("student_answer", rows[0])

    def test_no_raw_answer_survives_build_frames(self):
        frames, summary = _summary()
        dumped = "".join(df.to_csv() for df in frames.values()) + summary.to_csv()
        dumped += recent_completed_table(summary).to_csv()
        self.assertNotIn(SECRET_ANSWER, dumped)
        self.assertNotIn("student_answer", frames["step3_responses"].columns)

    def test_short_id(self):
        self.assertEqual(short_id("12345678-abcd-efgh"), "12345678")
        self.assertEqual(short_id(None), "-")


class TestCompletedSessions(unittest.TestCase):
    def test_only_sessions_with_all_three_steps(self):
        _, summary = _summary()
        self.assertEqual(sorted(summary["session_id"]), ["s-complete-1", "s-complete-2"])

    def test_missing_persona_labeled(self):
        _, summary = _summary()
        row = summary.set_index("session_id").loc["s-complete-2"]
        self.assertEqual(row["persona"], UNKNOWN_PERSONA_LABEL)

    def test_health_score_string_coerced_to_number(self):
        _, summary = _summary()
        row = summary.set_index("session_id").loc["s-complete-1"]
        self.assertAlmostEqual(row["health_score"], 40.5)


class TestFirstQuiz(unittest.TestCase):
    def test_first_quiz_is_smallest_id_even_with_same_timestamp(self):
        frames = build_frames(_raw())
        first = first_quiz_per_session(frames["step3_responses"]).set_index("session_id")
        row = first.loc["s-complete-1"]
        self.assertEqual(row["first_quiz_type"], "함수 주석 작성")
        self.assertFalse(row["first_quiz_correct"])
        self.assertEqual(row["quiz_attempts"], 2)
        self.assertEqual(row["first_quiz_answer_length"], len(SECRET_ANSWER))

    def test_step3_overview(self):
        _, summary = _summary()
        result = step3_overview(summary)
        self.assertEqual(result["sessions"], 2)
        self.assertAlmostEqual(result["first_quiz_correct_rate"], 0.5)  # 오답 1, 정답 1
        self.assertAlmostEqual(result["avg_attempts"], 1.5)  # (2 + 1) / 2

    def test_step3_by_case(self):
        _, summary = _summary()
        by_case = step3_by_case(summary).set_index("case_id")
        self.assertAlmostEqual(by_case.loc["case_x", "first_quiz_correct_rate"], 0.0)
        self.assertAlmostEqual(by_case.loc["case_y", "first_quiz_correct_rate"], 1.0)


class TestCaseCounts(unittest.TestCase):
    def test_zero_response_case_included(self):
        frames, summary = _summary()
        counts = case_counts(frames["cases"], summary).set_index("case_id")
        self.assertEqual(counts.loc["case_x", "completed_sessions"], 1)
        self.assertEqual(counts.loc["case_y", "completed_sessions"], 1)
        self.assertEqual(counts.loc["case_z", "completed_sessions"], 0)

    def test_labels_come_from_cases_table(self):
        frames, summary = _summary()
        labels = case_counts(frames["cases"], summary).set_index("case_id")["label"]
        self.assertEqual(labels["case_x"], "case_x (과제·B)")
        self.assertEqual(labels["case_y"], "case_y (수강)")

    def test_unknown_case_id_still_counted(self):
        frames, summary = _summary()
        summary.loc[0, "case_id"] = "not_in_cases"
        counts = case_counts(frames["cases"], summary).set_index("case_id")
        self.assertEqual(counts.loc["not_in_cases", "completed_sessions"], 1)
        self.assertEqual(counts.loc["not_in_cases", "label"], "not_in_cases")


class TestDistributions(unittest.TestCase):
    def test_persona_distribution(self):
        _, summary = _summary()
        dist = persona_distribution(summary).set_index("persona")["sessions"]
        self.assertEqual(dist["효율 중심형"], 1)
        self.assertEqual(dist[UNKNOWN_PERSONA_LABEL], 1)
        self.assertNotIn("방어형", dist.index)  # 미완료 세션 페르소나는 제외

    def test_histogram_bins_and_boundaries(self):
        summary = pd.DataFrame({"health_score": [0, 9.99, 10, 55, 99.9, 100]})
        hist = health_score_histogram(summary).set_index("bin")["sessions"]
        self.assertEqual(len(hist), 10)
        self.assertEqual(list(hist.index[:2]), ["0–10", "10–20"])
        self.assertEqual(hist["0–10"], 2)
        self.assertEqual(hist["10–20"], 1)
        self.assertEqual(hist["50–60"], 1)
        self.assertEqual(hist["90–100"], 2)  # 100은 마지막 구간에 포함
        self.assertEqual(hist.sum(), 6)

    def test_histogram_empty(self):
        hist = health_score_histogram(pd.DataFrame({"health_score": []}))
        self.assertEqual(hist["sessions"].sum(), 0)
        self.assertEqual(len(hist), 10)


class TestScatter(unittest.TestCase):
    def test_only_completed_sessions(self):
        _, summary = _summary()
        points = scatter_data(summary)
        self.assertEqual(len(points), 2)
        self.assertEqual(set(points["session"]), {"s-comple"})  # 앞 8자만

    def test_pearson_r(self):
        points = pd.DataFrame({"total_score": [5, 10, 15], "health_score": [10, 20, 30]})
        self.assertAlmostEqual(pearson_r(points), 1.0)

    def test_pearson_r_undefined(self):
        self.assertIsNone(pearson_r(pd.DataFrame({"total_score": [5], "health_score": [10]})))
        flat = pd.DataFrame({"total_score": [5, 5], "health_score": [10, 20]})
        self.assertIsNone(pearson_r(flat))


class TestFunnel(unittest.TestCase):
    def test_counts_are_monotonic_and_skip_inconsistent_rows(self):
        frames = build_frames(_raw())
        funnel = funnel_counts(frames)
        self.assertEqual(list(funnel["stage"]), FUNNEL_STAGES)
        # 세션 6 → 1단계 5 → 2단계 3 → 3단계 2 (s-no-step2는 2단계를 건너뛰어 3단계에서 제외)
        self.assertEqual(list(funnel["sessions"]), [6, 5, 3, 2])
        self.assertAlmostEqual(funnel["conversion_from_prev"].iloc[3], 2 / 3)
        self.assertAlmostEqual(funnel["conversion_from_start"].iloc[3], 2 / 6)
        self.assertTrue(pd.isna(funnel["conversion_from_prev"].iloc[0]))

    def test_overview(self):
        frames, summary = _summary()
        result = overview(frames, summary)
        self.assertEqual(result["total_sessions"], 6)
        self.assertEqual(result["completed_sessions"], 2)
        self.assertEqual(result["unique_anon_ids"], 3)
        self.assertEqual(format_kst(result["last_response_at"]), "2026-11-14 01:00 KST")


class TestEmptyData(unittest.TestCase):
    def test_all_functions_handle_empty(self):
        frames = build_frames({})
        summary = build_session_summary(frames)
        self.assertTrue(summary.empty)
        self.assertEqual(list(funnel_counts(frames)["sessions"]), [0, 0, 0, 0])
        self.assertTrue(persona_distribution(summary).empty)
        self.assertTrue(scatter_data(summary).empty)
        self.assertIsNone(pearson_r(scatter_data(summary)))
        self.assertEqual(step3_overview(summary)["sessions"], 0)
        self.assertTrue(step3_by_case(summary).empty)
        self.assertTrue(recent_completed_table(summary).empty)
        self.assertTrue(case_counts(frames["cases"], summary).empty)
        self.assertIsNone(overview(frames, summary)["last_response_at"])


class TestRecentTable(unittest.TestCase):
    def test_sorted_newest_first_with_kst(self):
        _, summary = _summary()
        table = recent_completed_table(summary)
        self.assertEqual(list(table["완료 시각(KST)"]), ["2026-11-14 01:00 KST", "2026-11-14 00:30 KST"])
        self.assertEqual(list(table["첫 퀴즈 정답"]), ["O", "X"])
        self.assertEqual(list(table["매칭 키워드"]), ["회상", "-"])


class TestFetchAdminRowsPagination(unittest.TestCase):
    @patch("utils.db_handler.ADMIN_PAGE_SIZE", 2)
    @patch("utils.db_handler.get_client")
    def test_reads_until_short_page(self, mock_get_client):
        from utils.db_handler import fetch_admin_rows

        queries = {}
        pages = {}

        def table(name):
            # _fetch_all은 페이지마다 table()을 다시 호출하므로 테이블별 mock을 재사용한다
            if name not in queries:
                query = MagicMock()
                chain = query.select.return_value.order.return_value
                batches = [[{"n": 1}, {"n": 2}], [{"n": 3}]] if name == "step3_responses" else [[]]
                chain.range.return_value.execute.side_effect = [MagicMock(data=b) for b in batches]
                pages[name] = chain.range
                queries[name] = query
            return queries[name]

        mock_get_client.return_value.table.side_effect = table
        result = fetch_admin_rows()
        self.assertEqual([r["n"] for r in result["step3_responses"]], [1, 2, 3])
        self.assertEqual(pages["step3_responses"].call_args_list[1].args, (2, 3))
        self.assertEqual(result["cases"], [])

    def test_sensitive_step2_columns_not_selected(self):
        from utils.db_handler import ADMIN_SELECT_COLUMNS

        step2_columns = ADMIN_SELECT_COLUMNS["step2_responses"][0]
        self.assertNotIn("risk_highlight", step2_columns)
        self.assertNotIn("analysis_summary", step2_columns)


if __name__ == "__main__":
    unittest.main()
