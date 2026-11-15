# utils/result_report.py
"""결과 리포트 화면(pages/4_결과리포트.py)에 표시할 데이터 구성.

설계: docs/07 3단계 "결과 리포트 화면". 세션 상태만 사용하며(DB 조회·저장 없음),
1·2단계 결과와 3단계 제출 이력을 한 화면용 dict로 정리한다. 교차검증은 판정 없이
"나란히 보여주기 + 해석 안내" 방식이라, 여기에는 일치/불일치 판정 로직을 두지 않는다.
"""
from collections.abc import Mapping

from utils.logic_step3 import STEP3_DONE_CORRECT, STEP3_DONE_FINISHED

# Health Score 세부 구성요소 표시 순서와 라벨(docs/07 "공통 산출 스키마 (Health Score)")
COMPONENT_LABELS = {
    "prompt_soundness": "프롬프트 건전성",
    "autonomy": "자립도",
    "risk_deduction": "위험구간 감점",
}

DONE_REASON_LABELS = {
    STEP3_DONE_CORRECT: "정답으로 통과",
    STEP3_DONE_FINISHED: "직접 마무리",
}

# 1단계: 5문항 × 리커트 1~5점(docs/07 1단계)
STEP1_QUESTION_COUNT = 5
STEP1_MAX_PER_QUESTION = 5

CROSS_CHECK_GUIDE = (
    "1단계 자가진단은 **내가 스스로 생각하는** AI 활용 습관을, 2단계 로그 분석은 **실제 AI와 "
    "나눈 대화에서 드러난** 행동을 보여줍니다. 두 결과가 비슷한 방향이라면 자신의 습관을 잘 "
    "파악하고 있다는 뜻이고, 서로 다르게 느껴진다면 그 차이가 이번 진단의 성찰 포인트입니다. "
    "예를 들어 스스로는 주도적으로 AI를 쓴다고 답했는데 로그 분석 결과가 기대와 달랐다면, "
    "대화 중 어느 순간에 판단을 AI에게 넘겼는지 다시 살펴보세요."
)

CROSS_CHECK_NOTE = (
    "이 비교는 판정이 아니라 스스로 돌아보기 위한 참고 자료입니다. 점수 해석 기준은 파일럿 "
    "데이터를 바탕으로 보정될 예정입니다."
)


def _step1_section(state: Mapping) -> dict:
    results = state.get("step1_results") or {}
    return {
        "persona": results.get("persona") or state.get("step1_persona"),
        "title": results.get("title"),
        "icon": results.get("icon"),
        "description": results.get("description"),
        "total_score": results.get("total_score", state.get("step1_total_score")),
        "max_score": STEP1_QUESTION_COUNT * STEP1_MAX_PER_QUESTION,
    }


def _step2_section(state: Mapping) -> dict:
    result = state.get("step2_result") or {}
    components = result.get("components") or {}
    ordered = [
        {"key": key, "label": label, "value": components[key]}
        for key, label in COMPONENT_LABELS.items()
        if components.get(key) is not None
    ]
    return {
        "health_score": result.get("health_score"),
        "components": ordered,
        "analysis_summary": result.get("analysis_summary"),
        "target_concept": result.get("target_concept"),
    }


def _step3_section(state: Mapping) -> dict:
    # 제출 단위 이력(오답 후 같은 문제 재제출 포함). quiz_no로 몇 번째 퀴즈였는지 구분한다.
    history = list(state.get("step3_history") or [])
    rows = [
        {
            "제출": i,
            "퀴즈": f"{item['quiz_no']}번" if item.get("quiz_no") else "-",
            "퀴즈 유형": item.get("quiz_type") or "-",
            "결과": "정답" if item.get("is_correct") else "오답",
        }
        for i, item in enumerate(history, start=1)
    ]
    quiz_numbers = {item.get("quiz_no") for item in history if item.get("quiz_no")}
    reason = state.get("step3_done_reason")
    return {
        "quiz_count": len(quiz_numbers) if quiz_numbers else len(history),
        "submission_count": len(history),
        "correct_count": sum(1 for item in history if item.get("is_correct")),
        "rows": rows,
        "done_reason": reason,
        "done_reason_label": DONE_REASON_LABELS.get(reason, "-"),
        "badges": list(state.get("acquired_keywords") or []),
    }


def is_report_ready(state: Mapping) -> bool:
    """3단계까지 완료된 세션만 리포트를 연다(docs/07 3단계 "제출·완료 흐름")."""
    return bool(state.get("step3_done"))


def build_report(state: Mapping) -> dict:
    """세션 상태로부터 결과 리포트 표시용 데이터를 만든다."""
    return {
        "case_id": state.get("case_id"),
        "step1": _step1_section(state),
        "step2": _step2_section(state),
        "step3": _step3_section(state),
        "cross_check": {"guide": CROSS_CHECK_GUIDE, "note": CROSS_CHECK_NOTE},
    }
