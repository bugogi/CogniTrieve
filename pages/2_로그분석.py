import streamlit as st
import sys
import os

# root 디렉토리를 path에 추가하여 utils 패키지가 정상 임포트되도록 보장
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.db_handler import save_step2_response
from utils.logic_step2 import analyze_student_log

# 페이지 설정
st.set_page_config(
    page_title="2단계: 로그분석 - CogniTrieve",
    page_icon="🔍",
    layout="wide"
)

# 동의/세션 가드: 홈 화면에서 동의 및 케이스 선택을 마치지 않은 경우 진행 차단
if not st.session_state.get("consented") or not st.session_state.get("session_id"):
    st.warning("⚠️ 먼저 홈 화면에서 동의 및 케이스 선택을 완료해 주세요.")
    if st.button("🏠 홈으로 이동", type="primary"):
        st.switch_page("app.py")
    st.stop()

# 커스텀 CSS 주입
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700;900&display=swap');
    
    html, body, [data-testid="stSidebar"] {
        font-family: 'Noto Sans KR', sans-serif;
    }
    
    .page-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1E1B4B;
        margin-bottom: 0.5rem;
    }
    
    .page-subtitle {
        font-size: 1.1rem;
        color: #4B5563;
        margin-bottom: 2rem;
    }
    
    /* 예제 박스 */
    .example-btn {
        margin-bottom: 1rem;
    }
    
    /* 분석 카드 */
    .metric-container {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: #F3F4F6;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 1.5rem;
        border-left: 8px solid #6B7280;
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: 900;
        color: #111827;
    }
    
    .metric-label {
        font-size: 1rem;
        font-weight: 700;
        color: #4B5563;
    }
    
    .risk-box {
        background-color: #FEF2F2;
        border: 1px solid #FCA5A5;
        border-left: 6px solid #EF4444;
        border-radius: 8px;
        padding: 18px;
        margin-bottom: 1.5rem;
    }
    
    .risk-title {
        font-weight: 700;
        color: #991B1B;
        font-size: 1.05rem;
        margin-bottom: 0.5rem;
    }
    
    .risk-text {
        color: #DC2626;
        font-style: italic;
        font-size: 0.95rem;
    }
    
    .concept-badge {
        display: inline-block;
        background: linear-gradient(135deg, #4F46E5, #3B82F6);
        color: white;
        font-weight: 700;
        padding: 6px 16px;
        border-radius: 9999px;
        font-size: 1.1rem;
        box-shadow: 0 4px 6px -1px rgba(79, 70, 229, 0.2);
    }
</style>
""", unsafe_allow_html=True)

# 페이지 헤더
st.markdown("<h1 class='page-title'>🔍 2단계: 로그 교차 검증 (Log Cross-Validation)</h1>", unsafe_allow_html=True)
st.markdown(
    "<p class='page-subtitle'>평소 AI와 주고받은 프롬프트/질문 로그 대화 전체 또는 일부를 아래에 입력해 주세요.<br>"
    "인간 튜터처럼 정밀하게 학생의 '인지적 구두쇠(의존성)' 행태를 잡아내고 취약한 CS 개념을 자동으로 분류합니다.</p>", 
    unsafe_allow_html=True
)

st.write("---")

# 세션 상태 초기화
if 'step2_result' not in st.session_state:
    st.session_state['step2_result'] = None
if 'step2_done' not in st.session_state:
    st.session_state['step2_done'] = False

# 사전 예제 데이터 구성
example_dependent = (
    "User: 파이썬으로 퀵 정렬 구현해줘. 완벽하게 실행되는 전체 코드만 통째로 짜주고 주석도 세세하게 달아줘.\n"
    "AI: 네, 아래는 파이썬으로 작성한 퀵 정렬 소스코드입니다...\n"
    "User: 이 코드 돌리니까 에러 발생하는데 이거 복사해 줄 테니까 왜 에러나는지 알아서 다 고치고 수정본 코드 다시 다 줘."
)

example_self_directed = (
    "User: 퀵 정렬에서 피벗(Pivot)을 배열의 첫 번째 원소로 선택했을 때와 무작위로 선택했을 때의 최악의 시간 복잡도 차이가 왜 발생하는지 궁금해. 첫 번째 원소로 정하면 왜 정렬된 배열에서 O(N^2)이 되는지 그 메커니즘을 쉽게 설명해 줄 수 있어?\n"
    "AI: 좋은 질문입니다! 피벗을 첫 번째 원소로 설정할 때 정렬된 배열을 만나면 분할이 1:N-1로 치우치게 되기 때문입니다...\n"
    "User: 아, 그렇다면 무작위(Randomized)로 피벗을 고르는 대신, 중간값(Median-of-Three) 방법을 사용하면 시간 복잡도를 평균적으로 안전하게 유지하면서도 오버헤드를 낮추는 가설을 세울 수 있을 것 같은데, 이 두 방법의 성능 차이를 이론적으로 증명하는 방향에 대해 알려줘."
)

# 예제 대화 로드 UI
col_ex1, col_ex2, col_ex3 = st.columns([1, 1, 2])
with col_ex1:
    if st.button("🚨 의존형 대화 예제 로드", use_container_width=True, help="수동적이고 통째로 짜달라는 식의 대화 예제를 입력란에 주입합니다."):
        # text_area의 key에 직접 값 할당
        st.session_state['log_input_widget'] = example_dependent
with col_ex2:
    if st.button("👑 주도형 대화 예제 로드", use_container_width=True, help="스스로 가설을 제시하고 깊이 있게 질문하는 대화 예제를 입력란에 주입합니다."):
        # text_area의 key에 직접 값 할당
        st.session_state['log_input_widget'] = example_self_directed

# 대화 입력 필드 설정
log_input = st.text_area(
    "AI 대화 로그 입력란",
    height=250,
    placeholder="여기에 복사한 AI 대화 로그를 붙여넣어 주세요.\n(또는 위쪽의 예제 로드 버튼을 눌러 테스트해 보실 수 있습니다.)",
    key="log_input_widget"
)

# 자기보고 UI: 결과물을 AI와 직접 비교할 수 없는 케이스(D=디자인, 수강, 시험대비)만 노출
case = st.session_state["case"]
uses_self_report = case.get("output_type") in (None, "D")
uses_code_compare = case.get("output_type") == "B"
uses_text_compare = case.get("output_type") == "A"
uses_math_compare = case.get("output_type") == "C"

adoption_choice = None
revision_count = 0
# C(물리)는 수식 파싱 실패 시 이 값으로 폴백해야 하므로, 항상 함께 표시한다.
if uses_self_report or uses_math_compare:
    st.markdown("##### 📝 자기보고: AI 결과물 처리 방식")
    adoption_choice = st.radio(
        "AI가 만든 결과물을 어떻게 처리했나요?",
        ["그대로 채택", "일부 수정", "전면 재작업"],
        index=None,
        key="adoption_choice_widget",
    )
    revision_count = st.number_input(
        "수정을 요청한 프롬프트 횟수",
        min_value=0,
        step=1,
        value=0,
        key="revision_count_widget",
    )

ai_code = ""
student_code = ""
if uses_code_compare:
    st.markdown("##### 📝 결과물 비교: AI가 제시한 코드 vs 학생 최종 코드")
    ai_code = st.text_area(
        "AI가 제시한 코드",
        height=200,
        placeholder="AI가 처음 제시한 코드를 붙여넣어 주세요.",
        key="ai_code_widget",
    )
    student_code = st.text_area(
        "학생 최종 코드",
        height=200,
        placeholder="실제로 제출/사용한 최종 코드를 붙여넣어 주세요.",
        key="student_code_widget",
    )

ai_text = ""
student_text = ""
if uses_text_compare:
    st.markdown("##### 📝 결과물 비교: AI 초안 vs 학생 최종 제출문")
    ai_text = st.text_area(
        "AI 초안",
        height=200,
        placeholder="AI가 처음 제시한 초안(글)을 붙여넣어 주세요.",
        key="ai_text_widget",
    )
    student_text = st.text_area(
        "학생 최종 제출문",
        height=200,
        placeholder="실제로 제출한 최종 글을 붙여넣어 주세요.",
        key="student_text_widget",
    )

ai_final_formula = ""
student_final_formula = ""
ai_solution_text = ""
student_solution_text = ""
if uses_math_compare:
    st.markdown("##### 📝 결과물 비교: 수식 동치 판정 + 전개 단계 수")
    st.caption(
        "곱셈은 반드시 `*`로 써주세요(예: `2*a*s`, `2as`는 인식되지 않습니다). "
        "최종 수식/답은 `=`가 포함된 한 줄로 입력해 주세요. "
        "수식 인식에 실패하면 위 자기보고 응답으로 자동 대체됩니다."
    )
    formula_col1, formula_col2 = st.columns(2)
    with formula_col1:
        ai_final_formula = st.text_input(
            "AI 최종 수식/답",
            placeholder="예: F = m*a",
            key="ai_final_formula_widget",
        )
    with formula_col2:
        student_final_formula = st.text_input(
            "학생 최종 수식/답",
            placeholder="예: F = m*a",
            key="student_final_formula_widget",
        )
    ai_solution_text = st.text_area(
        "AI 전체 풀이 과정",
        height=200,
        placeholder="AI가 제시한 전체 풀이 과정을 줄바꿈으로 구분해 붙여넣어 주세요.",
        key="ai_solution_text_widget",
    )
    student_solution_text = st.text_area(
        "학생 전체 풀이 과정",
        height=200,
        placeholder="실제로 작성한 전체 풀이 과정을 줄바꿈으로 구분해 붙여넣어 주세요.",
        key="student_solution_text_widget",
    )

# 분석 실행 버튼
if st.button("⚡ Gemini AI 교차 분석 시작", type="primary", use_container_width=True):
    if not log_input.strip():
        st.error("분석할 대화 로그를 입력해 주세요!")
    elif (uses_self_report or uses_math_compare) and adoption_choice is None:
        st.error("자기보고 항목(AI 결과물 처리 방식)을 선택해 주세요!")
    elif uses_code_compare and (not ai_code.strip() or not student_code.strip()):
        st.error("AI가 제시한 코드와 학생 최종 코드를 모두 입력해 주세요!")
    elif uses_text_compare and (not ai_text.strip() or not student_text.strip()):
        st.error("AI 초안과 학생 최종 제출문을 모두 입력해 주세요!")
    elif uses_math_compare and (
        not ai_final_formula.strip()
        or not student_final_formula.strip()
        or not ai_solution_text.strip()
        or not student_solution_text.strip()
    ):
        st.error("AI/학생 최종 수식과 전체 풀이 과정을 모두 입력해 주세요!")
    else:
        with st.spinner("Gemini API와 통신하여 대화 기록 속의 메타인지 성향을 정밀 분석 중입니다..."):
            try:
                self_report = (
                    {"adoption_choice": adoption_choice, "revision_count": revision_count}
                    if (uses_self_report or uses_math_compare)
                    else None
                )
                code_pair = (
                    {"ai_code": ai_code, "student_code": student_code}
                    if uses_code_compare
                    else None
                )
                text_pair = (
                    {"ai_text": ai_text, "student_text": student_text}
                    if uses_text_compare
                    else None
                )
                math_pair = (
                    {
                        "ai_final_formula": ai_final_formula,
                        "student_final_formula": student_final_formula,
                        "ai_solution_text": ai_solution_text,
                        "student_solution_text": student_solution_text,
                    }
                    if uses_math_compare
                    else None
                )
                # utils/logic_step2.py 모듈 호출
                analysis_res = analyze_student_log(
                    case, log_input, self_report, code_pair, text_pair, math_pair
                )
                
                # 결과 세션 저장
                st.session_state['step2_result'] = analysis_res
                st.session_state['step2_done'] = True

                # Supabase에 응답 영구 저장
                try:
                    save_step2_response(
                        session_id=st.session_state['session_id'],
                        case_id=st.session_state['case_id'],
                        health_score=analysis_res['health_score'],
                        components=analysis_res.get('components'),
                        risk_highlight=analysis_res['risk_highlight'],
                        analysis_summary=analysis_res['analysis_summary'],
                    )
                except Exception as db_e:
                    st.error(f"응답 저장 중 오류가 발생했습니다(분석 결과는 정상 표시됩니다): {db_e}")

            except Exception as e:
                st.error(f"분석 중 오류가 발생했습니다: {str(e)}")

# 분석 결과 렌더링
if st.session_state['step2_done'] and st.session_state['step2_result'] is not None:
    res = st.session_state['step2_result']
    score = res["health_score"]
    
    st.write("---")
    st.markdown("### 📊 분석 진단 리포트")
    
    # 1. 메타인지 건강도 점수 및 등급 렌더링
    if score >= 80:
        status_text = "💚 안전: 건강한 AI 협업 상태"
        border_color = "#10B981"
        bg_color = "rgba(16, 185, 129, 0.1)"
    elif score >= 50:
        status_text = "💛 주의: 무의식적 의존 경향 감지"
        border_color = "#F59E0B"
        bg_color = "rgba(245, 158, 11, 0.1)"
    else:
        status_text = "🚨 위험: 극심한 인지적 구두쇠 상태"
        border_color = "#EF4444"
        bg_color = "rgba(239, 68, 68, 0.1)"
        
    metric_col, desc_col = st.columns([1, 2])
    
    with metric_col:
        st.markdown(f"""
        <div class='metric-container' style='border-left-color: {border_color}; background-color: {bg_color};'>
            <div>
                <div class='metric-label'>{status_text}</div>
                <div class='metric-value'>{score} <span style='font-size: 1.2rem; color: #6B7280;'>/ 100 점</span></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        # HTML 프로그레스 바
        st.markdown(f"""
        <div style="background-color: #E5E7EB; border-radius: 9999px; height: 10px; width: 100%; margin-bottom: 20px;">
            <div style="background-color: {border_color}; width: {score}%; height: 100%; border-radius: 9999px;"></div>
        </div>
        """, unsafe_allow_html=True)
        
    with desc_col:
        st.markdown("##### 📌 AI 분석 종합 의견")
        st.write(res["analysis_summary"])
        
    # 2. 치명적 의존 문장 렌더링 (점수가 낮거나 감점 요소가 있을 때 경고창 부각)
    if res["risk_highlight"] and res["risk_highlight"].strip():
        st.markdown(f"""
        <div class='risk-box'>
            <div class='risk-title'>🚨 감점 요인 - 치명적 의존 의심 구문</div>
            <div class='risk-text'>"{res['risk_highlight']}"</div>
        </div>
        """, unsafe_allow_html=True)
        
    # 3. 3단계 퀴즈 대상 CS 핵심 개념 노출
    st.write("---")
    st.markdown("### 🎯 3단계 퀴즈용 핵심 CS 개념 추출")
    st.write("학생의 대화 패턴에서 검증이 가장 시급하다고 분류된 컴퓨터공학(CS) 핵심 개념 단어는 다음과 같습니다. 이 개념을 기반으로 3단계 동적 검증 퀴즈가 즉석 출제됩니다.")
    
    st.markdown(f"<p style='text-align: center; margin: 1.5rem 0;'><span class='concept-badge'>{res['target_concept']}</span></p>", unsafe_allow_html=True)
    
    # 1단계 결과와 매핑 확인 안내 (보너스 메타 정보 제공)
    if st.session_state.get('step1_done'):
        st.toast(f"1단계 사전진단 결과({st.session_state['step1_persona']})와 2단계 로그 점수({score}점)의 정합성을 비교해 보세요!")

    # 3단계 이동 버튼
    btn_col1, btn_col2, btn_col3 = st.columns([1, 2, 1])
    with btn_col2:
        st.markdown("<p style='text-align: center; color: #6B7280; font-size: 0.9rem; margin-top: 1rem;'>추출된 CS 핵심 개념으로 진짜 본인의 지식이 되었는지 검증해 보세요.</p>", unsafe_allow_html=True)
        if st.button("🎯 3단계: 적응형 전이 검증(퀴즈) 시작", type="primary", use_container_width=True):
            st.switch_page("pages/3_전이검증.py")

# 사이드바 설정
st.sidebar.markdown("### 🧠 CogniTrieve 네비게이터")
if st.session_state.get('step1_done'):
    st.sidebar.success(f"📋 1단계: 사전진단 ({st.session_state['step1_persona']})")
st.sidebar.success("🔍 2단계: 로그분석 진행 중")
if st.session_state['step2_done']:
    st.sidebar.markdown(f"**로그 분석 점수**: `{score} 점`")
    st.sidebar.markdown(f"**퀴즈 출제 개념**: `{res['target_concept']}`")

st.sidebar.info(
    "👉 **진행 순서**:\n"
    "1. 📋 사전진단 (완료)\n"
    "2. **🔍 로그분석 (완료)**\n"
    "3. 🎯 전이검증"
)
