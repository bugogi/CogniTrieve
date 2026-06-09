# utils/logic_step1.py

def calculate_persona(q1: int, q2: int, q3: int, q4: int, q5: int) -> dict:
    """
    1단계 사전진단 설문 결과를 바탕으로 점수를 합산하고,
    과락(Hotspot) 로직을 적용하여 최종 메타인지 AI 활용 페르소나를 도출합니다.
    """
    total_score = q1 + q2 + q3 + q4 + q5
    
    # 페르소나 정의 및 설명 매핑
    persona_info = {
        "맹목적 의존형": {
            "title": "맹목적 의존형 (Blindly Dependent)",
            "description": (
                "스스로 문제를 해결하거나 설계하려는 의지보다 AI가 제공하는 해답에 완전히 의존하고 있습니다. "
                "코드가 동작하는 원리를 파악하지 못한 채 단순 복사-붙여넣기를 할 가능성이 높습니다. "
                "이러한 방식은 단기적인 과제 해결에는 도움이 될 수 있으나, 장기적으로는 문제 해결 능력과 "
                "디버깅 역량을 현저히 떨어뜨립니다. '인지적 구두쇠(Cognitive Miser)' 상태에서 벗어나기 위해, "
                "시스템 구조를 먼저 기획하고, AI의 코드 중 일부를 분석하여 이해한 로직만 내 코드에 직접 작성해 보세요!"
            ),
            "color": "#EF4444",  # Red
            "icon": "🚨"
        },
        "효율 중심형": {
            "title": "효율 중심형 (Efficiency-Oriented)",
            "description": (
                "AI를 적극적으로 활용하여 과제 수행 속도를 높이고 있지만, 주도적인 설계(Q2)나 "
                "독립적인 디버깅(Q4) 과정이 생략되어 있을 위험이 큽니다. 에러가 발생했을 때 AI에 바로 "
                "로그를 대입하기보다는 먼저 3분간 원인을 스스로 추적해 보고, AI의 도움을 받기 전에 "
                "전체 시스템 아키텍처를 스스로 그려보는 '바람직한 마찰(Desirable Difficulty)' 단계를 의도적으로 추가해야 합니다."
            ),
            "color": "#F59E0B",  # Orange
            "icon": "⚠️"
        },
        "방어형": {
            "title": "방어형 (Defensive)",
            "description": (
                "기본적인 이해와 독립적 행동을 취하고 있지만, 완성도 높은 결과물에 대해 스스로 평가하고 "
                "장단점을 주도적으로 설명하는 단계(Q5)가 다소 부족합니다. AI가 완성해 주거나 분석해 주는 것에 "
                "의존하기보다는, 프로그램의 시간/공간 복잡도를 분석하거나 설계상의 Trade-off를 스스로 분석하여 "
                "본인의 언어로 명확히 설명하는 연습을 해보세요."
            ),
            "color": "#3B82F6",  # Blue
            "icon": "🛡️"
        },
        "자기 주도형": {
            "title": "자기 주도형 (Self-Directed)",
            "description": (
                "매우 바람직한 메타인지 능력을 발휘하고 있습니다! AI를 단순한 정답 자판기가 아닌, "
                "학습 파트너이자 페이스메이커로 건강하게 활용하고 있습니다. 스스로 구조를 기획하고, "
                "동작 원리를 완벽히 이해한 코드만 선별적으로 수용하며, 사후 평가까지 주체적으로 진행하고 있습니다. "
                "앞으로도 메타인지 자극 요소들을 학습 프로세스 곳곳에 배치하는 좋은 습관을 유지해 나가시기 바랍니다."
            ),
            "color": "#10B981",  # Green
            "icon": "👑"
        }
    }
    
    # 과락 로직 판정
    # 맹목적 의존형: If (총점 <= 11) OR (Q2 <= 2 AND Q4 <= 2)
    if (total_score <= 11) or (q2 <= 2 and q4 <= 2):
        persona = "맹목적 의존형"
    # 효율 중심형: Else If (Q2 <= 2 OR Q4 <= 2)
    elif (q2 <= 2 or q4 <= 2):
        persona = "효율 중심형"
    # 방어형: Else If (총점 <= 21) AND (Q5 <= 3)
    elif (total_score <= 21) and (q5 <= 3):
        persona = "방어형"
    # 자기 주도형: Else
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
        "scores": [q1, q2, q3, q4, q5]
    }
