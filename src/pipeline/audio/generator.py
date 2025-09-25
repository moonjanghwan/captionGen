import os
import json
import tempfile
import subprocess
from typing import Dict, List, Any, Optional, Tuple
from google.cloud import texttospeech
from google.cloud import texttospeech_v1 as texttospeech_v1_module
from google.api_core import exceptions as google_exceptions

from .ssml_builder import SSMLBuilder

class AudioGenerator:
    def __init__(self, config: Dict[str, Any], credentials_path: Optional[str] = None):
        self.config = config
        self.output_directory = os.path.abspath(config.get("output_directory", "output"))
        self.tts_config = config.get("tts", {})
        audio_settings = config.get("audio_settings", {})

        # Set properties from config, with defaults
        self.sample_rate = audio_settings.get("sample_rate", 24000)
        self.api_retries = audio_settings.get("api_retries", 3)
        self.api_retry_delay_s = audio_settings.get("api_retry_delay_s", 1.0)
        self.silence_duration_s = audio_settings.get("silence_duration_s", 1.0)
        self.punctuation_pause_ms = audio_settings.get("punctuation_pause_ms", {})
        
        self.ssml_builder = SSMLBuilder()
        self.client = None
        self._initialize_client(credentials_path)
        
        self.audio_config = texttospeech_v1_module.types.AudioConfig(
            audio_encoding=texttospeech_v1_module.types.AudioEncoding.MP3,
            sample_rate_hertz=self.sample_rate,
            effects_profile_id=["headphone-class-device"]
        )
        
        # API 호출 통계 초기화
        self.api_stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "retry_attempts": 0,
            "ssml_fallback_calls": 0,
            "text_mode_calls": 0
        }

    def _initialize_client(self, credentials_path: Optional[str] = None):
        try:
            if credentials_path and os.path.exists(credentials_path):
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
            self.client = texttospeech.TextToSpeechClient()
            print("✅ Google Cloud TTS 클라이언트 초기화 성공")
        except Exception as e:
            print(f"⚠️ Google Cloud TTS 클라이언트 초기화 실패: {e}")
            self.client = None

    def _synthesize_speech(self, ssml_text: str, output_path: str, voice_name: str = None, lang_code: str = None) -> Tuple[float, List[Dict[str, Any]]]:
        if not self.client:
            raise Exception("Google TTS 클라이언트가 초기화되지 않았습니다.")
        if not ssml_text:
            print("⚠️ 합성할 SSML 텍스트가 없습니다. 건너뜁니다.")
            return 0.0, []

        max_retries = self.api_retries
        retry_delay = self.api_retry_delay_s
        
        for attempt in range(max_retries):
            try:
                # 첫 시도에만 통계 및 기본 정보 출력
                if attempt == 0:
                    self.api_stats["total_calls"] += 1
                    print(f"--- Synthesizing Speech ---")
                    print(f"  Output Path: {output_path}")
                    print(f"  Voice: {voice_name}")

                synthesis_input = texttospeech.SynthesisInput(ssml=ssml_text)
                
                voice_params = None
                if voice_name and lang_code:
                    voice_params = texttospeech.VoiceSelectionParams(language_code=lang_code, name=voice_name)
                    if "Studio" in voice_name:
                        voice_params.model = "studio"
                
                response = self.client.synthesize_speech(
                    input=synthesis_input,
                    voice=voice_params,
                    audio_config=self.audio_config
                )
                
                if not response.audio_content:
                    raise ValueError("API returned empty audio content.")

                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, "wb") as out:
                    out.write(response.audio_content)

                duration = self._get_accurate_audio_duration(output_path)
                if duration == 0.0:
                    raise ValueError("Generated audio duration is 0 seconds.")

                timepoints = self._calculate_manual_timing(ssml_text, duration)
                
                if attempt > 0:
                    print(f"  ✅ 재시도 성공 (시도 {attempt + 1}번 만에 성공)")
                else:
                    print(f"  ✅ 성공")

                self.api_stats["successful_calls"] += 1
                return duration, timepoints

            except google_exceptions.InvalidArgument as e:
                # SSML 미지원 오류는 재시도하지 않고 즉시 폴백
                if "does not support SSML" in str(e):
                    print(f"  (INFO: SSML 미지원 목소리. 텍스트 모드로 자동 전환합니다.)")
                    self.api_stats["ssml_fallback_calls"] += 1
                    return self._synthesize_speech_fallback(ssml_text, output_path, voice_name, lang_code)
                else:
                    # 그 외의 InvalidArgument는 치명적 오류로 간주하고 즉시 중단
                    print(f"❌ 치명적인 API 매개변수 오류: {e.message}")
                    raise e

            except Exception as e:
                # 네트워크 오류 등 일시적일 수 있는 다른 모든 오류는 재시도
                print(f"  ❌ 합성 오류 (시도 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    self.api_stats["retry_attempts"] += 1
                    print(f"  ⏳ {retry_delay}초 후 재시도합니다...")
                    import time
                    time.sleep(retry_delay)
                    continue
                else:
                    print(f"  ❌ 최종 합성 실패: {os.path.basename(output_path)}")
                    raise e # 모든 재시도 실패 시, 작업을 중단시키기 위해 예외 발생
        
        # 모든 재시도가 실패한 경우
        self.api_stats["failed_calls"] += 1
        raise Exception(f"최대 재시도 횟수({max_retries})를 초과했습니다.")

    def _create_silence_segment(self, duration_seconds: float, output_path: str) -> Optional[str]:
        try:
            command = [
                'ffmpeg', '-f', 'lavfi', '-i', f'anullsrc=r={self.sample_rate}:cl=mono',
                '-t', str(duration_seconds), '-q:a', '9', '-acodec', 'libmp3lame',
                output_path, '-y'
            ]
            subprocess.run(command, check=True, capture_output=True, text=True)
            return output_path
        except Exception as e:
            print(f"❌ 무음 세그먼트 생성 실패: {e}")
            return None

    def _merge_audio_segments(self, segment_paths: List[str], output_path: str) -> bool:
        if not segment_paths:
            print("❌ 오디오 병합 실패: 병합할 오디오 세그먼트가 없습니다.")
            return False
        
        merge_list_path = ""
        try:
            list_content = "".join([f"file '{os.path.abspath(p)}'\n" for p in segment_paths])
            
            print("--- FFMPEG Concat File Content ---")
            print(list_content)
            print("------------------------------------")

            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".txt", encoding='utf-8') as tmp_list_file:
                tmp_list_file.write(list_content)
                merge_list_path = tmp_list_file.name

            command = [
                'ffmpeg', '-f', 'concat', '-safe', '0', '-i', merge_list_path,
                '-acodec', 'libmp3lame', '-q:a', '2', output_path, '-y'
            ]
            
            print(f"🚀 FFMPEG Command: {' '.join(command)}")
            
            subprocess.run(command, check=True, capture_output=True, text=True)
            
            if os.path.exists(merge_list_path):
                os.remove(merge_list_path)
            return True
        except subprocess.CalledProcessError as e:
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            print("!!!      FFMPEG ERROR DETECTED     !!!")
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            print(f"❌ 오디오 병합 실패 (FFMPEG stderr):\n{e.stderr}")
            if os.path.exists(merge_list_path):
                os.remove(merge_list_path)
            return False
        except Exception as e:
            print(f"❌ 오디오 병합 중 예기치 않은 오류: {e}")
            if os.path.exists(merge_list_path):
                os.remove(merge_list_path)
            return False
    
    def _get_accurate_audio_duration(self, audio_path: str) -> float:
        try:
            if not os.path.exists(audio_path): return 0.0
            cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', audio_path]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return round(float(json.loads(result.stdout)['format']['duration']), 3)
        except Exception:
            return 0.0

    def _save_ssml_file(self, ssml_content: str, output_path: str):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(ssml_content)
        print(f"💾 SSML 파일 저장: {output_path}")

    def _save_timing_file(self, timing_info: List[Dict[str, Any]], output_path: str):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(timing_info, f, ensure_ascii=False, indent=2)
        print(f"💾 타이밍 파일 저장: {output_path} ({len(timing_info)}개 마크)")

    def _calculate_manual_timing(self, ssml_text: str, total_duration: float) -> List[Dict[str, Any]]:
        """SSML에서 마크를 추출하고 수동으로 타이밍을 계산합니다."""
        import re
        
        # SSML에서 마크 추출
        mark_pattern = r'<mark name="([^"]+)"\s*/>'
        marks = re.findall(mark_pattern, ssml_text)
        
        if not marks:
            return []
        
        # 텍스트 길이 기반으로 대략적인 타이밍 계산
        # 전체 텍스트에서 각 마크까지의 비율을 계산
        text_content = re.sub(r'<[^>]+>', '', ssml_text)  # 태그 제거
        text_length = len(text_content)
        
        timepoints = []
        current_position = 0
        
        for i, mark_name in enumerate(marks):
            # 마크까지의 텍스트 길이 계산 (대략적)
            mark_position = ssml_text.find(f'<mark name="{mark_name}"')
            if mark_position != -1:
                text_before_mark = ssml_text[:mark_position]
                text_before_mark = re.sub(r'<[^>]+>', '', text_before_mark)
                current_position = len(text_before_mark)
            
            # 비율 기반 타이밍 계산
            if text_length > 0:
                time_ratio = current_position / text_length
                time_seconds = total_duration * time_ratio
            else:
                time_seconds = 0.0
            
            timepoints.append({
                "mark_name": mark_name,
                "time_seconds": round(time_seconds, 3)
            })
        
        return timepoints

    def _calculate_text_mode_timing(self, ssml_text: str, total_duration: float) -> List[Dict[str, Any]]:
        """텍스트 모드에서 대략적인 타이밍을 계산합니다."""
        import re
        
        # SSML에서 마크 추출
        mark_pattern = r'<mark name="([^"]+)"\s*/>'
        marks = re.findall(mark_pattern, ssml_text)
        
        if not marks:
            return []
        
        # 텍스트에서 마크 위치 기반으로 타이밍 계산
        text_content = re.sub(r'<[^>]+>', '', ssml_text)  # 태그 제거
        text_length = len(text_content)
        
        timepoints = []
        
        for mark_name in marks:
            # 마크까지의 텍스트 길이 계산
            mark_position = ssml_text.find(f'<mark name="{mark_name}"')
            if mark_position != -1:
                text_before_mark = ssml_text[:mark_position]
                text_before_mark = re.sub(r'<[^>]+>', '', text_before_mark)
                current_position = len(text_before_mark)
                
                # 비율 기반 타이밍 계산 (더 정확한 계산)
                if text_length > 0:
                    time_ratio = current_position / text_length
                    time_seconds = total_duration * time_ratio
                else:
                    time_seconds = 0.0
                
                timepoints.append({
                    "mark_name": mark_name,
                    "time_seconds": round(time_seconds, 3)
                })
        
        return timepoints

    def get_api_stats(self) -> Dict[str, Any]:
        """API 호출 통계를 반환합니다."""
        return self.api_stats.copy()
    
    def reset_api_stats(self):
        """API 호출 통계를 초기화합니다."""
        self.api_stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "retry_attempts": 0,
            "ssml_fallback_calls": 0,
            "text_mode_calls": 0
        }

    def _synthesize_speech_fallback(self, ssml_text: str, output_path: str, voice_name: str = None, lang_code: str = None) -> Tuple[float, List[Dict[str, Any]]]:
        """SSML 미지원 화자에 대한 텍스트 폴백 처리"""
        import re
        
        # SSML에서 순수 텍스트만 추출
        plain_text = re.sub(r'<[^>]+>', '', ssml_text)
        plain_text = plain_text.strip()
        
        print(f"  Fallback: Using plain text mode")
        print(f"  Text: {plain_text[:50]}...")
        
        max_retries = self.api_retries
        retry_delay = self.api_retry_delay_s
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    print(f"  Fallback 재시도 {attempt}/{max_retries-1}")
                else:
                    print(f"  Fallback 시도 1/{max_retries}")

                synthesis_input = texttospeech.SynthesisInput(text=plain_text)
                
                voice_params = None
                if voice_name and lang_code:
                    voice_params = texttospeech.VoiceSelectionParams(language_code=lang_code, name=voice_name)
                    if "Studio" in voice_name:
                        voice_params.model = "studio"
                
                response = self.client.synthesize_speech(
                    input=synthesis_input,
                    voice=voice_params,
                    audio_config=self.audio_config
                )
                
                if not response.audio_content:
                    raise ValueError("API returned empty audio content in fallback mode.")

                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, "wb") as out:
                    out.write(response.audio_content)

                if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                    raise ValueError("Failed to write audio file or file is empty in fallback mode.")
                
                duration = self._get_accurate_audio_duration(output_path)
                if duration == 0.0:
                    raise ValueError("Generated audio duration is 0 seconds in fallback mode.")

                timepoints = [{"mark_name": "sentence", "time_seconds": 0, "duration": duration}]
                
                if attempt > 0:
                    print(f"  ✅ Fallback 재시도 성공 (시도 {attempt + 1}번 만에 성공)")
                else:
                    print(f"  ✅ Fallback 성공")

                self.api_stats["text_mode_calls"] += 1
                return duration, timepoints
                
            except Exception as e:
                print(f"  ❌ Fallback 오류 (시도 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    print(f"  ⏳ {retry_delay}초 후 재시도합니다...")
                    import time
                    time.sleep(retry_delay)
                    continue
                else:
                    print(f"  ❌ 최종 Fallback 실패: {os.path.basename(output_path)}")
                    raise e # 작업을 중단시키기 위해 예외를 다시 발생시킴
        
        # 모든 재시도가 실패한 경우
        raise Exception(f"텍스트 모드에서 최대 재시도 횟수({max_retries})를 초과했습니다.")

    def generate_conversation_audio(self, manifest_data: Dict[str, Any]) -> Dict[str, Any]:
        identifier = manifest_data.get("identifier", "default")
        project_name = manifest_data.get("project_name", "default_project")
        
        mp3_dir = os.path.join(self.output_directory, project_name, identifier, "mp3")
        ssml_dir = os.path.join(self.output_directory, project_name, identifier, "SSML")
        image_dir = os.path.join(self.output_directory, project_name, identifier, "subtitles", "conversation") # 이미지 경로
        os.makedirs(mp3_dir, exist_ok=True)
        os.makedirs(ssml_dir, exist_ok=True)
        os.makedirs(image_dir, exist_ok=True)

        final_mp3_path = os.path.join(mp3_dir, f"{identifier}_conversation.mp3")
        final_ssml_path = os.path.join(ssml_dir, f"{identifier}_conversation.ssml")

        full_ssml_content = ""
        segment_paths = []
        timing_info = []
        total_duration = 0.0
        temp_dir = tempfile.mkdtemp(prefix="conv_audio_")

        expected_segments = 0
        successful_segments = 0

        try:
            voices = {
                "native": self.tts_config.get("native_voice"),
                "learner_1": self.tts_config.get("learner_1_voice"),
                "learner_2": self.tts_config.get("learner_2_voice"),
                "learner_3": self.tts_config.get("learner_3_voice"),
                "learner_4": self.tts_config.get("learner_4_voice"),
            }
            
            for i, scene in enumerate(manifest_data.get('scenes', [])):
                scene_num = i + 1
                # 1. Native Speaker
                native_script = scene.get('native_script', '').strip()
                if native_script:
                    expected_segments += 1
                    ssml = self.ssml_builder.build_ssml_with_marks(native_script, self.tts_config["native_lang_code"], f"s{i}_n", self.punctuation_pause_ms)
                    path = os.path.join(temp_dir, f"seg_{i}_native.mp3")
                    duration, _ = self._synthesize_speech(ssml, path, voices["native"], self.tts_config["native_lang_code"])
                    
                    if duration > 0:
                        successful_segments += 1
                        segment_duration = duration
                        segment_paths.append(path)
                        
                        # Add silence
                        silence_path = os.path.join(temp_dir, f"silence_{i}_n.mp3")
                        if self._create_silence_segment(self.silence_duration_s, silence_path):
                            segment_paths.append(silence_path)
                            segment_duration += self.silence_duration_s

                        image_filename = f"{identifier}_conversation_{scene_num:03d}_screen1.png"
                        full_image_path = os.path.join(image_dir, image_filename)

                        timing_entry = {
                            "scene_id": i,
                            "speaker": "native",
                            "text": native_script,
                            "image_filename": full_image_path,
                            "start_time": round(total_duration, 3),
                            "end_time": round(total_duration + segment_duration, 3),
                            "duration": round(segment_duration, 3)
                        }
                        timing_info.append(timing_entry)
                        
                        total_duration += segment_duration
                        full_ssml_content += ssml + "\n"
                    else:
                        print(f"⚠️ Native audio for scene {i} failed to generate and will be skipped.")

                # 2. Learner Speakers
                learning_script = scene.get('learning_script', '').strip()
                if learning_script:
                    image_filename = f"{identifier}_conversation_{scene_num:03d}_screen2.png"
                    full_image_path = os.path.join(image_dir, image_filename)

                    for j in range(1, 5):
                        role = f"learner_{j}"
                        if voices[role]:
                            expected_segments += 1
                            ssml = self.ssml_builder.build_ssml_with_marks(learning_script, self.tts_config["learning_lang_code"], f"s{i}_l{j}", self.punctuation_pause_ms)
                            path = os.path.join(temp_dir, f"seg_{i}_learner_{j}.mp3")
                            duration, _ = self._synthesize_speech(ssml, path, voices[role], self.tts_config["learning_lang_code"])
                            
                            if duration > 0:
                                successful_segments += 1
                                segment_duration = duration
                                segment_paths.append(path)

                                # Add silence AFTER EVERY LEARNER
                                silence_path = os.path.join(temp_dir, f"silence_{i}_l{j}.mp3")
                                if self._create_silence_segment(self.silence_duration_s, silence_path):
                                    segment_paths.append(silence_path)
                                    segment_duration += self.silence_duration_s
                                
                                timing_entry = {
                                    "scene_id": i,
                                    "speaker": role,
                                    "text": learning_script,
                                    "image_filename": full_image_path,
                                    "start_time": round(total_duration, 3),
                                    "end_time": round(total_duration + segment_duration, 3),
                                    "duration": round(segment_duration, 3)
                                }
                                timing_info.append(timing_entry)

                                total_duration += segment_duration
                                full_ssml_content += ssml + "\n"
                            else:
                                print(f"⚠️ Learner audio for scene {i}, learner {j} failed to generate and will be skipped.")
            
            if not self._merge_audio_segments(segment_paths, final_mp3_path):
                raise Exception("오디오 병합 실패")

            self._save_ssml_file(full_ssml_content, final_ssml_path)
            
            timing_dir = os.path.join(self.output_directory, project_name, identifier, "timing")
            os.makedirs(timing_dir, exist_ok=True)
            timing_file_path = os.path.join(timing_dir, f"{identifier}_conversation.json")
            self._save_timing_file(timing_info, timing_file_path)
            
            print("\n--- 오디오 생성 최종 리포트 ---")
            if expected_segments == successful_segments:
                print(f"✅ 성공: 총 {expected_segments}개의 오디오 블록이 모두 성공적으로 생성되었습니다.")
            else:
                print(f"⚠️ 경고: 총 {expected_segments}개 중 {successful_segments}개의 오디오 블록만 성공했습니다.")
                print(f"  ({expected_segments - successful_segments}개 실패). 최종 오디오 파일이 완전하지 않을 수 있습니다.")
            print("---------------------------------\n")

            return {
                "success": True, 
                "audio_file": final_mp3_path, 
                "ssml_file": final_ssml_path, 
                "timing_file": timing_file_path, 
                "timing_info": timing_info,
                "api_stats": self.get_api_stats()
            }

        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            for f in os.listdir(temp_dir): 
                try: os.remove(os.path.join(temp_dir, f)) 
                except: pass
            try: os.rmdir(temp_dir) 
            except: pass

    def generate_intro_ending_audio(self, manifest_data: Dict[str, Any], script_type: str) -> Dict[str, Any]:
        identifier = manifest_data.get("identifier", "default")
        project_name = manifest_data.get("project_name", "default_project")

        mp3_dir = os.path.join(self.output_directory, project_name, identifier, "mp3")
        ssml_dir = os.path.join(self.output_directory, project_name, identifier, "SSML")
        image_dir = os.path.join(self.output_directory, project_name, identifier, "subtitles", script_type)
        os.makedirs(mp3_dir, exist_ok=True)
        os.makedirs(ssml_dir, exist_ok=True)
        os.makedirs(image_dir, exist_ok=True)

        final_mp3_path = os.path.join(mp3_dir, f"{identifier}_{script_type}.mp3")
        final_ssml_path = os.path.join(ssml_dir, f"{identifier}_{script_type}.ssml")

        full_ssml_content = ""
        segment_paths = []
        timing_info = []
        total_duration = 0.0
        segment_counter = 1
        temp_dir = tempfile.mkdtemp(prefix=f"{script_type}_audio_")

        try:
            voice = self.tts_config.get("native_voice")
            lang_code = self.tts_config.get("native_lang_code")
            
            scenes = manifest_data.get('scenes', [])
            for i, scene in enumerate(scenes):
                text = scene.get('text', '').strip()
                if text:
                    ssml = self.ssml_builder.build_ssml_with_marks(text, lang_code, f"s{i}", self.punctuation_pause_ms)
                    path = os.path.join(temp_dir, f"seg_{i}.mp3")
                    duration, _ = self._synthesize_speech(ssml, path, voice, lang_code)

                    if duration > 0:
                        segment_paths.append(path)
                        full_ssml_content += ssml + "\n"
                        
                        segment_duration = duration
                        
                        # 무음 추가
                        silence_path = os.path.join(temp_dir, f"silence_{i}.mp3")
                        if self._create_silence_segment(self.silence_duration_s, silence_path):
                            segment_paths.append(silence_path)
                            segment_duration += self.silence_duration_s
                        
                        # 이미지 파일명 생성
                        image_filename = f"{identifier}_{script_type}_{segment_counter:03d}.png"
                        full_image_path = os.path.join(image_dir, image_filename)

                        # 문장 단위의 단일 타이밍 정보 생성
                        timing_entry = {
                            "scene_id": i,
                            "text": text,
                            "image_filename": full_image_path,
                            "start_time": round(total_duration, 3),
                            "end_time": round(total_duration + segment_duration, 3),
                            "duration": round(segment_duration, 3)
                        }
                        timing_info.append(timing_entry)
                        
                        total_duration += segment_duration
                        segment_counter += 1
                    else:
                        print(f"⚠️ 인트로/엔딩 오디오 생성 실패 (장면 {i}). 건너뜁니다.")
            
            if not self._merge_audio_segments(segment_paths, final_mp3_path):
                raise Exception("오디오 병합 실패")

            self._save_ssml_file(full_ssml_content, final_ssml_path)
            
            # 타이밍 파일 저장
            timing_dir = os.path.join(self.output_directory, project_name, identifier, "timing")
            os.makedirs(timing_dir, exist_ok=True)
            timing_file_path = os.path.join(timing_dir, f"{identifier}_{script_type}.json")
            self._save_timing_file(timing_info, timing_file_path)

            return {
                "success": True, 
                "audio_file": final_mp3_path, 
                "ssml_file": final_ssml_path, 
                "timing_file": timing_file_path, 
                "timing_info": timing_info,
                "api_stats": self.get_api_stats()
            }

        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            for f in os.listdir(temp_dir): 
                try: os.remove(os.path.join(temp_dir, f)) 
                except: pass
            try: os.rmdir(temp_dir) 
            except: pass
