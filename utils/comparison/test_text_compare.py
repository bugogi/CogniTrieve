# utils/comparison/test_text_compare.py
import unittest
from unittest.mock import patch
from utils.comparison.text_compare import calculate_autonomy_score

AI_TEXT = "이것은 첫 번째 문장입니다. 이것은 두 번째 문장입니다. 이것은 세 번째 문장입니다."


def _unit_vector(*values: float) -> list[float]:
    """테스트용 저차원 임베딩 벡터 (embed_text를 mock하므로 3072차원일 필요 없음)."""
    return list(values)


class TestCalculateAutonomyScore(unittest.TestCase):
    @patch('utils.comparison.text_compare.embed_text')
    def test_identical_text_is_lowest_autonomy(self, mock_embed):
        # 코사인 유사도 1.0(동일 벡터) + 모든 문장이 그대로 남음(verbatim_survival_ratio=1.0)
        mock_embed.return_value = _unit_vector(1.0, 0.0, 0.0)

        score = calculate_autonomy_score(AI_TEXT, AI_TEXT)
        self.assertEqual(score, 0)

    @patch('utils.comparison.text_compare.embed_text')
    def test_completely_different_text_is_high_autonomy(self, mock_embed):
        # 서로 다른 벡터(코사인 유사도 0) + 문장도 전혀 겹치지 않음
        mock_embed.side_effect = [
            _unit_vector(1.0, 0.0, 0.0),
            _unit_vector(0.0, 1.0, 0.0),
        ]
        student_text = "전혀 다른 내용의 완전히 새로운 글을 스스로 작성했습니다."

        score = calculate_autonomy_score(AI_TEXT, student_text)
        self.assertGreaterEqual(score, 90)

    @patch('utils.comparison.text_compare.embed_text')
    def test_verbatim_sentence_threshold_counts_near_identical_sentences(self, mock_embed):
        # 두 벡터의 코사인 유사도가 0도 1도 아닌 중간값이 되도록 서로 다른 벡터를 사용
        mock_embed.side_effect = [_unit_vector(1.0, 0.0), _unit_vector(1.0, 1.0)]
        ai_text = "나는 사과를 먹었다. 나는 학교에 갔다."
        # 첫 문장은 거의 그대로(유사도 0.9 이상), 두 번째 문장은 완전히 다시 씀
        student_text = "나는 사과를 먹었다. 오늘 오후에는 도서관에서 새로운 책을 읽으며 시간을 보냈다."

        score = calculate_autonomy_score(ai_text, student_text)
        # 문장 2개 중 1개만 살아남았으므로 verbatim_survival_ratio=0.5, 완전 표절(0점)도
        # 완전 재작성(100점)도 아닌 중간 영역이어야 한다.
        self.assertGreater(score, 0)
        self.assertLess(score, 100)

    @patch('utils.comparison.text_compare.embed_text')
    def test_embedding_failure_propagates_without_fallback(self, mock_embed):
        mock_embed.side_effect = RuntimeError("Gemini Embedding API 호출 중 오류 발생: 네트워크 오류")

        with self.assertRaises(RuntimeError):
            calculate_autonomy_score(AI_TEXT, "학생 제출문")

    @patch('utils.comparison.text_compare.embed_text')
    def test_score_is_within_bounds(self, mock_embed):
        mock_embed.return_value = _unit_vector(0.3, 0.4, 0.5)
        score = calculate_autonomy_score(AI_TEXT, "")
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)


if __name__ == "__main__":
    unittest.main()
