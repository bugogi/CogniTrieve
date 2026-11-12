# utils/admin_metrics.py
"""관리자 뷰(pages/9_관리자.py) 집계 로직.

DB 호출 없이 fetch_admin_rows()가 돌려준 원본 row(테이블별 dict 리스트)만 받아
pandas로 집계한다. 집계 기준(Phase 5 그룹 A 확정):
- "완료 세션" = 1·2·3단계 응답이 모두 있는 세션.
- 1·2단계는 재제출 차단으로 세션당 최대 1행이므로 그 행을 그대로 쓴다.
- 3단계는 세션의 "첫 퀴즈"(id가 가장 작은 row)의 is_correct를 주 지표로,
  세션당 시도(제출) 횟수를 보조 지표로 쓴다.
- 3단계 student_answer 원문은 build_frames()에서 글자 수로 바꾼 뒤 즉시 버린다
  (화면·스크린샷 노출 방지). 2단계 risk_highlight/analysis_summary는 애초에
  조회하지 않는다.
- 시각은 DB에 UTC로 저장되어 있으므로 화면 표시는 KST로 변환한다.
"""
from datetime import timedelta, timezone

import pandas as pd

# 한국은 서머타임이 없으므로 고정 오프셋으로 충분하다(Windows 로컬에서 tzdata 의존 회피).
KST = timezone(timedelta(hours=9), name="KST")

SHORT_ID_LENGTH = 8
HEALTH_SCORE_BIN_WIDTH = 10  # 표시용 구간 폭일 뿐, 위험 등급 등의 해석 기준이 아니다.
HEALTH_SCORE_MAX = 100
UNKNOWN_PERSONA_LABEL = "(미기록)"

FUNNEL_STAGES = ["세션 생성", "1단계 사전진단", "2단계 로그분석", "3단계 전이검증"]

_COLUMNS = {
    "cases": ["case_id", "learning_type", "output_type"],
    "sessions": ["session_id", "anon_id", "case_id", "created_at"],
    "step1_responses": ["id", "session_id", "case_id", "total_score", "persona", "created_at"],
    "step2_responses": ["id", "session_id", "case_id", "health_score", "created_at"],
    "step3_responses": [
        "id", "session_id", "case_id", "quiz_type", "answer_length",
        "is_correct", "matched_keyword", "created_at",
    ],
}

SUMMARY_COLUMNS = [
    "session_id", "case_id", "total_score", "persona", "health_score",
    "first_quiz_type", "first_quiz_correct", "first_quiz_answer_length",
    "first_quiz_matched_keyword", "quiz_attempts", "completed_at",
]


# ---------------------------------------------------------------------------
# 공통 변환
# ---------------------------------------------------------------------------

def to_kst(values: pd.Series) -> pd.Series:
    """Supabase의 UTC ISO 문자열(또는 None)을 KST tz-aware datetime으로 변환한다."""
    parsed = pd.to_datetime(values, utc=True, format="ISO8601", errors="coerce")
    return parsed.dt.tz_convert(KST)


def format_kst(value) -> str:
    """KST datetime을 화면 표시용 문자열로 만든다. 값이 없으면 '-'."""
    if value is None or pd.isna(value):
        return "-"
    return value.strftime("%Y-%m-%d %H:%M KST")


def short_id(session_id) -> str:
    """세션 ID를 앞 8자로 줄인다(스크린샷 노출 최소화)."""
    if session_id is None or pd.isna(session_id):
        return "-"
    return str(session_id)[:SHORT_ID_LENGTH]


def mask_answers(rows: list[dict]) -> list[dict]:
    """step3 row에서 student_answer 원문을 제거하고 글자 수(answer_length)만 남긴다."""
    masked = []
    for row in rows:
        row = dict(row)
        answer = row.pop("student_answer", None)
        row["answer_length"] = len(answer.strip()) if isinstance(answer, str) else 0
        masked.append(row)
    return masked


