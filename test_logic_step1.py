# test_logic_step1.py
import unittest
from utils.logic_step1 import calculate_persona

# 실제 시딩 데이터(scripts/seed_cases.py) 기준 핫스팟 파라미터만 발췌한 fixture.
# assignment_B: 최고위험 1개(Q4) + 위험 1개(Q2) 조합 — 등급별 차등 임계값이 실제로
# 갈리는 케이스.
CASE_B = {
    "hotspot_primary": 4,
    "hotspot_secondary": 2,
    "hotspot_tier": {"primary": "최고위험", "secondary": "위험"},
}

# assignment_C: 최고위험 2개(Q2, Q4) 조합 — 두 핫스팟 모두 threshold=2로 기존(1학기)
# CS 로직과 동일하게 동작해야 하는 케이스.
CASE_C = {
    "hotspot_primary": 2,
    "hotspot_secondary": 4,
    "hotspot_tier": {"primary": "최고위험", "secondary": "최고위험"},
}


class TestLogicStep1(unittest.TestCase):
    def test_blindly_dependent_low_score(self):
        # 1. 맹목적 의존형: 총점 <= 11 (핫스팟 히트와 무관하게 항상 성립)
        result = calculate_persona(CASE_B, 2, 2, 2, 2, 2)  # 총점 10
        self.assertEqual(result["persona"], "맹목적 의존형")
        self.assertEqual(result["total_score"], 10)

    def test_blindly_dependent_hotspot_mixed_tier(self):
        # 2. 맹목적 의존형: 최고위험(Q4<=2) AND 위험(Q2<=1) 모두 히트 (총점 18로 높아도 과락)
        result = calculate_persona(CASE_B, 5, 1, 5, 2, 5)  # 총점 18
        self.assertEqual(result["persona"], "맹목적 의존형")

    def test_blindly_dependent_hotspot_uniform_tier(self):
        # 2-1. 최고위험 2개 조합(assignment_C형)에서는 기존과 동일하게 두 문항 모두
        #      threshold=2 기준으로 과락 판정된다 (docs/07: "C·D는 기존과 동일 동작")
        result = calculate_persona(CASE_C, 5, 2, 5, 2, 5)  # 총점 19, Q2=Q4=2
        self.assertEqual(result["persona"], "맹목적 의존형")

    def test_efficiency_oriented_secondary_hit_only(self):
        # 3. 효율 중심형: 위험 등급 보조 핫스팟(Q2<=1)만 히트, 최고위험(Q4)은 미달
        result = calculate_persona(CASE_B, 5, 1, 5, 5, 5)  # 총점 21
        self.assertEqual(result["persona"], "효율 중심형")

    def test_efficiency_oriented_primary_hit_only(self):
        # 4. 효율 중심형: 최고위험 주 핫스팟(Q4<=2)만 히트, 위험 등급(Q2)은 미달
        result = calculate_persona(CASE_B, 5, 3, 5, 2, 5)  # 총점 20
        self.assertEqual(result["persona"], "효율 중심형")

    def test_defensive(self):
        # 5. 방어형: 총점 <= 21 AND Q5 <= 3 (핫스팟 미히트)
        result = calculate_persona(CASE_B, 4, 4, 4, 4, 3)  # 총점 19, Q5=3
        self.assertEqual(result["persona"], "방어형")

    def test_self_directed_high(self):
        # 6. 자기 주도형: 모든 기준 만족
        result = calculate_persona(CASE_B, 5, 5, 5, 5, 5)  # 총점 25
        self.assertEqual(result["persona"], "자기 주도형")

    def test_self_directed_moderate(self):
        result = calculate_persona(CASE_B, 4, 4, 4, 4, 4)  # 총점 20, Q5=4 (>3)
        self.assertEqual(result["persona"], "자기 주도형")


if __name__ == "__main__":
    unittest.main()
