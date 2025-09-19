#!/usr/bin/env python3
"""
간단한 비디오 생성기
타이밍 JSON + 이미지 파일 + 오디오 파일로 직접 비디오 생성
"""

import os
import json
import tempfile
import ffmpeg
from typing import List, Dict

class SimpleVideoCreator:
    def __init__(self):
        self._check_ffmpeg()
    
    def _check_ffmpeg(self):
        """FFmpeg 사용 가능 여부 확인"""
        try:
            import subprocess
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            print("✅ FFmpeg 사용 가능")
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError("FFmpeg가 설치되지 않았거나 PATH에 없습니다.")
    
    def create_video_from_timing(self, 
                                timing_file: str, 
                                image_dir: str, 
                                audio_file: str, 
                                output_file: str,
                                resolution: str = "1920x1080"):
        """
        타이밍 파일을 기반으로 비디오 생성
        
        Args:
            timing_file: 타이밍 JSON 파일 경로
            image_dir: 이미지 파일들이 있는 디렉토리
            audio_file: 오디오 파일 경로
            output_file: 출력 비디오 파일 경로
            resolution: 비디오 해상도
        """
        print(f"🎬 간단한 비디오 생성 시작...")
        print(f"  📄 타이밍 파일: {timing_file}")
        print(f"  🖼️ 이미지 디렉토리: {image_dir}")
        print(f"  🎵 오디오 파일: {audio_file}")
        print(f"  📹 출력 파일: {output_file}")
        
        # 1. 타이밍 데이터 로드
        with open(timing_file, 'r', encoding='utf-8') as f:
            timing_data = json.load(f)
        
        print(f"✅ 타이밍 데이터 로드 완료: {len(timing_data['scenes'])}개 장면")
        
        # 2. 비디오 세그먼트 생성
        video_segments = []
        current_time = 0.0
        
        for scene in timing_data['scenes']:
            sequence = scene['sequence']
            timings = scene['timings']
            
            # Screen1 처리
            if 'screen1' in timings:
                screen1_timing = timings['screen1']
                start_ms = screen1_timing['start']
                end_ms = screen1_timing['end']
                duration = (end_ms - start_ms) / 1000.0  # ms를 초로 변환
                
                image_path = os.path.join(image_dir, f"kor-chn_{sequence:0>3}_screen1.png")
                if os.path.exists(image_path):
                    video_segments.append({
                        'image_path': image_path,
                        'start_time': current_time,
                        'duration': duration,
                        'type': 'screen1',
                        'sequence': sequence
                    })
                    current_time += duration
                    print(f"  📊 Screen1 {sequence}: {duration:.2f}초 ({os.path.basename(image_path)})")
                else:
                    print(f"  ❌ 이미지 파일을 찾을 수 없습니다: {image_path}")
            
            # Screen2 처리
            if 'screen2' in timings:
                screen2_timing = timings['screen2']
                start_ms = screen2_timing['start']
                end_ms = screen2_timing['end']
                duration = (end_ms - start_ms) / 1000.0  # ms를 초로 변환
                
                image_path = os.path.join(image_dir, f"kor-chn_{sequence:0>3}_screen2.png")
                if os.path.exists(image_path):
                    video_segments.append({
                        'image_path': image_path,
                        'start_time': current_time,
                        'duration': duration,
                        'type': 'screen2',
                        'sequence': sequence
                    })
                    current_time += duration
                    print(f"  📊 Screen2 {sequence}: {duration:.2f}초 ({os.path.basename(image_path)})")
                else:
                    print(f"  ❌ 이미지 파일을 찾을 수 없습니다: {image_path}")
        
        if not video_segments:
            print("❌ 비디오 세그먼트가 없습니다.")
            return False
        
        print(f"✅ 총 {len(video_segments)}개 세그먼트 생성 완료")
        
        # 3. FFmpeg concat 파일 생성
        concat_file = self._create_concat_file(video_segments)
        
        # 4. 비디오 생성
        success = self._render_video(concat_file, audio_file, output_file, resolution)
        
        # 5. 임시 파일 정리
        os.unlink(concat_file)
        
        if success:
            print(f"✅ 비디오 생성 완료: {output_file}")
            return True
        else:
            print(f"❌ 비디오 생성 실패")
            return False
    
    def _create_concat_file(self, video_segments: List[Dict]) -> str:
        """FFmpeg concat 파일 생성"""
        concat_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
        
        for segment in video_segments:
            concat_file.write(f"file '{os.path.abspath(segment['image_path'])}'\n")
            concat_file.write(f"duration {segment['duration']}\n")
        
        # 마지막 이미지 다시 추가 (duration 없이)
        if video_segments:
            concat_file.write(f"file '{os.path.abspath(video_segments[-1]['image_path'])}'\n")
        
        concat_file.close()
        return concat_file.name
    
    def _render_video(self, concat_file: str, audio_file: str, output_file: str, resolution: str) -> bool:
        """FFmpeg로 비디오 렌더링"""
        try:
            width, height = map(int, resolution.split('x'))
            
            # 이미지 입력 (concat)
            image_input = ffmpeg.input(concat_file, f='concat', safe=0, r='30')
            
            # 해상도 적용
            video_stream = image_input.filter('scale', width, height)
            
            # 오디오 입력
            audio_input = ffmpeg.input(audio_file)
            
            # 비디오 출력
            output = ffmpeg.output(
                video_stream, 
                audio_input, 
                output_file,
                vcodec='libx264',
                acodec='aac',
                pix_fmt='yuv420p',
                shortest=None
            )
            
            # 실행
            ffmpeg.run(output, overwrite_output=True, quiet=True)
            return True
            
        except Exception as e:
            print(f"❌ 비디오 렌더링 실패: {e}")
            return False

def main():
    """메인 함수"""
    creator = SimpleVideoCreator()
    
    # 파일 경로 설정
    base_dir = "output/kor-chn/kor-chn"
    timing_file = os.path.join(base_dir, "timing", "kor-chn_conversation.json")
    image_dir = os.path.join(base_dir, "conversation")
    audio_file = os.path.join(base_dir, "mp3", "kor-chn_conversation.mp3")
    output_file = os.path.join(base_dir, "video", "kor-chn_conversation_simple.mp4")
    
    # 출력 디렉토리 생성
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # 비디오 생성
    success = creator.create_video_from_timing(
        timing_file=timing_file,
        image_dir=image_dir,
        audio_file=audio_file,
        output_file=output_file,
        resolution="1920x1080"
    )
    
    if success:
        print(f"🎉 비디오 생성 성공!")
        print(f"📁 파일 위치: {output_file}")
    else:
        print(f"💥 비디오 생성 실패!")

if __name__ == "__main__":
    main()