def build_frames(raw: dict[str, list[dict]]) -> dict[str, pd.DataFrame]:
    """원본 row를 테이블별 DataFrame으로 바꾼다. 빈 테이블도 컬럼은 항상 갖춘다.

    step3의 student_answer는 이 단계에서 마스킹되어 이후 어떤 DataFrame에도 남지 않는다.
    """
    frames = {}
    for table, columns in _COLUMNS.items():
        rows = raw.get(table) or []
        if table == "step3_responses":
            rows = mask_answers(rows)
        df = pd.DataFrame(rows)
        for col in columns:
            if col not in df.columns:
                df[col] = pd.Series(dtype="object")
        df = df[columns].copy()
        if "created_at" in df.columns:
            df["created_at"] = to_kst(df["created_at"])
        frames[table] = df

    frames["step1_responses"]["total_score"] = pd.to_numeric(
        frames["step1_responses"]["total_score"], errors="coerce"
    )
    frames["step2_responses"]["health_score"] = pd.to_numeric(
        frames["step2_responses"]["health_score"], errors="coerce"
    )
    step3 = frames["step3_responses"]
    step3["id"] = pd.to_numeric(step3["id"], errors="coerce")
    step3["is_correct"] = step3["is_correct"].eq(True)
    return frames


# ---------------------------------------------------------------------------
# 세션 단위 집계
# ---------------------------------------------------------------------------

def first_quiz_per_session(step3: pd.DataFrame) -> pd.DataFrame:
    """세션별 첫 퀴즈(id 최소 row)와 시도 횟수를 구한다."""
    columns = [
        "session_id", "first_quiz_type", "first_quiz_correct",
        "first_quiz_answer_length", "first_quiz_matched_keyword",
        "quiz_attempts", "completed_at",
    ]
    if step3.empty:
        return pd.DataFrame(columns=columns)

    ordered = step3.sort_values("id", kind="stable")
    # groupby().first()는 컬럼별로 NaN이 아닌 첫 값을 골라 서로 다른 row가 섞이므로 쓰지 않는다
    # (예: 첫 퀴즈의 matched_keyword가 None이면 두 번째 시도의 키워드가 들어감).
    first = ordered.drop_duplicates("session_id", keep="first")
    attempts = ordered.groupby("session_id").size().rename("quiz_attempts").reset_index()
    first = first.merge(attempts, on="session_id")
    first = first.rename(columns={
        "quiz_type": "first_quiz_type",
        "is_correct": "first_quiz_correct",
        "answer_length": "first_quiz_answer_length",
        "matched_keyword": "first_quiz_matched_keyword",
        "created_at": "completed_at",  # 첫 퀴즈 제출 시점 = 1~3단계를 처음 모두 마친 시점
    })
    first["first_quiz_correct"] = first["first_quiz_correct"].astype(bool)
    return first[columns]


