# src/pipeline/media_factory.py

import os
import json
import subprocess
import tempfile
from typing import Dict, Any, List, Tuple
from google.cloud import texttospeech

from ..settings import MergedSettings
from .renderers.png_renderer import PNGRenderer

class MediaFactory:
    """
    오디오, 이미지, 타임라인, 비디오 생성을 총괄하는 통합 클래스.
    제작 사양서에 따른 복잡한 미디어 생성 파이프라인을 관리합니다.
    """
    def __init__(self, merged_settings: MergedSettings):
        self.settings = merged_settings
        self.png_renderer = PNGRenderer(merged_settings)
        self.tts_client = texttospeech.TextToSpeechClient()
        print("✅ MediaFactory 초기화 완료")

    # --- SSML 빌더 로직 ---
    def _build_conversation_ssml(self, scene_data: Dict[str, Any]) -> str:
        # ... (회화용 SSML 생성 로직) ...
        return f"""<?xml version="1.0"?>
<speak version="1.1" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="ko-KR">
    <voice name="{scene_data['native_voice']}"><mark name="scene_{scene_data['sequence']}_screen1_start"/><prosody rate="medium">{scene_data['native_script']}</prosody><mark name="scene_{scene_data['sequence']}_screen1_end"/></voice>
    <break time="1s"/>
    <mark name="scene_{scene_data['sequence']}_screen2_start"/>
    <voice name="{scene_data['learner_voices'][0]}"><prosody rate="medium">{scene_data['learning_script']}</prosody></voice><break time="1s"/>
    <voice name="{scene_data['learner_voices'][1]}"><prosody rate="medium">{scene_data['learning_script']}</prosody></voice><break time="1s"/>
    <voice name="{scene_data['learner_voices'][2]}"><prosody rate="medium">{scene_data['learning_script']}</prosody></voice><break time="1s"/>
    <voice name="{scene_data['learner_voices'][3]}"><prosody rate="medium">{scene_data['learning_script']}</prosody></voice>
    <mark name="scene_{scene_data['sequence']}_screen2_end"/>
</speak>"""

    def _build_intro_ending_ssml(self, full_script: str, voice_name: str) -> str:
        # ... (인트로/엔딩용 SSML 생성 로직) ...
        sentences = [s.strip() for s in full_script.split('\n') if s.strip()]
        ssml_body = ""
        for i, sentence in enumerate(sentences):
            ssml_body += f'<mark name="sentence_{i+1}_start"/><prosody rate="medium">{sentence}</prosody><mark name="sentence_{i+1}_end"/><break time="1s"/>'
        return f"""<?xml version="1.0"?><speak version="1.1" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="ko-KR"><voice name="{voice_name}">{ssml_body}</voice></speak>"""


    # --- 오디오 및 타이밍 생성 ---
    def create_audio_and_timing(self, ssml_content: str, output_audio_path: str, output_timing_path: str) -> bool:
        print(f"🔊 [오디오 생성] 시작: {os.path.basename(output_audio_path)}")
        try:
            synthesis_input = texttospeech.SynthesisInput(ssml=ssml_content)
            voice = texttospeech.VoiceSelectionParams(language_code="ko-KR") # 기본값, SSML 내부 voice 태그가 우선
            audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3, sample_rate_hertz=22050)
            
            request = texttospeech.SynthesizeSpeechRequest(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config,
                enable_time_pointing=[texttospeech.SynthesizeSpeechRequest.TimepointType.SSML_MARK]
            )
            response = self.tts_client.synthesize_speech(request=request)

            with open(output_audio_path, "wb") as out:
                out.write(response.audio_content)
            print(f"✅ [오디오 생성] 완료: {os.path.basename(output_audio_path)}")

            timing_data = [{"mark_name": timepoint.mark_name, "time_seconds": timepoint.time_seconds} for timepoint in response.timepoints]
            with open(output_timing_path, "w", encoding="utf-8") as f:
                json.dump(timing_data, f, indent=2)
            print(f"✅ [타이밍 추출] 완료: {os.path.basename(output_timing_path)}")
            return True
        except Exception as e:
            print(f"❌ [오디오/타이밍 생성] 실패: {e}")
            return False

    # --- 타임라인 빌더 ---
    def build_timeline(self, manifest_data: Dict[str, Any], timing_data: List[Dict[str, Any]], image_dir: str, audio_path: str) -> Dict[str, Any]:
        # ... (이전 답변의 타임라인 빌더 로직과 유사) ...
        pass

    # --- 비디오 렌더러 ---
    def render_video(self, timeline_data: Dict[str, Any], output_video_path: str) -> bool:
        # ... (이전 답변의 비디오 생성 로직과 유사) ...
        pass

    # --- 통합 파이프라인 ---
    def create_conversation_video(self, manifest_scene: Dict[str, Any], paths: Dict[str, str], resolution: Tuple[int, int]) -> bool:
        """회화 비디오 제작 파이프라인"""
        # 1. SSML 생성 (사양서에 맞게)
        # ... 
        
        # 2. 오디오 및 타이밍 생성
        # ...

        # 3. 이미지 생성 (2개 화면)
        # ...
        
        # 4. 타임라인 생성
        # ...

        # 5. 비디오 렌더링
        # ...
        return True # 성공 여부 반환

    def create_intro_ending_video(self, manifest_scene: Dict[str, Any], paths: Dict[str, str], resolution: Tuple[int, int], script_type: str) -> bool:
        """인트로/엔딩 비디오 제작 파이프라인"""
        # ... (인트로/엔딩에 맞는 전체 프로세스) ...
        return True # 성공 여부 반환