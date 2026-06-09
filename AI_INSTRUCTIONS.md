# 프로젝트 명: CogniTrieve (메타인지 기반 AI 활용 자가진단 및 학습 검증 파이프라인)
- 목적: CS(컴퓨터공학) 전공 학생들의 무분별한 AI 코드 복붙(인지적 구두쇠)을 방지하고, 메타인지를 자극하는 '바람직한 마찰' 제공.
- 기술 스택: Python, Streamlit, Google Generative AI (Gemini API)

## 1. 시스템 아키텍처 및 상태 관리 (필수 준수 규칙)
1. 모든 UI는 Streamlit 기반으로 작성하며, 멀티 페이지 기능(pages/ 폴더)을 사용한다.
2. 단계별 데이터(1단계 페르소나 -> 2단계 로그 분석 결과 -> 3단계 퀴즈)는 반드시 st.session_state를 사용하여 페이지 간에 안전하게 전달한다.
3. 핵심 비즈니스 로직 및 LLM API 호출은 UI 파일(pages/)에 하드코딩하지 않고, utils/ 폴더 내 모듈로 분리하여 import 한다.

## 2. 디렉토리 구조
```
Plaintext
CogniTrieve/
├── AI_INSTRUCTIONS.md      # 본 명세서
├── app.py                  # 메인 홈 화면
├── requirements.txt        
├── .env                    # GEMINI_API_KEY 저장
├── pages/                  
│   ├── 1_사전진단.py     
│   ├── 2_로그분석.py     
│   └── 3_전이검증.py     
└── utils/                  
    ├── __init__.py
    ├── logic_step1.py      # 점수 산출 및 과락 판별 로직
    ├── logic_step2.py      # 2단계 LLM 파싱 로직
    ├── logic_step3.py      # 3단계 퀴즈 파싱 및 채점 알고리즘
    └── llm_handler.py      # Gemini API 통신 모듈
```
## 3. 파이프라인 단계별 핵심 논리 및 데이터 스펙
### [1단계: 사전 진단] (1_사전진단.py)
- 5개의 리커트 척도(1~5점) 설문을 진행.
- 단순 총점 합산이 아닌 '과락(Hotspot) 로직' 적용 (예: Q2(시스템 설계)나 Q4(디버깅) 문항이 2점 이하면 총점이 높아도 무조건 하위 페르소나로 강등).
- 4가지 페르소나(맹목적 의존형, 효율 중심형, 방어형, 자기 주도형) 중 하나를 도출하여 피드백 텍스트 렌더링.

### [2단계: 로그 교차 검증] (2_🔍_로그분석.py)
- 학생이 AI와 나눈 대화 로그(수동 Copy&Paste 텍스트)를 입력받아 Gemini API 호출.

- "해줘", "통째로 짜줘" 등의 인지적 구두쇠 행동을 감지하여 아래 규격의 JSON 형태로 결과를 반환.
```
JSON
{
  "health_score": 35,
  "risk_highlight": "[위험 문장 추출]",
  "analysis_summary": "[분석 요약]",
  "target_concept": "[3단계 퀴즈 출제용 핵심 CS 개념]"
}
```
## [3단계: 적응형 학습 전이 검증] (3_🎯_전이검증.py)
- 2단계 결과를 바탕으로 Gemini API를 재호출하여 1문장 서술형 '동적 퀴즈' 생성.
- [3단계 Output JSON 스펙]
```
JSON
{
  "quiz_type": "에러 원인 분석",
  "dynamic_question": "[학생에게 던질 50자 이내 답변 유도 퀴즈]",
  "expected_keywords": ["키워드1", "대체키워드2"]
}
```
- 채점 로직: LLM을 추가 호출하지 않고, 파이썬 백엔드에서 expected_keywords 배열 내 단어 중 하나라도 학생의 답변 문자열(student_answer)에 포함(in 연산자 활용)되어 있으면 정답으로 처리.
- 보상 UI: 정답 시 st.session_state에 획득 키워드를 저장하고, 화면 하단에 '해시태그 뱃지' 형태로 누적하여 보여주며 st.balloons()를 실행.