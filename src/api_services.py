import google.generativeai as genai
from google.cloud import texttospeech, texttospeech_v1
from src import config
import os
import json
import re

def initialize_gemini():
    """Gemini API 키를 사용하여 API를 초기화하고 연결 상태를 확인합니다."""
    try:
        if not config.GEMINI_API_KEY:
            return "Gemini API 키가 .env 파일에 설정되지 않았습니다."
        
        genai.configure(api_key=config.GEMINI_API_KEY)
        # 간단한 모델 목록 조회로 연결 테스트
        models = genai.list_models()
        
        # 'gemini-pro' 또는 유사 모델이 있는지 확인
        if any('gemini' in m.name for m in models):
            return "Gemini API에 성공적으로 연결되었습니다."
        else:
            return "Gemini API에 연결되었으나, 사용 가능한 Gemini 모델을 찾을 수 없습니다."

    except Exception as e:
        return f"Gemini API 연결 중 오류 발생: {e}"

def initialize_google_tts():
    """Google TTS API 인증 정보를 사용하여 클라이언트를 초기화하고 연결 상태를 확인합니다."""
    try:
        if not os.path.exists(config.GOOGLE_CREDENTIALS_PATH):
            return "Google TTS 인증 파일(credentials.json)을 찾을 수 없습니다."
        
        # GOOGLE_APPLICATION_CREDENTIALS 환경 변수를 설정할 필요 없이,
        # client 생성 시 명시적으로 credentials_path를 지정할 수 있습니다.
        # 하지만 일반적으로는 환경 변수 설정을 권장합니다.
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = config.GOOGLE_CREDENTIALS_PATH
        
        client = texttospeech.TextToSpeechClient()
        
        # 간단한 목소리 목록 조회로 연결 테스트
        response = client.list_voices()
        
        if response.voices:
            return "Google TTS API에 성공적으로 연결되었습니다."
        else:
            return "Google TTS API에 연결되었으나, 사용 가능한 목소리를 찾을 수 없습니다."

    except Exception as e:
        return f"Google TTS API 연결 중 오류 발생: {e}"

def get_tts_supported_languages():
    """Google TTS에서 지원하는 언어 목록을 동적으로 가져옵니다."""
    try:
        client = texttospeech.TextToSpeechClient()
        response = client.list_voices()
        
        languages = {}
        # BCP-47 language code (e.g., "en-US")를 사용하고, 중복을 제거합니다.
        for voice in response.voices:
            for lang_code in voice.language_codes:
                # 언어 코드로부터 언어 이름 (예: 'English (United States)')을 얻는 것은
                # 간단하지 않으므로, 여기서는 코드 자체를 사용하거나,
                # 필요한 주요 언어만 매핑 테이블을 만들어 사용할 수 있습니다.
                # 지금은 코드만 사용하겠습니다.
                languages[lang_code] = lang_code # 간단히 코드-코드 매핑
        
        # 제작 사양서에 명시된 언어 형식과 유사하게 맞추기 위한 임시 매핑
        spec_languages = {
            "ko-KR": "한국어", "en-US": "영어", "ja-JP": "일본어", "zh-CN": "중국어",
            "vi-VN": "베트남어", "id-ID": "인도네시아어", "it-IT": "이탈리아어",
            "es-US": "스페인어", "fr-FR": "프랑스어", "de-DE": "독일어"
        }

        # TTS API가 지원하는 언어 중, 우리가 사용하고자 하는 언어 목록만 필터링
        supported_languages = {}
        for code, name in spec_languages.items():
            if code in languages:
                supported_languages[name] = code

        # API에서 가져온 목록이 비어있을 경우 대비
        if not supported_languages:
            return {name: code.split('-')[0] for name, code in {
                "한국어": "ko-KR", "영어": "en-US", "일본어": "ja-JP", "중국어": "zh-CN",
                "베트남어": "vi-VN", "인도네시아어": "id-ID", "이탈리아어": "it-IT",
                "스페인어": "es-US", "프랑스어": "fr-FR", "독일어": "de-DE"
            }.items()}
            
        return supported_languages

    except Exception as e:
        print(f"Google TTS 언어 목록을 가져오는 중 오류 발생: {e}")
        # 오류 발생 시 기존의 하드코딩된 목록 반환
        return {name: code.split('-')[0] for name, code in {
            "한국어": "ko-KR", "영어": "en-US", "일본어": "ja-JP", "중국어": "zh-CN",
            "베트남어": "vi-VN", "인도네시아어": "id-ID", "이탈리아어": "it-IT",
            "스페인어": "es-US", "프랑스어": "fr-FR", "독일어": "de-DE"
        }.items()}

