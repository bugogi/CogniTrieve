# utils/db_handler.py
"""Supabase 클라이언트 초기화 및 세션/응답 CRUD."""
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

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


def save_step2_response(
    session_id: str,
    case_id: str,
    health_score: float,
    components: dict | None,
    risk_highlight: str,
    analysis_summary: str,
) -> None:
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
