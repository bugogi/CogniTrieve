# 프로젝트명: CogniTrieve (메타인지 기반 AI 활용 자가진단 및 학습 검증 파이프라인)

- **목적**: 대학생이 **과제 / 수강 / 시험 대비**라는 학습 맥락에서 AI를 어떻게
  활용했는지 스스로 진단·성찰하도록 돕는다. 1학기에는 CS(컴퓨터공학) 전공 코딩
  과제 하나만 다뤘으나, 2학기 확장으로 산출물 유형(텍스트/코드/수리/디자인) 4종과
  학습 유형(수강/시험 대비) 2종을 더해 **총 6개 케이스**를 다루는 일반화된 시스템이
  되었다.
- **기술 스택**: Python, Streamlit, Google Generative AI(Gemini API), **Supabase
  (Postgres)** — 파일럿 데이터 영구 저장을 위해 2학기에 추가됨. React/FastAPI 등으로의
  스택 전환은 검토 후 기각되었다(1인 개발 체제, 파일럿 목적에 Streamlit으로 충분하다고
  판단).
- **설계 근거**: 이 프로젝트의 모든 설계 판단은 `docs/00`~`docs/10` 마크다운 문서에
  이미 정리되어 있다. **AI는 새로운 설계 판단(예: 임계값 수치, 문항 문구, 위험도 등급)
  이 필요할 때 임의로 만들어내지 말고, 먼저 관련 `docs/` 문서를 확인한다.** 문서에
  답이 없으면 사용자에게 확인을 요청한다. 특히:
  - `docs/04_블룸매트릭스_유형별.md`, `docs/05_AI개입깊이_핫스팟매핑.md`,
    `docs/06_학습이벤트_명세.md` — 산출물 유형 A/B/C/D의 이론적 근거
  - `docs/08_학습유형_확장_설계방향.md`, `docs/08-1_수강_학습유형_설계.md`,
    `docs/08-2_시험대비_학습유형_설계.md` — 수강/시험대비 학습유형의 이론적 근거
  - `docs/07_파이프라인_설계.md` — 진단 문항, 과락 로직, Health Score, 3단계 질문
    포맷 등 **파이프라인 로직의 1차 스펙**
  - `docs/09_학습유형_통합비교.md` — 6개 케이스 통합 스키마, 설계 정합성 검토 이력
  - `docs/10_구현로드맵.md` — 이 코드베이스를 어떤 순서로 구현하는지의 계획(구현
    Phase 1~5), DB 스키마 정의

---

## 0. 케이스(Case) 모델 — 이번 확장의 핵심 개념

프로젝트는 이제 **6개 케이스**를 다룬다. 각 케이스는 Supabase `cases` 테이블(스키마는
`docs/10` 부록 A 참조)에 정의되며, 코드에 하드코딩하지 않는다.

| case_id | learning_type | output_type | 대표 시나리오 |
|---|---|---|---|
| `assignment_A` | 과제 | A(텍스트) | 교양 에세이 |
| `assignment_B` | 과제 | B(코드) | CS 코딩 (1학기 원본) |
| `assignment_C` | 과제 | C(수리) | 물리 문제풀이 |
| `assignment_D` | 과제 | D(디자인) | 브랜드 아이덴티티 기획 |
| `course` | 수강 | 없음(공통) | 예습~자기점검 |
| `exam_prep` | 시험 대비 | 없음(공통) | 범위파악~실전시뮬레이션 |

각 케이스 레코드는 다음 필드를 가진다: `questions`(5문항), `hotspot_primary`,
`hotspot_secondary`, `hotspot_tier`(등급: "최고위험"/"위험"), `concept_vocabulary`
(2·3단계에서 쓰는 케이스별 용어 사전). 학생은 1단계 진입 시 케이스를 선택하고,
선택된 `case_id`는 전체 파이프라인(1→2→3단계)에 걸쳐 세션에 유지된다.

---

## 1. 시스템 아키텍처 및 상태 관리 (필수 준수 규칙)

1. 모든 UI는 Streamlit 기반으로 작성하며, 멀티 페이지 기능(`pages/` 폴더)을 사용한다.
2. 단계별 데이터(선택된 `case_id` → 1단계 페르소나 → 2단계 로그 분석 결과 → 3단계
   퀴즈)는 반드시 `st.session_state`를 사용하여 페이지 간에 안전하게 전달한다.
   `case_id`는 세션 최초 진입 시점부터 끝까지 유지되어야 한다.
