"""
Google Cloud Text-to-Speech API를 사용한 오디오 생성기

SSML을 MP3로 변환하고 정확한 타이밍 정보를 추출합니다.
"""

import os
import json
import tempfile
import subprocess
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
    
    def _synthesize_text_segment(self, text: str, voice_name: str, language_code: str, output_path: str) -> bool:
        """단일 텍스트 조각을 음성으로 합성합니다."""
        if not self.client or not text or not voice_name or not language_code:
            print(f"TTS 클라이언트가 초기화되지 않았거나, 필수 정보가 누락되었습니다. Voice: {voice_name}, Lang: {language_code}, Text: {text[:20]}...")
            return False
        try:
            synthesis_input = texttospeech.SynthesisInput(text=text)
            voice_params = texttospeech.VoiceSelectionParams(
                language_code=language_code,
                name=voice_name
            )
            
            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice_params,
                audio_config=self.audio_config
            )
            
            with open(output_path, "wb") as out:
                out.write(response.audio_content)
            
            print(f"✅ 오디오 세그먼트 생성: {os.path.basename(output_path)}")
            return True

        except Exception as e:
            print(f"❌ 오디오 세그먼트 생성 실패 ({voice_name}): {e}")
            return False
    
    def generate_audio_from_manifest(self, manifest_data: Dict[str, Any], 
                                   output_dir: str, script_type: str = "conversation") -> Tuple[bool, str]:
        """
        Manifest에서 장면별 오디오 세그먼트를 생성하고 병합하여 최종 오디오 파일을 만듭니다.
        """
        try:
            project_name = manifest_data.get("project_name", "untitled_project")
            identifier = manifest_data.get("identifier", project_name)
            scenes = manifest_data.get("scenes", [])

            # 1. 화자 설정 로드
            voice_configs = self._load_voice_configs(project_name, identifier)
            if not voice_configs:
                print("화자 설정이 없어 오디오 생성을 중단합니다.")
                return False, ""

            # 2. 임시 디렉토리 생성
            temp_dir = tempfile.mkdtemp(prefix="audio_segments_")
            segment_paths = []

            # 3. 장면별, 파트별 오디오 세그먼트 생성
            for scene in scenes:
                scene_segments = self._generate_segments_for_scene(scene, voice_configs, temp_dir)
                if not scene_segments:
                    print(f"장면 {scene.get('sequence')} 오디오 생성 실패. 전체 프로세스를 중단합니다.")
                    return False, ""
                segment_paths.extend(scene_segments)

            # 4. 최종 오디오 파일 병합
            os.makedirs(output_dir, exist_ok=True)
            english_script_type = {"회화": "conversation", "대화": "conversation", "인트로": "intro", "엔딩": "ending"}.get(script_type, script_type)
            final_audio_path = os.path.join(output_dir, f"{identifier}_{english_script_type}.mp3")

            success = self.merge_audio_segments(segment_paths, final_audio_path)

            # 5. 임시 파일 정리 (필요 시)
            # for path in segment_paths: os.remove(path)
            # os.rmdir(temp_dir)

            if success:
                print(f"✅ 최종 오디오 파일 생성 완료: {final_audio_path}")
                return True, final_audio_path
            else:
                print("❌ 최종 오디오 파일 병합 실패")
                return False, ""

        except Exception as e:
            import traceback
            print(f"❌ Manifest 오디오 생성 실패: {e}")
            print(traceback.format_exc())
            return False, ""

    def _generate_segments_for_scene(self, scene: Dict[str, Any], voice_configs: Dict[str, Any], temp_dir: str) -> List[str]:
        """한 장면을 구성하는 모든 오디오 세그먼트(음성+무음)를 생성합니다."""
        scene_type = scene.get("type")
        sequence = scene.get("sequence", scene.get("id", "unknown"))
        segment_paths = []

        if scene_type == "conversation":
            # 1. 원어 스크립트
            native_script = scene.get("native_script", "")
            if native_script:
                voice_info = voice_configs.get("native", {})
                output_path = os.path.join(temp_dir, f"scene_{sequence}_native.mp3")
                success = self._synthesize_text_segment(native_script, voice_info.get("name"), voice_info.get("language"), output_path)
                if not success: return []
                segment_paths.append(output_path)

            # 2. 1초 무음
            silence_path = self._create_silence_segment(1, os.path.join(temp_dir, f"scene_{sequence}_silence_1.mp3"))
            if not silence_path: return []
            segment_paths.append(silence_path)

            # 3. 학습어 스크립트 (4회 반복)
            learning_script = scene.get("learning_script", "")
            if learning_script:
                for i in range(1, 5):
                    voice_info = voice_configs.get(f"learner_{i}", {})
                    output_path = os.path.join(temp_dir, f"scene_{sequence}_learner_{i}.mp3")
                    success = self._synthesize_text_segment(learning_script, voice_info.get("name"), voice_info.get("language"), output_path)
                    if not success: return []
                    segment_paths.append(output_path)

                    # 마지막 학습어 뒤에는 무음 없음
                    if i < 4:
                        silence_path = self._create_silence_segment(1, os.path.join(temp_dir, f"scene_{sequence}_silence_learner_{i}.mp3"))
                        if not silence_path: return []
                        segment_paths.append(silence_path)
            
            return segment_paths

        elif scene_type in ["intro", "ending"]:
            script_text = scene.get("full_script") or scene.get("script_text", "")
            if script_text:
                voice_info = voice_configs.get("native", {})
                output_path = os.path.join(temp_dir, f"scene_{sequence}_{scene_type}.mp3")
                success = self._synthesize_text_segment(script_text, voice_info.get("name"), voice_info.get("language"), output_path)
                if not success: return []
                segment_paths.append(output_path)
            return segment_paths

        else:
            print(f"알 수 없는 장면 타입: {scene_type}")
            return []

    def _create_silence_segment(self, duration_seconds: int, output_path: str) -> Optional[str]:
        """지정된 길이의 무음 MP3 파일을 생성합니다."""
        try:
            # FFmpeg를 사용하여 무음 오디오 생성 (macOS 호환성을 위해 큰따옴표 이스케이프 처리)
            command = f'ffmpeg -f lavfi -i anullsrc=r=22050:cl=mono -t {duration_seconds} -q:a 9 -acodec libmp3lame "{output_path}"'
            
            # FFmpeg 실행
            result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
            
            print(f"✅ 무음 세그먼트 생성: {os.path.basename(output_path)}")
            return output_path
        except subprocess.CalledProcessError as e:
            print(f"❌ 무음 세그먼트 생성 실패 (FFmpeg 오류): {e.stderr}")
            return None
        except Exception as e:
            print(f"❌ 무음 세그먼트 생성 중 예외 발생: {e}")
            return None

    def _load_voice_configs(self, project_name: str, identifier: str) -> Optional[Dict[str, Any]]:
        """화자 설정 파일 (speaker.json)을 로드하고 SSMLBuilder에 맞는 형식으로 변환합니다."""
        try:
            # config.py 또는 다른 설정 관리자에서 OUTPUT_PATH를 가져와야 합니다.
            # 여기서는 상대 경로를 사용하지만, 실제로는 절대 경로를 구성해야 합니다.
            speaker_config_path = os.path.join("output", project_name, identifier, f"{identifier}_speaker.json")

            if not os.path.exists(speaker_config_path):
                print(f"⚠️ 화자 설정 파일을 찾을 수 없습니다: {speaker_config_path}. 기본 설정을 사용합니다.")
                return None

            with open(speaker_config_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            
            print(f"✅ 화자 설정을 불러왔습니다: {speaker_config_path}")

            # SSMLBuilder가 기대하는 형식으로 변환
            voice_configs = {
                "native": {
                    "name": settings.get("native_speaker"),
                    "language": self._extract_lang_code(settings.get("native_speaker"))
                }
            }
            
            learner_speakers = settings.get("learner_speakers", [])
            for i, speaker_name in enumerate(learner_speakers):
                voice_configs[f"learner_{i+1}"] = {
                    "name": speaker_name,
                    "language": self._extract_lang_code(speaker_name)
                }
            
            return voice_configs

        except Exception as e:
            print(f"❌ 화자 설정 로드 실패: {e}. 기본 설정을 사용합니다.")
            return None

    def _extract_lang_code(self, voice_name: str) -> str:
        """음성 이름에서 언어 코드를 추출합니다 (예: ko-KR-Standard-A -> ko-KR)."""
        if not voice_name:
            return ""
        parts = voice_name.split('-')
        if len(parts) >= 2:
            return f"{parts[0]}-{parts[1]}"
        return ""
    
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
        """FFmpeg를 사용하여 여러 오디오 세그먼트를 하나로 병합합니다."""
        if not segment_paths:
            print("병합할 오디오 세그먼트가 없습니다.")
            return False
        try:
            # FFmpeg는 파일 경로에 공백이 있을 경우를 대비해 경로를 따옴표로 감싸는 것이 안전합니다.
            # 또한, 윈도우와 macOS/Linux의 경로 구분자 차이를 고려해야 합니다.
            # 여기서는 Python의 os.path.abspath를 사용하여 절대 경로를 보장합니다.
            
            # merge list 파일 생성
            list_content = ""
            for path in segment_paths:
                # 경로의 백슬래시를 슬래시로 변경 (ffmpeg 호환성)
                safe_path = os.path.abspath(path).replace('\\', '/')
                list_content += f"file '{safe_path}'\n"
            
            # 임시 파일에 리스트 작성
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".txt", encoding='utf-8') as tmp_list_file:
                tmp_list_file.write(list_content)
                merge_list_path = tmp_list_file.name

            print(f"✅ 병합 리스트 생성: {merge_list_path}")

            # FFmpeg 병합 명령 실행
            command = f'ffmpeg -f concat -safe 0 -i "{merge_list_path}" -c copy "{output_path}" -y'
            print(f"실행할 FFmpeg 명령: {command}")

            result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
            
            print(f"✅ 오디오 병합 완료: {output_path}")
            os.remove(merge_list_path) # 임시 리스트 파일 삭제
            return True

        except subprocess.CalledProcessError as e:
            print(f"❌ 오디오 병합 실패 (FFmpeg 오류): {e.stderr}")
            if os.path.exists(merge_list_path):
                os.remove(merge_list_path)
            return False
        except Exception as e:
            print(f"❌ 오디오 병합 중 예외 발생: {e}")
            if 'merge_list_path' in locals() and os.path.exists(merge_list_path):
                os.remove(merge_list_path)
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
            voice_params = texttospeech.VoiceSelectionParams(language_code="ko-KR")
            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice_params,
                audio_config=self.audio_config
            )
            
            return len(response.audio_content) > 0
            
        except Exception as e:
            print(f"TTS 연결 테스트 실패: {e}")
            return False
