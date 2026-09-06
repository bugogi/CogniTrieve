# utils/logic_step3.py
import json
from utils.llm_handler import call_gemini_api

# output_type이 A/B/C/D인 케이스(assignment_*)의 허용 quiz_type 목록.
# B만 2개('함수 주석 작성'/'에러 로그 원인 작성'), 나머지는 1개씩이다(docs/07 Phase 6b 표).
_QUIZ_TYPES_BY_OUTPUT_TYPE = {
    "A": ["문단 핵심 논거 요약 작성"],
    "B": ["함수 주석 작성", "에러 로그 원인 작성"],
    "C": ["수식 도출 근거 작성"],
    "D": ["아이디어 근거 작성"],
}

# output_type이 None인 케이스(course/exam_prep)는 output_type만으로 구분이
# 안 되므로 learning_type으로 재분기한다(docs/07 Phase 6b 2026-08 추가분).
_QUIZ_TYPES_BY_LEARNING_TYPE = {
    "수강": ["개념 자기설명 작성"],
    "시험 대비": ["오답 원인 재설명 작성"],
}

# quiz_type 파싱/생성 실패 시 사용할 질문 템플릿. 최종 채택된 quiz_type(정상
# 생성이든 허용 목록 첫 항목 폴백이든)을 키로 조회해 사용한다(docs/10 구현 Phase 4
# 설계 결정: quiz_type 폴백 기본값 = 허용 목록의 첫 번째 항목).
_FALLBACK_QUESTION_TEMPLATES = {
    "문단 핵심 논거 요약 작성": "'{target_concept}'의 핵심 주장을 나의 언어로 1문장 요약하면?",
    "함수 주석 작성": "'{target_concept}'이 하는 일을 주석 한 줄로 설명한다면?",
    "에러 로그 원인 작성": "'{target_concept}'와 관련된 에러가 왜 발생했다고 생각하나요?",
    "수식 도출 근거 작성": "'{target_concept}'이 어떤 원리에서 도출되었는지 1문장으로 설명한다면?",
    "아이디어 근거 작성": "'{target_concept}'을 선택한 이유를 1문장으로 설명한다면?",
    "개념 자기설명 작성": "'{target_concept}'을 나만의 언어로 1문장으로 설명한다면?",
    "오답 원인 재설명 작성": "'{target_concept}'과 관련된 오답의 원인을 AI 설명 없이 내 언어로 다시 설명한다면?",
}

_STEP3_SYSTEM_PROMPT_INTRO = (
    "당신은 학생의 이해도를 적응형으로 평가하는 AI 튜터입니다.\n"
    "2단계 로그 분석 결과로 파악된 핵심 개념(target_concept)과 학생의 위험 대화 로그 패턴(risk_highlight)을 바탕으로,\n"
    "학생이 이 개념을 정말로 직접 이해하고 설명할 수 있는지 검증하기 위한 1문장의 짧은 주관식 '동적 퀴즈'를 출제해 주세요.\n\n"
    "지시사항:\n"
)

_STEP3_SYSTEM_PROMPT_BODY = (
    "2. dynamic_question은 학생에게 던질 50자 이내의 주관식 답변 유도 퀴즈여야 하며, 명확하고 친절하지만 도전적인 톤으로 작성해 주세요. (질문 끝에 물음표 필수)\n"
    "3. expected_keywords는 학생의 정답 문장에 반드시 들어가야 할 핵심 개념 단어 및 주요 대체 동의어(또는 영문명/한글명 쌍) 목록입니다. (1개에서 최대 4개 단어)\n"
    "   - 예: target_concept가 '시간 복잡도'라면, ['시간복잡도', '빅오', 'bigo', '대문자o'] 등\n"
    "   - 예: target_concept가 '포인터'라면, ['주소값', '메모리주소', 'pointer', '참조'] 등\n"
    "4. 응답은 반드시 다른 텍스트 없이 아래 지정된 JSON 규격으로만 채워져야 합니다. JSON 형식을 엄격히 준수해 주세요:\n"
)


# logic_step2.py의 _build_concept_vocabulary_hint와 의도적으로 동일한 로직의
# 로컬 복제본이다 — 비공개(_ prefix) 헬퍼를 다른 모듈에서 끌어다 쓰는 것은
# 캡슐화 관례에 어긋난다고 판단해 각 모듈에 따로 둔다. 두 곳이 계속 같이
# 바뀌어야 한다면 추후 공용 모듈(예: utils/prompt_helpers.py)로 추출할 여지가 있다.
def _build_concept_vocabulary_hint(concept_vocabulary: list[str] | None) -> str:
    """case의 concept_vocabulary를 참고 자료로 프롬프트에 주입할 문단을 만듭니다.

    target_concept은 이미 2단계에서 확정되어 3단계로 넘어오므로, 여기서는
    quiz_type 선택과 expected_keywords 생성을 이 목록에 가깝게 유도하는
    용도로만 쓴다. concept_vocabulary가 없거나 빈 리스트면 빈 문자열을 반환해
    기존 프롬프트 그대로 동작하게 한다.
    """
    if not concept_vocabulary:
        return ""

    vocabulary_text = ", ".join(concept_vocabulary)
    return (
        "\n\n[참고 개념 목록] 이 학습 케이스와 관련된 핵심 개념은 다음과 같습니다: "
        f"{vocabulary_text}.\n"
        "expected_keywords를 고를 때 가능하면 이 목록 중 target_concept과 관련된 단어를 "
        "우선 참고하세요. 단, 목록에 적합한 단어가 없다면 목록 밖 단어를 자유롭게 선택해도 됩니다.\n\n"
    )


