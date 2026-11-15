import os
import sys

import altair as alt
import pandas as pd
import streamlit as st

# root 디렉토리를 path에 추가하여 utils 패키지가 정상 임포트되도록 보장
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import admin_metrics as am
from utils.db_handler import fetch_admin_rows

st.set_page_config(
    page_title="관리자 - CogniTrieve",
    page_icon="📊",
    layout="wide"
)

# 접근 제어: 현재(Phase 5 그룹 A)는 본인+교수님 2인 사용이라 인증 없이 운영한다.
# 학생 파일럿 전에 비밀번호 가드(st.secrets 기반)를 바로 이 위치 — 데이터 조회·캐시
# 호출보다 앞 — 에 추가한다(docs/10 Phase 5 그룹 B 백로그 참조).


@st.cache_data(ttl=60, show_spinner=False)
def load_frames() -> dict[str, pd.DataFrame]:
    # 캐시에는 마스킹이 끝난 DataFrame만 남는다(student_answer 원문은 build_frames에서 제거).
    return am.build_frames(fetch_admin_rows())


def _pct(value) -> str:
    return "-" if value is None or pd.isna(value) else f"{value:.0%}"


def _bar_chart(df: pd.DataFrame, category: str, value: str, title: str, sort=None, horizontal=True):
    """단일 계열 막대 차트(한 가지 색, 툴팁, 값 라벨)."""
    category_enc = alt.Y if horizontal else alt.X
    value_enc = alt.X if horizontal else alt.Y
    base = alt.Chart(df).encode(
        category_enc(f"{category}:N", sort=sort, title=None),
        value_enc(f"{value}:Q", title=title, axis=alt.Axis(tickMinStep=1)),
        tooltip=[alt.Tooltip(f"{category}:N", title="항목"), alt.Tooltip(f"{value}:Q", title=title)],
    )
    bars = base.mark_bar(cornerRadiusEnd=4)
    labels = base.mark_text(
        align="left" if horizontal else "center",
        baseline="middle" if horizontal else "bottom",
        dx=4 if horizontal else 0,
        dy=0 if horizontal else -4,
    ).encode(text=f"{value}:Q")
    return (bars + labels).properties(height=max(160, 36 * len(df)) if horizontal else 260)


st.markdown("## 📊 관리자 뷰")
st.caption(
    "파일럿 응답 집계. 시각은 모두 KST 기준이며, 학생 서술형 답변·로그 원문은 표시하지 않습니다."
)

refresh_col, _ = st.columns([1, 5])
with refresh_col:
    if st.button("🔄 새로고침", use_container_width=True):
        load_frames.clear()
        st.rerun()

try:
    frames = load_frames()
except Exception as e:
    st.error(f"데이터를 불러오지 못했습니다: {e}")
    st.stop()

summary = am.build_session_summary(frames)
stats = am.overview(frames, summary)

# 요약 지표
m1, m2, m3, m4 = st.columns(4)
m1.metric("전체 세션", stats["total_sessions"])
m2.metric("완료 세션 (1~3단계)", stats["completed_sessions"])
m3.metric("고유 참여자 (anon_id)", stats["unique_anon_ids"])
m4.metric("마지막 응답", am.format_kst(stats["last_response_at"]))

st.write("---")

# 완주 퍼널 (전체 세션 기준)
st.markdown("### 1→2→3단계 완주 퍼널")
st.caption(
    "세션 기준 집계입니다. '처음부터 다시 시작'을 누르면 새 세션이 생기므로, 재시작 전 세션은 "
    "중도 이탈로 집계됩니다. 각 단계는 이전 단계를 모두 거친 세션만 셉니다."
)
funnel = am.funnel_counts(frames)
funnel["label"] = [
    f"{n}  ({_pct(rate)})" if i > 0 else f"{n}"
    for i, (n, rate) in enumerate(zip(funnel["sessions"], funnel["conversion_from_prev"]))
]
funnel["이전 단계 대비"] = funnel["conversion_from_prev"].map(_pct)
funnel["시작 대비"] = funnel["conversion_from_start"].map(_pct)
funnel_base = alt.Chart(funnel).encode(
    alt.Y("stage:N", sort=am.FUNNEL_STAGES, title=None),
    alt.X("sessions:Q", title="세션 수", axis=alt.Axis(tickMinStep=1)),
    tooltip=[
        alt.Tooltip("stage:N", title="단계"),
        alt.Tooltip("sessions:Q", title="세션 수"),
        alt.Tooltip("이전 단계 대비:N"),
        alt.Tooltip("시작 대비:N"),
    ],
)
funnel_chart = (
    funnel_base.mark_bar(cornerRadiusEnd=4)
    + funnel_base.mark_text(align="left", baseline="middle", dx=4).encode(text="label:N")
).properties(height=200)
st.altair_chart(funnel_chart, use_container_width=True)

