import os
import google.generativeai as genai
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# API 키 가져오기 및 초기화
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def call_gemini_api(system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
    """
    google-generativeai 패키지를 사용하여 Gemini 1.5 Flash 모델과 통신하는 공통 함수입니다.
    결과를 반드시 JSON 형태로 강제 파싱하도록 response_mime_type="application/json"을 설정합니다.
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다. 프로젝트 루트의 .env 파일에 'GEMINI_API_KEY=your_key_here'를 등록해 주세요.")

    try:
        # Gemini 1.5 Flash 모델 인스턴스 생성
        model = genai.GenerativeModel(
            model_name="gemini-3.1-flash-lite",
            generation_config={
                "response_mime_type": "application/json",
                "temperature": temperature
            },
            system_instruction=system_prompt
        )
        
        # 모델 콘텐츠 생성 호출
        response = model.generate_content(user_prompt)
        
        # 안전 조치: 응답 텍스트 반환
        if response and response.text:
            return response.text
        else:
            raise RuntimeError("Gemini API로부터 빈 응답을 받았습니다.")
            
    except Exception as e:
        raise RuntimeError(f"Gemini API 호출 중 오류 발생: {str(e)}")


def embed_text(text: str, task_type: str = "SEMANTIC_SIMILARITY") -> list[float]:
    """
    Gemini Embedding API(models/gemini-embedding-001)로 텍스트를 임베딩 벡터(3072차원)로
    변환하는 공통 함수입니다. task_type 기본값은 의미 유사도 비교에 특화된
    "SEMANTIC_SIMILARITY"입니다.
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다. 프로젝트 루트의 .env 파일에 'GEMINI_API_KEY=your_key_here'를 등록해 주세요.")

    try:
        response = genai.embed_content(
            model="models/gemini-embedding-001",
            content=text,
            task_type=task_type,
        )
        return response["embedding"]
    except Exception as e:
        raise RuntimeError(f"Gemini Embedding API 호출 중 오류 발생: {str(e)}")