def build_session_summary(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """완료 세션(1·2·3단계 응답이 모두 있는 세션)만 1행씩 모은 요약표를 만든다."""
    step1 = frames["step1_responses"][["session_id", "case_id", "total_score", "persona"]]
    step2 = frames["step2_responses"][["session_id", "health_score"]]
    step3 = first_quiz_per_session(frames["step3_responses"])

    summary = (
        step1.drop_duplicates("session_id")
        .merge(step2.drop_duplicates("session_id"), on="session_id", how="inner")
        .merge(step3, on="session_id", how="inner")
    )
    if summary.empty:
        return pd.DataFrame(columns=SUMMARY_COLUMNS)
    summary["persona"] = summary["persona"].fillna(UNKNOWN_PERSONA_LABEL)
    return summary[SUMMARY_COLUMNS].reset_index(drop=True)


# ---------------------------------------------------------------------------
# 지표
# ---------------------------------------------------------------------------

def overview(frames: dict[str, pd.DataFrame], summary: pd.DataFrame) -> dict:
    """상단 요약 지표: 세션 수, 완료 세션 수, 고유 anon_id 수, 마지막 응답 시각(KST)."""
    timestamps = pd.concat(
        [frames[t]["created_at"] for t in ("step1_responses", "step2_responses", "step3_responses")],
        ignore_index=True,
    ).dropna()
    sessions = frames["sessions"]
    return {
        "total_sessions": int(sessions["session_id"].nunique()),
        "completed_sessions": int(len(summary)),
        "unique_anon_ids": int(sessions["anon_id"].nunique()),
        "last_response_at": timestamps.max() if not timestamps.empty else None,
    }


def funnel_counts(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """세션 생성 → 1단계 → 2단계 → 3단계 퀴즈 제출 완주 퍼널(세션 기준).

    각 단계는 이전 단계를 모두 거친 세션만 세므로 항상 단조감소한다.
    """
    stage_sets = [
        set(frames["sessions"]["session_id"].dropna()),
        set(frames["step1_responses"]["session_id"].dropna()),
        set(frames["step2_responses"]["session_id"].dropna()),
        set(frames["step3_responses"]["session_id"].dropna()),
    ]
    reached = []
    current = None
    for stage_set in stage_sets:
        current = stage_set if current is None else current & stage_set
        reached.append(len(current))

    rows = []
    for i, (stage, count) in enumerate(zip(FUNNEL_STAGES, reached)):
        prev = reached[i - 1] if i > 0 else None
        rows.append({
            "stage": stage,
            "sessions": count,
            "conversion_from_prev": (count / prev) if prev else None,
            "conversion_from_start": (count / reached[0]) if reached[0] else None,
        })
    return pd.DataFrame(rows)


def case_label(case_row) -> str:
    """cases 테이블 값으로 케이스 라벨을 만든다(case_id 하드코딩 없음)."""
    case_id = case_row["case_id"]
    learning_type = case_row.get("learning_type")
    output_type = case_row.get("output_type")
    if learning_type is None or pd.isna(learning_type):
        return str(case_id)
    if output_type is None or pd.isna(output_type):
        return f"{case_id} ({learning_type})"
    return f"{case_id} ({learning_type}·{output_type})"


def case_counts(cases: pd.DataFrame, summary: pd.DataFrame) -> pd.DataFrame:
    """케이스별 완료 세션 수. cases 테이블 기준이라 응답 0건 케이스도 0으로 나온다.

    cases에 없는 case_id가 응답에 있으면(정상 경로에선 FK로 불가) 그대로 라벨링해 함께 보여준다.
    """
    counts = summary.groupby("case_id").size().rename("completed_sessions").reset_index()
    merged = cases[["case_id", "learning_type", "output_type"]].merge(
        counts, on="case_id", how="outer"
    )
    merged["completed_sessions"] = merged["completed_sessions"].fillna(0).astype(int)
    merged["label"] = merged.apply(case_label, axis=1)
    merged = merged.sort_values("case_id", kind="stable").reset_index(drop=True)
    return merged[["case_id", "label", "completed_sessions"]]


def persona_distribution(summary: pd.DataFrame) -> pd.DataFrame:
    """완료 세션의 페르소나별 세션 수(내림차순)."""
    if summary.empty:
        return pd.DataFrame(columns=["persona", "sessions"])
    counts = summary["persona"].value_counts().rename_axis("persona").rename("sessions")
    return counts.reset_index()


def persona_by_case(summary: pd.DataFrame) -> pd.DataFrame:
    """케이스(행) × 페르소나(열) 교차표."""
    if summary.empty:
        return pd.DataFrame()
    return pd.crosstab(summary["case_id"], summary["persona"])


def health_score_histogram(
    summary: pd.DataFrame, bin_width: int = HEALTH_SCORE_BIN_WIDTH
) -> pd.DataFrame:
    """Health Score를 표시용 고정 폭 구간으로 센다. 빈 구간도 0으로 포함, 구간 순서 유지.

    구간은 [a, a+폭) 이고 마지막 구간만 최댓값(100)을 포함한다.
    """
    edges = list(range(0, HEALTH_SCORE_MAX + bin_width, bin_width))
    labels = [f"{lo}–{hi}" for lo, hi in zip(edges[:-1], edges[1:])]
    scores = pd.to_numeric(summary["health_score"], errors="coerce").dropna()
    scores = scores.clip(lower=0, upper=HEALTH_SCORE_MAX)
    # 마지막 구간에 최댓값이 포함되도록 상한만 살짝 밀어 right=False로 자른다.
    cut_edges = edges[:-1] + [HEALTH_SCORE_MAX + 1e-9]
    binned = pd.cut(scores, bins=cut_edges, labels=labels, right=False)
    counts = binned.value_counts(sort=False).reindex(labels, fill_value=0)
    return pd.DataFrame({
        "bin": labels,
        "bin_start": edges[:-1],
        "sessions": counts.astype(int).to_list(),
    })


def scatter_data(summary: pd.DataFrame) -> pd.DataFrame:
    """1단계 총점 vs 2단계 Health Score 교차검증용 점 데이터(완료 세션만)."""
    columns = ["session", "case_id", "persona", "total_score", "health_score"]
    if summary.empty:
        return pd.DataFrame(columns=columns)
    df = summary[["session_id", "case_id", "persona", "total_score", "health_score"]].copy()
    df = df.dropna(subset=["total_score", "health_score"])
    df["session"] = df["session_id"].map(short_id)
    return df[columns].reset_index(drop=True)


def pearson_r(points: pd.DataFrame) -> float | None:
    """총점-Health Score 피어슨 상관계수. 점이 2개 미만이거나 분산이 0이면 None."""
    if len(points) < 2:
        return None
    x = points["total_score"].astype(float)
    y = points["health_score"].astype(float)
    if x.std() == 0 or y.std() == 0:
        return None
    return float(x.corr(y))


def step3_overview(summary: pd.DataFrame) -> dict:
    """3단계 주 지표(첫 퀴즈 정답률)와 보조 지표(세션당 평균 시도 횟수)."""
    if summary.empty:
        return {"sessions": 0, "first_quiz_correct_rate": None, "avg_attempts": None}
    return {
        "sessions": int(len(summary)),
        "first_quiz_correct_rate": float(summary["first_quiz_correct"].mean()),
        "avg_attempts": float(summary["quiz_attempts"].mean()),
    }


def step3_by_case(summary: pd.DataFrame) -> pd.DataFrame:
    """케이스별 첫 퀴즈 정답률과 평균 시도 횟수."""
    columns = ["case_id", "sessions", "first_quiz_correct_rate", "avg_attempts"]
    if summary.empty:
        return pd.DataFrame(columns=columns)
    grouped = summary.groupby("case_id").agg(
        sessions=("session_id", "size"),
        first_quiz_correct_rate=("first_quiz_correct", "mean"),
        avg_attempts=("quiz_attempts", "mean"),
    )
    return grouped.reset_index()[columns]


def recent_completed_table(summary: pd.DataFrame, limit: int = 20) -> pd.DataFrame:
    """최근 완료 세션 표(화면 표시용). 원문 텍스트 컬럼은 포함하지 않는다."""
    columns = [
        "완료 시각(KST)", "세션", "케이스", "페르소나", "1단계 총점", "Health Score",
        "첫 퀴즈 유형", "첫 퀴즈 정답", "답변 글자 수", "매칭 키워드", "시도 횟수",
    ]
    if summary.empty:
        return pd.DataFrame(columns=columns)
    recent = summary.sort_values("completed_at", ascending=False, kind="stable").head(limit)
    table = pd.DataFrame({
        "완료 시각(KST)": recent["completed_at"].map(format_kst),
        "세션": recent["session_id"].map(short_id),
        "케이스": recent["case_id"],
        "페르소나": recent["persona"],
        "1단계 총점": recent["total_score"],
        "Health Score": recent["health_score"],
        "첫 퀴즈 유형": recent["first_quiz_type"],
        "첫 퀴즈 정답": recent["first_quiz_correct"].map({True: "O", False: "X"}),
        "답변 글자 수": recent["first_quiz_answer_length"],
        "매칭 키워드": recent["first_quiz_matched_keyword"].fillna("-"),
        "시도 횟수": recent["quiz_attempts"],
    })
    return table.reset_index(drop=True)
