# utils/comparison/code_compare.py
"""B(코드) 케이스의 diff/AST 비교 방식 자립도(autonomy) 점수 산출.

AI가 제시한 코드와 학생 최종 코드를 비교해, 얼마나 다시 작성했는지를 자립도의
대리 지표로 삼는다(docs/07 2단계 절 "유형별 결과물 비교 방식" B행 참조).
유사도가 높을수록(거의 그대로 베낌) autonomy는 낮고, 유사도가 낮을수록(스스로 많이
고침) autonomy는 높다 — utils/comparison/self_report.py와 같은 방향.

AST 비교는 Python 코드에 대해서만 가능한 best-effort 보조 지표다. 두 코드 중
하나라도 ast.parse()에 실패하면(비-Python 코드이거나 문법이 깨졌으면) 예외를
던지지 않고 language-agnostic한 difflib 기반 비교로만 조용히 폴백한다.
"""
import ast
import difflib


def _line_diff_ratio(ai_code: str, student_code: str) -> float:
    """라인 단위 원문 유사도 (git diff와 같은 단위, 언어 무관). 0~1."""
    return difflib.SequenceMatcher(
        None, ai_code.splitlines(), student_code.splitlines()
    ).ratio()


def _ast_structure_ratio(ai_tree: ast.AST, student_tree: ast.AST) -> float:
    """AST 구조 유사도 — 공백·주석·포맷 차이엔 둔감하고 실제 로직 변화엔 민감. 0~1."""
    return difflib.SequenceMatcher(
        None,
        ast.dump(ai_tree, annotate_fields=False),
        ast.dump(student_tree, annotate_fields=False),
    ).ratio()


def _defined_identifiers(tree: ast.AST) -> set[str]:
    """함수명/클래스명/함수 인자/대입 대상 변수명(정의된 식별자)만 수집."""
    identifiers: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            identifiers.add(node.name)
        elif isinstance(node, ast.arg):
            identifiers.add(node.arg)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            identifiers.add(node.id)
    return identifiers


def _identifier_overlap_ratio(ai_tree: ast.AST, student_tree: ast.AST) -> float:
    """함수·변수명 일치율 (Jaccard 유사도). 두 코드 모두 식별자가 없으면 1.0(비교 불능은 '동일'로 취급)."""
    ai_ids = _defined_identifiers(ai_tree)
    student_ids = _defined_identifiers(student_tree)
    union = ai_ids | student_ids
    if not union:
        return 1.0
    return len(ai_ids & student_ids) / len(union)


def calculate_autonomy_score(ai_code: str, student_code: str) -> int:
    """AI 제시 코드와 학생 최종 코드를 비교해 0~100 자립도(autonomy) 점수로 변환합니다."""
    diff_ratio = _line_diff_ratio(ai_code, student_code)

    try:
        ai_tree = ast.parse(ai_code)
        student_tree = ast.parse(student_code)
    except SyntaxError:
        combined_similarity = diff_ratio
    else:
        ast_ratio = _ast_structure_ratio(ai_tree, student_tree)
        identifier_overlap = _identifier_overlap_ratio(ai_tree, student_tree)
        combined_similarity = (diff_ratio + ast_ratio + identifier_overlap) / 3

    autonomy = round((1 - combined_similarity) * 100)
    return max(0, min(100, autonomy))
