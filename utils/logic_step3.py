# utils/logic_step3.py
import json
from utils.llm_handler import call_gemini_api

SYSTEM_PROMPT = (
    "당신은 CS 전공 학생의 이해도를 적응형으로 평가하는 AI 튜터입니다.\n"
    "2단계 로그 분석 결과로 파악된 핵심 CS 개념(target_concept)과 학생의 위험 대화 로그 패턴(risk_highlight)을 바탕으로,\n"
    "학생이 이 개념을 정말로 직접 이해하고 설명할 수 있는지 검증하기 위한 1문장의 짧은 주관식 '동적 퀴즈'를 출제해 주세요.\n\n"
    "지시사항:\n"
    "1. quiz_type은 다음 세 가지 중 가장 적합한 하나를 선택하세요: ['에러 원인 분석', '핵심 로직 주석', '아이디어 근거']\n"
    "2. dynamic_question은 학생에게 던질 50자 이내의 주관식 답변 유도 퀴즈여야 하며, 명확하고 친절하지만 도전적인 톤으로 작성해 주세요. (질문 끝에 물음표 필수)\n"
    "3. expected_keywords는 학생의 정답 문장에 반드시 들어가야 할 핵심 개념 단어 및 주요 대체 동의어(또는 영문명/한글명 쌍) 목록입니다. (1개에서 최대 4개 단어)\n"
    "   - 예: target_concept가 '시간 복잡도'라면, ['시간복잡도', '빅오', 'bigo', '대문자o'] 등\n"
    "   - 예: target_concept가 '포인터'라면, ['주소값', '메모리주소', 'pointer', '참조'] 등\n"
    "4. 응답은 반드시 다른 텍스트 없이 아래 지정된 JSON 규격으로만 채워져야 합니다. JSON 형식을 엄격히 준수해 주세요:\n"
    "{\n"
    '  "quiz_type": "에러 원인 분석 / 핵심 로직 주석 / 아이디어 근거 중 택1",\n'
    '  "dynamic_question": "학생에게 던질 50자 이내 답변 유도 퀴즈",\n'
    '  "expected_keywords": ["정답키워드1", "대체키워드2"]\n'
    "}"
)

def generate_adaptive_quiz(target_concept: str, risk_highlight: str) -> dict:
    """
    2단계 분석 정보(핵심 개념 및 위험 문장)를 기반으로 Gemini API를 호출하여
    학생의 메타인지를 검증하기 위한 서술형 동적 퀴즈를 생성합니다.
    """
    if not target_concept or not target_concept.strip():
        target_concept = "컴퓨터공학 기초"
        
    user_prompt = (
        f"핵심 CS 개념: {target_concept}\n"
        f"이전 의존형 행동(위험 의심 구문): {risk_highlight or '없음'}\n\n"
        f"위 정보를 기반으로 {target_concept}에 대한 퀴즈를 생성해 주세요."
    )
    
    # API 호출
    raw_response = call_gemini_api(SYSTEM_PROMPT, user_prompt, temperature=0.3)
    
    # JSON 파싱 및 예외 처리
    try:
        result = json.loads(raw_response)
    except json.JSONDecodeError as e:
        # 파싱 실패 시 기본 퀴즈 딕셔너리 생성
        result = {}
        
    # 필수 필드 보장 및 정제
    if "quiz_type" not in result or result["quiz_type"] not in ["에러 원인 분석", "핵심 로직 주석", "아이디어 근거"]:
        result["quiz_type"] = "핵심 로직 주석"
        
    if "dynamic_question" not in result or not result["dynamic_question"].strip():
        result["dynamic_question"] = f"'{target_concept}'의 동작 원리와 왜 중요한지 50자 이내로 핵심을 서술해 보세요."
        
    if "expected_keywords" not in result or not isinstance(result["expected_keywords"], list) or len(result["expected_keywords"]) == 0:
        # target_concept 자체를 기본 키워드로 사용
        result["expected_keywords"] = [target_concept]
        
    return result

def find_matched_keyword(student_answer: str, expected_keywords: list):
    """
    학생의 답변에 실제로 포함된 첫 번째 예상 키워드를 반환합니다(없으면 None).
    순수 파이썬 로직으로 동작하며, 대소문자나 띄어쓰기에 무관하게 동작하도록 문자열을 정제합니다.
    """
    if not student_answer or not expected_keywords:
        return None

    # 학생 답변 공백 제거 및 소문자 변환
    cleaned_student = "".join(student_answer.split()).lower()

    for kw in expected_keywords:
        if not kw:
            continue
        # 각 키워드도 동일하게 공백 제거 및 소문자 변환
        cleaned_kw = "".join(kw.split()).lower()
        if not cleaned_kw:
            continue
        # 포함 여부 검증
        if cleaned_kw in cleaned_student:
            return kw

    return None


def verify_answer(student_answer: str, expected_keywords: list) -> bool:
    """
    학생의 답변이 예상 키워드(expected_keywords) 중 하나라도 포함하고 있는지 검증합니다.
    """
    return find_matched_keyword(student_answer, expected_keywords) is not None
