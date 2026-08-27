# utils/comparison/test_self_report.py
import unittest
from utils.comparison.self_report import calculate_autonomy_score


class TestCalculateAutonomyScore(unittest.TestCase):
    def test_adopt_as_is_no_revisions_is_lowest(self):
        self.assertEqual(calculate_autonomy_score("그대로 채택", 0), 20)

    def test_partial_revision_baseline(self):
        self.assertEqual(calculate_autonomy_score("일부 수정", 0), 50)

    def test_full_rework_baseline(self):
        self.assertEqual(calculate_autonomy_score("전면 재작업", 0), 80)

    def test_revision_bonus_scales_linearly_below_cap(self):
        self.assertEqual(calculate_autonomy_score("그대로 채택", 2), 30)  # 20 + 2*5

    def test_revision_bonus_caps_at_20(self):
        self.assertEqual(calculate_autonomy_score("전면 재작업", 4), 100)  # 80 + min(20, 20)
        self.assertEqual(calculate_autonomy_score("전면 재작업", 10), 100)  # bonus still capped

    def test_invalid_adoption_choice_raises(self):
        with self.assertRaises(ValueError):
            calculate_autonomy_score("알 수 없음", 0)


if __name__ == "__main__":
    unittest.main()
