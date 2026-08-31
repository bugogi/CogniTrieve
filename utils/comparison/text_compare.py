# utils/comparison/text_compare.py
"""A(텍스트) 케이스의 임베딩 유사도 + 문장 재구성 비율 방식 자립도(autonomy) 점수 산출.

AI 초안과 학생 최종 제출문을 비교해, 얼마나 다시 썼는지를 자립도의 대리 지표로
삼는다(docs/07 2단계 절 "유형별 결과물 비교 방식" A행 참조).
유사도가 높을수록(거의 그대로 채택) autonomy는 낮고, 유사도가 낮을수록(스스로 많이
고침) autonomy는 높다 — self_report.py/code_compare.py와 같은 방향.

임베딩 API(embed_text) 호출이 실패하면(네트워크/인증/할당량 등) 폴백 없이 예외를
그대로 전파한다 — code_compare.py의 "AST 파싱 실패 시 조용히 폴백"과 달리, 임베딩
실패는 정상적으로 발생할 수 있는 상황(예: 비-Python 코드)이 아니라 인프라성 오류이기
때문이다.
"""
import difflib
import math
import re

from utils.llm_handler import embed_text

# 문장 단위 difflib 유사도가 이 값 이상이면 "AI 문장이 학생 제출문에 거의 그대로
# 남아있다"고 판정한다. docs/07의 "유사도 90% 초과 시 미수정 채택으로 판정"이라는
# 참고 기준을 전체 텍스트 코사인 유사도가 아니라 문장 단위 difflib 유사도에
# 재해석해 적용한 것이다.
VERBATIM_SENTENCE_THRESHOLD = 0.9

# 두 지표(임베딩 코사인 유사도 / 문장 재구성 비율) 균등 가중 — HEALTH_SCORE_WEIGHTS,
# code_compare.py와 동일한 "근거 없는 가중치보다 균등 가중이 정직하다" 원칙 적용
_SIMILARITY_WEIGHTS = (0.5, 0.5)

_SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+")


def _split_sentences(text: str) -> list[str]:
    """마침표/물음표/느낌표 기준으로 문장을 분리합니다.

    한국어는 구어체·비격식 글에서 마침표를 일관되게 쓰지 않는 경우가 많아, 이
    정규식 기반 분리는 문장 경계를 완벽히 잡지 못할 수 있다(과분할/과소분할
    가능성) — 파일럿 수준에서 허용 가능한 한계로 남겨둔다.
    """
    return [s.strip() for s in _SENTENCE_SPLIT_PATTERN.split(text.strip()) if s.strip()]


def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _verbatim_survival_ratio(ai_sentences: list[str], student_sentences: list[str]) -> float | None:
    """AI 초안 문장 중 학생 제출문에 거의 그대로(문장 단위 유사도 >= 임계값) 남은 비율.

    ai_sentences가 비어 있으면(문장 분리 실패 등) 계산 불가이므로 None을 반환한다 —
    이 경우 호출부는 embedding_similarity만으로 점수를 산출한다.
    """
    if not ai_sentences:
        return None
    if not student_sentences:
        return 0.0

    verbatim_count = 0
    for ai_sentence in ai_sentences:
        best_ratio = max(
            difflib.SequenceMatcher(None, ai_sentence, student_sentence).ratio()
            for student_sentence in student_sentences
        )
        if best_ratio >= VERBATIM_SENTENCE_THRESHOLD:
            verbatim_count += 1

    return verbatim_count / len(ai_sentences)


def calculate_autonomy_score(ai_text: str, student_text: str) -> int:
    """AI 초안과 학생 최종 제출문을 비교해 0~100 자립도(autonomy) 점수로 변환합니다."""
    vec_ai = embed_text(ai_text)
    vec_student = embed_text(student_text)
    embedding_similarity = max(0.0, min(1.0, _cosine_similarity(vec_ai, vec_student)))

    ai_sentences = _split_sentences(ai_text)
    student_sentences = _split_sentences(student_text)
    verbatim_survival_ratio = _verbatim_survival_ratio(ai_sentences, student_sentences)

    if verbatim_survival_ratio is None:
        combined_similarity = embedding_similarity
    else:
        combined_similarity = (
            _SIMILARITY_WEIGHTS[0] * embedding_similarity
            + _SIMILARITY_WEIGHTS[1] * verbatim_survival_ratio
        )

    autonomy = round((1 - combined_similarity) * 100)
    return max(0, min(100, autonomy))