def _get_allowed_quiz_types(case: dict) -> list[str]:
    """case의 output_type(A/B/C/D) 또는 learning_type(수강/시험 대비)으로 허용
    quiz_type 목록을 결정합니다. 어느 쪽에도 해당하지 않으면 ValueError를 던져
    cases 테이블에 잘못된 값이 들어간 경우를 조기에 드러냅니다.
    """
    output_type = case.get("output_type")
    if output_type in _QUIZ_TYPES_BY_OUTPUT_TYPE:
        return _QUIZ_TYPES_BY_OUTPUT_TYPE[output_type]

    learning_type = case.get("learning_type")
    if learning_type in _QUIZ_TYPES_BY_LEARNING_TYPE:
        return _QUIZ_TYPES_BY_LEARNING_TYPE[learning_type]

    raise ValueError(
        f"알 수 없는 케이스입니다: output_type={output_type!r}, learning_type={learning_type!r}"
    )


def _build_system_prompt(case: dict, allowed_quiz_types: list[str]) -> str:
    quiz_type_list = ", ".join(f"'{t}'" for t in allowed_quiz_types)
    quiz_type_instruction = f"1. quiz_type은 다음 중 가장 적합한 하나를 선택하세요: [{quiz_type_list}]\n"

    concept_hint = _build_concept_vocabulary_hint(case.get("concept_vocabulary"))

    quiz_type_options = " / ".join(allowed_quiz_types)
    schema_block = (
        "{\n"
        f'  "quiz_type": "{quiz_type_options} 중 택1",\n'
        '  "dynamic_question": "학생에게 던질 50자 이내 답변 유도 퀴즈",\n'
        '  "expected_keywords": ["정답키워드1", "대체키워드2"]\n'
        "}"
    )

    return (
        _STEP3_SYSTEM_PROMPT_INTRO
        + quiz_type_instruction
        + _STEP3_SYSTEM_PROMPT_BODY
        + concept_hint
        + schema_block
    )


def generate_adaptive_quiz(target_concept: str, risk_highlight: str, case: dict) -> dict:
    """
    2단계 분석 정보(핵심 개념 및 위험 문장)와 case(output_type/learning_type/
    concept_vocabulary)를 기반으로 Gemini API를 호출하여 학생의 메타인지를
    검증하기 위한 서술형 동적 퀴즈를 생성합니다.

    quiz_type 후보와 파싱 실패 시 폴백(quiz_type/dynamic_question/expected_keywords/
    target_concept)이 모두 case에 따라 달라집니다(docs/07 Phase 6b, docs/10 구현
    Phase 4).
    """
    allowed_quiz_types = _get_allowed_quiz_types(case)

    if not target_concept or not target_concept.strip():
        vocabulary = case.get("concept_vocabulary")
        target_concept = vocabulary[0] if vocabulary else "핵심 학습 개념"

    system_prompt = _build_system_prompt(case, allowed_quiz_types)

    user_prompt = (
        f"핵심 개념: {target_concept}\n"
        f"이전 의존형 행동(위험 의심 구문): {risk_highlight or '없음'}\n\n"
        f"위 정보를 기반으로 {target_concept}에 대한 퀴즈를 생성해 주세요."
    )

    # API 호출
    raw_response = call_gemini_api(system_prompt, user_prompt, temperature=0.3)

    # JSON 파싱 및 예외 처리
    try:
        result = json.loads(raw_response)
    except json.JSONDecodeError:
        # 파싱 실패 시 기본 퀴즈 딕셔너리 생성
        result = {}

    # 필수 필드 보장 및 정제 (docs/10 구현 Phase 4 설계 결정: quiz_type 폴백
    # 기본값은 case별 허용 목록의 첫 번째 항목)
    if "quiz_type" not in result or result["quiz_type"] not in allowed_quiz_types:
        result["quiz_type"] = allowed_quiz_types[0]

    if "dynamic_question" not in result or not result["dynamic_question"].strip():
        template = _FALLBACK_QUESTION_TEMPLATES[result["quiz_type"]]
        result["dynamic_question"] = template.format(target_concept=target_concept)

    if "expected_keywords" not in result or not isinstance(result["expected_keywords"], list) or len(result["expected_keywords"]) == 0:
        # docs/10 구현 Phase 4 설계 결정: expected_keywords 폴백은
        # case["concept_vocabulary"] 전체를 채점 키워드 뱅크로 재사용한다
        # (07 "채점 로직 일반화" 원칙 적용 — "해석 A"는 정상 생성 경로에 대한
        # 결정이라 이 실패 경로 결정과 배치되지 않는다).
        vocabulary = case.get("concept_vocabulary")
        result["expected_keywords"] = list(vocabulary) if vocabulary else [target_concept]

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
