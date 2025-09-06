"""
Google Cloud Text-to-Speech API를 사용한 오디오 생성기

SSML을 MP3로 변환하고 정확한 타이밍 정보를 추출합니다.
"""

import os
import json
import tempfile
from typing import Dict, List, Any, Optional, Tuple
from google.cloud import texttospeech
from google.cloud.texttospeech_v1 import AudioConfig, AudioEncoding
import wave
import struct
import io

from .ssml_builder import SSMLBuilder


class AudioGenerator:
    """오디오 생성 클래스"""
    
    def __init__(self, credentials_path: Optional[str] = None):
        """
        오디오 생성기 초기화
        
        Args:
            credentials_path: Google Cloud 인증 파일 경로
        """
        self.ssml_builder = SSMLBuilder()
        self.client = None
        self._initialize_client(credentials_path)
        
        # 오디오 설정
        self.audio_config = AudioConfig(
            audio_encoding=AudioEncoding.MP3,
            sample_rate_hertz=22050,
            effects_profile_id=["headphone-class-device"]
        )
    
    def _initialize_client(self, credentials_path: Optional[str] = None):
        """Google Cloud TTS 클라이언트 초기화"""
        try:
            if credentials_path and os.path.exists(credentials_path):
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
            
            self.client = texttospeech.TextToSpeechClient()
            print("✅ Google Cloud TTS 클라이언트 초기화 성공")
            
        except Exception as e:
            print(f"⚠️ Google Cloud TTS 클라이언트 초기화 실패: {e}")
            print("🔧 로컬 TTS 또는 다른 서비스 사용을 고려하세요")
            self.client = None
    
    def generate_audio_from_ssml(self, ssml_content: str, output_path: str) -> bool:
        """
        SSML에서 MP3 오디오 생성
        
        Args:
            ssml_content: SSML 내용
            output_path: 출력 MP3 파일 경로
            
        Returns:
            bool: 성공 여부
        """
        if not self.client:
            print("❌ TTS 클라이언트가 초기화되지 않았습니다")
            return False
        
        try:
            # SSML 유효성 검사
            if not self.ssml_builder.validate_ssml(ssml_content):
                print("❌ SSML 유효성 검사 실패")
                return False
            
            # TTS 요청 생성
            synthesis_input = texttospeech.SynthesisInput(ssml=ssml_content)
            
            # 오디오 생성 요청
            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=texttospeech.Voice(
                    language_code="ko-KR",
                    name="ko-KR-Standard-A"
                ),
                audio_config=self.audio_config
            )
            
            # MP3 파일 저장
            with open(output_path, "wb") as out:
                out.write(response.audio_content)
            
            print(f"✅ 오디오 생성 완료: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ 오디오 생성 실패: {e}")
            return False
    
    def generate_audio_from_manifest(self, manifest_data: Dict[str, Any], 
                                   output_dir: str) -> Tuple[bool, str]:
        """
        Manifest에서 전체 오디오 생성
        
        Args:
            manifest_data: Manifest 데이터
            output_dir: 출력 디렉토리
            
        Returns:
            Tuple[bool, str]: (성공 여부, 생성된 오디오 파일 경로)
        """
        try:
            # 출력 디렉토리 생성
            os.makedirs(output_dir, exist_ok=True)
            
            # SSML 생성
            ssml_content = self.ssml_builder.build_manifest_ssml(manifest_data)
            
            # SSML 파일 저장
            ssml_path = os.path.join(output_dir, "manifest.ssml")
            self.ssml_builder.create_ssml_file(ssml_content, ssml_path)
            print(f"✅ SSML 파일 생성: {ssml_path}")
            
            # MP3 오디오 생성
            mp3_path = os.path.join(output_dir, "manifest_audio.mp3")
            success = self.generate_audio_from_ssml(ssml_content, mp3_path)
            
            if success:
                # 타이밍 정보 추출
                timing_info = self.extract_timing_info(ssml_content, mp3_path)
                
                # 타이밍 정보 저장
                timing_path = os.path.join(output_dir, "timing_info.json")
                with open(timing_path, 'w', encoding='utf-8') as f:
                    json.dump(timing_info, f, ensure_ascii=False, indent=2)
                print(f"✅ 타이밍 정보 저장: {timing_path}")
                
                return True, mp3_path
            else:
                return False, ""
                
        except Exception as e:
            print(f"❌ Manifest 오디오 생성 실패: {e}")
            return False, ""
    
    def extract_timing_info(self, ssml_content: str, audio_path: str) -> Dict[str, Any]:
        """
        SSML과 오디오에서 타이밍 정보 추출
        
        Args:
            ssml_content: SSML 내용
            audio_path: 오디오 파일 경로
            
        Returns:
            Dict[str, Any]: 타이밍 정보
        """
        # SSML에서 mark 태그 정보 추출
        marks = self.ssml_builder.get_mark_timings(ssml_content)
        
        # 오디오 길이 계산 (대략적 추정)
        audio_duration = self._estimate_audio_duration(audio_path)
        
        # 타이밍 정보 구성
        timing_info = {
            "audio_file": audio_path,
            "total_duration": audio_duration,
            "marks": marks,
            "scenes": self._analyze_scene_timings(marks, audio_duration)
        }
        
        return timing_info
    
    def _estimate_audio_duration(self, audio_path: str) -> float:
        """오디오 파일 길이 추정 (초 단위)"""
        try:
            # MP3 파일 길이를 정확히 계산하는 것은 복잡하므로
            # 파일 크기와 비트레이트를 기반으로 추정
            file_size = os.path.getsize(audio_path)
            
            # MP3 비트레이트 (kbps) - 기본값 128kbps
            bitrate = 128 * 1000  # bits per second
            
            # 파일 크기 (bits) / 비트레이트 = 초
            duration = (file_size * 8) / bitrate
            
            return round(duration, 2)
            
        except Exception as e:
            print(f"⚠️ 오디오 길이 추정 실패: {e}")
            return 0.0
    
    def _analyze_scene_timings(self, marks: List[Dict[str, Any]], 
                              total_duration: float) -> List[Dict[str, Any]]:
        """장면별 타이밍 분석"""
        scenes = []
        current_scene = None
        
        for mark in marks:
            mark_name = mark["name"]
            
            # 장면 번호 추출
            if "scene_" in mark_name:
                parts = mark_name.split("_")
                if len(parts) >= 2:
                    scene_num = parts[1]
                    
                    if current_scene is None or current_scene["sequence"] != scene_num:
                        # 새 장면 시작
                        current_scene = {
                            "sequence": scene_num,
                            "type": "conversation",
                            "timings": {
                                "screen1": {"start": None, "end": None},
                                "screen2": {"start": None, "end": None}
                            }
                        }
                        scenes.append(current_scene)
                    
                    # 타이밍 정보 업데이트
                    if "screen1_start" in mark_name:
                        current_scene["timings"]["screen1"]["start"] = mark["position"]
                    elif "screen1_end" in mark_name:
                        current_scene["timings"]["screen1"]["end"] = mark["position"]
                    elif "screen2_start" in mark_name:
                        current_scene["timings"]["screen2"]["start"] = mark["position"]
                    elif "screen2_end" in mark_name:
                        current_scene["timings"]["screen2"]["end"] = mark["position"]
        
        return scenes
    
    def create_audio_segments(self, manifest_data: Dict[str, Any], 
                            output_dir: str) -> List[str]:
        """
        각 장면별로 개별 오디오 세그먼트 생성
        
        Args:
            manifest_data: Manifest 데이터
            output_dir: 출력 디렉토리
            
        Returns:
            List[str]: 생성된 오디오 파일 경로 리스트
        """
        segments = []
        scenes = manifest_data.get("scenes", [])
        
        for scene in scenes:
            scene_type = scene.get("type", "")
            scene_id = scene.get("id", "")
            
            if scene_type == "conversation":
                # conversation 타입은 별도 SSML 생성
                ssml_content = self.ssml_builder.build_conversation_ssml(scene)
                
                # 개별 오디오 파일 생성
                segment_path = os.path.join(output_dir, f"{scene_id}_audio.mp3")
                if self.generate_audio_from_ssml(ssml_content, segment_path):
                    segments.append(segment_path)
            
            elif scene_type in ["intro", "ending"]:
                # intro/ending 타입
                ssml_content = self.ssml_builder.build_intro_ending_ssml(scene)
                
                segment_path = os.path.join(output_dir, f"{scene_id}_audio.mp3")
                if self.generate_audio_from_ssml(ssml_content, segment_path):
                    segments.append(segment_path)
            
            elif scene_type == "dialogue":
                # dialogue 타입
                ssml_content = self.ssml_builder.build_dialogue_ssml(scene)
                
                segment_path = os.path.join(output_dir, f"{scene_id}_audio.mp3")
                if self.generate_audio_from_ssml(ssml_content, segment_path):
                    segments.append(segment_path)
        
        return segments
    
    def merge_audio_segments(self, segment_paths: List[str], 
                           output_path: str) -> bool:
        """
        여러 오디오 세그먼트를 하나로 병합
        
        Args:
            segment_paths: 세그먼트 파일 경로 리스트
            output_path: 출력 파일 경로
            
        Returns:
            bool: 성공 여부
        """
        try:
            # 간단한 병합 (실제로는 더 정교한 오디오 처리 필요)
            # 여기서는 파일 리스트만 생성
            merge_list_path = output_path.replace('.mp3', '_merge_list.txt')
            
            with open(merge_list_path, 'w', encoding='utf-8') as f:
                for segment_path in segment_paths:
                    f.write(f"file '{segment_path}'\n")
            
            print(f"✅ 병합 리스트 생성: {merge_list_path}")
            print("🔧 FFmpeg를 사용하여 실제 병합을 수행하세요:")
            print(f"ffmpeg -f concat -safe 0 -i {merge_list_path} -c copy {output_path}")
            
            return True
            
        except Exception as e:
            print(f"❌ 오디오 병합 실패: {e}")
            return False
    
    def get_voice_list(self) -> List[Dict[str, str]]:
        """사용 가능한 음성 목록 반환"""
        if not self.client:
            return []
        
        try:
            voices = self.client.list_voices()
            voice_list = []
            
            for voice in voices.voices:
                voice_list.append({
                    "name": voice.name,
                    "language_code": voice.language_codes[0] if voice.language_codes else "",
                    "gender": voice.ssml_gender.name if voice.ssml_gender else ""
                })
            
            return voice_list
            
        except Exception as e:
            print(f"⚠️ 음성 목록 조회 실패: {e}")
            return []
    
    def test_tts_connection(self) -> bool:
        """TTS 연결 테스트"""
        if not self.client:
            return False
        
        try:
            # 간단한 테스트 요청
            synthesis_input = texttospeech.SynthesisInput(text="테스트")
            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=texttospeech.Voice(language_code="ko-KR"),
                audio_config=self.audio_config
            )
            
            return len(response.audio_content) > 0
            
        except Exception as e:
            print(f"TTS 연결 테스트 실패: {e}")
            return False