3. 핵심 비즈니스 로직 및 LLM API 호출은 UI 파일(`pages/`)에 하드코딩하지 않고,
   `utils/` 폴더 내 모듈로 분리하여 import 한다.
4. **[신규] 핫스팟·페르소나 판별 로직에 특정 케이스를 하드코딩하지 않는다.** 과거
   1학기 코드처럼 `Q2`, `Q4`를 직접 코드에 박아 넣지 말고, 반드시 `cases` 테이블에서
   해당 `case_id`의 `hotspot_primary`/`hotspot_secondary`/`hotspot_tier`를 조회해
   사용한다.
5. **[신규] 응답은 Supabase에 영구 저장한다.** `st.session_state`는 페이지 간 임시
   전달 용도이고, 최종 데이터의 소스는 항상 DB다(파일럿 데이터 축적 목적).
6. **[신규] 동의(consent)를 완료하지 않은 세션은 진단을 진행할 수 없다.** `app.py`
   진입 시 최초 1회 동의 화면을 거치며, 동의 시각을 `sessions.consented_at`에 기록한다.

---

## 2. 디렉토리 구조

```
CogniTrieve/
├── AI_INSTRUCTIONS.md      # 본 명세서
├── app.py                  # 메인 홈 화면 + 동의(consent) 화면 + 케이스 선택 진입점
├── requirements.txt
├── .env                    # GEMINI_API_KEY, SUPABASE_URL, SUPABASE_KEY 저장
├── .env.example
├── docs/                    # 설계 문서 전체 (00~10)
├── scripts/
│   └── seed_cases.py       # cases 테이블에 6개 케이스 시딩
├── pages/
│   ├── 1_사전진단.py
│   ├── 2_로그분석.py
│   └── 3_전이검증.py
└── utils/
    ├── __init__.py
    ├── db_handler.py       # [신규] Supabase 클라이언트, 세션/응답 CRUD
    ├── logic_step1.py      # 점수 산출 및 과락 판별 로직 (케이스 파라미터화)
    ├── logic_step2.py      # 2단계 LLM 파싱 로직 (케이스별 비교 로직 분기)
    ├── comparison/         # [신규] 유형별 "결과물 일치율" 산출 서브패키지
    │   ├── __init__.py
    │   ├── code_compare.py     # B: 기존 diff/AST 로직
    │   ├── text_compare.py     # A: 임베딩 유사도
    │   ├── math_compare.py     # C: sympy 동치 판정
    │   └── self_report.py      # D·수강·시험대비: 자기보고 방식
    ├── logic_step3.py      # 3단계 퀴즈 파싱 및 채점 알고리즘 (quiz_type 확장)
    └── llm_handler.py      # Gemini API 통신 모듈
```

---

## 3. 파이프라인 단계별 핵심 논리 및 데이터 스펙

### [0단계: 동의 및 케이스 선택] (`app.py`)
- 최초 진입 시 수집 목적·활용 범위·보존 기간을 안내하고 동의를 받는다(미동의 시
  진행 불가).
- 동의 후 6개 케이스 중 하나를 선택하게 하고, `sessions` 테이블에 세션을 생성한다
  (`anon_id`는 UUID로 발급).

### [1단계: 사전 진단] (`1_사전진단.py`)
- 선택된 `case_id`에 해당하는 5개 리커트 척도(1~5점) 문항을 `cases` 테이블에서
  조회해 렌더링한다 (문항 텍스트는 케이스마다 다름 — `docs/07` 3절 참조).
- **단순 총점 합산이 아닌 '핫스팟 과락 로직'을 적용**하되, 등급별 차등 임계값을
  쓴다: `threshold(tier)` — `tier == "최고위험"`이면 `<= 2`, `tier == "위험"`이면
  `<= 1` (`docs/07` 5.2 반영 로직). CS 케이스(`assignment_B`)만 예시로 들면
  `hotspot_primary = Q4(디버깅, 최고위험)`, `hotspot_secondary = Q2(시스템설계,
  위험)`이 되어 임계값이 서로 다르게 적용된다.
