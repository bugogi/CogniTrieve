import streamlit as st

# 페이지 기본 설정
st.set_page_config(
    page_title="CogniTrieve - 메타인지 AI 진단 파이프라인",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 커스텀 CSS 주입 (깔끔하고 세련된 UI 스타일링)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700;900&display=swap');
    
    html, body, [data-testid="stSidebar"] {
        font-family: 'Noto Sans KR', sans-serif;
    }
    
    /* 헤더 스타일링 */
    .main-title {
        font-size: 3rem;
        font-weight: 900;
        background: linear-gradient(135deg, #4F46E5, #06B6D4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
        text-align: center;
    }
    
    .main-subtitle {
        font-size: 1.25rem;
        color: #4B5563;
        text-align: center;
        margin-bottom: 3rem;
        font-weight: 400;
    }
    
    /* 카드 디자인 */
    .card {
        background-color: #F9FAFB;
        border-radius: 12px;
        padding: 24px;
        border: 1px solid #E5E7EB;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        height: 100%;
        margin-bottom: 1.5rem;
    }
    .card:hover {
        transform: translateY(-4px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        border-color: #3B82F6;
    }
    
    .card-step {
        display: inline-block;
        background: linear-gradient(135deg, #3B82F6, #1D4ED8);
        color: white;
        font-weight: 700;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.85rem;
        margin-bottom: 1rem;
    }
    
    .card-title {
        font-size: 1.35rem;
        font-weight: 700;
        color: #111827;
        margin-bottom: 0.75rem;
    }
    
    .card-desc {
        font-size: 0.95rem;
        color: #4B5563;
        line-height: 1.6;
    }
    
    /* 핵심 강조 박스 */
    .highlight-box {
        background: linear-gradient(135deg, #EEF2F6, #E0E7FF);
        border-left: 6px solid #4F46E5;
        padding: 20px;
        border-radius: 0 12px 12px 0;
        margin-top: 2rem;
        margin-bottom: 2rem;
    }
    
    .highlight-title {
        font-weight: 700;
        color: #1E1B4B;
        font-size: 1.1rem;
        margin-bottom: 0.5rem;
    }
    
    .highlight-desc {
        color: #312E81;
        font-size: 0.95rem;
        line-height: 1.6;
    }
</style>
""", unsafe_allow_html=True)

# 홈 화면 콘텐츠
st.markdown("<h1 class='main-title'>CogniTrieve</h1>", unsafe_allow_html=True)
st.markdown("<p class='main-subtitle'>메타인지 기반 AI 활용 자가진단 및 학습 검증 파이프라인</p>", unsafe_allow_html=True)

# 인트로덕션 및 핵심 철학 소개
st.markdown("""
<div class='highlight-box'>
    <div class='highlight-title'>💡 인지적 구두쇠(Cognitive Miser) 방지와 '바람직한 마찰(Desirable Difficulty)'</div>
    <div class='highlight-desc'>
        인공지능(AI) 비서의 보편화로 개발 공부가 쉬워진 오늘날, 많은 학습자들이 동작 원리를 완전히 이해하지 못한 채 
        코드를 단순히 복사해서 붙여넣는 <b>'인지적 구두쇠'</b> 행동에 빠지고 있습니다.<br>
        <b>CogniTrieve</b>는 학습 과정에 의도적으로 유익한 장벽인 <b>'바람직한 마찰'</b>을 설계하여, 
        학습자가 본인의 AI 의존도를 자가 진단하고 AI와의 대화 로그를 기반으로 지식의 전이도를 검증할 수 있도록 돕는 메타인지 자극 플랫폼입니다.
    </div>
</div>
""", unsafe_allow_html=True)

st.write("---")

# 3단계 파이프라인 구조 시각화
st.markdown("<h3 style='text-align: center; margin-bottom: 2rem; font-weight:700; color:#1F2937;'>🧠 CogniTrieve 3단계 검증 파이프라인</h3>", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div class='card'>
        <span class='card-step'>1단계</span>
        <div class='card-title'>📋 사전 진단 (Pre-Diagnosis)</div>
        <div class='card-desc'>
            5개의 리커트 척도 질문을 통해 자신의 <b>AI 의존 성향</b>을 진단합니다. 
            단순 점수 합산이 아닌 핵심 설계/디버깅 역량 결핍을 감지하는 <b>과락(Hotspot) 로직</b>을 적용하여 
            4가지 메타인지 페르소나를 정확히 산출합니다.
        </div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class='card'>
        <span class='card-step'>2단계</span>
        <div class='card-title'>🔍 로그 교차 검증 (Log Analysis)</div>
        <div class='card-desc'>
            평소 AI와 나눈 실제 코딩 질문 및 대화 로그를 복사-붙여넣기하여 검증을 요청합니다. 
            <b>Gemini API</b>가 대화 패턴을 정밀 분석해 '통째로 짜줘' 식의 수동적인 태도를 정량 점수로 채점하고, 
            추후 역량 검증에 필요한 <b>핵심 CS 개념</b>을 추출합니다.
        </div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class='card'>
        <span class='card-step'>3단계</span>
        <div class='card-title'>🎯 적응형 학습 전이 검증 (Quiz)</div>
        <div class='card-desc'>
            2단계에서 분석된 핵심 CS 개념을 바탕으로 생성되는 맞춤형 <b>1문장 서술형 동적 퀴즈</b>를 해결합니다. 
            정답 단어가 포함되어 있는지 백엔드에서 정밀하게 판별하며, 정답 시 <b>핵심 키워드 해시태그 배지</b>를 누적 보상으로 제공합니다.
        </div>
    </div>
    """, unsafe_allow_html=True)

st.write("")
st.write("")

# 시작하기 버튼 세션 및 레이아웃
btn_col1, btn_col2, btn_col3 = st.columns([1, 2, 1])
with btn_col2:
    st.markdown("<p style='text-align: center; color: #6B7280; font-size: 0.95rem; margin-bottom:0.5rem;'>준비되셨나요? 첫 단계인 메타인지 사전 진단을 시작해 보세요.</p>", unsafe_allow_html=True)
    if st.button("🚀 사전 진단 시작하기", use_container_width=True, type="primary"):
        st.switch_page("pages/1_사전진단.py")

# 사이드바 안내 정보
st.sidebar.markdown("### 🧠 CogniTrieve 네비게이터")
st.sidebar.info(
    "메뉴나 화면 하단의 버튼을 통해 단계별 파이프라인을 차례로 진행해 주시기 바랍니다.\n\n"
    "👉 **진행 순서**:\n"
    "1. 📋 사전진단\n"
    "2. 🔍 로그분석\n"
    "3. 🎯 전이검증"
)
