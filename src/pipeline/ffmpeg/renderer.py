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
    
    def create_video_from_timing(self, timing_path: str, output_path: str, image_dir: str, script_type: str = None) -> bool:
        """
        타이밍 JSON 파일을 직접 사용하여 비디오 생성
        타임라인 생성 단계를 건너뛰고 바로 비디오 제작
        스무스 전환을 위해 앞뒤 1초 패딩 포함
        """
        print(f"🎬 타이밍 기반 비디오 생성 시작 (스무스 전환용 패딩 포함) - 스크립트 타입: {script_type}")
        
        try:
            # VideoGenerator의 create_video_from_timing 함수 호출 (패딩 기능 포함)
            success = self.video_generator.create_video_from_timing(timing_path, output_path, image_dir, script_type)
            
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
    

    
    def create_final_merged_video(self, intro_path: str, conversation_path: str,
                                 ending_path: str, output_path: str, smooth_transition: bool = True) -> bool:
        """
        최종 병합 비디오 생성 - 스무스 전환 효과 포함
        """
        print("🔗 최종 병합 비디오 생성 시작 (스무스 전환 포함)")
        
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
            
            # 스무스 전환 여부에 따라 다른 방식 사용
            if smooth_transition and len(existing_videos) > 1:
                return self._create_smooth_merged_video(existing_videos, output_path)
            else:
                return self._create_simple_merged_video(existing_videos, output_path)
                
        except Exception as e:
            print(f"🔥🔥🔥 [오류] 최종 병합 중 예상치 못한 오류: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _create_smooth_merged_video(self, video_paths: list, output_path: str) -> bool:
        """
        스무스 전환 효과가 포함된 비디오 병합 (오디오 기반 전환)
        """
        import subprocess
        
        print("🎬 스무스 전환 효과로 비디오 병합 중...")
        
        # 각 비디오의 오디오 길이 측정
        audio_durations = []
        for video_path in video_paths:
            duration = self._get_audio_duration(video_path)
            if duration is None:
                print(f"⚠️ 오디오 길이 측정 실패, 기본 concat 사용: {video_path}")
                return self._create_simple_merged_video(video_paths, output_path)
            audio_durations.append(duration)
            print(f"📊 {os.path.basename(video_path)}: {duration:.2f}초")
        
        # 입력 파일들
        input_args = []
        for video_path in video_paths:
            input_args.extend(['-i', video_path])
        
        # 오디오 겹치지 않는 스무스 전환 필터 생성 (패딩 고려)
        if len(video_paths) == 2:
            # 2개 비디오: 첫 번째 오디오 끝에서 비디오만 전환
            # 패딩이 추가된 비디오이므로 원본 오디오 길이 + 1초 패딩에서 1초 전에 전환
            offset1 = max(0, audio_durations[0] - 1.0)  # 1초 전에 전환 시작
            filter_complex = f"[0:v]trim=start=0.001,setpts=PTS-STARTPTS[v0];[1:v]setpts=PTS-STARTPTS[v1];[v0][v1]xfade=transition=dissolve:duration=1.0:offset={offset1}[v];[0:a][1:a]concat=n=2:v=0:a=1[a]"
            map_args = ['-map', '[v]', '-map', '[a]']
        elif len(video_paths) == 3:
            # 3개 비디오: 각 오디오 끝에서 비디오만 전환, 오디오는 순차 재생
            # 패딩이 추가된 비디오이므로 원본 오디오 길이 + 1초 패딩에서 1초 전에 전환
            offset1 = max(0, audio_durations[0] - 1.0)  # 인트로→회화 전환 시점
            offset2 = max(0, audio_durations[0] + audio_durations[1] - 1.0)  # 회화→엔딩 전환 시점
            
            filter_complex = f"[0:v]trim=start=0.001,setpts=PTS-STARTPTS[v0];[1:v]setpts=PTS-STARTPTS[v1];[2:v]setpts=PTS-STARTPTS[v2];[v0][v1]xfade=transition=dissolve:duration=1.0:offset={offset1}[v01];[v01][v2]xfade=transition=dissolve:duration=1.0:offset={offset2}[v];[0:a][1:a][2:a]concat=n=3:v=0:a=1[a]"
            map_args = ['-map', '[v]', '-map', '[a]']
            
            print(f"🎯 전환 시점: 인트로→회화 {offset1:.2f}초, 회화→엔딩 {offset2:.2f}초")
            print(f"🎵 오디오: 겹치지 않고 순차 재생 (인트로 {audio_durations[0]:.2f}초 → 회화 {audio_durations[1]:.2f}초 → 엔딩 {audio_durations[2]:.2f}초)")
            print(f"📊 패딩 고려: 각 비디오에 1초 패딩이 추가되어 스무스 전환이 더 자연스럽게 됩니다.")
        else:
            # 3개 이상: 기본 concat 사용
            return self._create_simple_merged_video(video_paths, output_path)
        
        # FFmpeg 명령어
        cmd = [
            'ffmpeg', '-y',
            *input_args,
            '-filter_complex', filter_complex,
            *map_args,
            '-c:v', 'libx264',
            '-profile:v', 'baseline',  # QuickTime Player 호환성
            '-level', '3.1',           # QuickTime Player 호환성
            '-pix_fmt', 'yuv420p',     # QuickTime Player 호환성
            '-c:a', 'aac',
            '-ar', '44100',            # 오디오 샘플링 레이트
            '-ac', '2',                # 스테레오 오디오
            '-preset', 'fast',         # 더 빠른 인코딩
            '-crf', '28',              # 더 작은 파일 크기
            '-movflags', '+faststart', # 스트리밍 최적화
            '-f', 'mp4',               # 명시적 MP4 포맷
            '-avoid_negative_ts', 'make_zero',  # 타임스탬프 정규화
            '-fflags', '+genpts',      # 타임스탬프 생성
            '-max_muxing_queue_size', '1024',  # 버퍼 크기 증가
            output_path
        ]
        
        print(f"🚀 [FFmpeg] 스무스 전환 명령어:")
        print(f"{' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                print(f"✅ 스무스 전환 비디오 병합 완료: {output_path}")
                return True
            else:
                print(f"🔥🔥🔥 [오류] FFmpeg 스무스 전환 실행 중 오류 발생!")
                print(f"Return code: {result.returncode}")
                print(f"Error output: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            print("🔥🔥🔥 [오류] FFmpeg 실행 시간 초과 (5분)")
            return False
        except Exception as e:
            print(f"🔥🔥🔥 [오류] FFmpeg 실행 중 예외 발생: {e}")
            return False
    
    def _get_audio_duration(self, video_path: str) -> Optional[float]:
        """
        비디오 파일의 오디오 길이를 측정
        """
        import subprocess
        
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                '-of', 'csv=p=0', video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                duration = float(result.stdout.strip())
                return duration
            else:
                print(f"⚠️ ffprobe 오류: {result.stderr}")
                return None
        except Exception as e:
            print(f"⚠️ 오디오 길이 측정 실패: {e}")
            return None
    
    def _create_simple_merged_video(self, video_paths: list, output_path: str) -> bool:
        """
        기본 concat 프로토콜 방식으로 비디오를 병합합니다. (빠르고 안정적, 전환 효과 없음)
        """
        import subprocess
        
        print("🔗 기본 concat 프로토콜 방식으로 비디오 병합 중...")

        # 임시 concat 리스트 파일 생성
        concat_list_path = output_path + "_concat_list.txt"
        try:
            with open(concat_list_path, 'w', encoding='utf-8') as f:
                for video_path in video_paths:
                    # 절대 경로를 사용하여 FFmpeg가 파일을 정확히 찾도록 수정
                    absolute_path = os.path.abspath(video_path)
                    safe_path = absolute_path.replace("'", "'\\''")
                    f.write(f"file '{safe_path}'\n")

            command = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_list_path,
                '-c', 'copy', # 재인코딩 없이 스트림 복사 (매우 빠름)
                output_path
            ]
            
            print("🚀 [FFmpeg] 기본 병합 (프로토콜) 명령어:")
            print(" ".join(command))

            result = subprocess.run(command, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                print(f"✅ 기본 병합 비디오 생성 완료: {output_path}")
                return True
            else:
                print(f"🔥🔥🔥 [오류] FFmpeg 기본 병합 실행 중 오류 발생!")
                print(f"Return code: {result.returncode}")
                print(f"Error output: {result.stderr}")
                return False

        except Exception as e:
            print(f"🔥🔥🔥 [오류] 최종 병합 중 예상치 못한 오류: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            if os.path.exists(concat_list_path):
                os.remove(concat_list_path)
    
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
