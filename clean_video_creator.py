#!/usr/bin/env python3
"""
깔끔한 타이밍 JSON을 사용한 비디오 생성기
- 중복 정보 제거
- 간결한 구조
"""

import os
import json
import subprocess
import tempfile
from typing import Dict, List

class CleanVideoCreator:
    def __init__(self):
        self._check_ffmpeg()
    
    def _check_ffmpeg(self):
        """FFmpeg 사용 가능 여부 확인"""
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            print("✅ FFmpeg 사용 가능")
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError("FFmpeg가 설치되지 않았거나 PATH에 없습니다.")
    
    def create_video_from_clean_timing(self, timing_file: str, output_file: str = None):
        """깔끔한 타이밍 JSON을 사용하여 비디오 생성"""
        
        print(f"🎬 깔끔한 타이밍 기반 비디오 생성 시작...")
        print(f"  📄 타이밍 파일: {timing_file}")
        
        # 타이밍 파일 로드
        if not os.path.exists(timing_file):
            print(f"❌ 타이밍 파일을 찾을 수 없습니다: {timing_file}")
            return False
        
        with open(timing_file, 'r', encoding='utf-8') as f:
            timing_data = json.load(f)
        
        # 기본 정보 추출
        project_info = timing_data.get("project_info", {})
        audio_file = timing_data.get("audio_file")
        segments = timing_data.get("segments", [])
        
        print(f"  📊 프로젝트: {project_info.get('name', 'Unknown')}")
        print(f"  🎵 오디오: {audio_file}")
        print(f"  🖼️ 세그먼트: {len(segments)}개")
        
        # 출력 파일 경로 설정
        if not output_file:
            base_dir = os.path.dirname(os.path.dirname(timing_file))
            output_file = os.path.join(base_dir, "video", f"{project_info.get('name', 'output')}_clean.mp4")
        
        print(f"  📹 출력 파일: {output_file}")
        
        # 오디오 파일 존재 확인
        if not os.path.exists(audio_file):
            print(f"❌ 오디오 파일을 찾을 수 없습니다: {audio_file}")
            return False
        
        # 이미지 파일 존재 확인
        missing_images = []
        for segment in segments:
            image_file = segment.get("image_file")
            if not os.path.exists(image_file):
                missing_images.append(image_file)
        
        if missing_images:
            print(f"❌ 누락된 이미지 파일들:")
            for img in missing_images:
                print(f"  - {img}")
            return False
        
        # FFmpeg 명령어 생성
        try:
            # 임시 concat 파일 생성
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as concat_file:
                for segment in segments:
                    image_file = segment.get("image_file")
                    duration = segment.get("duration", 1.0)
                    concat_file.write(f"file '{os.path.abspath(image_file)}'\n")
                    concat_file.write(f"duration {duration}\n")
                
                concat_file_path = concat_file.name
            
            # FFmpeg 명령어 실행
            cmd = [
                'ffmpeg', '-y',  # 덮어쓰기 허용
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file_path,
                '-i', audio_file,
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-shortest',  # 오디오와 비디오 중 짧은 것에 맞춤
                '-pix_fmt', 'yuv420p',
                output_file
            ]
            
            print(f"🔧 FFmpeg 명령어 실행 중...")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ 비디오 생성 완료: {output_file}")
                
                # 파일 크기 확인
                if os.path.exists(output_file):
                    file_size = os.path.getsize(output_file) / (1024 * 1024)  # MB
                    print(f"📁 파일 크기: {file_size:.2f} MB")
                
                return True
            else:
                print(f"❌ FFmpeg 실행 실패:")
                print(f"  오류: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ 비디오 생성 중 오류: {e}")
            return False
        finally:
            # 임시 파일 정리
            if 'concat_file_path' in locals() and os.path.exists(concat_file_path):
                os.unlink(concat_file_path)
    
    def create_video_with_precise_timing(self, timing_file: str, output_file: str = None):
        """정확한 타이밍으로 비디오 생성 (오디오 동기화)"""
        
        print(f"🎬 정확한 타이밍 비디오 생성 시작...")
        
        # 타이밍 파일 로드
        with open(timing_file, 'r', encoding='utf-8') as f:
            timing_data = json.load(f)
        
        audio_file = timing_data.get("audio_file")
        segments = timing_data.get("segments", [])
        
        # 출력 파일 경로 설정
        if not output_file:
            base_dir = os.path.dirname(os.path.dirname(timing_file))
            project_name = timing_data.get("project_info", {}).get("name", "output")
            output_file = os.path.join(base_dir, "video", f"{project_name}_precise.mp4")
        
        try:
            # 각 세그먼트별로 개별 비디오 생성
            temp_videos = []
            
            for i, segment in enumerate(segments):
                image_file = segment.get("image_file")
                duration = segment.get("duration", 1.0)
                
                # 임시 비디오 파일 생성
                temp_video = f"temp_segment_{i:03d}.mp4"
                temp_videos.append(temp_video)
                
                # 이미지를 지정된 시간만큼 표시하는 비디오 생성
                cmd = [
                    'ffmpeg', '-y',
                    '-loop', '1',
                    '-i', image_file,
                    '-c:v', 'libx264',
                    '-t', str(duration),
                    '-pix_fmt', 'yuv420p',
                    '-r', '30',
                    temp_video
                ]
                
                print(f"  📹 세그먼트 {i+1}/{len(segments)} 생성 중... ({duration}초)")
                subprocess.run(cmd, capture_output=True, check=True)
            
            # 모든 세그먼트를 연결
            concat_file = "temp_concat.txt"
            with open(concat_file, 'w') as f:
                for temp_video in temp_videos:
                    f.write(f"file '{temp_video}'\n")
            
            # 최종 비디오 생성 (오디오 포함)
            cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-i', audio_file,
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-shortest',
                output_file
            ]
            
            print(f"🔧 최종 비디오 생성 중...")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ 정확한 타이밍 비디오 생성 완료: {output_file}")
                return True
            else:
                print(f"❌ 최종 비디오 생성 실패: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ 정확한 타이밍 비디오 생성 중 오류: {e}")
            return False
        finally:
            # 임시 파일 정리
            for temp_video in temp_videos:
                if os.path.exists(temp_video):
                    os.unlink(temp_video)
            if os.path.exists(concat_file):
                os.unlink(concat_file)

def main():
    """메인 함수"""
    creator = CleanVideoCreator()
    
    # 깔끔한 타이밍 파일 경로
    timing_file = "output/kor-chn/kor-chn/timing/kor-chn_conversation_clean.json"
    
    if not os.path.exists(timing_file):
        print(f"❌ 타이밍 파일을 찾을 수 없습니다: {timing_file}")
        return
    
    print("🎬 깔끔한 타이밍 기반 비디오 생성 시작...")
    
    # 방법 1: 기본 비디오 생성
    print("\n📹 방법 1: 기본 비디오 생성")
    success1 = creator.create_video_from_clean_timing(timing_file)
    
    # 방법 2: 정확한 타이밍 비디오 생성
    print("\n📹 방법 2: 정확한 타이밍 비디오 생성")
    success2 = creator.create_video_with_precise_timing(timing_file)
    
    if success1 or success2:
        print("\n🎉 비디오 생성 완료!")
    else:
        print("\n❌ 비디오 생성 실패")

if __name__ == "__main__":
    main()
