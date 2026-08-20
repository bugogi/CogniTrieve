# utils/logic_step1.py

# 핫스팟 위험 등급별 임계값 (docs/07 3절 5.2 반영)
HOTSPOT_THRESHOLDS = {"최고위험": 2, "위험": 1}

REFLECTION_QUESTION_INDEX = 5  # Q5, 모든 케이스 공통 고정 (docs/07 3절)


def threshold(tier: str) -> int:
    """핫스팟 위험 등급에 대응하는 임계값을 반환합니다."""
    return HOTSPOT_THRESHOLDS[tier]


def calculate_persona(case: dict, q1: int, q2: int, q3: int, q4: int, q5: int) -> dict:
    """
    1단계 사전진단 설문 결과를 바탕으로 점수를 합산하고,
    선택된 케이스의 핫스팟(hotspot_primary/secondary/tier)을 조회하여
    일반화된 과락(Hotspot) 로직을 적용해 최종 메타인지 AI 활용 페르소나를 도출합니다.
    """
    scores = [q1, q2, q3, q4, q5]
    total_score = sum(scores)

    tier_primary = case["hotspot_tier"]["primary"]
    tier_secondary = case["hotspot_tier"]["secondary"]
    q_primary = scores[case["hotspot_primary"] - 1]
    q_secondary = scores[case["hotspot_secondary"] - 1]
    q_reflection = scores[REFLECTION_QUESTION_INDEX - 1]

    primary_hit = q_primary <= threshold(tier_primary)
    secondary_hit = q_secondary <= threshold(tier_secondary)

    # 페르소나 정의 및 설명 매핑 (케이스 무관 공통 정의, docs/07 3절)
    persona_info = {
        "맹목적 의존형": {
            "title": "맹목적 의존형 (Blindly Dependent)",
            "description": (
                "스스로 뼈대(구조·논리)를 설계하거나 결과물(문장·코드·수식·시안 등)을 직접 만들어보려는 "
                "시도보다, AI가 내놓는 결과에 전반적으로 의존하고 있습니다. 결과물이 어떤 논리와 원리로 "
                "만들어졌는지 파악하지 못한 채 그대로 채택할 가능성이 높습니다. 이런 방식은 단기적인 과제 "
                "해결에는 도움이 될 수 있으나, 장기적으로는 스스로 사고하고 문제를 해결하는 역량을 현저히 "
                "떨어뜨립니다. '인지적 구두쇠(Cognitive Miser)' 상태에서 벗어나기 위해, 결과물의 뼈대를 "
                "먼저 스스로 기획해보고, AI가 제시한 내용 중 원리를 이해한 부분만 선별해 직접 표현해 보세요!"
            ),
            "color": "#EF4444",  # Red
            "icon": "🚨"
        },
        "효율 중심형": {
            "title": "효율 중심형 (Efficiency-Oriented)",
            "description": (
                "AI를 적극적으로 활용해 과제 수행 속도를 높이고 있지만, 이 과제에서 가장 핵심적인 인지 "
                "단계는 AI에 위임하고 있을 위험이 큽니다. 막힌 지점에서 곧바로 AI에 결과를 맡기기보다는 "
                "먼저 스스로 3분간 시도해보고, AI의 도움을 받기 전에 전체 흐름을 스스로 그려보는 "
                "'바람직한 마찰(Desirable Difficulty)' 단계를 의도적으로 추가해야 합니다."
            ),
            "color": "#F59E0B",  # Orange
            "icon": "⚠️"
        },
        "방어형": {
            "title": "방어형 (Defensive)",
            "description": (
                "기본적인 이해와 독립적인 시도는 하고 있지만, 완성된 결과물에 대해 스스로 평가하고 근거를 "
                "주도적으로 설명하는 성찰 단계가 다소 부족합니다. AI의 판단 뒤에 결론을 숨기기보다는, "
                "결과물의 장단점이나 한계를 스스로 분석해 본인의 언어로 명확히 설명하는 연습을 해보세요."
            ),
            "color": "#3B82F6",  # Blue
            "icon": "🛡️"
        },
        "자기 주도형": {
            "title": "자기 주도형 (Self-Directed)",
            "description": (
                "매우 바람직한 메타인지 능력을 발휘하고 있습니다! AI를 단순한 정답 자판기가 아닌, 학습 "
                "파트너이자 지적 스파링 파트너로 건강하게 활용하고 있습니다. 스스로 뼈대를 기획하고, 원리를 "
                "이해한 부분만 선별적으로 수용하며, 결과물에 대한 사후 평가까지 주체적으로 진행하고 "
                "있습니다. 앞으로도 메타인지 자극 요소들을 학습 과정 곳곳에 배치하는 좋은 습관을 유지해 "
                "나가시기 바랍니다."
            ),
            "color": "#10B981",  # Green
            "icon": "👑"
        }
    }

    # 과락 로직 판정 (docs/07 3절 "일반화된 판별 로직")
    if (total_score <= 11) or (primary_hit and secondary_hit):
        persona = "맹목적 의존형"
    elif primary_hit or secondary_hit:
        persona = "효율 중심형"
    elif (total_score <= 21) and (q_reflection <= 3):
        persona = "방어형"
    else:
        persona = "자기 주도형"

    info = persona_info[persona]

    return {
        "total_score": total_score,
        "persona": persona,
        "title": info["title"],
        "description": info["description"],
        "color": info["color"],
        "icon": info["icon"],
        "scores": scores
    }
