# utils/db_handler.py
"""Supabase 클라이언트 초기화 및 세션/응답 CRUD."""
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from postgrest.exceptions import APIError
from supabase import Client, create_client

load_dotenv()

UNIQUE_VIOLATION_CODE = "23505"


class DuplicateSubmissionError(Exception):
    """해당 세션에 대해 이미 저장된 응답이 있을 때(유니크 제약 위반 시) 발생."""

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

_client: Client | None = None


def get_client() -> Client:
    """Supabase 클라이언트를 지연 초기화하여 반환합니다(service_role key, 서버 사이드 전용)."""
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError(
                "SUPABASE_URL / SUPABASE_KEY가 설정되지 않았습니다. 프로젝트 루트의 .env 파일을 확인해 주세요."
            )
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


def list_cases() -> list[dict]:
    """cases 테이블의 전체 케이스 목록을 case_id 순으로 조회합니다."""
    response = get_client().table("cases").select("*").order("case_id").execute()
    return response.data


def get_case(case_id: str) -> dict | None:
    """단일 케이스를 조회합니다. 없으면 None을 반환합니다."""
    response = (
        get_client().table("cases").select("*").eq("case_id", case_id).limit(1).execute()
    )
    return response.data[0] if response.data else None


def create_session(anon_id: str, case_id: str) -> str:
    """동의 완료 및 케이스 선택 시점에 세션을 생성하고 consented_at을 함께 기록합니다.

    생성된 session_id(uuid)를 문자열로 반환합니다.
    """
    payload = {
        "anon_id": anon_id,
        "case_id": case_id,
        "consented_at": datetime.now(timezone.utc).isoformat(),
    }
    response = get_client().table("sessions").insert(payload).execute()
    return response.data[0]["session_id"]


def save_step1_response(
    session_id: str,
    case_id: str,
    q1: int,
    q2: int,
    q3: int,
    q4: int,
    q5: int,
    total_score: int,
    persona: str,
) -> None:
    try:
        get_client().table("step1_responses").insert(
            {
                "session_id": session_id,
                "case_id": case_id,
                "q1": q1,
                "q2": q2,
                "q3": q3,
                "q4": q4,
                "q5": q5,
                "total_score": total_score,
                "persona": persona,
            }
        ).execute()
    except APIError as e:
        if e.code == UNIQUE_VIOLATION_CODE:
            raise DuplicateSubmissionError(
                "이미 해당 세션의 1단계 응답이 저장되어 있습니다."
            ) from e
        raise


def save_step2_response(
    session_id: str,
    case_id: str,
    health_score: float,
    components: dict | None,
    risk_highlight: str,
    analysis_summary: str,
) -> None:
    try:
        get_client().table("step2_responses").insert(
            {
                "session_id": session_id,
                "case_id": case_id,
                "health_score": health_score,
                "components": components,
                "risk_highlight": risk_highlight,
                "analysis_summary": analysis_summary,
            }
        ).execute()
    except APIError as e:
        if e.code == UNIQUE_VIOLATION_CODE:
            raise DuplicateSubmissionError(
                "이미 해당 세션의 2단계 응답이 저장되어 있습니다."
            ) from e
        raise


def save_step3_response(
    session_id: str,
    case_id: str,
    quiz_type: str,
    dynamic_question: str,
    student_answer: str,
    is_correct: bool,
    matched_keyword: str | None,
) -> None:
    get_client().table("step3_responses").insert(
        {
            "session_id": session_id,
            "case_id": case_id,
            "quiz_type": quiz_type,
            "dynamic_question": dynamic_question,
            "student_answer": student_answer,
            "is_correct": is_correct,
            "matched_keyword": matched_keyword,
        }
    ).execute()


# ---------------------------------------------------------------------------
# 관리자 뷰 전용 읽기(pages/9_관리자.py) — 쓰기 없음
# ---------------------------------------------------------------------------

ADMIN_PAGE_SIZE = 1000  # PostgREST 기본 응답 상한과 동일

# 관리자 뷰가 실제로 필요한 컬럼만 조회한다. step2의 risk_highlight/analysis_summary는
# 학생 로그에서 뽑은 문장이라 의도적으로 제외한다. step3의 student_answer는 글자 수
# 산출용으로만 가져오며, utils.admin_metrics.build_frames()에서 즉시 제거된다.
ADMIN_SELECT_COLUMNS = {
    "cases": ("case_id, learning_type, output_type", "case_id"),
    "sessions": ("session_id, anon_id, case_id, created_at", "session_id"),
    "step1_responses": ("id, session_id, case_id, total_score, persona, created_at", "id"),
    "step2_responses": ("id, session_id, case_id, health_score, created_at", "id"),
    "step3_responses": (
        "id, session_id, case_id, quiz_type, student_answer, is_correct, matched_keyword, created_at",
        "id",
    ),
}


def _fetch_all(table: str, columns: str, order_by: str) -> list[dict]:
    """응답 상한(1000행)을 넘어도 끝까지 읽도록 range로 페이지를 넘기며 조회합니다."""
    rows: list[dict] = []
    start = 0
    while True:
        response = (
            get_client()
            .table(table)
            .select(columns)
            .order(order_by)
            .range(start, start + ADMIN_PAGE_SIZE - 1)
            .execute()
        )
        batch = response.data or []
        rows.extend(batch)
        if len(batch) < ADMIN_PAGE_SIZE:
            return rows
        start += ADMIN_PAGE_SIZE


def fetch_admin_rows() -> dict[str, list[dict]]:
    """관리자 뷰 집계용 원본 row를 테이블별로 조회합니다(읽기 전용)."""
    return {
        table: _fetch_all(table, columns, order_by)
        for table, (columns, order_by) in ADMIN_SELECT_COLUMNS.items()
    }
