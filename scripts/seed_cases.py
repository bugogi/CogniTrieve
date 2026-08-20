# scripts/seed_cases.py
"""
cases 테이블에 6개 케이스를 시딩하는 독립 실행 스크립트.
문항/핫스팟 데이터 출처: docs/07_파이프라인_설계.md(assignment_A/B/C/D),
docs/08-1_수강_학습유형_설계.md(course), docs/08-2_시험대비_학습유형_설계.md(exam_prep).

concept_vocabulary는 docs/09에서 "Phase 6a(구현 Phase 3) 참조"로 남겨진 미확정 값이라
Phase 1에서는 채우지 않고 NULL로 둔다(스키마상 nullable).

실행: python scripts/seed_cases.py
"""
import os
import sys

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

CASES = [
    {
        "case_id": "assignment_A",
        "learning_type": "과제",
        "output_type": "A",
        "questions": [
            "나는 AI에게 묻기 전에 텍스트의 핵심 논지를 스스로 파악하려고 시도했다.",
            "나는 에세이의 주제(입장)를 AI 없이 스스로 결정했다.",
            "나는 초안을 완성된 글로 다듬는 과정을 AI에 전적으로 맡기지 않고 직접 문장을 작성했다.",
            "나는 팀 토론에서 나온 의견 차이를 AI 요약에 의존하지 않고 직접 종합했다.",
            "나는 발표 자료에 담긴 논리 전개를 스스로 설명할 수 있다.",
        ],
        "hotspot_primary": 3,
        "hotspot_secondary": 4,
        "hotspot_tier": {"primary": "최고위험", "secondary": "위험"},
        "concept_vocabulary": None,
    },
    {
        "case_id": "assignment_B",
        "learning_type": "과제",
        "output_type": "B",
        "questions": [
            "과제 명세서를 읽고, AI에게 요약이나 조건 추출을 맡기기 전에 나 스스로 과제의 핵심 목표와 필요한 기술 스택을 정리해 보았다.",
            "코드를 타이핑하기 전, 전체 시스템의 아키텍처(클래스 구조, 데이터 흐름 등)를 AI의 도움 없이 스스로 기획하고 스케치했다.",
            "AI가 제시한 코드를 내 프로젝트에 적용할 때, 작동 원리를 100% 이해한 로직만 선별하여 직접 타이핑하거나 부분적으로 반영했다.",
            "에러가 발생했을 때, AI에게 로그를 복사해 주기 전에 스스로 원인을 추론해 보는 시간(최소 3분 이상)을 가졌다.",
            "작성된 결과물의 장단점(예: 시간/공간 복잡도의 한계)을 AI의 분석에 의존하지 않고, 내 스스로의 논리로 평가하여 설명할 수 있다.",
        ],
        "hotspot_primary": 4,
        "hotspot_secondary": 2,
        "hotspot_tier": {"primary": "최고위험", "secondary": "위험"},
        "concept_vocabulary": None,
    },
    {
        "case_id": "assignment_C",
        "learning_type": "과제",
        "output_type": "C",
        "questions": [
            "나는 문제에 어떤 물리 개념이 적용되는지 AI에 묻기 전에 스스로 떠올렸다.",
            "나는 문제 상황을 수식으로 세우는 과정을 스스로 수행했다.",
            "나는 계산 전개 과정을 AI가 준 결과를 그대로 베끼지 않고 직접 따라갔다.",
            "나는 최종 답이 물리적으로 타당한지 스스로 검증했다(단위, 극한상황 등).",
            "나는 내 풀이 과정의 약점이나 헷갈렸던 지점을 명확히 설명할 수 있다.",
        ],
        "hotspot_primary": 2,
        "hotspot_secondary": 4,
        "hotspot_tier": {"primary": "최고위험", "secondary": "최고위험"},
        "concept_vocabulary": None,
    },
    {
        "case_id": "assignment_D",
        "learning_type": "과제",
        "output_type": "D",
        "questions": [
            "나는 레퍼런스를 단순 수집하는 데 그치지 않고 트렌드의 배경을 스스로 해석하려 했다.",
            "나는 브랜드 컨셉을 AI가 제시한 안 중 하나를 그대로 채택하지 않고 스스로 발전시켰다.",
            "나는 시안 제작 과정에서 툴을 직접 조작하며 결과물을 완성했다.",
            "나는 기획 의도서에 담긴 논리가 실제 제작 과정과 일치하도록 직접 서술했다.",
            "나는 받은 피드백을 반영한 이유를 스스로 설명할 수 있다.",
        ],
        "hotspot_primary": 2,
        "hotspot_secondary": 3,
        "hotspot_tier": {"primary": "최고위험", "secondary": "최고위험"},
        "concept_vocabulary": None,
    },
    {
        "case_id": "course",
        "learning_type": "수강",
        "output_type": None,
        "questions": [
            "나는 수업 전 예습 자료를 AI 요약본에만 의존하지 않고 직접 읽어봤다.",
            "나는 수업 중 필기를 AI 자동 요약에 전적으로 의존하지 않고 직접 기록했다.",
            "나는 이해 안 되는 부분을 AI뿐 아니라 교수·동료에게도 질문하려 시도했다.",
            "나는 복습 노트를 AI가 만든 요약본을 그대로 쓰지 않고 스스로 정리했다.",
            "나는 AI의 '잘 이해했다'는 반응이 아니라, 직접 설명해보며 이해도를 확인했다.",
        ],
        "hotspot_primary": 2,
        "hotspot_secondary": 4,
        "hotspot_tier": {"primary": "최고위험", "secondary": "최고위험"},
        "concept_vocabulary": None,
    },
    {
        "case_id": "exam_prep",
        "learning_type": "시험 대비",
        "output_type": None,
        "questions": [
            "나는 시험 범위와 기출 유형을 AI 요약에만 의존하지 않고 직접 확인했다.",
            "나는 개념 정리·암기자료를 AI가 만든 것을 그대로 쓰지 않고 스스로 정리했다.",
            "나는 모의문제를 풀 때 AI에게 답을 바로 묻지 않고 스스로 끝까지 풀어보려 시도했다.",
            "나는 오답의 원인을 AI 설명을 읽는 데 그치지 않고, 같은 유형 문제를 다시 풀어 확인했다.",
            "나는 실전 감각(시간 배분 등)을 AI 예상문제 풀이가 아니라 직접 시뮬레이션으로 점검했다.",
        ],
        "hotspot_primary": 3,
        "hotspot_secondary": 4,
        "hotspot_tier": {"primary": "최고위험", "secondary": "최고위험"},
        "concept_vocabulary": None,
    },
]


def main() -> None:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        print("SUPABASE_URL / SUPABASE_KEY가 .env에 설정되어 있지 않습니다.", file=sys.stderr)
        sys.exit(1)

    client = create_client(url, key)
    result = client.table("cases").upsert(CASES).execute()
    print(f"{len(result.data)}개 케이스 시딩 완료: {[row['case_id'] for row in result.data]}")


if __name__ == "__main__":
    main()
