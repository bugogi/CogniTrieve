# utils/logic_step2.py
import json
from utils.llm_handler import call_gemini_api

SYSTEM_PROMPT = (
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

def analyze_student_log(dialogue_log: str) -> dict:
    """
    학생이 AI와 나눈 대화 로그를 받아 Gemini API를 호출하고 분석 결과를 반환합니다.
    """
    if not dialogue_log.strip():
        raise ValueError("입력된 대화 로그가 비어 있습니다. 분석할 로그를 입력해 주세요.")
        
    # API 호출
    raw_response = call_gemini_api(SYSTEM_PROMPT, dialogue_log, temperature=0.1)
    
    # JSON 파싱 및 데이터 정제
    try:
        result = json.loads(raw_response)
    except json.JSONDecodeError as e:
        # JSON 형식이 아닐 경우 예외 처리 및 대강의 키 구조를 가진 사전 생성 시도
        raise RuntimeError(f"API 응답이 올바른 JSON 형식이 아닙니다. 원본 응답: {raw_response}") from e
        
    # 필수 필드 검증 및 기본값 보장
    required_keys = ["health_score", "risk_highlight", "analysis_summary", "target_concept"]
    for key in required_keys:
        if key not in result:
            if key == "health_score":
                result[key] = 50
            elif key == "target_concept":
                result[key] = "데이터 구조 기초"
            else:
                result[key] = f"[{key} 분석 정보가 누락되었습니다]"
                
    # 점수 범위 보장 (0~100)
    try:
        result["health_score"] = max(0, min(100, int(result["health_score"])))
    except (ValueError, TypeError):
        result["health_score"] = 50
        
    return result