def get_voices_for_language(language_code):
    """특정 언어 코드에 해당하는 모든 음성(화자) 목록을 가져옵니다."""
    try:
        client = texttospeech.TextToSpeechClient()
        voices = client.list_voices(language_code=language_code).voices
        
        voice_details = []
        for voice in voices:
            # Construct a more descriptive display name
            display_name = f"{voice.name} ({voice.ssml_gender.name.lower()}, {', '.join(voice.language_codes)})"
            voice_details.append({
                "name": voice.name,
                "display_name": display_name
            })
        
        # Sort by display_name for better readability in UI
        return sorted(voice_details, key=lambda x: x["display_name"])
    except Exception as e:
        print(f"'{language_code}'에 대한 음성 목록을 가져오는 중 오류 발생: {e}")
        return []

def synthesize_speech(text_or_ssml, language_code, voice_name, *, audio_encoding: str = "LINEAR16", sample_rate_hz: int | None = None, enable_timepoints: bool = False):
    """주어진 텍스트/SSML, 언어, 음성을 사용하여 오디오 데이터를 생성합니다.

    audio_encoding: "LINEAR16" | "MP3"
    """
    try:
        client = texttospeech.TextToSpeechClient()

        is_ssml = isinstance(text_or_ssml, str) and text_or_ssml.strip().startswith("<")
        if is_ssml:
            input_data = texttospeech.SynthesisInput(ssml=text_or_ssml)
        else:
            input_data = texttospeech.SynthesisInput(text=text_or_ssml)

        voice_params = texttospeech.VoiceSelectionParams(
            language_code=language_code, name=voice_name
        )
        if "Studio" in voice_name:
            voice_params.model = "studio"

        encoding_enum = texttospeech.AudioEncoding.LINEAR16 if audio_encoding == "LINEAR16" else texttospeech.AudioEncoding.MP3
        
        # WaveNet/Studio는 24000Hz에서 최적의 품질을 보여줌. 지정되지 않은 경우 24000을 기본값으로 사용.
        final_sample_rate = sample_rate_hz if sample_rate_hz is not None else 24000
        audio_config = texttospeech.AudioConfig(
            audio_encoding=encoding_enum,
            sample_rate_hertz=final_sample_rate
        )

        # 최신 API에서는 enable_time_pointing이 지원되지 않으므로 기본 호출만 사용
        response = client.synthesize_speech(
            input=input_data, voice=voice_params, audio_config=audio_config
        )
        return response.audio_content
    except Exception as e:
        # SSML 미지원 음성인 경우 텍스트로 자동 폴백
        try:
            message = str(e)
            if is_ssml and ("does not support SSML" in message or "support SSML" in message or "SSML" in message):
                # 태그 제거하여 순수 텍스트 생성
                plain_text = re.sub(r"<[^>]+>", "", text_or_ssml)
                client = texttospeech.TextToSpeechClient()
                input_text = texttospeech.SynthesisInput(text=plain_text)
                voice_params = texttospeech.VoiceSelectionParams(language_code=language_code, name=voice_name)
                if "Studio" in voice_name:
                    voice_params.model = "studio"
                encoding_enum = texttospeech.AudioEncoding.LINEAR16 if audio_encoding == "LINEAR16" else texttospeech.AudioEncoding.MP3
                if sample_rate_hz:
                    audio_config = texttospeech.AudioConfig(audio_encoding=encoding_enum, sample_rate_hertz=sample_rate_hz)
                else:
                    audio_config = texttospeech.AudioConfig(audio_encoding=encoding_enum)
                resp2 = client.synthesize_speech(input=input_text, voice=voice_params, audio_config=audio_config)
                return resp2.audio_content
        except Exception:
            pass
        print(f"음성 합성 중 오류 발생: {e}")
        return None


def _ensure_output_dir(project_name: str, identifier: str) -> str:
    """출력 디렉토리 경로를 생성하고 반환합니다."""
    out_dir = os.path.join(config.OUTPUT_PATH, project_name, identifier)
    os.makedirs(out_dir, exist_ok=True)
    return out_dir


def _read_master_prompt() -> str:
    """루트의 'AI Prompt.txt' 내용을 읽어 반환합니다."""
    prompt_path = os.path.join(config.BASE_DIR, "AI Prompt.txt")
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


def _build_prompt_with_params(master_prompt: str, params: dict) -> str:
    """마스터 프롬프트의 플레이스홀더를 params 값으로 치환하여 최종 프롬프트를 생성합니다."""
    prompt = master_prompt
    for key, value in params.items():
        prompt = prompt.replace(f"{{{key}}}", str(value))
    return prompt


def _parse_json_from_text(text: str) -> dict:
    """모델 응답 텍스트에서 JSON 객체를 최대한 견고하게 파싱합니다."""
    try:
        return json.loads(text)
    except Exception:
        # ```json ... ``` 혹은 앞뒤 설명 제거
        try:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                cleaned = text[start : end + 1]
                return json.loads(cleaned)
        except Exception:
            pass
        raise