- 4가지 페르소나(맹목적 의존형, 효율 중심형, 방어형, 자기 주도형)는 케이스 무관
  공통 정의를 쓴다 — 판별 공식만 위 임계값을 케이스별로 조회해 적용한다.
- 결과를 `step1_responses`(session_id, **case_id**, q1~q5, total_score, persona)에
  저장한다.

### [2단계: 로그 교차 검증] (`2_로그분석.py`)
- 학생이 AI와 나눈 대화 로그(수동 Copy&Paste 텍스트)를 입력받아 Gemini API 호출.
- `case_id`의 `output_type`에 따라 `utils/comparison/`의 해당 모듈로 "결과물 일치율"을
  산출한다 (A=임베딩 유사도, B=코드 diff, C=수식 동치 판정, D·수강·시험대비=자기보고).
- "해줘", "통째로 짜줘" 등의 인지적 구두쇠 행동을 감지하고, `case_id`의
  `concept_vocabulary`를 프롬프트에 주입해 케이스에 맞는 개념/키워드를 추출하도록
  Gemini에 요청한다.
- Health Score는 **균등 가중**(프롬프트 건전성/자립도/위험구간 감점 각 1/3)으로
  산출한다(`docs/07` 5.4 반영) — 세부 계수는 `HEALTH_SCORE_WEIGHTS` 상수로 관리하고
  코드에 흩어 쓰지 않는다.
- 결과 JSON 스펙:
```json
{
  "health_score": 35,
  "components": {"prompt_soundness": 40, "autonomy": 30, "risk_deduction": 35},
  "risk_highlight": "[위험 문장 추출]",
  "analysis_summary": "[분석 요약]",
  "target_concept": "[3단계 퀴즈 출제용 핵심 개념 — concept_vocabulary 기반]"
}
```
- `step2_responses`(session_id, **case_id**, health_score, **components**(jsonb),
  risk_highlight, analysis_summary)에 저장한다. `components`는 `docs/09` 5.4 보정
  작업을 위해 세부 원본값을 그대로 보존한다.

### [3단계: 적응형 학습 전이 검증] (`3_전이검증.py`)
- 2단계 결과(`target_concept`)를 바탕으로 Gemini API를 재호출해 1문장 서술형 '동적
  퀴즈'를 생성한다.
- `quiz_type`은 케이스별로 다음 중 하나: `함수 주석 작성`/`에러 로그 원인 작성`(B),
  `아이디어 근거 작성`(D), **`문단 논거 요약 작성`(A, 신규)**, **`수식 도출 근거
  작성`(C, 신규)**. 수강·시험대비는 `docs/07` "질문 포맷 일반화(Phase 6b)" 표
  (2026-08 추가분)에 정의된 `개념 자기설명 작성`/`오답 원인 재설명 작성`을 따른다.
- Output JSON 스펙 (기존과 동일, 유지):
```json
{
  "quiz_type": "함수 주석 작성",
  "dynamic_question": "[학생에게 던질 50자 이내 답변 유도 퀴즈]",
  "expected_keywords": ["키워드1", "대체키워드2"]
}
```
- 채점: LLM 추가 호출 없이, `expected_keywords`(케이스의 `concept_vocabulary`를 채점
  키워드 뱅크로 재사용) 중 하나라도 학생 답변에 포함되면 정답 처리.
- 보상 UI(해시태그 뱃지, `st.balloons()`)는 케이스 무관 공통 로직이며 변경 불필요.
- `step3_responses`(session_id, **case_id**, quiz_type, dynamic_question,
  student_answer, is_correct, matched_keyword)에 저장한다.

---

## 4. 구현 시 주의사항

- **한 번에 하나씩 진행한다.** `docs/10` 구현 Phase 1~5 순서를 따르며, 이전 Phase의
  완료 기준을 만족하지 않은 상태에서 다음 Phase로 넘어가지 않는다.
- Supabase는 **dev/prod 프로젝트를 분리**해서 쓴다. 개발 중에는 dev 프로젝트만
  건드린다.
- RLS(Row Level Security)는 최소 1개 이상 정책을 적용한다(`docs/10` 부록 A 참조).
- 새로운 설계 판단이 필요한 상황(예: 신규 케이스 추가, 임계값 변경)이 생기면 코드부터
  고치지 말고, 먼저 관련 `docs/` 문서를 갱신할지 사용자와 논의한다.
