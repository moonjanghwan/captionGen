# src/pipeline/ffmpeg/renderer.py
# 새로운 VideoGenerator 기반 렌더러

import os
import json
from typing import Dict, List, Optional
from ..video.generator import VideoGenerator

class FFmpegRenderer:
    """
    새로운 VideoGenerator를 사용하는 FFmpeg 렌더러
    기존 인터페이스를 유지하면서 내부적으로 VideoGenerator 사용
    """
    
    def __init__(self):
        self.video_generator = VideoGenerator()
        print("✅ 새로운 VideoGenerator 기반 FFmpeg 렌더러 초기화 완료")
    
    def create_conversation_video(self, conversation_data: List[Dict], audio_path: str, 
                                 subtitle_dir: str, output_path: str, resolution: str, 
                                 background_path: str) -> bool:
        """
        회화 비디오 생성 - 타임라인 기반으로 변경
        """
        print("🎬 회화 비디오 생성 시작 (새로운 VideoGenerator 사용)")
        
        try:
            # 1. 타임라인 파일 경로 생성 (output_path에서 추출)
            # output_path: output/kor-chn/kor-chn/video/kor-chn_conversation.mp4
            # timeline_path: output/kor-chn/kor-chn/timeline/kor-chn_conversation.json
            
            output_dir = os.path.dirname(os.path.dirname(output_path))  # output/kor-chn/kor-chn
            filename = os.path.basename(output_path)  # kor-chn_conversation.mp4
            base_name = filename.replace('.mp4', '')  # kor-chn_conversation
            timeline_path = os.path.join(output_dir, "timeline", f"{base_name}.json")
            
            print(f"🔍 타임라인 파일 경로: {timeline_path}")
            
            if not os.path.exists(timeline_path):
                print(f"🔥🔥🔥 [오류] 타임라인 파일을 찾을 수 없습니다: {timeline_path}")
                print("💡 먼저 '타임라인 생성' 버튼을 눌러 타임라인을 생성해주세요.")
                return False
            
            # 2. VideoGenerator를 사용하여 비디오 생성
            success = self.video_generator.create_video_from_timeline(timeline_path, output_path)
            
            if success:
                print(f"✅ 회화 비디오 생성 완료: {output_path}")
            else:
                print(f"❌ 회화 비디오 생성 실패")
            
            return success
            
        except Exception as e:
            print(f"🔥🔥🔥 [오류] 회화 비디오 생성 중 오류: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def create_video_from_timing(self, timing_path: str, output_path: str, image_dir: str) -> bool:
        """
        타이밍 JSON 파일을 직접 사용하여 비디오 생성
        타임라인 생성 단계를 건너뛰고 바로 비디오 제작
        """
        print("🎬 타이밍 기반 비디오 생성 시작 (타임라인 생성 생략)")
        
        try:
            success = self.video_generator.create_video_from_timing(timing_path, output_path, image_dir)
            
            if success:
                print(f"✅ 타이밍 기반 비디오 생성 완료: {output_path}")
            else:
                print(f"❌ 타이밍 기반 비디오 생성 실패")
            
            return success
            
        except Exception as e:
            print(f"🔥🔥🔥 [오류] 타이밍 기반 비디오 생성 중 오류: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def create_intro_ending_video(self, sentences: List[str], audio_path: str, 
                                 subtitle_dir: str, output_path: str, resolution: str, 
                                 background_path: str) -> bool:
        """
        인트로/엔딩 비디오 생성 - 타임라인 기반으로 변경
        """
        print("🎬 인트로/엔딩 비디오 생성 시작 (새로운 VideoGenerator 사용)")
        
        try:
            # 1. 타임라인 파일 경로 생성 (output_path에서 추출)
            # output_path: output/kor-chn/kor-chn/video/kor-chn_intro.mp4
            # timeline_path: output/kor-chn/kor-chn/timeline/kor-chn_intro.json
            
            output_dir = os.path.dirname(os.path.dirname(output_path))  # output/kor-chn/kor-chn
            filename = os.path.basename(output_path)  # kor-chn_intro.mp4
            base_name = filename.replace('.mp4', '')  # kor-chn_intro
            timeline_path = os.path.join(output_dir, "timeline", f"{base_name}.json")
            
            print(f"🔍 타임라인 파일 경로: {timeline_path}")
            
            if not os.path.exists(timeline_path):
                print(f"🔥🔥🔥 [오류] 타임라인 파일을 찾을 수 없습니다: {timeline_path}")
                print("💡 먼저 '타임라인 생성' 버튼을 눌러 타임라인을 생성해주세요.")
                return False
            
            # 2. VideoGenerator를 사용하여 비디오 생성
            success = self.video_generator.create_video_from_timeline(timeline_path, output_path)
            
            if success:
                print(f"✅ 인트로/엔딩 비디오 생성 완료: {output_path}")
            else:
                print(f"❌ 인트로/엔딩 비디오 생성 실패")
            
            return success
            
        except Exception as e:
            print(f"🔥🔥🔥 [오류] 인트로/엔딩 비디오 생성 중 오류: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def create_final_merged_video(self, intro_path: str, conversation_path: str,
                                 ending_path: str, output_path: str) -> bool:
        """
        최종 병합 비디오 생성 - filter_complex 방식으로 안정적인 병합
        """
        print("🔗 최종 병합 비디오 생성 시작")
        
        try:
            # 존재하는 비디오 파일들만 수집
            existing_videos = []
            
            if intro_path and os.path.exists(intro_path):
                existing_videos.append(intro_path)
                print(f"✅ 인트로 비디오 포함: {intro_path}")
            
            if conversation_path and os.path.exists(conversation_path):
                existing_videos.append(conversation_path)
                print(f"✅ 회화 비디오 포함: {conversation_path}")
            
            if ending_path and os.path.exists(ending_path):
                existing_videos.append(ending_path)
                print(f"✅ 엔딩 비디오 포함: {ending_path}")
            
            if not existing_videos:
                print("🔥🔥🔥 [오류] 병합할 비디오 파일이 없습니다.")
                return False
            
            # 출력 디렉토리 생성
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # filter_complex 방식으로 안정적인 병합
            import subprocess
            
            # 입력 파일들
            input_args = []
            for video_path in existing_videos:
                input_args.extend(['-i', video_path])
            
            # filter_complex 생성
            filter_parts = []
            concat_inputs = []
            
            for i in range(len(existing_videos)):
                filter_parts.append(f"[{i}:v][{i}:a]")
                concat_inputs.append(f"v{i}")
                concat_inputs.append(f"a{i}")
            
            filter_complex = f"{''.join(filter_parts)}concat=n={len(existing_videos)}:v=1:a=1[outv][outa]"
            
            # FFmpeg 명령어
            command = [
                'ffmpeg', '-y',
                *input_args,
                '-filter_complex', filter_complex,
                '-map', '[outv]',
                '-map', '[outa]',
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-preset', 'fast',
                output_path
            ]
            
            print("🚀 [FFmpeg] 병합 명령어:")
            print(" ".join(command))
            
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            
            print(f"✅ 최종 병합 비디오 생성 완료: {output_path}")
            return True
            
        except subprocess.CalledProcessError as e:
            print("🔥🔥🔥 [오류] FFmpeg 병합 실행 중 오류 발생!")
            print(f"Return code: {e.returncode}")
            print(f"Error output: {e.stderr}")
            return False
        except Exception as e:
            print(f"🔥🔥🔥 [오류] 최종 병합 중 예상치 못한 오류: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def render_scene_video(self, audio_path: str, subtitle_frames: List[Dict], 
                          output_path: str, resolution: str, default_background: str):
        """
        기존 호환성을 위한 메서드 - 새로운 VideoGenerator 사용
        """
        print("🎬 장면 비디오 렌더링 (새로운 VideoGenerator 사용)")
        
        try:
            # 간단한 비디오 생성으로 대체
            image_paths = [frame.get('image_path') for frame in subtitle_frames if frame.get('image_path')]
            
            if not image_paths:
                print("🔥🔥🔥 [오류] 렌더링할 이미지가 없습니다.")
                return False
            
            success = self.video_generator.create_simple_video(
                image_paths=image_paths,
                audio_path=audio_path,
                output_path=output_path,
                duration_per_image=2.0
            )
            
            return success
            
        except Exception as e:
            print(f"🔥🔥🔥 [오류] 장면 비디오 렌더링 중 오류: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def merge_videos(self, video_paths: List[str], output_path: str):
        """
        기존 호환성을 위한 메서드 - 새로운 VideoGenerator 사용
        """
        print("🔗 비디오 병합 (새로운 VideoGenerator 사용)")
        
        try:
            # 존재하는 비디오 파일들만 수집
            existing_videos = [path for path in video_paths if os.path.exists(path)]
            
            if not existing_videos:
                print("🔥🔥🔥 [오류] 병합할 비디오 파일이 없습니다.")
                return False
            
            # 출력 디렉토리 생성
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # FFmpeg concat 명령어 생성
            concat_list_path = output_path.replace('.mp4', '_concat_list.txt')
            
            with open(concat_list_path, 'w', encoding='utf-8') as f:
                for video_path in existing_videos:
                    f.write(f"file '{os.path.abspath(video_path)}'\n")
            
            # FFmpeg 실행
            import subprocess
            command = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_list_path,
                '-c', 'copy',
                output_path
            ]
            
            print("🚀 [FFmpeg] 병합 명령어:")
            print(" ".join(command))
            
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            
            # 임시 파일 정리
            if os.path.exists(concat_list_path):
                os.remove(concat_list_path)            
            print(f"✅ 비디오 병합 완료: {output_path}")
            return True
            
        except subprocess.CalledProcessError as e:
            print("🔥🔥🔥 [오류] FFmpeg 병합 실행 중 오류 발생!")
            print(f"Return code: {e.returncode}")
            print(f"Error output: {e.stderr}")
            return False
        except Exception as e:
            print(f"🔥🔥🔥 [오류] 비디오 병합 중 예상치 못한 오류: {e}")
            import traceback
            traceback.print_exc()
            return False
