# utils/comparison/test_code_compare.py
import unittest
from utils.comparison.code_compare import calculate_autonomy_score

AI_CODE = """
def add(a, b):
    result = a + b
    return result
"""

# AI 코드와 완전히 동일 (그대로 베낌) — autonomy 최저
IDENTICAL_STUDENT_CODE = AI_CODE

# 로직은 같지만 변수명/함수명만 바꾼 코드 — 표면적 diff는 크지만 구조는 거의 동일
RENAMED_STUDENT_CODE = """
def sum_two(x, y):
    total = x + y
    return total
"""

# 완전히 다른 로직으로 다시 작성 — autonomy 최고
REWRITTEN_STUDENT_CODE = """
class Calculator:
    def __init__(self):
        self.history = []

    def multiply(self, values):
        product = 1
        for v in values:
            product *= v
        self.history.append(product)
        return product
"""

NON_PYTHON_AI_CODE = "function add(a, b) { return a + b; }"
NON_PYTHON_STUDENT_CODE = "function add(a, b) { const sum = a + b; return sum; }"


class TestCalculateAutonomyScore(unittest.TestCase):
    def test_identical_code_is_lowest_autonomy(self):
        self.assertEqual(calculate_autonomy_score(AI_CODE, IDENTICAL_STUDENT_CODE), 0)

    def test_completely_rewritten_code_is_high_autonomy(self):
        score = calculate_autonomy_score(AI_CODE, REWRITTEN_STUDENT_CODE)
        self.assertGreaterEqual(score, 80)

    def test_renamed_but_structurally_identical_code_scores_low(self):
        # 구조(ast_ratio)는 동일하지만 표면 텍스트(diff_ratio)와 식별자(identifier_overlap)가
        # 달라지므로, "완전히 다시 작성"한 경우보다는 낮은 autonomy가 나와야 한다.
        renamed_score = calculate_autonomy_score(AI_CODE, RENAMED_STUDENT_CODE)
        rewritten_score = calculate_autonomy_score(AI_CODE, REWRITTEN_STUDENT_CODE)
        self.assertLess(renamed_score, rewritten_score)

    def test_non_python_code_falls_back_to_diff_ratio_without_raising(self):
        # ast.parse()가 실패하는 코드(JS 등)여도 예외 없이 0~100 정수를 반환해야 한다.
        try:
            score = calculate_autonomy_score(NON_PYTHON_AI_CODE, NON_PYTHON_STUDENT_CODE)
        except Exception as e:  # noqa: BLE001 - 폴백 경로가 예외를 던지지 않는지가 테스트 목적
            self.fail(f"비-Python 코드 비교 시 예외가 발생하면 안 됩니다: {e}")
        self.assertIsInstance(score, int)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)

    def test_one_side_invalid_python_falls_back_to_diff_ratio(self):
        broken_code = "def broken(:\n    pass"
        try:
            score = calculate_autonomy_score(AI_CODE, broken_code)
        except Exception as e:  # noqa: BLE001
            self.fail(f"한쪽만 파싱 실패해도 예외가 발생하면 안 됩니다: {e}")
        self.assertIsInstance(score, int)

    def test_score_is_within_bounds(self):
        score = calculate_autonomy_score(AI_CODE, "")
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)


if __name__ == "__main__":
    unittest.main()
