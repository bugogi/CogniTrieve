import streamlit as st
import sys
import os

# root 디렉토리를 path에 추가하여 utils 패키지가 정상 임포트되도록 보장
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logic_step3 import generate_adaptive_quiz, verify_answer

# 페이지 설정
st.set_page_config(
    page_title="3단계: 전이검증 - CogniTrieve",
    page_icon="🎯",
    layout="wide"
)

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
    
    /* 퀴즈 카드 */
    .quiz-card {
        background: linear-gradient(135deg, #FAFAFE, #F5F3FF);
        border: 1px solid #DDD6FE;
        border-left: 8px solid #8B5CF6;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 10px rgba(139, 92, 246, 0.05);
    }
    
    .quiz-type-badge {
        display: inline-block;
        background-color: #EDE9FE;
        color: #6D28D9;
        font-weight: 700;
        padding: 4px 12px;
        border-radius: 6px;
        font-size: 0.85rem;
        margin-bottom: 1rem;
        border: 1px solid #DDD6FE;
    }
    
    .quiz-question {
        font-size: 1.3rem;
        font-weight: 800;
        color: #1E1B4B;
        line-height: 1.5;
        margin-bottom: 1rem;
    }
    
    /* 획득 키워드 뱃지 보관함 */
    .badge-shelf {
        background-color: #F9FAFB;
        border: 1px dashed #D1D5DB;
        border-radius: 12px;
        padding: 20px;
        margin-top: 2rem;
    }
    
    .shelf-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #374151;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .badge-container {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
    }
    
    .hashtag-badge {
        display: inline-flex;
        align-items: center;
        background: linear-gradient(135deg, #06B6D4, #0891B2);
        color: white;
        font-weight: 700;
        padding: 6px 14px;
        border-radius: 9999px;
        font-size: 0.95rem;
        box-shadow: 0 4px 6px -1px rgba(6, 182, 212, 0.2);
        border: 1px solid rgba(255, 255, 255, 0.2);
        transition: all 0.2s ease;
    }
    
    .hashtag-badge:hover {
        transform: scale(1.05);
        box-shadow: 0 6px 10px -1px rgba(6, 182, 212, 0.3);
    }
    
    .empty-shelf {
        color: #9CA3AF;
        font-size: 0.95rem;
        font-style: italic;
    }
    
    /* 타겟 개념 배너 */
    .concept-banner {
        background: #EEF2F6;
        border-radius: 8px;
        padding: 12px 18px;
        font-weight: 600;
        color: #4F46E5;
        display: inline-block;
        margin-bottom: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

# 페이지 헤더
st.markdown("<h1 class='page-title'>🎯 3단계: 적응형 학습 전이 검증 (Transfer Verification)</h1>", unsafe_allow_html=True)
st.markdown(
    "<p class='page-subtitle'>이전 단계에서 분석된 핵심 개념을 바탕으로 생성된 퀴즈를 풀어보세요.<br>"
    "단순 코드 복사에서 벗어나 실제 개념을 자신의 머리로 완전히 이해했는지 즉석에서 스스로 진증합니다.</p>", 
    unsafe_allow_html=True
)

st.write("---")

# 획득한 키워드 뱃지 보관함 세션 초기화 (전체 세션에 영구 보관용)
if 'acquired_keywords' not in st.session_state:
    st.session_state['acquired_keywords'] = []

# 2단계 결과 데이터가 세션에 존재하지 않는 경우 진입 차단 및 경고 처리
step2_done = st.session_state.get('step2_done', False)
step2_result = st.session_state.get('step2_result', None)

if not step2_done or step2_result is None:
    st.warning("⚠️ 아직 2단계 대화 로그 분석이 완료되지 않았습니다! 2단계를 먼저 진행하여 핵심 분석 및 검증 개념을 도출해 주세요.")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔍 2단계: 로그분석 페이지로 가기", type="primary", use_container_width=True):
            st.switch_page("pages/2_로그분석.py")
            
    st.stop()

# 2단계에서 도출된 개념 및 문장 불러오기
target_concept = step2_result.get('target_concept', '컴퓨터공학 기초')
risk_highlight = step2_result.get('risk_highlight', '')

# 상단 핵심 개념 정보 알림
st.markdown(f"""
<div class='concept-banner'>
    💡 검증 대상 CS 핵심 개념: <b>{target_concept}</b>
</div>
""", unsafe_allow_html=True)

# 퀴즈 및 답변 제출 상태 관리용 세션 변수 초기화
if 'step3_quiz' not in st.session_state:
    st.session_state['step3_quiz'] = None

if 'step3_submitted' not in st.session_state:
    st.session_state['step3_submitted'] = False

if 'step3_is_correct' not in st.session_state:
    st.session_state['step3_is_correct'] = False

if 'last_target_concept' not in st.session_state:
    st.session_state['last_target_concept'] = target_concept

# 2단계 핵심 개념이 이전 문제 생성 시점과 달라졌다면 퀴즈 초기화
if st.session_state['last_target_concept'] != target_concept:
    st.session_state['step3_quiz'] = None
    st.session_state['step3_submitted'] = False
    st.session_state['step3_is_correct'] = False
    st.session_state['last_target_concept'] = target_concept

# 퀴즈 생성 (세션에 캐싱하여 리런 시 재생성 방지)
if st.session_state['step3_quiz'] is None:
    with st.spinner("Gemini AI가 당신의 메타인지를 도울 서술형 퀴즈를 생성하고 있습니다..."):
        try:
            quiz_data = generate_adaptive_quiz(target_concept, risk_highlight)
            st.session_state['step3_quiz'] = quiz_data
        except Exception as e:
            st.error(f"퀴즈 생성 중 오류 발생: {str(e)}")
            st.stop()

quiz = st.session_state['step3_quiz']

# 퀴즈 UI 렌더링
st.markdown(f"""
<div class='quiz-card'>
    <div class='quiz-type-badge'>🧩 {quiz['quiz_type']} 퀴즈</div>
    <div class='quiz-question'>{quiz['dynamic_question']}</div>
    <div style='color: #6B7280; font-size: 0.85rem;'>* 예상 핵심 개념 및 유의어들이 한 단어 이상 꼭 포함되어야 올바른 서술로 자동 판정됩니다.</div>
</div>
""", unsafe_allow_html=True)

# 답변 입력 양식 (st.text_input 사용)
# 상태를 일관되게 관리하기 위해 default 값을 세션에서 가져올 수도 있으나 단순한 텍스트 입력으로 구성
student_answer = st.text_input(
    "여기에 퀴즈에 대한 정답이나 설명을 작성하세요:",
    placeholder="예시) 포인터는 메모리 공간의 실제 주소값을 담고 있어 직접 제어가 가능합니다.",
    key="student_answer_widget"
)

col_submit, col_reset, _ = st.columns([2, 1, 3])

with col_submit:
    if st.button("🚀 정답 검증 및 제출", type="primary", use_container_width=True):
        if not student_answer.strip():
            st.warning("답변을 먼저 입력해 주세요!")
        else:
            # 정답 검증 로직 수행 (순수 파이썬 알고리즘 호출)
            is_correct = verify_answer(student_answer, quiz['expected_keywords'])
            st.session_state['step3_submitted'] = True
            st.session_state['step3_is_correct'] = is_correct
            
            # 정답일 경우 세션 리스트에 키워드를 영구 저장 및 축하 풍선
            if is_correct:
                st.balloons()
                if target_concept not in st.session_state['acquired_keywords']:
                    st.session_state['acquired_keywords'].append(target_concept)

with col_reset:
    if st.button("🔄 새로운 퀴즈 출제", use_container_width=True):
        # 퀴즈 관련 상태를 모두 초기화하여 새로운 퀴즈를 강제 생성하도록 유도
        st.session_state['step3_quiz'] = None
        st.session_state['step3_submitted'] = False
        st.session_state['step3_is_correct'] = False
        st.rerun()

# 검증 피드백 출력
if st.session_state['step3_submitted']:
    st.write("---")
    if st.session_state['step3_is_correct']:
        st.success("🎉 정답입니다!")
        st.markdown(f"""
        <div style='background-color: #ECFDF5; border: 1px solid #10B981; border-radius: 8px; padding: 18px; margin-bottom: 1.5rem;'>
            <h4 style='color: #065F46; margin-top:0;'>✨ 메타인지 검증 통과!</h4>
            <p style='color: #047857; font-size: 0.95rem; margin-bottom:0;'>
                훌륭합니다! 답변 속에 핵심 개념을 지목할 수 있는 단어가 올바르게 녹아 들어가 있습니다.<br>
                이제 <b>'{target_concept}'</b> 개념은 단순 AI의 힘을 빌려 복붙한 것이 아니라 본인의 실제 지식으로 전이되었음을 스스로 검증하였습니다.
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.error("❌ 키워드 판정 보완 필요")
        st.markdown(f"""
        <div style='background-color: #FFF5F5; border: 1px solid #EF4444; border-radius: 8px; padding: 18px; margin-bottom: 1.5rem;'>
            <h4 style='color: #991B1B; margin-top:0;'>💡 조금 더 보완해 보거나 다시 시도해 볼까요?</h4>
            <p style='color: #B91C1C; font-size: 0.95rem;'>
                출제 의도에 딱 들어맞는 핵심 키워드나 원리가 답변에 포함되지 않았거나 부족해 보입니다.<br>
                기저 동작 원리를 반영하여 질문에 구체적으로 1문장 작성해 보세요! (예상 정답 키워드 중 하나 이상 포함 필요)
            </p>
            <p style='color: #4B5563; font-size: 0.85rem; margin-bottom:0;'>
                <b>Tip:</b> 2단계 분석 카드 상단의 '<b>{target_concept}</b>'을 충분히 설명할 수 있도록 용어를 의식적으로 사용해 보세요!
            </p>
        </div>
        """, unsafe_allow_html=True)

# 나의 메타 CS 뱃지 보관함 렌더링 (영구적 누적 누적 렌더링)
st.markdown("""
<div class='badge-shelf'>
    <div class='shelf-title'>🏆 나의 메타 CS 획득 배지 보관함</div>
""", unsafe_allow_html=True)

if len(st.session_state['acquired_keywords']) == 0:
    st.markdown("<p class='empty-shelf'>아직 획득한 배지가 없습니다. 퀴즈를 맞히고 첫 번째 CS 뱃지를 이곳에 획득해 보세요!</p>", unsafe_allow_html=True)
else:
    # 획득한 키워드를 예쁜 '해시태그 뱃지' 모양으로 누적 렌더링
    st.write("축하합니다! 직접 이해한 지식으로 자격을 증명하여 획득한 CS 역량 목록입니다:")
    badges_html = "<div class='badge-container'>"
    for kw in st.session_state['acquired_keywords']:
        badges_html += f"<span class='hashtag-badge'>#{kw}</span>"
    badges_html += "</div>"
    st.markdown(badges_html, unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# 사이드바 설정
st.sidebar.markdown("### 🧠 CogniTrieve 네비게이터")
if st.session_state.get('step1_done'):
    st.sidebar.success(f"📋 1단계: 사전진단 ({st.session_state['step1_persona']})")
if st.session_state.get('step2_done'):
    st.sidebar.success(f"🔍 2단계: 로그분석 완료 (`{st.session_state['step2_result']['health_score']} 점`)")

st.sidebar.info("🎯 3단계: 적응형 전이 검증 진행 중")

# 획득 배지 정보 사이드바 요약
if st.session_state['acquired_keywords']:
    st.sidebar.markdown("---")
    st.sidebar.markdown("🏅 **나의 획득 배지 수**: `" + str(len(st.session_state['acquired_keywords'])) + "개`")
    for kw in st.session_state['acquired_keywords']:
        st.sidebar.write(f"- `{kw}`")

st.sidebar.info(
    "👉 **진행 순서**:\n"
    "1. 📋 사전진단 (완료)\n"
    "2. 🔍 로그분석 (완료)\n"
    "3. **🎯 전이검증 (진행 중)**"
)
