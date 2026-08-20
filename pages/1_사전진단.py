import streamlit as st
import sys
import os

# root 디렉토리를 path에 추가하여 utils 패키지가 정상 임포트되도록 보장
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.db_handler import save_step1_response
from utils.logic_step1 import calculate_persona

# 페이지 설정
st.set_page_config(
    page_title="1단계: 사전진단 - CogniTrieve",
    page_icon="📋",
    layout="wide"
)

# 동의/세션 가드: 홈 화면에서 동의 및 케이스 선택을 마치지 않은 경우 진행 차단
if (
    not st.session_state.get("consented")
    or not st.session_state.get("session_id")
    or not st.session_state.get("case")
):
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
    
    .question-box {
        background-color: #F9FAFB;
        border-radius: 8px;
        padding: 20px;
        border: 1px solid #E5E7EB;
        margin-bottom: 1.5rem;
    }
    
    .question-text {
        font-size: 1.1rem;
        font-weight: 600;
        color: #1F2937;
        margin-bottom: 0.75rem;
    }
    
    .result-card {
        border-radius: 12px;
        padding: 30px;
        color: #1F2937;
        margin-top: 2rem;
        margin-bottom: 2rem;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
    }
    
    .result-header {
        display: flex;
        align-items: center;
        gap: 12px;
        font-size: 1.8rem;
        font-weight: 800;
        margin-bottom: 1rem;
    }
    
    .result-score {
        font-size: 1.25rem;
        font-weight: 600;
        margin-bottom: 1.5rem;
        background-color: rgba(255, 255, 255, 0.5);
        display: inline-block;
        padding: 4px 12px;
        border-radius: 6px;
    }
    
    .result-body {
        font-size: 1.05rem;
        line-height: 1.7;
    }
</style>
""", unsafe_allow_html=True)

# 페이지 헤더
st.markdown("<h1 class='page-title'>📋 1단계: 메타인지 자가 사전진단</h1>", unsafe_allow_html=True)
st.markdown(
    "<p class='page-subtitle'>평소 AI(ChatGPT, Claude, Gemini 등)를 과제·학습 과정에서 어떻게 활용하고 있는지 솔직하게 답변해 주세요.</p>",
    unsafe_allow_html=True
)

st.write("---")

# 리커트 척도 매핑 딕셔너리
options_map = {
    "1점 (전혀 아니다)": 1,
    "2점 (그렇지 않다)": 2,
    "3점 (보통이다)": 3,
    "4점 (그렇다)": 4,
    "5점 (매우 그렇다)": 5
}

# 선택된 케이스의 문항을 동적으로 렌더링 (case_id별 텍스트는 cases 테이블 기준, docs/07 3절)
case = st.session_state["case"]
questions = [
    {"id": f"q{i}", "text": f"질문 {i}: {text}"}
    for i, text in enumerate(case["questions"], start=1)
]

# 세션 상태 초기화 (결과를 유지하기 위함)
if 'step1_results' not in st.session_state:
    st.session_state['step1_results'] = None

# 설문 폼 구성
with st.form("diagnosis_form"):
    answers = {}
    
    for q in questions:
        st.markdown(f"<div class='question-box'><div class='question-text'>{q['text']}</div>", unsafe_allow_html=True)
        # 기본값을 '3점 (보통이다)'으로 설정하여 편안하게 선택할 수 있게 함
        answers[q['id']] = st.radio(
            label=q['text'],
            options=list(options_map.keys()),
            index=2,
            horizontal=True,
            key=f"widget_{q['id']}",
            label_visibility="collapsed"
        )
        st.markdown("</div>", unsafe_allow_html=True)
        
    submit_button = st.form_submit_button("🩺 사전 진단 결과 분석하기", use_container_width=True)

# 폼 제출 시 비즈니스 로직 수행
if submit_button:
    # 텍스트 형태의 선택지를 정수 점수로 변환
    q1_score = options_map[answers['q1']]
    q2_score = options_map[answers['q2']]
    q3_score = options_map[answers['q3']]
    q4_score = options_map[answers['q4']]
    q5_score = options_map[answers['q5']]
    
    # logic_step1 모듈을 통해 결과 계산
    diag_result = calculate_persona(case, q1_score, q2_score, q3_score, q4_score, q5_score)
    
    # 세션 상태에 저장하여 다음 페이지 및 파이프라인에서 유지
    st.session_state['step1_done'] = True
    st.session_state['step1_persona'] = diag_result['persona']
    st.session_state['step1_total_score'] = diag_result['total_score']
    st.session_state['step1_results'] = diag_result

    # Supabase에 응답 영구 저장
    try:
        save_step1_response(
            session_id=st.session_state['session_id'],
            case_id=st.session_state['case_id'],
            q1=q1_score, q2=q2_score, q3=q3_score, q4=q4_score, q5=q5_score,
            total_score=diag_result['total_score'],
            persona=diag_result['persona'],
        )
    except Exception as e:
        st.error(f"응답 저장 중 오류가 발생했습니다(진단 결과는 정상 표시됩니다): {e}")

# 결과 렌더링
if st.session_state['step1_results'] is not None:
    res = st.session_state['step1_results']
    
    # 페르소나별 테마 백그라운드 색상 계산 (투명도 조절 버전)
    bg_color_map = {
        "맹목적 의존형": "rgba(239, 68, 68, 0.15)",
        "효율 중심형": "rgba(245, 158, 11, 0.15)",
        "방어형": "rgba(59, 130, 246, 0.15)",
        "자기 주도형": "rgba(16, 185, 129, 0.15)"
    }
    bg_color = bg_color_map.get(res['persona'], "rgba(107, 114, 128, 0.15)")
    
    st.write("---")
    st.markdown(f"""
    <div class='result-card' style='background-color: {bg_color}; border: 2px solid {res['color']};'>
        <div class='result-header' style='color: {res['color']};'>
            <span>{res['icon']}</span>
            <span>진단 결과: {res['title']}</span>
        </div>
        <div class='result-score' style='color: #1F2937;'>
            📊 메타인지 지수 총점: <b>{res['total_score']} / 25 점</b>
        </div>
        <div class='result-body'>
            {res['description']}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 2단계 이동 권장 메세지
    st.info(
        "💡 사전 진단이 완료되었습니다! 다음 단계인 **'2단계: 로그 교차 검증'**에서는 실제 AI와의 대화 기록을 분석하여 "
        "메타인지 성향을 정량적으로 교차 확인하고, 취약한 핵심 개념을 파악하게 됩니다."
    )
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔍 2단계 로그 교차 검증 페이지로 이동", use_container_width=True, type="primary"):
            st.switch_page("pages/2_로그분석.py")

# 사이드바 설정
st.sidebar.markdown("### 🧠 CogniTrieve 네비게이터")
st.sidebar.success("📋 1단계: 사전진단 진행 중")
if st.session_state['step1_results'] is not None:
    st.sidebar.markdown(f"**현재 진단 페르소나**:\n`{st.session_state['step1_persona']}`")

st.sidebar.info(
    "👉 **진행 순서**:\n"
    "1. **📋 사전진단 (완료)**\n"
    "2. 🔍 로그분석\n"
    "3. 🎯 전이검증"
)
