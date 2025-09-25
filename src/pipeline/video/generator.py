# src/pipeline/video/generator.py

import os
import json
import subprocess
from typing import Dict, Any, List, Optional
from PIL import Image

class VideoGenerator:
    """
    타임라인 JSON 파일을 기반으로 FFmpeg을 사용하여 최종 비디오를 생성합니다.
    """
    
    def __init__(self):
        self._check_ffmpeg_availability()
    
    def _check_ffmpeg_availability(self):
        """FFmpeg 설치 및 사용 가능 여부 확인"""
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            print("✅ FFmpeg 사용 가능")
        except FileNotFoundError:
            raise FileNotFoundError("FFmpeg이 설치되지 않았거나 PATH에 없습니다.")
        except subprocess.CalledProcessError:
            raise RuntimeError("FFmpeg 실행 중 오류가 발생했습니다.")
    
    def _get_accurate_audio_duration(self, audio_path: str) -> float:
        try:
            if not os.path.exists(audio_path): return 0.0
            cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', audio_path]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return round(float(json.loads(result.stdout)['format']['duration']), 3)
        except Exception:
            return 0.0
    

    
    
    
    def create_simple_video(self, image_paths: List[str], audio_path: str, 
                           output_path: str, duration_per_image: float = 2.0) -> bool:
        """
        간단한 비디오 생성 (타임라인 없이)
        
        Args:
            image_paths: 이미지 파일 경로 리스트
            audio_path: 오디오 파일 경로
            output_path: 출력 비디오 경로
            duration_per_image: 각 이미지당 표시 시간 (초)
        """
        print("--- 🎬 [간단 비디오 생성] 시작 ---")
        
        try:
            # 입력 파일 검증
            for img_path in image_paths:
                if not os.path.exists(img_path):
                    print(f"🔥🔥🔥 [오류] 이미지 파일을 찾을 수 없습니다: {img_path}")
                    return False
            
            if not os.path.exists(audio_path):
                print(f"🔥🔥🔥 [오류] 오디오 파일을 찾을 수 없습니다: {audio_path}")
                return False
            
            # 출력 디렉토리 생성
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # FFmpeg 명령어 구성
            command = [
                'ffmpeg', '-y',
                '-i', audio_path,
                *[item for img in image_paths for item in ['-loop', '1', '-t', str(duration_per_image), '-i', img]],
                '-filter_complex', f'[1:v][2:v][3:v]concat=n={len(image_paths)}:v=1:a=0[v]',
                '-map', '[v]',
                '-map', '0:a',
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-shortest',
                output_path
            ]
            
            print("🚀 [FFmpeg] 간단 비디오 생성 명령어:")
            print(" ".join(command))
            
            # FFmpeg 실행
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            print(f"✅ [성공] 간단 비디오 생성 완료: {output_path}")
            return True
            
        except subprocess.CalledProcessError as e:
            print("🔥🔥🔥 [오류] 간단 비디오 생성 실패!")
            print(f"Return code: {e.returncode}")
            print(f"Error output: {e.stderr}")
            return False
        except Exception as e:
            print(f"🔥🔥🔥 [오류] 간단 비디오 생성 중 예상치 못한 오류: {e}")
            return False
    
    def create_video_from_timing(self, timing_path: str, output_video_path: str, image_dir: str, script_type: str = None, background_color: str = "black") -> bool:
        """
        타이밍 JSON 파일을 직접 사용하여 오디오와 싱크가 맞는 비디오를 생성합니다.
        (v5) Concat 필터 방식으로 변경하여 정확도 향상
        """
        print(f"--- 🎬 [타이밍 기반 비디오 렌더링] 시작 (Concat 필터 방식 v5) - 스크립트 타입: {script_type} ---")
        temp_dir = None

        try:
            with open(timing_path, 'r', encoding='utf-8') as f:
                timing_entries = json.load(f)
            print(f"✅ 타이밍 데이터 로드 완료: {len(timing_entries)}개 항목")

            if not timing_entries:
                print(f"🔥🔥🔥 [오류] 타이밍 파일에 내용이 없습니다: {timing_path}")
                return False

            # 오디오 파일 경로 생성
            filename = os.path.basename(output_video_path)
            identifier = filename.replace(f"_{script_type}.mp4", "")
            project_name = output_video_path.split(os.sep)[-4]
            audio_input = os.path.join("output", project_name, identifier, "mp3", f"{identifier}_{script_type}.mp3")
            
            if not os.path.exists(audio_input):
                print(f"🔥🔥🔥 [오류] 오디오 파일을 찾을 수 없습니다: {audio_input}")
                return False
            print(f"✅ 오디오 파일 확인: {audio_input}")

            # 오디오 길이 측정
            audio_duration = self._get_accurate_audio_duration(audio_input)
            if not audio_duration or audio_duration == 0.0:
                print(f"🔥🔥🔥 [오류] 오디오 파일의 길이를 측정할 수 없거나 길이가 0입니다: {audio_input}")
                return False
            print(f"✅ 오디오 길이 측정 완료: {audio_duration:.2f}초")

            # 이미지 전처리 준비
            target_resolution = (1920, 1080)
            temp_dir = os.path.join(os.path.dirname(output_video_path), "temp_images_for_concat")
            os.makedirs(temp_dir, exist_ok=True)
            print(f"⚙️ 이미지 전처리 시작... (목표 해상도: {target_resolution})")

            input_images_args = []
            filter_complex_video_streams = ""
            valid_segments_count = 0

            # --- 로직 분기 ---
            if script_type == "conversation":
                from itertools import groupby
                from operator import itemgetter

                timing_entries.sort(key=itemgetter('scene_id'))
                grouped_scenes = {k: list(v) for k, v in groupby(timing_entries, key=itemgetter('scene_id'))}
                print(f"🔄 'conversation' 타입 감지. {len(grouped_scenes)}개의 장면으로 그룹화합니다.")

                for scene_id, segments in sorted(grouped_scenes.items()):
                    # 1. 원어민 처리
                    native_segment = next((s for s in segments if s['speaker'] == 'native'), None)
                    if native_segment:
                        duration = native_segment['end_time'] - native_segment['start_time']
                        image_path = native_segment.get("image_filename")
                        if duration > 0 and image_path and os.path.exists(image_path):
                            processed_img_path = os.path.join(temp_dir, f"frame_{valid_segments_count:04d}.png")
                            with Image.open(image_path) as img: img.resize(target_resolution, Image.Resampling.LANCZOS).save(processed_img_path, 'PNG')
                            input_images_args.extend(['-loop', '1', '-t', str(duration), '-i', os.path.abspath(processed_img_path)])
                            filter_complex_video_streams += f"[{valid_segments_count+1}:v]"
                            valid_segments_count += 1

                    # 2. 학습자 그룹 처리
                    learner_segments = [s for s in segments if s['speaker'].startswith('learner_')]
                    if learner_segments:
                        learner_segments.sort(key=lambda s: s['speaker'])
                        duration = learner_segments[-1]['end_time'] - learner_segments[0]['start_time']
                        image_path = learner_segments[0].get("image_filename")
                        if duration > 0 and image_path and os.path.exists(image_path):
                            processed_img_path = os.path.join(temp_dir, f"frame_{valid_segments_count:04d}.png")
                            with Image.open(image_path) as img: img.resize(target_resolution, Image.Resampling.LANCZOS).save(processed_img_path, 'PNG')
                            input_images_args.extend(['-loop', '1', '-t', str(duration), '-i', os.path.abspath(processed_img_path)])
                            filter_complex_video_streams += f"[{valid_segments_count+1}:v]"
                            valid_segments_count += 1
            else:
                print(f"🔄 '{script_type}' 타입 감지. 1:1로 이미지를 매칭합니다.")
                for segment in timing_entries:
                    duration = segment['end_time'] - segment['start_time']
                    image_path = segment.get("image_filename")
                    if duration > 0 and image_path and os.path.exists(image_path):
                        processed_img_path = os.path.join(temp_dir, f"frame_{valid_segments_count:04d}.png")
                        with Image.open(image_path) as img: img.resize(target_resolution, Image.Resampling.LANCZOS).save(processed_img_path, 'PNG')
                        input_images_args.extend(['-loop', '1', '-t', str(duration), '-i', os.path.abspath(processed_img_path)])
                        filter_complex_video_streams += f"[{valid_segments_count+1}:v]"
                        valid_segments_count += 1

            if valid_segments_count == 0:
                print(f"🔥🔥🔥 [오류] 처리할 유효한 이미지 세그먼트가 없습니다. FFmpeg을 실행할 수 없습니다.")
                return False

            filter_complex = f"{filter_complex_video_streams}concat=n={valid_segments_count}:v=1:a=0[v]"

            command = [
                'ffmpeg', '-y',
                '-i', audio_input,
                *input_images_args,
                '-filter_complex', filter_complex,
                '-map', '[v]',
                '-map', '0:a',
                '-t', str(audio_duration),
                '-c:v', 'h264_videotoolbox',
                '-b:v', '8000k',
                '-r', '25',
                '-pix_fmt', 'yuv420p',
                '-c:a', 'aac', '-ar', '44100', '-ac', '2',
                output_video_path
            ]
            
            print("🚀 [FFmpeg] 실행 명령어 (Concat 필터 방식 v5):")
            print(" ".join(command))
            print("🔄 FFmpeg 실행 중...")

            subprocess.run(command, check=True, capture_output=True, text=True)
            print(f"✅ [성공] 비디오 생성 완료: {output_video_path}")
            return True

        except subprocess.CalledProcessError as e:
            print(f"🔥🔥🔥 [오류] FFmpeg 실행 중 오류 발생! 🔥🔥🔥")
            print(f"  - FFmpeg stderr:\n{e.stderr}")
            return False
        except Exception as e:
            print(f"🔥🔥🔥 [오류] 비디오 생성 중 예외 발생! 🔥🔥🔥")
            print(f"  - 오류 타입: {type(e).__name__}")
            print(f"  - 오류 메시지: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            if temp_dir and os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir)
    
    def _find_background_image(self, script_type: str = None, timing_path: str = None) -> Optional[str]:
        """
        UI 설정에서 배경 이미지 파일을 찾아서 경로를 반환
        script_type: 'intro', 'conversation', 'ending' 중 하나
        """
        try:
            print(f"🔍 배경 이미지 찾기 시작 - 스크립트 타입: {script_type}")
            
            # UI 설정에서 배경 이미지 가져오기
            tab_backgrounds = self._get_current_background_settings(timing_path)
            print(f"🔍 로드된 배경 설정: {tab_backgrounds}")
            
            if not tab_backgrounds:
                print("⚠️ UI 배경 설정을 찾을 수 없습니다.")
                return None
            
            # 스크립트 타입이 이제 설정의 키와 동일하므로 직접 사용합니다.
            tab_name = script_type
            print(f"🔍 설정 탭 이름: {tab_name}")
            
            if not tab_name or tab_name not in tab_backgrounds:
                print(f"⚠️ {script_type}에 해당하는 배경 설정을 찾을 수 없습니다.")
                print(f"🔍 사용 가능한 탭들: {list(tab_backgrounds.keys())}")
                return None
            
            background_settings = tab_backgrounds[tab_name]
            print(f"🔍 {tab_name} 배경 설정: {background_settings}")
            
            if background_settings and background_settings.get('enabled', False):
                bg_path = background_settings.get('value', '')
                if bg_path and os.path.exists(bg_path):
                    print(f"✅ {script_type} 배경 이미지 발견: {bg_path}")
                    return bg_path
                else:
                    print(f"⚠️ {script_type} 배경 이미지 파일이 존재하지 않습니다: {bg_path}")
            else:
                print(f"⚠️ {script_type} 배경 설정이 비활성화되어 있습니다.")
            
            return None
            
        except Exception as e:
            print(f"❌ 배경 이미지 찾기 중 오류: {e}")
            return None

    def _get_current_background_settings(self, timing_path: str = None):
        """
        현재 활성화된 탭의 배경 설정을 가져오기
        """
        try:
            if not timing_path:
                print("❌ 타이밍 경로가 제공되지 않아 설정을 찾을 수 없습니다.")
                return None

            # timing_path로부터 project_dir 유추: output/project/id/timing/file.json -> output/project/id
            project_dir = os.path.dirname(os.path.dirname(timing_path))
            settings_file = os.path.join(project_dir, "_text_settings.json")
            
            print(f"🔍 설정 파일 경로: {settings_file}")

            if os.path.exists(settings_file):
                import json
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings_data = json.load(f)
                
                # 탭별 배경 설정에서 현재 스크립트 타입에 맞는 설정 찾기
                tab_backgrounds = settings_data.get('common', {}).get('tab_backgrounds', {})
                return tab_backgrounds
                
            return None
            
        except Exception as e:
            print(f"❌ 배경 설정 로드 중 오류: {e}")
            return None