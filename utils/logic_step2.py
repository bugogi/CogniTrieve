# utils/logic_step2.py
import json

from utils.comparison import code_compare
from utils.comparison.self_report import calculate_autonomy_score
from utils.llm_handler import call_gemini_api

# 세 컴포넌트(prompt_soundness/autonomy/risk_deduction) 균등 가중 (docs/07 5.4, docs/09 5.4)
HEALTH_SCORE_WEIGHTS = (1 / 3, 1 / 3, 1 / 3)

# output_type이 이 값에 해당하는 케이스(D/수강/시험대비)는 결과물 직접 비교가 불가능해
# 자기보고 방식(신규 경로)을 쓴다 (docs/10 구현 Phase 3 3-a 범위).
_SELF_REPORT_OUTPUT_TYPES = (None, "D")

# B(코드)는 diff/AST 비교 방식(신규 경로)을 쓴다 (docs/10 구현 Phase 3 3-b 범위).
# A/C는 각자의 comparison 모듈이 아직 없어 레거시 단일 health_score 경로를 그대로 유지한다.
_CODE_COMPARE_OUTPUT_TYPES = ("B",)

_LEGACY_SYSTEM_PROMPT = (
    "당신은 CS 전공 학생의 메타인지를 평가하는 AI 튜터입니다. 사용자가 입력한 프롬프트 대화 로그를 분석하여 '인지적 구두쇠' 행동을 찾아내세요.\n\n"
    "'전체 코드 짜줘', '이 에러 알아서 고쳐줘' 같은 무지성 위임 지시어에는 health_score(건강도 점수)를 대폭 감점하세요.\n\n"
    "에러 메시지의 의미를 묻거나, 가설을 제시하거나, 로직의 방향성을 토론하는 질문에는 가점을 주십시오.\n\n"
    "분석 결과는 반드시 다음 구조의 JSON 객체로만 반환해야 합니다:\n"
    "{\n"
    '  "health_score": (0~100 사이의 정수),\n'
    '  "risk_highlight": "로그에서 추출한 가장 치명적인 의존형 지시 문장 (최대 2문장)",\n'
    '  "analysis_summary": "인지 패턴에 대한 정성적 분석 및 평가 요약",\n'
    '  "target_concept": "3단계 퀴즈 출제용 핵심 CS 개념 단어 1개 (예: 포인터 메모리 유효 범위, 시간 복잡도 등)"\n'
    "}"
)

_GENERAL_SYSTEM_PROMPT = (
    "당신은 학생의 메타인지를 평가하는 AI 튜터입니다. 사용자가 입력한 프롬프트 대화 로그를 분석하여 '인지적 구두쇠' 행동을 찾아내세요.\n\n"
    "'전체 다 짜줘', '알아서 완성해줘' 같은 무지성 위임 지시어에는 prompt_soundness(프롬프트 건전성 지수)를 대폭 감점하세요.\n\n"
    "왜/어떻게에 해당하는 원리탐구형 질문, 가설 제시, 방향성 토론에는 가점을 주십시오.\n\n"
    "risk_deduction은 '감점 폭'이 아니라 다른 두 지표와 동일한 방향의 0~100 점수입니다 — "
    "위험한 의존 패턴(인지적 구두쇠 행동)이 로그에 적을수록/약할수록 100에 가깝고, 많을수록/강할수록 0에 가깝습니다. "
    "부호를 뒤집지 마세요.\n\n"
    "분석 결과는 반드시 다음 구조의 JSON 객체로만 반환해야 합니다:\n"
    "{\n"
    '  "prompt_soundness": (0~100 사이의 정수, 프롬프트 건전성 지수),\n'
    '  "risk_deduction": (0~100 사이의 정수, 위험 패턴이 적을수록 높은 값),\n'
    '  "risk_highlight": "로그에서 추출한 가장 치명적인 의존형 지시 문장 (최대 2문장)",\n'
    '  "analysis_summary": "인지 패턴에 대한 정성적 분석 및 평가 요약",\n'
    '  "target_concept": "3단계 퀴즈 출제용 핵심 개념 단어 1개"\n'
    "}"
)


def calculate_health_score(components: dict) -> int:
    """prompt_soundness/autonomy/risk_deduction을 균등 가중 평균해 0~100 정수로 반환합니다."""
    weighted_sum = (
        components["prompt_soundness"] * HEALTH_SCORE_WEIGHTS[0]
        + components["autonomy"] * HEALTH_SCORE_WEIGHTS[1]
        + components["risk_deduction"] * HEALTH_SCORE_WEIGHTS[2]
    )
    return max(0, min(100, round(weighted_sum)))


