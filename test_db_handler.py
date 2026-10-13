# test_db_handler.py
import unittest
from unittest.mock import MagicMock, patch

from postgrest.exceptions import APIError

from utils.db_handler import (
    DuplicateSubmissionError,
    save_step1_response,
    save_step2_response,
    save_step3_response,
)


def _unique_violation() -> APIError:
    return APIError({
        "code": "23505",
        "message": "duplicate key value violates unique constraint",
    })


def _other_db_error() -> APIError:
    return APIError({
        "code": "08006",
        "message": "connection failure",
    })


def _mock_client_raising(exc: Exception) -> MagicMock:
    client = MagicMock()
    client.table.return_value.insert.return_value.execute.side_effect = exc
    return client


class TestSaveStep1ResponseDuplicateHandling(unittest.TestCase):
    @patch("utils.db_handler.get_client")
    def test_unique_violation_raises_duplicate_submission_error(self, mock_get_client):
        mock_get_client.return_value = _mock_client_raising(_unique_violation())
        with self.assertRaises(DuplicateSubmissionError):
            save_step1_response(
                session_id="s1", case_id="assignment_A",
                q1=1, q2=1, q3=1, q4=1, q5=1,
                total_score=5, persona="자기 주도형",
            )

    @patch("utils.db_handler.get_client")
    def test_other_api_error_is_not_converted(self, mock_get_client):
        mock_get_client.return_value = _mock_client_raising(_other_db_error())
        with self.assertRaises(APIError) as ctx:
            save_step1_response(
                session_id="s1", case_id="assignment_A",
                q1=1, q2=1, q3=1, q4=1, q5=1,
                total_score=5, persona="자기 주도형",
            )
        self.assertNotIsInstance(ctx.exception, DuplicateSubmissionError)


class TestSaveStep2ResponseDuplicateHandling(unittest.TestCase):
    @patch("utils.db_handler.get_client")
    def test_unique_violation_raises_duplicate_submission_error(self, mock_get_client):
        mock_get_client.return_value = _mock_client_raising(_unique_violation())
        with self.assertRaises(DuplicateSubmissionError):
            save_step2_response(
                session_id="s1", case_id="assignment_A",
                health_score=80, components=None,
                risk_highlight="", analysis_summary="요약",
            )

    @patch("utils.db_handler.get_client")
    def test_other_api_error_is_not_converted(self, mock_get_client):
        mock_get_client.return_value = _mock_client_raising(_other_db_error())
        with self.assertRaises(APIError) as ctx:
            save_step2_response(
                session_id="s1", case_id="assignment_A",
                health_score=80, components=None,
                risk_highlight="", analysis_summary="요약",
            )
        self.assertNotIsInstance(ctx.exception, DuplicateSubmissionError)


class TestSaveStep3ResponseHasNoDuplicateHandling(unittest.TestCase):
    # step3_responses는 세션당 여러 row(퀴즈별 제출)를 허용하므로 유니크 제약이 없고,
    # 따라서 save_step3_response는 APIError를 DuplicateSubmissionError로 변환하지 않는다.
    @patch("utils.db_handler.get_client")
    def test_unique_violation_like_error_passes_through_unconverted(self, mock_get_client):
        mock_get_client.return_value = _mock_client_raising(_unique_violation())
        with self.assertRaises(APIError) as ctx:
            save_step3_response(
                session_id="s1", case_id="assignment_A",
                quiz_type="개념설명", dynamic_question="질문",
                student_answer="답", is_correct=True, matched_keyword="포인터",
            )
        self.assertNotIsInstance(ctx.exception, DuplicateSubmissionError)


if __name__ == "__main__":
    unittest.main()
