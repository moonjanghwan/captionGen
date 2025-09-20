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
        (v2) FFmpeg concat demuxer와 이미지 전처리로 성능 및 안정성 최적화.
        """
        print(f"--- 🎬 [타이밍 기반 비디오 렌더링] 시작 (Concat 방식 v2) - 스크립트 타입: {script_type} ---")
        temp_dir = None
        concat_file_path = output_video_path + ".txt"

        try:
            with open(timing_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"✅ 타이밍 데이터 로드 완료: {timing_path}")

            audio_input = data.get('final_audio_path')
            if not audio_input or not os.path.exists(audio_input):
                print(f"🔥🔥🔥 [오류] 오디오 파일을 찾을 수 없습니다: {audio_input}")
                return False

            # 1. 전처리 단계: 모든 이미지를 동일한 속성으로 만들기
            target_resolution = tuple(map(int, data.get('resolution', '1920x1080').split('x')))
            temp_dir = os.path.join(os.path.dirname(output_video_path), "temp_images_for_concat")
            os.makedirs(temp_dir, exist_ok=True)
            print(f"⚙️ 이미지 전처리 시작... (목표 해상도: {target_resolution})")

            # 배경 이미지 전처리
            background_image_path = self._find_background_image(script_type, timing_path)
            processed_bg_path = os.path.join(temp_dir, "bg.png")
            try:
                if background_image_path and os.path.exists(background_image_path):
                    with Image.open(background_image_path) as img:
                        img.resize(target_resolution, Image.Resampling.LANCZOS).save(processed_bg_path, 'PNG')
                else:
                    Image.new('RGBA', target_resolution, (0,0,0,255)).save(processed_bg_path, 'PNG')
            except Exception as img_e:
                print(f"⚠️ 배경 이미지 처리 실패, 검은색 배경으로 대체: {img_e}")
                Image.new('RGBA', target_resolution, (0,0,0,255)).save(processed_bg_path, 'PNG')

            # 2. Concat 파일 내용 생성
            padding_duration = 1.0
            concat_content = f"file '{os.path.abspath(processed_bg_path)}'\nduration {padding_duration}\n"
            
            content_segments = [seg for seg in data.get('segments', []) if not seg.get('is_background', False)]
            for i, segment in enumerate(content_segments):
                image_path_from_timeline = segment.get("image_path")
                if image_path_from_timeline and os.path.exists(image_path_from_timeline):
                    image_path = image_path_from_timeline
                else:
                    image_path = os.path.join(image_dir, segment.get("name"))

                if not os.path.exists(image_path):
                    print(f"  ⚠️ [경고] 이미지 파일을 찾을 수 없습니다: {image_path}, 이 세그먼트를 건너뜁니다.")
                    continue
                
                processed_img_path = os.path.join(temp_dir, f"frame_{i:04d}.png")
                try:
                    with Image.open(image_path) as img:
                        if img.size != target_resolution:
                            img.resize(target_resolution, Image.Resampling.LANCZOS).save(processed_img_path, 'PNG')
                        else:
                            import shutil
                            shutil.copy(image_path, processed_img_path)
                except Exception as img_e:
                    print(f"⚠️ 자막 이미지 처리 실패, 건너뜁니다: {img_e}")
                    continue

                duration = segment['end_time'] - segment['start_time']
                if duration > 0:
                    concat_content += f"file '{os.path.abspath(processed_img_path)}'\nduration {duration}\n"

            concat_content += f"file '{os.path.abspath(processed_bg_path)}'\nduration {padding_duration}\n"

            # 3. Concat 파일 저장
            with open(concat_file_path, 'w', encoding='utf-8') as f:
                f.write(concat_content)
            print(f"✅ Concat 파일 생성 완료: {concat_file_path}")

            # 4. 오디오 필터 생성 (패딩 처리)
            audio_filter = f"adelay={int(padding_duration*1000)}|{int(padding_duration*1000)},apad=pad_len={int(44100*padding_duration)}"

            # 5. 최종 FFmpeg 명령어 생성 및 실행
            command = [
                'ffmpeg', '-y',
                '-f', 'concat', '-safe', '0', '-i', concat_file_path,
                '-i', audio_input,
                '-filter_complex', f"[1:a]{audio_filter}[a]",
                '-map', '0:v', '-map', '[a]',
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                '-c:a', 'aac', '-ar', '44100', '-ac', '2',
                '-shortest',
                output_video_path
            ]
            
            print("🚀 [FFmpeg] 실행 명령어 (Concat 방식 v2):")
            print(" ".join(command))
            print("🔄 FFmpeg 실행 중...")

            subprocess.run(command, check=True, capture_output=False)
            print(f"✅ [성공] 비디오 생성 완료: {output_video_path}")
            return True

        except Exception as e:
            print(f"🔥🔥🔥 [오류] 비디오 생성 중 예외 발생! 🔥🔥🔥")
            print(f"  - 오류 타입: {type(e).__name__}")
            print(f"  - 오류 메시지: {e}")
            return False
        finally:
            # 임시 파일 및 디렉토리 정리
            if os.path.exists(concat_file_path):
                os.remove(concat_file_path)
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
            
            # 스크립트 타입별 매핑
            script_type_mapping = {
                'intro': '인트로 설정',
                'conversation': '회화 설정', 
                'ending': '엔딩 설정'
            }
            
            # 스크립트 타입이 지정되지 않은 경우, 파일명에서 추출 시도
            if not script_type:
                # 현재 처리 중인 파일에서 스크립트 타입 추출
                # 이는 create_video_from_timing에서 호출할 때 전달받아야 함
                print("⚠️ 스크립트 타입이 지정되지 않았습니다.")
                return None
            
            # 해당 스크립트 타입의 배경 설정 가져오기
            tab_name = script_type_mapping.get(script_type)
            print(f"🔍 탭 이름: {tab_name}")
            
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