def generate_ai_data(params: dict, model_name: str, project_name: str, identifier: str) -> dict:
    """
    - 마스터 프롬프트 + 입력 파라미터로 최종 프롬프트를 구성
    - Gemini 호출로 JSON 문자열 수신 후 파싱
    - ./output/{project_name}/{identifier}/에 프롬프트(.txt)와 결과(.json) 저장

    반환값: {
      "out_dir": str,
      "prompt_path": str,
      "json_path": str,
      "data": dict
    }
    """
    # 출력 경로 준비
    out_dir = _ensure_output_dir(project_name, identifier)

    # 프롬프트 구성 및 저장
    master_prompt = _read_master_prompt()
    final_prompt = _build_prompt_with_params(master_prompt, params)
    prompt_path = os.path.join(out_dir, f"{identifier}_prompt.txt")
    with open(prompt_path, "w", encoding="utf-8") as f:
        f.write(final_prompt)

    # Gemini 호출
    if not config.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY가 설정되어 있지 않습니다.")
    genai.configure(api_key=config.GEMINI_API_KEY)
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(final_prompt)
    text = getattr(response, "text", None) or ""
    if not text:
        # 일부 SDK 버전은 candidates[0].content.parts[0].text 형태일 수 있음
        try:
            candidates = getattr(response, "candidates", [])
            if candidates and candidates[0].content.parts:
                text = candidates[0].content.parts[0].text
        except Exception:
            pass
    if not text:
        raise RuntimeError("Gemini 응답에서 텍스트를 찾을 수 없습니다.")

    try:
        data = _parse_json_from_text(text)
    except json.JSONDecodeError:
        print("--- [JSON 파싱 오류] ---")
        print("AI가 반환한 원본 텍스트:")
        print(text)
        print("--------------------------")
        raise RuntimeError("AI 응답을 JSON으로 파싱하는 데 실패했습니다. 콘솔 로그에서 원본 응답을 확인하세요.")

    # 결과 저장
    json_path = os.path.join(out_dir, f"{identifier}_ai.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return {
        "out_dir": out_dir,
        "prompt_path": prompt_path,
        "json_path": json_path,
        "data": data,
    }


def save_outputs_from_ai_data(data: dict, project_name: str, identifier: str) -> dict:
    """AI JSON 데이터에서 스크립트별 텍스트 파일을 저장합니다.

    저장 파일 예:
    - videoTitleSuggestions.txt, title.txt
    - videoDescription.txt
    - videoKeywords.txt, keywords.txt
    - thumbnailTextVersions.txt, thumbnail.txt
    - intro.txt, introScript.txt
    - ending.txt, endingScript.txt
    - fullVideoScript.txt, dialogue.txt
    """
    out_dir = _ensure_output_dir(project_name, identifier)

    saved: dict = {}

    def _write(name: str, content: str):
        if content is None:
            return None
        path = os.path.join(out_dir, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        saved[name] = path
        return path

    # Titles
    titles = data.get("videoTitleSuggestions") or []
    if isinstance(titles, list) and titles:
        _write("videoTitleSuggestions.txt", "\n".join(titles))
        _write("title.txt", titles[0])

    # Description
    desc = data.get("videoDescription")
    if isinstance(desc, str):
        _write("videoDescription.txt", desc)

    # Keywords
    keywords = data.get("videoKeywords") or []
    if isinstance(keywords, list) and keywords:
        kw_text = ", ".join(keywords)
        _write("videoKeywords.txt", kw_text)
        _write("keywords.txt", kw_text)

    # Thumbnail texts
    thumbs = data.get("thumbnailTextVersions") or []
    if isinstance(thumbs, list) and thumbs:
        lines = []
        first_text = None
        for i, v in enumerate(thumbs, 1):
            t = (v or {}).get("text") or ""
            c = (v or {}).get("imageConcept") or ""
            if first_text is None and t:
                first_text = t
            lines.append(f"[버전 {i}]\n{t}\n- 콘셉트: {c}\n")
        _write("thumbnailTextVersions.txt", "\n".join(lines))
        if first_text:
            _write("thumbnail.txt", first_text)

    # Intro/Ending
    intro = data.get("introScript")
    if isinstance(intro, str):
        _write("intro.txt", intro)
        _write("introScript.txt", intro)
    ending = data.get("endingScript")
    if isinstance(ending, str):
        _write("ending.txt", ending)
        _write("endingScript.txt", ending)

    # Dialogue CSV
    dialogue_csv = (data.get("fullVideoScript") or {}).get("dialogueCsv")
    if isinstance(dialogue_csv, str) and dialogue_csv.strip():
        _write("fullVideoScript.txt", dialogue_csv)
        _write("dialogue.txt", dialogue_csv)

    # 장면 묘사 파일은 더 이상 생성하지 않으며, 기존 파일이 있으면 삭제합니다.
    try:
        legacy_path = os.path.join(out_dir, "dialogueVideoSceneDescription.txt")
        if os.path.exists(legacy_path):
            os.remove(legacy_path)
    except Exception:
        pass

    return saved