def _parse_json_response(raw_response: str) -> dict:
    try:
        return json.loads(raw_response)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"API 응답이 올바른 JSON 형식이 아닙니다. 원본 응답: {raw_response}") from e


def _analyze_log_legacy(dialogue_log: str) -> dict:
    """output_type이 A/C인 케이스용 레거시 경로: Gemini가 health_score를 직접 산출."""
    raw_response = call_gemini_api(_LEGACY_SYSTEM_PROMPT, dialogue_log, temperature=0.1)
    result = _parse_json_response(raw_response)

    required_keys = ["health_score", "risk_highlight", "analysis_summary", "target_concept"]
    for key in required_keys:
        if key not in result:
            if key == "health_score":
                result[key] = 50
            elif key == "target_concept":
                result[key] = "데이터 구조 기초"
            else:
                result[key] = f"[{key} 분석 정보가 누락되었습니다]"

    try:
        result["health_score"] = max(0, min(100, int(result["health_score"])))
    except (ValueError, TypeError):
        result["health_score"] = 50

    return result


def _analyze_log_general(dialogue_log: str) -> dict:
    """output_type이 None/D인 케이스용 신규 경로: prompt_soundness/risk_deduction만 산출."""
    raw_response = call_gemini_api(_GENERAL_SYSTEM_PROMPT, dialogue_log, temperature=0.1)
    result = _parse_json_response(raw_response)

    required_keys = ["prompt_soundness", "risk_deduction", "risk_highlight", "analysis_summary", "target_concept"]
    for key in required_keys:
        if key not in result:
            if key in ("prompt_soundness", "risk_deduction"):
                result[key] = 50
            elif key == "target_concept":
                result[key] = "핵심 학습 개념 미도출"
            else:
                result[key] = f"[{key} 분석 정보가 누락되었습니다]"

    for key in ("prompt_soundness", "risk_deduction"):
        try:
            result[key] = max(0, min(100, int(result[key])))
        except (ValueError, TypeError):
            result[key] = 50

    return result


def analyze_student_log(
    case: dict,
    dialogue_log: str,
    self_report: dict | None = None,
    code_pair: dict | None = None,
) -> dict:
    """
    학생이 AI와 나눈 대화 로그를 받아 Gemini API를 호출하고 분석 결과를 반환합니다.

    case["output_type"]이 None(수강/시험대비) 또는 "D"(디자인)이면 자기보고 방식으로,
    "B"(코드)면 diff/AST 비교 방식으로 autonomy를 산출해 세 컴포넌트 균등 가중
    health_score를 계산한다(각각 self_report/code_pair 필수). A/C이면 기존 레거시
    경로(Gemini가 health_score 직접 산출)를 그대로 사용한다.
    """
    if not dialogue_log.strip():
        raise ValueError("입력된 대화 로그가 비어 있습니다. 분석할 로그를 입력해 주세요.")

    output_type = case.get("output_type")

    if output_type in _SELF_REPORT_OUTPUT_TYPES:
        if self_report is None:
            raise ValueError("이 케이스는 자기보고(self_report) 입력이 필요합니다.")

        llm_result = _analyze_log_general(dialogue_log)
        autonomy = calculate_autonomy_score(
            self_report["adoption_choice"], self_report["revision_count"]
        )
        return _build_component_result(llm_result, autonomy)

    if output_type in _CODE_COMPARE_OUTPUT_TYPES:
        if code_pair is None:
            raise ValueError("이 케이스는 코드 비교(code_pair) 입력이 필요합니다.")

        llm_result = _analyze_log_general(dialogue_log)
        autonomy = code_compare.calculate_autonomy_score(
            code_pair["ai_code"], code_pair["student_code"]
        )
        return _build_component_result(llm_result, autonomy)

    return _analyze_log_legacy(dialogue_log)


def _build_component_result(llm_result: dict, autonomy: int) -> dict:
    """prompt_soundness/risk_deduction(LLM) + autonomy(비교 모듈)를 조합해 최종 응답을 구성합니다."""
    components = {
        "prompt_soundness": llm_result["prompt_soundness"],
        "autonomy": autonomy,
        "risk_deduction": llm_result["risk_deduction"],
    }
    return {
        "health_score": calculate_health_score(components),
        "components": components,
        "risk_highlight": llm_result["risk_highlight"],
        "analysis_summary": llm_result["analysis_summary"],
        "target_concept": llm_result["target_concept"],
    }
