# utils/comparison/math_compare.py
"""C(물리) 케이스의 수식 구조 비교 방식 자립도(autonomy) 점수 산출.

docs/07 2단계 절 "유형별 결과물 비교 방식" C행: "수식 자체보다 전개 과정 생략
여부가 핵심"이라는 강조를 반영해, 두 지표를 다른 비중으로 배합한다.
- 전개 단계 수 비율 × 내용 차이(파싱 불필요, 항상 계산): 비중 0.7 — 줄 수 비율만
  쓰면 AI 풀이를 그대로 복사해도(줄 수가 같으므로) 만점에 가까운 점수를 받는
  허점이 있어, code_compare.py와 동일한 라인 단위 difflib 유사도로 "내용이 AI와
  얼마나 다른가"를 곱해 보정한다.
- 최종 수식 동치 판정(sympy, best-effort, 짧은 한 줄만 대상): 비중 0.3

물리 문제는 대개 정답이 하나뿐이라, AI 풀이와 학생 풀이가 독립적으로 진행돼도
최종 수식이 동치로 나오는 게 정상일 수 있다. 즉 동치 판정은 다른 유형(텍스트/
코드)만큼 "표절 여부"를 강하게 시사하지 않는 약한 신호이며, 그래서 가중치를
30%로 낮게(전개 과정 70%보다 작게) 설계했다(docs/10 3-d 노트 참조).

최종 수식이 sympy로 파싱되지 않으면(한글/자연어 혼입, 문법 오류 등)
MathParsingError를 던진다 — 호출부(logic_step2.py)는 이걸 잡아
utils/comparison/self_report.py로 폴백해야 한다. "전체 풀이 과정"(자유 서술) 텍스트는
파싱 대상이 아니라 줄 수만 세므로 이 예외와 무관하다.
"""
import difflib
import re

import sympy
from sympy.parsing.sympy_parser import convert_xor, parse_expr, standard_transformations

# 암시적 곱셈(예: "v0"를 "v*0"으로 오인)을 켜면 첨자 변수명이 조용히 파괴되고
# 한글이 섞인 문장도 예외 없이 "성공"으로 잘못 파싱됨을 실측으로 확인했다
# (docs/10 3-d 노트 참조). 곱셈은 반드시 "*"를 명시하도록 강제한다(UI 안내 필요).
_TRANSFORMATIONS = standard_transformations + (convert_xor,)

# 파싱 전 사전 가드: 이 화이트리스트를 벗어나는 문자(한글, 그리스 문자 등)가
# 하나라도 섞여 있으면 sympy를 호출하지 않고 즉시 파싱 실패로 처리한다.
_ALLOWED_CHARS_PATTERN = re.compile(r"^[A-Za-z0-9\s+\-*/^().,_=]+$")

# (전개 단계 수 비율, 동치 판정) — docs/07 "전개 과정 생략 여부가 핵심"을 반영해
# 전개 단계 수 비율에 더 큰 비중을 둔다.
WEIGHTS = (0.7, 0.3)


class MathParsingError(Exception):
    """최종 수식을 sympy로 파싱할 수 없을 때(한글/자연어 혼입, 문법 오류 등)."""


def _parse_equation(formula: str) -> sympy.Expr:
    """"lhs = rhs" 형태의 한 줄을 lhs-rhs 차 형태의 sympy 식으로 변환합니다."""
    formula = formula.strip()
    if not formula or not _ALLOWED_CHARS_PATTERN.match(formula):
        raise MathParsingError(f"허용되지 않은 문자가 포함되어 있습니다: {formula!r}")
    if "=" not in formula:
        raise MathParsingError(f"'=' 기호가 없어 방정식으로 인식할 수 없습니다: {formula!r}")

    lhs_str, _, rhs_str = formula.partition("=")
    try:
        lhs = parse_expr(lhs_str, transformations=_TRANSFORMATIONS)
        rhs = parse_expr(rhs_str, transformations=_TRANSFORMATIONS)
    except (SyntaxError, TypeError, ValueError) as e:
        raise MathParsingError(f"수식 파싱에 실패했습니다: {formula!r} ({e})") from e

    return lhs - rhs


def _is_equivalent(ai_diff: sympy.Expr, student_diff: sympy.Expr) -> bool:
    """두 방정식이 (재배열 없이) 완전히 같은 관계인지 엄격하게 판정합니다."""
    return sympy.simplify(ai_diff - student_diff) == 0


def _count_steps(solution_text: str) -> int:
    """비어있지 않은 줄 수를 '전개 단계 수'의 대리 지표로 사용합니다(파싱 불필요)."""
    return len([line for line in solution_text.splitlines() if line.strip()])


def _line_similarity(ai_solution_text: str, student_solution_text: str) -> float:
    """줄 단위 원문 유사도 (code_compare.py의 라인 단위 difflib 비교와 동일한 방식). 0~1."""
    return difflib.SequenceMatcher(
        None, ai_solution_text.splitlines(), student_solution_text.splitlines()
    ).ratio()


def calculate_autonomy_score(
    ai_final_formula: str,
    student_final_formula: str,
    ai_solution_text: str,
    student_solution_text: str,
) -> int:
    """
    최종 수식 동치 판정(sympy, best-effort)과 전개 단계 수 비율×내용 차이(파싱
    불필요)를 0.3/0.7로 배합해 0~100 자립도(autonomy) 점수로 변환합니다.

    ai_final_formula/student_final_formula 중 하나라도 파싱에 실패하면
    MathParsingError를 던집니다 — 호출부는 이 경우 self_report.py로 폴백해야 합니다.
    """
    ai_diff = _parse_equation(ai_final_formula)
    student_diff = _parse_equation(student_final_formula)
    equivalent = _is_equivalent(ai_diff, student_diff)
    equivalence_score = 0 if equivalent else 100

    ai_steps = _count_steps(ai_solution_text)
    student_steps = _count_steps(student_solution_text)
    step_count_ratio = min(student_steps / max(ai_steps, 1), 1.0)

    # 줄 수만 세면 AI 풀이를 그대로 복사·붙여넣기해도(줄 수가 같으므로) 만점에
    # 가까운 점수를 받는 허점이 있어, 내용이 AI와 얼마나 다른지(1 - 라인 유사도)를
    # 곱해 보정한다. code_compare.py와 동일한 라인 단위 difflib 방식 재사용.
    content_difference = 1 - _line_similarity(ai_solution_text, student_solution_text)
    thoroughness_score = step_count_ratio * content_difference * 100

    combined_autonomy = WEIGHTS[0] * thoroughness_score + WEIGHTS[1] * equivalence_score
    return max(0, min(100, round(combined_autonomy)))
