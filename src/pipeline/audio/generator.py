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
            self.client = None
    
    def _get_emotion_settings(self, script_type: str) -> Dict[str, Any]:
        """스크립트 타입별 감정 설정 반환"""
        
        if script_type in ["인트로", "intro"]:
            return {
                "use_ssml": False,  # SSML 미지원 화자 때문에 False로 설정
                "rate": "1.0",
                "pitch": "+1st", 
                "volume": "0dB",
                "emphasis": "moderate",
                "effects_profile": ["headphone-class-device", "telephony-class-application"],
                "description": "친근하고 자연스러운 일상 대화 (일반 텍스트)"
            }
        
        elif script_type in ["회화", "대화", "conversation"]:
            return {
                "use_ssml": False,  # SSML 미지원 화자 때문에 False로 설정
                "rate": "1.0",  # 정상 속도로 정확한 발음
                "pitch": "0st",  # 중립적 톤
                "volume": "0dB",  # 정상 볼륨
                "emphasis": "none",  # 강조 없음 (교육용)
                "effects_profile": ["headphone-class-device"],  # 기본 프로필만
                "description": "교육용 정확한 발음 (감정 최소화)"
            }
        
        elif script_type in ["엔딩", "ending"]:
            return {
                "use_ssml": False,  # SSML 미지원 화자 때문에 False로 설정
                "rate": "0.9",
                "pitch": "0st", 
                "volume": "0dB",
                "emphasis": "moderate",
                "effects_profile": ["headphone-class-device", "telephony-class-application"],
                "description": "따뜻하고 마무리하는 톤 (일반 텍스트)"
            }
        
        else:  # 기본값
            return {
                "use_ssml": False,
                "effects_profile": ["headphone-class-device"],
                "description": "기본 설정"
            }

    def _add_comma_pauses(self, text: str, script_type: str) -> str:
        """쉼표와 슬래시 위치에 자연스러운 휴지 추가 (SSML용)"""
        pause_time = self._get_comma_pause_time(script_type)
        # 쉼표와 슬래시 모두 휴지로 대체
        text_with_pauses = text.replace(',', f'<break time="{pause_time}"/>').replace('/', f'<break time="{pause_time}"/>')
        return text_with_pauses
    
    def _add_comma_pauses_plain_text(self, text: str, script_type: str) -> str:
        """쉼표와 슬래시 위치에 자연스러운 휴지 추가 (일반 텍스트용)"""
        pause_time = self._get_comma_pause_time(script_type)
        # 쉼표와 슬래시를 실제 휴지 시간으로 대체
        if pause_time == "0.5s":
            pause_dots = "..."  # 인트로/회화용
        elif pause_time == "0.6s":
            pause_dots = "...."  # 엔딩용
        elif pause_time == "0.2s":
            pause_dots = "."  # 최소 휴지
        else:
            pause_dots = ".."  # 기본값
        
        # 쉼표와 슬래시 모두 휴지로 대체
        text_with_pauses = text.replace(',', pause_dots).replace('/', pause_dots)
        return text_with_pauses

    def _get_comma_pause_time(self, script_type: str) -> str:
        """스크립트 타입별 쉼표 휴지 시간 반환"""
        
        if script_type in ["인트로", "intro"]:
            return "0.5s"  # 자연스러운 인사말
        elif script_type in ["엔딩", "ending"]:
            return "0.6s"  # 마무리 인사 (조금 더 느긋하게)
        elif script_type in ["회화", "대화", "conversation"]:
            return "0.5s"  # 회화에서도 0.5초 휴지
        else:
            return "0.3s"  # 기본값

    def _create_emotional_ssml(self, text: str, emotion_settings: Dict[str, Any], 
                              script_type: str = "conversation") -> str:
        """감정 설정에 따른 SSML 생성 (쉼표 휴지 포함, 화자 제외)"""
        
        # 인트로/엔딩인 경우 쉼표에 휴지 추가
        if script_type in ["인트로", "엔딩", "intro", "ending"]:
            text = self._add_comma_pauses(text, script_type)
        
        # SSML에는 감정 표현만 포함 (화자는 별도로 지정)
        return f"""<speak>
<prosody rate="{emotion_settings['rate']}" 
         pitch="{emotion_settings['pitch']}" 
         volume="{emotion_settings['volume']}">
    <emphasis level="{emotion_settings['emphasis']}">
        {text}
    </emphasis>
</prosody>
</speak>"""

    def _synthesize_segment_audio(self, text: str, output_path: str, voice_name: str, 
                                 language_code: str, script_type: str = "conversation") -> float:
        """개별 세그먼트 오디오 생성 및 정확한 길이 반환 (감정 표현 및 휴지 포함)"""
        try:
            if not self.client:
                print("❌ Google TTS 클라이언트가 초기화되지 않았습니다.")
                return 0.0
            
            # 감정 설정 가져오기
            emotion_settings = self._get_emotion_settings(script_type)
            
            # 화자는 Google TTS API 호출 시에 별도로 지정
            voice = texttospeech.VoiceSelectionParams(language_code=language_code, name=voice_name)
            
            # 감정 설정에 따른 AudioConfig 생성
            audio_config = AudioConfig(
                audio_encoding=AudioEncoding.MP3,
                sample_rate_hertz=22050,
                effects_profile_id=emotion_settings.get("effects_profile", ["headphone-class-device"])
            )
            
            # SSML 사용 여부에 따라 입력 방식 결정
            if emotion_settings.get("use_ssml", False):
                # SSML로 감정 표현 및 휴지 포함 (화자는 별도 지정)
                ssml_text = self._create_emotional_ssml(text, emotion_settings, script_type)
                synthesis_input = texttospeech.SynthesisInput(ssml=ssml_text)
                print(f"🎵 감정 표현 적용: {emotion_settings['description']}")
                
                # 휴지 시간 로깅
                if script_type in ["인트로", "엔딩", "회화", "대화", "intro", "ending", "conversation"]:
                    comma_count = text.count(',')
                    slash_count = text.count('/')
                    total_pause_count = comma_count + slash_count
                    pause_time = self._get_comma_pause_time(script_type)
                    pause_seconds = float(pause_time.replace('s', ''))
                    total_pause_time = total_pause_count * pause_seconds
                    
                    if total_pause_count > 0:
                        print(f"🎵 휴지 정보: 쉼표 {comma_count}개, 슬래시 {slash_count}개, 휴지 {pause_seconds}초씩, 총 {total_pause_time}초")
            else:
                # 일반 텍스트 (쉼표 휴지 포함)
                text_with_pauses = self._add_comma_pauses_plain_text(text, script_type)
                synthesis_input = texttospeech.SynthesisInput(text=text_with_pauses)
                
                # 휴지 시간 로깅
                if script_type in ["인트로", "엔딩", "회화", "대화", "intro", "ending", "conversation"]:
                    comma_count = text.count(',')
                    slash_count = text.count('/')
                    total_pause_count = comma_count + slash_count
                    pause_time = self._get_comma_pause_time(script_type)
                    pause_seconds = float(pause_time.replace('s', ''))
                    total_pause_time = total_pause_count * pause_seconds
                    
                    if total_pause_count > 0:
                        print(f"🎵 휴지 정보: 쉼표 {comma_count}개, 슬래시 {slash_count}개, 휴지 {pause_seconds}초씩, 총 {total_pause_time}초")
            
            # Google TTS API 호출 (화자는 voice 파라미터로 별도 지정)
            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "wb") as out:
                out.write(response.audio_content)
            
            duration = self._get_accurate_audio_duration(output_path)
            print(f"✅ 세그먼트 오디오 생성: {os.path.basename(output_path)} ({duration:.2f}초)")
            return duration
        except Exception as e:
            print(f"❌ 세그먼트 오디오 생성 실패: {e}")
            return 0.0

    def _create_silence_segment(self, duration_seconds: int, output_path: str) -> Optional[str]:
        """지정된 길이의 무음 MP3 파일을 생성합니다."""
        try:
            command = f'ffmpeg -f lavfi -i anullsrc=r=22050:cl=mono -t {duration_seconds} -q:a 9 -acodec libmp3lame "{output_path}"'
            subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
            print(f"✅ 무음 세그먼트 생성: {os.path.basename(output_path)}")
            return output_path
        except Exception as e:
            print(f"❌ 무음 세그먼트 생성 실패: {e}")
            return None

    def merge_audio_segments(self, segment_paths: List[str], output_path: str) -> bool:
        """FFmpeg를 사용하여 여러 오디오 세그먼트를 하나로 병합합니다."""
        if not segment_paths:
            print("병합할 오디오 세그먼트가 없습니다.")
            return False
        try:
            list_content = ""
            for path in segment_paths:
                safe_path = os.path.abspath(path).replace('\\', '/')
                list_content += f"file '{safe_path}'\n"
            
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".txt", encoding='utf-8') as tmp_list_file:
                tmp_list_file.write(list_content)
                merge_list_path = tmp_list_file.name

            command = f'ffmpeg -f concat -safe 0 -i "{merge_list_path}" -c copy "{output_path}" -y'
            subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
            
            print(f"✅ 오디오 병합 완료: {output_path}")
            os.remove(merge_list_path)
            return True
        except Exception as e:
            print(f"❌ 오디오 병합 실패: {e}")
            if 'merge_list_path' in locals() and os.path.exists(merge_list_path):
                os.remove(merge_list_path)
            return False
    
    def _load_speaker_config(self, output_dir: str, identifier: str) -> Dict[str, Any]:
        """화자 설정 파일을 로드합니다."""
        try:
            # output_dir는 mp3 디렉토리이므로, 상위 디렉토리에서 화자 설정 파일을 찾습니다
            # output_dir: output/kor-chn/kor-chn/mp3
            # base_dir: output/kor-chn/kor-chn
            base_dir = os.path.dirname(output_dir)  # mp3 디렉토리의 상위 디렉토리
            speaker_config_path = os.path.join(base_dir, f"{identifier}_speaker.json")
            
            print(f"🔍 화자 설정 파일 경로 확인: {speaker_config_path}")
            
            if not os.path.exists(speaker_config_path):
                print(f"⚠️ 화자 설정 파일을 찾을 수 없습니다: {speaker_config_path}")
                # 대안 경로들도 확인해보기
                alternative_paths = [
                    os.path.join(output_dir, f"{identifier}_speaker.json"),  # mp3 디렉토리 내
                    os.path.join(os.path.dirname(base_dir), f"{identifier}_speaker.json"),  # 더 상위 디렉토리
                ]
                
                for alt_path in alternative_paths:
                    if os.path.exists(alt_path):
                        print(f"✅ 대안 경로에서 화자 설정 파일 발견: {alt_path}")
                        speaker_config_path = alt_path
                        break
                else:
                    print(f"❌ 모든 경로에서 화자 설정 파일을 찾을 수 없습니다.")
                    return {}
            
            with open(speaker_config_path, 'r', encoding='utf-8') as f:
                speaker_config = json.load(f)
            
            print(f"✅ 화자 설정 로드 완료: {speaker_config_path}")
            print(f"  - 원어 화자: {speaker_config.get('native_speaker', 'N/A')}")
            print(f"  - 학습어 화자 수: {speaker_config.get('learner_count', 'N/A')}")
            print(f"  - 학습어 화자 목록: {speaker_config.get('learner_speakers', [])}")
            
            return speaker_config
        except Exception as e:
            print(f"❌ 화자 설정 로드 실패: {e}")
            return {}

    def generate_audio_and_timing(self, manifest_data: Dict, output_dir: str, script_type: str) -> Tuple[Optional[str], Optional[Dict]]:
        """
        (Refactored) 오디오와 타이밍 정보를 일관된 단일 프로세스에서 생성합니다.
        """
        try:
            print("🎵 [통합] 오디오 및 타이밍 생성 시작...")
            timing_info = {"total_duration": 0.0, "segments": []}
            segment_paths_for_merge = []
            temp_dir = tempfile.mkdtemp(prefix="audio_temp_")
            current_time = 0.0
            
            project_name = manifest_data.get("project_name", "untitled_project")
            identifier = manifest_data.get("identifier", project_name)
            
            # 화자 설정 로드
            speaker_config = self._load_speaker_config(output_dir, identifier)
            native_speaker = speaker_config.get('native_speaker', 'ko-KR-Standard-A')
            learner_speakers = speaker_config.get('learner_speakers', ['cmn-CN-Standard-A', 'cmn-CN-Standard-B', 'cmn-CN-Standard-C', 'cmn-CN-Standard-D'])

            print("\n" + "="*50)
            print("🎵 오디오 타이밍 계산 로그")
            print("="*50)
            
            # 스크립트 타입에 따른 처리
            if script_type in ["회화", "대화"]:
                # 회화/대화 타입 처리
                for scene in manifest_data.get('scenes', []):
                    if scene.get('type') == 'conversation':
                        sequence = scene.get('sequence', 1)
                        
                        native_script = scene.get('native_script', '')
                        if native_script:
                            screen1_audio_path = os.path.join(temp_dir, f"segment_{sequence:03d}_screen1.mp3")
                            screen1_duration = self._synthesize_segment_audio(
                                native_script, screen1_audio_path, 
                                voice_name=native_speaker, language_code="ko-KR", script_type=script_type
                            )
                            if screen1_duration > 0:
                                segment_paths_for_merge.append(screen1_audio_path)
                                silence_path = self._create_silence_segment(1, os.path.join(temp_dir, f"silence_{sequence:03d}_s1.mp3"))
                                if not silence_path: raise Exception("Silence creation failed")
                                segment_paths_for_merge.append(silence_path)

                                screen1_end_time = current_time + screen1_duration + 1.0
                                print(f"  - 장면 {sequence} (Screen 1):")
                                print(f"    - 원어 화자: {native_speaker}")
                                print(f"    - 시작: {current_time:.3f}초")
                                print(f"    - 음성 길이: {screen1_duration:.3f}초")
                                print(f"    - 무음 포함 종료: {screen1_end_time:.3f}초")
                                print("  "+"-"*20)
                                
                                timing_info["segments"].append({
                                    "name": f"{identifier}_{sequence:03d}_screen1.png",
                                    "start_time": round(current_time, 2),
                                    "end_time": round(screen1_end_time, 2),
                                    "duration": round(screen1_duration + 1.0, 2),
                                    "text": native_script
                                })
                                current_time = screen1_end_time
                        
                        learning_script = scene.get('learning_script', '')
                        reading_script = scene.get('reading_script', '')
                        if learning_script or reading_script:
                            screen2_start_time = current_time
                            print(f"  - 장면 {sequence} (Screen 2):")
                            print(f"    - Screen 2 시작: {screen2_start_time:.3f}초")
                            
                            learner_texts = [learning_script, reading_script, learning_script, reading_script]
                            screen2_total_duration = 0.0
                            
                            for i in range(1, 5):
                                text_to_speak = learner_texts[i-1].strip()
                                if text_to_speak:
                                    learner_audio_path = os.path.join(temp_dir, f"segment_{sequence:03d}_screen2_learner_{i}.mp3")
                                    # 학습어 화자 순서대로 사용 (1-4번 화자)
                                    learner_voice = learner_speakers[i-1] if i-1 < len(learner_speakers) else learner_speakers[0]
                                    learner_duration = self._synthesize_segment_audio(
                                        text_to_speak, learner_audio_path,
                                        voice_name=learner_voice, language_code="cmn-CN", script_type=script_type
                                    )
                                    if learner_duration > 0:
                                        segment_paths_for_merge.append(learner_audio_path)
                                        silence_path = self._create_silence_segment(1, os.path.join(temp_dir, f"silence_{sequence:03d}_s2_l{i}.mp3"))
                                        if not silence_path: raise Exception("Silence creation failed")
                                        segment_paths_for_merge.append(silence_path)
                                        print(f"      - 학습자 {i} 음성 ({learner_voice}): {learner_duration:.3f}초 / 무음 포함: {learner_duration + 1.0:.3f}초")
                                        screen2_total_duration += learner_duration + 1.0
                            
                            if screen2_total_duration > 0:
                                screen2_end_time = screen2_start_time + screen2_total_duration
                                print(f"    - Screen 2 총합 (무음 포함): {screen2_total_duration:.3f}초")
                                print(f"    - Screen 2 종료: {screen2_end_time:.3f}초")
                                print("  "+"-"*20)

                                screen2_text = f"{learning_script} {reading_script}".strip()
                                timing_info["segments"].append({
                                    "name": f"{identifier}_{sequence:03d}_screen2.png",
                                    "start_time": round(screen2_start_time, 2),
                                    "end_time": round(screen2_end_time, 2),
                                    "duration": round(screen2_total_duration, 2),
                                    "text": screen2_text
                                })
                                current_time = screen2_end_time
            
            elif script_type in ["인트로", "엔딩"]:
                # 인트로/엔딩 타입 처리 - 라인별로 분리하여 처리
                for scene in manifest_data.get('scenes', []):
                    if scene.get('type') in ['intro', 'ending']:
                        sequence = scene.get('sequence', 1)
                        script_text = scene.get('script', '') or scene.get('full_script', '')
                        
                        if script_text:
                            # 스크립트를 라인별로 분리
                            lines = [line.strip() for line in script_text.split('\n') if line.strip()]
                            
                            print(f"  - 장면 {sequence} ({script_type}):")
                            print(f"    - 총 {len(lines)}개 라인 처리")
                            print(f"    - 화자: {native_speaker}")
                            print(f"    - 시작: {current_time:.3f}초")
                            
                            scene_start_time = current_time
                            
                            for line_idx, line in enumerate(lines):
                                if line:  # 빈 라인이 아닌 경우만 처리
                                    audio_path = os.path.join(temp_dir, f"segment_{sequence:03d}_line_{line_idx+1:02d}.mp3")
                                    duration = self._synthesize_segment_audio(
                                        line, audio_path, 
                                        voice_name=native_speaker, language_code="ko-KR", script_type=script_type
                                    )
                                    
                                    if duration > 0:
                                        segment_paths_for_merge.append(audio_path)
                                        
                                        # 마지막 라인이 아닌 경우에만 무음 추가
                                        if line_idx < len(lines) - 1:
                                            silence_path = self._create_silence_segment(1, os.path.join(temp_dir, f"silence_{sequence:03d}_line_{line_idx+1:02d}.mp3"))
                                            if not silence_path: raise Exception("Silence creation failed")
                                            segment_paths_for_merge.append(silence_path)
                                        
                                        end_time = current_time + duration + (1.0 if line_idx < len(lines) - 1 else 0.0)
                                        
                                        print(f"      - 라인 {line_idx+1}: {line[:30]}{'...' if len(line) > 30 else ''}")
                                        print(f"        - 음성 길이: {duration:.3f}초")
                                        print(f"        - 종료: {end_time:.3f}초")
                                        
                                        # 각 라인별 타이밍 정보 추가
                                        # 스크립트 타입을 영어로 변환
                                        english_script_type = {"인트로": "intro", "엔딩": "ending"}.get(script_type, script_type.lower())
                                        timing_info["segments"].append({
                                            "name": f"{identifier}_{english_script_type}_{line_idx+1:03d}.png",
                                            "start_time": round(current_time, 2),
                                            "end_time": round(end_time, 2),
                                            "duration": round(duration + (1.0 if line_idx < len(lines) - 1 else 0.0), 2),
                                            "text": line
                                        })
                                        
                                        current_time = end_time
                            
                            scene_end_time = current_time
                            print(f"    - 장면 총 길이: {scene_end_time - scene_start_time:.3f}초")
                            print("  "+"-"*20)
            
            # 세그먼트가 없는 경우 처리
            if not segment_paths_for_merge:
                print(f"⚠️ {script_type} 스크립트에 처리할 데이터가 없습니다.")
                # 빈 오디오 파일 생성 (1초 무음)
                empty_audio_path = os.path.join(temp_dir, "empty.mp3")
                silence_path = self._create_silence_segment(1, empty_audio_path)
                if silence_path:
                    segment_paths_for_merge.append(silence_path)
                    timing_info["segments"].append({
                        "name": f"{identifier}_001.png",
                        "start_time": 0.0,
                        "end_time": 1.0,
                        "duration": 1.0,
                        "text": ""
                    })
                    current_time = 1.0
            
            print("="*50 + "\n")

            english_script_type = {"회화": "conversation", "대화": "conversation", "인트로": "intro", "엔딩": "ending"}.get(script_type, script_type)
            final_audio_path = os.path.join(output_dir, f"{identifier}_{english_script_type}.mp3")
            
            print(f"🎵 생성된 모든 세그먼트 병합 중... -> {final_audio_path}")
            merge_success = self.merge_audio_segments(segment_paths_for_merge, final_audio_path)
            if not merge_success:
                raise Exception("Audio segment merging failed.")
            
            print(f"🔍 최종 오디오 파일 길이 검증: {final_audio_path}")
            actual_duration = self._get_accurate_audio_duration(final_audio_path)
            if actual_duration > 0:
                print(f"🎵 실제 오디오 파일 길이: {actual_duration:.3f}초 (이 값을 최종 사용)")
                timing_info["total_duration"] = round(actual_duration, 2)
                if timing_info["segments"]:
                    last_segment = timing_info["segments"][-1]
                    last_segment["end_time"] = round(actual_duration, 2)
                    last_segment["duration"] = round(actual_duration - last_segment["start_time"], 2)
                    print(f"🔧 마지막 세그먼트 타이밍 보정: {last_segment['start_time']:.2f}초 ~ {last_segment['end_time']:.2f}초")
            else:
                print(f"⚠️ 최종 오디오 파일 길이를 측정할 수 없습니다. 계산된 값을 사용합니다: {current_time:.2f}초")
                timing_info["total_duration"] = round(current_time, 2)

            timing_info["final_audio_path"] = final_audio_path
            
            for p in segment_paths_for_merge:
                try:
                    os.remove(p)
                except OSError:
                    pass
            try:
                os.rmdir(temp_dir)
            except OSError:
                pass
            
            print(f"✅ [통합] 오디오 및 타이밍 생성 완료: {len(timing_info['segments'])}개 세그먼트, 총 {timing_info['total_duration']:.2f}초")
            return final_audio_path, timing_info
            
        except Exception as e:
            import traceback
            print(f"❌ [통합] 오디오 및 타이밍 생성 실패: {e}")
            print(traceback.format_exc())
            return None, None

    def save_precise_timing_info(self, timing_info: Dict, output_path: str) -> bool:
        """정확한 타이밍 정보를 JSON 파일로 저장"""
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(timing_info, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 정확한 타이밍 정보 저장: {output_path}")
            print(f"   - 총 {len(timing_info.get('segments', []))}개 세그먼트")
            print(f"   - 총 재생시간: {timing_info.get('total_duration', 0):.2f}초")
            
            return True
            
        except Exception as e:
            print(f"❌ 타이밍 정보 저장 실패: {e}")
            return False
        
    def _get_accurate_audio_duration(self, audio_path: str) -> float:
        """FFmpeg로 정확한 오디오 길이 측정"""
        try:
            import subprocess
            import json
            
            if not os.path.exists(audio_path):
                print(f"⚠️ 오디오 파일이 존재하지 않습니다: {audio_path}")
                return 0.0
            
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', audio_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"⚠️ FFprobe 실행 실패: {result.stderr}")
                return self._fallback_duration_estimation(audio_path)
            
            audio_info = json.loads(result.stdout)
            duration = float(audio_info['format']['duration'])
            
            print(f"🎵 정확한 오디오 길이 측정: {audio_path} ({duration:.2f}초)")
            return round(duration, 2)
            
        except Exception as e:
            print(f"⚠️ FFmpeg 기반 오디오 길이 측정 실패: {e}")
            return self._fallback_duration_estimation(audio_path)
    
    def _fallback_duration_estimation(self, audio_path: str) -> float:
        """FFmpeg 실패 시 파일 크기 기반 추정"""
        try:
            file_size = os.path.getsize(audio_path)
            bitrate = 128 * 1000  # bits per second
            duration = (file_size * 8) / bitrate
            print(f"📊 파일 크기 기반 추정: {audio_path} ({duration:.2f}초)")
            return round(duration, 2)
        except Exception as e:
            print(f"❌ 오디오 길이 측정 완전 실패: {e}")
            return 0.0
