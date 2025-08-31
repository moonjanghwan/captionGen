import os
from dotenv import load_dotenv

# .env 파일에서 환경 변수를 로드합니다.
# 프로젝트 루트 디렉토리에 .env 파일이 있어야 합니다.
load_dotenv()

# --- API 키 설정 ---
# .env 파일에서 Gemini API 키를 가져옵니다.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- 경로 설정 ---
# 프로젝트의 루트 디렉토리를 기준으로 경로를 설정합니다.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Google Cloud 인증 키 파일 경로
# 사용자는 이 경로에 자신의 credentials.json 파일을 위치시켜야 합니다.
GOOGLE_CREDENTIALS_PATH = os.path.join(BASE_DIR, "credentials.json")

# 리소스 및 결과물 경로
ASSETS_PATH = os.path.join(BASE_DIR, "assets")
OUTPUT_PATH = os.path.join(BASE_DIR, "output")
FONTS_PATH = os.path.join(ASSETS_PATH, "fonts")


# --- UI 테마 및 색상 설정 ---
# "제작 사양서"에 명시된 색상값입니다.
COLOR_THEME = {
    "background": "#2C3E50",    # Charcoal Blue
    "widget": "#34495E",        # Wet Asphalt
    "button": "#3498DB",        # Peter River Blue
    "button_hover": "#5DADE2",   # Bright Peter River Blue
    "text": "#FFFFFF"           # White
}
UI_THEME = "blue" 
UI_APPEARANCE_MODE = "Dark"


# --- 비디오 제작 기본 설정 ---
DEFAULT_RESOLUTION = "1920x1080"
DEFAULT_ASPECT_RATIO = "16:9"
DEFAULT_FONT = "NotoSansKR-Bold.otf" # assets/fonts/ 에 위치해야 함