st.write("---")

if summary.empty:
    st.info("아직 1~3단계를 모두 마친 세션이 없습니다. 아래 지표는 완료 세션이 생기면 표시됩니다.")
    st.stop()

st.caption(f"아래 지표는 모두 1~3단계를 마친 완료 세션 {len(summary)}건 기준입니다.")

# 케이스별 응답 수 / 페르소나 분포
col_case, col_persona = st.columns(2)
with col_case:
    st.markdown("### 케이스별 완료 세션 수")
    counts = am.case_counts(frames["cases"], summary)
    st.altair_chart(
        _bar_chart(counts, "label", "completed_sessions", "완료 세션 수", sort=list(counts["label"])),
        use_container_width=True,
    )
with col_persona:
    st.markdown("### 페르소나 분포")
    personas = am.persona_distribution(summary)
    st.altair_chart(
        _bar_chart(personas, "persona", "sessions", "세션 수", sort=list(personas["persona"])),
        use_container_width=True,
    )
    with st.expander("케이스별 페르소나 교차표"):
        st.dataframe(am.persona_by_case(summary), use_container_width=True)

# Health Score 분포
st.markdown("### Health Score 분포")
hist = am.health_score_histogram(summary)
st.altair_chart(
    _bar_chart(hist, "bin", "sessions", "세션 수", sort=list(hist["bin"]), horizontal=False),
    use_container_width=True,
)
st.caption("구간은 표시용 10점 단위이며, 위험 등급 같은 해석 기준이 아닙니다.")

st.write("---")

# 1단계 총점 vs 2단계 Health Score 교차검증 산점도
st.markdown("### 교차검증: 1단계 자가진단 총점 vs 2단계 Health Score")
points = am.scatter_data(summary)
r = am.pearson_r(points)
st.caption(
    f"n = {len(points)}, Pearson r = {'계산 불가(점 2개 미만 또는 분산 0)' if r is None else f'{r:.2f}'}. "
    "케이스마다 1단계 문항이 다르므로 케이스 간 총점 비교에는 주의가 필요합니다."
)
scatter_base = alt.Chart(points).encode(
    alt.X("total_score:Q", title="1단계 총점", scale=alt.Scale(zero=False)),
    alt.Y("health_score:Q", title="2단계 Health Score", scale=alt.Scale(zero=False)),
)
scatter = scatter_base.mark_circle(size=90, opacity=0.85, stroke="white", strokeWidth=2).encode(
    color=alt.Color("case_id:N", title="케이스"),
    tooltip=[
        alt.Tooltip("session:N", title="세션"),
        alt.Tooltip("case_id:N", title="케이스"),
        alt.Tooltip("persona:N", title="페르소나"),
        alt.Tooltip("total_score:Q", title="1단계 총점"),
        alt.Tooltip("health_score:Q", title="Health Score"),
    ],
)
if r is not None:
    trend = scatter_base.transform_regression("total_score", "health_score").mark_line(
        color="gray", strokeDash=[4, 4], strokeWidth=2
    )
    scatter = trend + scatter
st.altair_chart(scatter.properties(height=360), use_container_width=True)

st.write("---")

# 3단계 결과
st.markdown("### 3단계 전이검증 결과")
s3 = am.step3_overview(summary)
c1, c2 = st.columns(2)
c1.metric("첫 퀴즈 정답률 (주 지표)", _pct(s3["first_quiz_correct_rate"]))
c2.metric("세션당 평균 시도 횟수 (보조 지표)", f"{s3['avg_attempts']:.2f}회")
st.caption("첫 퀴즈 = 세션에서 가장 먼저 제출된 퀴즈(id 최소 row). '새 퀴즈 출제'로 인한 재시도는 시도 횟수에만 반영됩니다.")
by_case = am.step3_by_case(summary)
by_case["first_quiz_correct_rate"] = by_case["first_quiz_correct_rate"].map(_pct)
by_case["avg_attempts"] = by_case["avg_attempts"].map(lambda v: f"{v:.2f}")
st.dataframe(
    by_case.rename(columns={
        "case_id": "케이스",
        "sessions": "완료 세션",
        "first_quiz_correct_rate": "첫 퀴즈 정답률",
        "avg_attempts": "평균 시도 횟수",
    }),
    hide_index=True,
    use_container_width=True,
)

st.write("---")

# 최근 완료 세션
st.markdown("### 최근 완료 세션")
st.caption("세션 ID는 앞 8자만, 서술형 답변은 글자 수만 표시합니다.")
st.dataframe(am.recent_completed_table(summary), hide_index=True, use_container_width=True)
