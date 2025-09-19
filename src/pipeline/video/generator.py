# src/pipeline/video/generator.py

import os
import json
import subprocess
from typing import Dict, Any, List

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
    
    def create_video_from_timeline(self, timeline_path: str, output_video_path: str) -> bool:
        """
        타임라인 JSON 파일을 읽어 최종 비디오를 렌더링합니다. (수정된 overlay 방식)
        
        Args:
            timeline_path (str): timeline.json 파일 경로
            output_video_path (str): 최종 MP4 비디오 저장 경로
            
        Returns:
            bool: 성공 여부
        """
        print("--- 🎬 [비디오 렌더링] 시작 (Overlay 방식) ---")
        
        try:
            with open(timeline_path, 'r', encoding='utf-8') as f:
                timeline_data = json.load(f)
            print(f"✅ 타임라인 데이터 로드 완료: {timeline_path}")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"🔥🔥🔥 [오류] 타임라인 파일 로드 또는 파싱 실패: {e}")
            return False

        # 1. 필수 데이터 검증
        if not self._validate_timeline_data(timeline_data):
            return False

        # 2. FFmpeg에 필요한 입력 파일 리스트와 필터 그래프 생성
        audio_input = timeline_data.get('final_audio_path')
        if not os.path.exists(audio_input):
            print(f"🔥🔥🔥 [오류] 최종 오디오 파일을 찾을 수 없습니다: {audio_input}")
            return False

        image_inputs = []
        filter_complex_parts = []
        
        resolution = timeline_data.get('resolution', '1920x1080')
        total_duration = timeline_data.get('total_duration', 30.0)
        
        # 첫 번째 입력(검은 화면)을 베이스로 사용
        stream_counter = 1
        overlay_stream = "0:v"

        # --- 상세 로깅 시작 ---
        log_messages = []
        log_messages.append("="*50)
        log_messages.append("🎬 FFMPEG 렌더링 타이밍 정보")
        log_messages.append("="*50)
        log_messages.append("아래 정보는 FFmpeg에 전달되는 각 이미지의 표시 시간입니다.")
        log_messages.append("이 시간과 타이밍 파일의 시간을 비교하여 동기화를 확인하세요.")
        log_messages.append("-"*50)

        for i, clip in enumerate(timeline_data['timeline']):
            image_path = clip.get("image_path")
            if not (image_path and os.path.exists(image_path)):
                log_messages.append(f"  ⚠️ [경고] 이미지 파일을 찾을 수 없습니다: {image_path}, 이 클립을 건너뜁니다.")
                continue

            image_inputs.extend(['-i', image_path])
            start_time = clip['start_time']
            end_time = clip['end_time']
            
            log_messages.append(f"  - 이미지: {os.path.basename(image_path)}")
            log_messages.append(f"    - 시작: {start_time:.3f}초")
            log_messages.append(f"    - 종료: {end_time:.3f}초")
            log_messages.append(f"    - 유지: {end_time-start_time:.3f}초")
            log_messages.append("  "+"-"*20)

            current_image_stream = f"{stream_counter}:v"
            next_overlay_stream = f"ovr{stream_counter}"
            
            filter_complex_parts.append(
                f"[{overlay_stream}][{current_image_stream}]overlay=enable='between(t,{start_time},{end_time})'[{next_overlay_stream}];"
            )
            overlay_stream = next_overlay_stream
            stream_counter += 1
        
        log_messages.append("="*50 + "\n")

        # 로그를 콘솔과 파일에 저장
        log_output = "\n".join(log_messages)
        print(log_output)
        try:
            log_file_path = os.path.join("output", "rendering_log.txt")
            os.makedirs("output", exist_ok=True)
            with open(log_file_path, 'w', encoding='utf-8') as f:
                f.write(log_output)
            print(f"✅ 상세 렌더링 로그를 파일에 저장했습니다: {log_file_path}")
        except Exception as e:
            print(f"⚠️ 상세 렌더링 로그 파일 저장에 실패했습니다: {e}")
        # --- 상세 로깅 종료 ---
            
        if not image_inputs:
            print("🔥🔥🔥 [오류] 타임라인에 유효한 이미지가 하나도 없습니다.")
            return False

        filter_complex_string = "".join(filter_complex_parts).rstrip(';')
        
        # 3. 최종 FFmpeg 명령어 생성 및 실행
        command = [
            'ffmpeg', '-y',
            '-f', 'lavfi', '-i', f"color=c=black:s={resolution}:d={total_duration}",
            *image_inputs,
            '-i', audio_input,
            '-filter_complex', filter_complex_string,
            '-map', f'[{overlay_stream}]',
            '-map', f'{stream_counter}:a',
            '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
            '-c:a', 'aac',
            '-t', str(total_duration), # 오디오 길이에 맞게 비디오 길이 제한
            output_video_path
        ]
        
        print("🚀 [FFmpeg] 실행 명령어:")
        formatted_cmd = " \
  ".join(command)
        print(formatted_cmd)

        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
            print(f"✅ [성공] 비디오 생성 완료: {output_video_path}")
            return True
        except subprocess.CalledProcessError as e:
            print("🔥🔥🔥 [오류] FFmpeg 실행 중 오류 발생! 🔥🔥🔥")
            print(e.stderr)
            return False
    
    def _validate_timeline_data(self, timeline_data: Dict) -> bool:
        """타임라인 데이터 유효성 검증"""
        required_fields = ['timeline', 'final_audio_path', 'resolution', 'total_duration']
        for field in required_fields:
            if field not in timeline_data:
                print(f"🔥🔥🔥 [오류] 필수 필드 누락: {field}")
                return False
        
        if not timeline_data['timeline']:
            print("🔥🔥🔥 [오류] 타임라인이 비어있습니다.")
            return False
            
        if timeline_data['total_duration'] <= 0:
            print("🔥🔥🔥 [오류] 총 재생시간(total_duration)이 유효하지 않습니다.")
            return False

        return True
    
    
    
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
    
    def create_video_from_timing(self, timing_path: str, output_video_path: str, image_dir: str) -> bool:
        """
        타이밍 JSON 파일을 직접 사용하여 오디오와 싱크가 맞는 비디오를 생성합니다.
        """
        print("--- 🎬 [타이밍 기반 비디오 렌더링] 시작 ---")
        
        try:
            with open(timing_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"✅ 타이밍 데이터 로드 완료: {timing_path}")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"🔥🔥🔥 [오류] 타이밍 파일 로드 또는 파싱 실패: {e}")
            return False

        segments = data['segments']
        audio_input = data.get('final_audio_path')

        if not audio_input:
            base_name = os.path.basename(timing_path).replace('_conversation.json', '').replace('_intro.json', '').replace('_ending.json', '')
            audio_input = os.path.join(os.path.dirname(os.path.dirname(timing_path)), "mp3", f"{base_name}_conversation.mp3")

        if not os.path.exists(audio_input):
            print(f"🔥🔥🔥 [오류] 최종 오디오 파일을 찾을 수 없습니다: {audio_input}")
            return False
            
        # 1. FFmpeg에 필요한 입력 파일 리스트와 필터 그래프 생성
        image_inputs = []
        filter_complex_parts = []
        
        resolution = data.get('resolution', '1920x1080')
        total_duration = data.get('total_duration', 30.0)
        
        stream_counter = 1
        overlay_stream = "0:v"

        # --- 상세 로깅 시작 ---
        log_messages = []
        log_messages.append("="*50)
        log_messages.append("🎬 FFMPEG 렌더링 타이밍 정보 (from timing.json)")
        log_messages.append("="*50)
        log_messages.append("아래 정보는 FFmpeg에 전달되는 각 이미지의 표시 시간입니다.")
        log_messages.append("이 시간과 타이밍 파일의 시간을 비교하여 동기화를 확인하세요.")
        log_messages.append("-"*50)

        for i, segment in enumerate(segments):
            scene_id = segment.get("name")
            image_path_from_timeline = segment.get("image_path")

            if image_path_from_timeline and os.path.exists(image_path_from_timeline):
                 image_path = image_path_from_timeline
            else:
                image_filename = scene_id
                image_path = os.path.join(image_dir, image_filename)

            if not os.path.exists(image_path):
                log_messages.append(f"  ⚠️ [경고] 이미지 파일을 찾을 수 없습니다: {image_path}, 이 세그먼트를 건너뜁니다.")
                continue

            image_inputs.extend(['-i', image_path])
            start_time = segment['start_time']
            end_time = segment['end_time']
            
            log_messages.append(f"  - 이미지: {os.path.basename(image_path)}")
            log_messages.append(f"    - 시작: {start_time:.3f}초")
            log_messages.append(f"    - 종료: {end_time:.3f}초")
            log_messages.append(f"    - 유지: {end_time-start_time:.3f}초")
            log_messages.append("  "+"-"*20)
            
            current_image_stream = f"{stream_counter}:v"
            next_overlay_stream = f"ovr{stream_counter}"
            
            filter_complex_parts.append(
                f"[{overlay_stream}][{current_image_stream}]overlay=enable='between(t,{start_time},{end_time})'[{next_overlay_stream}];"
            )
            overlay_stream = next_overlay_stream
            stream_counter += 1

        log_messages.append("="*50 + "\n")

        # 로그를 콘솔과 파일에 저장
        log_output = "\n".join(log_messages)
        print(log_output)
        try:
            log_file_path = os.path.join("output", "rendering_log.txt")
            os.makedirs("output", exist_ok=True)
            with open(log_file_path, 'w', encoding='utf-8') as f:
                f.write(log_output)
            print(f"✅ 상세 렌더링 로그를 파일에 저장했습니다: {log_file_path}")
        except Exception as e:
            print(f"⚠️ 상세 렌더링 로그 파일 저장에 실패했습니다: {e}")
        # --- 상세 로깅 종료 ---
            
        if not image_inputs:
            print("🔥🔥🔥 [오류] 타임라인에 유효한 이미지가 하나도 없습니다.")
            return False

        filter_complex_string = "".join(filter_complex_parts).rstrip(';')
        
        # 2. 최종 FFmpeg 명령어 생성
        command = [
            'ffmpeg', '-y',
            '-f', 'lavfi', '-i', f"color=c=black:s={resolution}:d={total_duration}",
            *image_inputs,
            '-i', audio_input,
            '-filter_complex', filter_complex_string,
            '-map', f'[{overlay_stream}]',
            '-map', f'{len(image_inputs)//2+1}:a',
            '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
            '-c:a', 'aac',
            '-t', str(total_duration),
            output_video_path
        ]
        
        print("🚀 [FFmpeg] 실행 명령어:")
        formatted_cmd = " \
  ".join(command)
        print(formatted_cmd)

        # 3. FFmpeg 실행
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
            print(f"✅ [성공] 비디오 생성 완료: {output_video_path}")
            return True
        except subprocess.CalledProcessError as e:
            print("🔥🔥🔥 [오류] FFmpeg 실행 중 오류 발생! 🔥🔥🔥")
            print(e.stderr)
            return False
