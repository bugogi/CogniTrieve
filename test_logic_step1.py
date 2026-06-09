# test_logic_step1.py
import unittest
from utils.logic_step1 import calculate_persona

class TestLogicStep1(unittest.TestCase):
    def test_blindly_dependent_low_score(self):
        # 1. 맹목적 의존형: 총점 <= 11
        result = calculate_persona(2, 2, 2, 2, 2)  # 총점 10
        self.assertEqual(result["persona"], "맹목적 의존형")
        self.assertEqual(result["total_score"], 10)

    def test_blindly_dependent_hotspot(self):
        # 2. 맹목적 의존형: Q2 <= 2 AND Q4 <= 2 (총점이 높아도 과락 로직 작동)
        result = calculate_persona(5, 2, 5, 2, 5)  # 총점 19
        self.assertEqual(result["persona"], "맹목적 의존형")

    def test_efficiency_oriented_q2_low(self):
        # 3. 효율 중심형: Q2 <= 2 OR Q4 <= 2 중 하나만 해당 (그리고 맹목적 의존형 요건 미충족)
        result = calculate_persona(5, 2, 5, 5, 5)  # 총점 22
        self.assertEqual(result["persona"], "효율 중심형")

    def test_efficiency_oriented_q4_low(self):
        result = calculate_persona(5, 5, 5, 2, 5)  # 총점 22
        self.assertEqual(result["persona"], "효율 중심형")

    def test_defensive(self):
        # 4. 방어형: 총점 <= 21 AND Q5 <= 3 (효율 중심 및 의존형 요건 미충족)
        result = calculate_persona(4, 4, 4, 4, 3)  # 총점 19, Q5=3, Q2/Q4=4
        self.assertEqual(result["persona"], "방어형")

    def test_self_directed_high(self):
        # 5. 자기 주도형: 모든 기준 만족
        result = calculate_persona(5, 5, 5, 5, 5)  # 총점 25
        self.assertEqual(result["persona"], "자기 주도형")

    def test_self_directed_moderate(self):
        result = calculate_persona(4, 4, 4, 4, 4)  # 총점 20, Q5=4 (>3), Q2/Q4=4 (>2)
        self.assertEqual(result["persona"], "자기 주도형")

if __name__ == "__main__":
    unittest.main()
