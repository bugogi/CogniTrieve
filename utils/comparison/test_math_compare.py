# utils/comparison/test_math_compare.py
import unittest
from utils.comparison.math_compare import (
    MathParsingError,
    _is_equivalent,
    _parse_equation,
    calculate_autonomy_score,
)

AI_SOLUTION = "F = m*a\na = (v - v0)/t\nF = m*(v - v0)/t"
STUDENT_SOLUTION_SAME_STEPS = "F = m*a\na = (v - v0)/t\nF = m*(v - v0)/t"
STUDENT_SOLUTION_MORE_STEPS = "뉴턴 제2법칙: F = m*a\n가속도 정의: a = (v - v0)/t\n대입하면: F = m*(v-v0)/t\n정리 완료"

# 아래 두 fixture는 "복사 여부"가 아니라 "단계 수"만 다르도록, 둘 다 AI 풀이와
# 다른 말로(패러프레이즈해) 작성했다 — 검증 대상은 STUDENT_SOLUTION_SAME_STEPS
# 처럼 완전 복사가 아닌, 순수 단계 수 차이의 영향이다.
STUDENT_SOLUTION_GENUINE_SAME_STEPS = (
    "뉴턴 제2법칙을 적용: F = m*a\n가속도의 정의를 대입: a = (v - v0)/t\n최종 정리: F = m*(v-v0)/t"
)
STUDENT_SOLUTION_GENUINE_FEWER_STEPS = "정리하면 F = m*(v-v0)/t"


class TestCalculateAutonomyScore(unittest.TestCase):
    def test_verbatim_copy_is_zero_autonomy(self):
        # 줄 수·내용·최종 수식이 AI 풀이와 완전히 동일(그대로 복사) — content_difference
        # 보정이 없으면 줄 수 비율만으로 70점이 나오는 루프홀이 있었음(구현 중 발견,
        # docs/10 3-d 노트 참조). 보정 후에는 0점이어야 한다.
        score = calculate_autonomy_score(
            "F = m*a", "F = m*a", AI_SOLUTION, STUDENT_SOLUTION_SAME_STEPS
        )
        self.assertEqual(score, 0)

    def test_non_equivalent_formula_and_more_steps_is_high_autonomy(self):
        score = calculate_autonomy_score(
            "F = m*a", "a = F/m", AI_SOLUTION, STUDENT_SOLUTION_MORE_STEPS
        )
        self.assertGreaterEqual(score, 90)

    def test_fewer_steps_than_ai_lowers_autonomy(self):
        # 복사 여부(내용 차이)는 동일하게 통제(둘 다 패러프레이즈, 복사 아님)하고
        # 단계 수만 다르게 해서, 단계 수 비율 자체의 영향만 분리해 검증한다.
        score_same_steps = calculate_autonomy_score(
            "F = m*a", "F = m*a", AI_SOLUTION, STUDENT_SOLUTION_GENUINE_SAME_STEPS
        )
        score_fewer_steps = calculate_autonomy_score(
            "F = m*a", "F = m*a", AI_SOLUTION, STUDENT_SOLUTION_GENUINE_FEWER_STEPS
        )
        self.assertLess(score_fewer_steps, score_same_steps)

    def test_subscript_variable_v0_is_not_misparsed_as_v_times_zero(self):
        # 암시적 곱셈이 켜져 있으면 "v0"가 "v*0"(=0)으로 오인되어, "y=v0"과 "y=0"이
        # 잘못 동치로 판정된다(구현 전 실측으로 확인한 버그). 암시적 곱셈을 끈
        # 현재 설정에서는 v0가 독립된 심볼로 유지되어 두 식이 동치가 아니어야 한다.
        diff_v0 = _parse_equation("y = v0")
        diff_zero = _parse_equation("y = 0")
        self.assertFalse(_is_equivalent(diff_v0, diff_zero))

    def test_korean_in_final_formula_raises_math_parsing_error(self):
        with self.assertRaises(MathParsingError):
            calculate_autonomy_score(
                "F = m*a", "뉴턴 제2법칙에 의해 F=ma이다", AI_SOLUTION, STUDENT_SOLUTION_SAME_STEPS
            )

    def test_implicit_multiplication_is_not_supported_and_raises(self):
        # "2as"처럼 곱셈 기호 없이 붙여 쓰면 파싱 실패해야 한다(암시적 곱셈 비활성화).
        with self.assertRaises(MathParsingError):
            calculate_autonomy_score(
                "v^2 = v0^2 + 2as", "v^2 = v0^2 + 2*a*s", AI_SOLUTION, STUDENT_SOLUTION_SAME_STEPS
            )

    def test_missing_equals_sign_raises(self):
        with self.assertRaises(MathParsingError):
            calculate_autonomy_score("F = m*a", "m*a", AI_SOLUTION, STUDENT_SOLUTION_SAME_STEPS)

    def test_empty_ai_solution_does_not_raise_zero_division(self):
        score = calculate_autonomy_score("F = m*a", "F = m*a", "", "F = m*a\na = (v-v0)/t")
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)


if __name__ == "__main__":
    unittest.main()
