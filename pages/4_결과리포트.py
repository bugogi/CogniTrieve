import streamlit as st
import sys
import html
import os

import pandas as pd

# root 디렉토리를 path에 추가하여 utils 패키지가 정상 임포트되도록 보장
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.result_report import build_report, is_report_ready

# 페이지 설정
st.set_page_config(
    page_title="결과 리포트 - CogniTrieve",
    page_icon="📄",
    layout="wide"
)

# 동의/세션 가드: 홈 화면에서 동의 및 케이스 선택을 마치지 않은 경우 진행 차단
if not st.session_state.get("consented") or not st.session_state.get("session_id"):
    st.warning("⚠️ 먼저 홈 화면에서 동의 및 케이스 선택을 완료해 주세요.")
    if st.button("🏠 홈으로 이동", type="primary"):
        st.switch_page("app.py")
    st.stop()

# 3단계 완료 가드: 결과 리포트는 3단계를 마친 뒤에만 열린다
if not is_report_ready(st.session_state):
    st.warning("⚠️ 결과 리포트는 3단계 전이검증을 마친 뒤에 열립니다. 퀴즈를 맞히거나 '여기서 마무리'를 선택해 주세요.")
    if st.button("🎯 3단계: 전이검증 페이지로 가기", type="primary"):
        st.switch_page("pages/3_전이검증.py")
    st.stop()

report = build_report(st.session_state)
step1, step2, step3 = report["step1"], report["step2"], report["step3"]

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

    .report-card {
        background-color: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 12px;
        padding: 20px;
        height: 100%;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.03);
    }

    .report-step {
        display: inline-block;
        background-color: #EEF2FF;
        color: #4F46E5;
        font-weight: 700;
        padding: 3px 10px;
        border-radius: 6px;
        font-size: 0.8rem;
        margin-bottom: 0.6rem;
    }

    .report-label {
        color: #6B7280;
        font-size: 0.9rem;
    }

    .report-value {
        font-size: 1.6rem;
        font-weight: 800;
        color: #1F2937;
        margin-bottom: 0.3rem;
    }

    .report-badge {
        display: inline-flex;
        background-color: #ECFEFF;
        color: #0E7490;
        font-weight: 700;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.9rem;
        margin: 0 6px 6px 0;
        border: 1px solid #A5F3FC;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='page-title'>📄 나의 결과 리포트</h1>", unsafe_allow_html=True)
st.markdown(
    "<p class='page-subtitle'>사전진단 → 로그분석 → 전이검증까지, 이번 세션에서 확인한 나의 AI 활용 습관을 한눈에 정리했습니다.</p>",
    unsafe_allow_html=True,
)

# 단계별 요약 카드
col1, col2, col3 = st.columns(3)

with col1:
    persona_label = html.escape(step1["title"] or step1["persona"] or "-")
    icon = step1["icon"] or "📋"
    st.markdown(f"""
    <div class='report-card'>
        <span class='report-step'>1단계 사전진단</span>
        <div class='report-label'>자가진단 페르소나</div>
        <div class='report-value'>{icon} {persona_label}</div>
        <div class='report-label'>자가진단 총점 <b>{step1['total_score'] if step1['total_score'] is not None else '-'}</b> / {step1['max_score']}점</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    score = step2["health_score"]
    st.markdown(f"""
    <div class='report-card'>
        <span class='report-step'>2단계 로그분석</span>
        <div class='report-label'>메타인지 Health Score</div>
        <div class='report-value'>{score if score is not None else '-'} <span style='font-size: 1rem; color: #6B7280;'>/ 100점</span></div>
        <div class='report-label'>검증 대상 개념 <b>{html.escape(step2['target_concept'] or '-')}</b></div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class='report-card'>
        <span class='report-step'>3단계 전이검증</span>
        <div class='report-label'>완료 방식</div>
        <div class='report-value'>{step3['done_reason_label']}</div>
        <div class='report-label'>푼 퀴즈 <b>{step3['quiz_count']}</b>개 · 정답 <b>{step3['correct_count']}</b>개</div>
    </div>
    """, unsafe_allow_html=True)

st.write("")

# 교차검증: 나의 인식 vs 실제 행동 (판정 없이 나란히 보여주기 + 해석 안내)
st.markdown("### 🧭 교차검증: 나의 인식 vs 실제 행동")
left, right = st.columns(2)
with left:
    st.markdown("**1단계 · 내가 생각하는 나**")
    st.markdown(f"- 페르소나: **{step1['persona'] or '-'}**")
    st.markdown(f"- 자가진단 총점: **{step1['total_score'] if step1['total_score'] is not None else '-'} / {step1['max_score']}점**")
    if step1["description"]:
        with st.expander("페르소나 설명 다시 보기"):
            st.write(step1["description"])
with right:
    st.markdown("**2단계 · 대화 로그에 드러난 나**")
    st.markdown(f"- Health Score: **{score if score is not None else '-'} / 100점**")
    for comp in step2["components"]:
        st.markdown(f"- {comp['label']}: {comp['value']}점")

st.info(report["cross_check"]["guide"])
st.caption(report["cross_check"]["note"])

if step2["analysis_summary"]:
    st.markdown("##### 📌 2단계 AI 분석 종합 의견")
    st.write(step2["analysis_summary"])

st.write("---")

# 3단계 상세
st.markdown("### 🎯 3단계 전이검증 기록")
if step3["rows"]:
    st.dataframe(pd.DataFrame(step3["rows"]), hide_index=True, use_container_width=True)

st.markdown("**🏆 획득 배지**")
if step3["badges"]:
    st.markdown(
        "".join(f"<span class='report-badge'>#{html.escape(kw)}</span>" for kw in step3["badges"]),
        unsafe_allow_html=True,
    )
else:
    st.caption("이번 세션에서는 획득한 배지가 없습니다. 다음 진단에서 다시 도전해 보세요!")

st.write("---")
st.caption("다른 케이스로 다시 진단하려면 홈 화면 사이드바의 '처음부터 다시 시작'을 눌러 주세요. 이번 세션의 응답은 그대로 보존됩니다.")
if st.button("🏠 홈으로 이동"):
    st.switch_page("app.py")

# 사이드바 설정
st.sidebar.markdown("### 🧠 CogniTrieve 네비게이터")
if st.session_state.get('step1_done'):
    st.sidebar.success(f"📋 1단계: 사전진단 ({st.session_state['step1_persona']})")
if st.session_state.get('step2_done'):
    st.sidebar.success(f"🔍 2단계: 로그분석 완료 (`{st.session_state['step2_result']['health_score']} 점`)")
st.sidebar.success("🎯 3단계: 전이 검증 완료")
st.sidebar.info("📄 결과 리포트 확인 중")
