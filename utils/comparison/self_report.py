# utils/comparison/self_report.py
"""D(디자인)/수강/시험대비 케이스의 자기보고 방식 자립도(autonomy) 점수 산출.

산출물을 AI 결과와 직접 비교할 수 없는 케이스(docs/07 Phase 6a 표 참조)를 위한
대리 지표: "AI가 만든 결과물을 어떻게 처리했는가" 3지선다 + 수정요청 프롬프트 횟수.
"""

# 3지선다 기본 점수 (docs/10 3-a 항목: 그대로 채택=낮은 점수, 전면 재작업=높은 점수)
ADOPTION_BASE_SCORES = {
    "그대로 채택": 20,
    "일부 수정": 50,
    "전면 재작업": 80,
}

REVISION_BONUS_PER_REQUEST = 5  # 수정요청 1회당 가점
REVISION_BONUS_CAP = 20  # 가점 상한 (4회 이상부터 상한 도달)


def calculate_autonomy_score(adoption_choice: str, revision_count: int) -> int:
    """3지선다 응답과 수정요청 횟수를 0~100 자립도(autonomy) 점수로 변환합니다."""
    if adoption_choice not in ADOPTION_BASE_SCORES:
        raise ValueError(f"알 수 없는 adoption_choice 값입니다: {adoption_choice!r}")

    base = ADOPTION_BASE_SCORES[adoption_choice]
    bonus = min(revision_count * REVISION_BONUS_PER_REQUEST, REVISION_BONUS_CAP)
    return max(0, min(100, base + bonus))
