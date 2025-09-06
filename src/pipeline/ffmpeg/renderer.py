"""
FFmpeg 렌더러

오디오와 자막 이미지를 동기화하고 최종 MP4를 렌더링합니다.
품질 최적화 및 다양한 출력 옵션을 지원합니다.
"""

import os
import json
import subprocess
import tempfile
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import shutil


@dataclass
class RenderConfig:
    """렌더링 설정"""
    fps: int = 30
    resolution: str = "1920x1080"
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    video_bitrate: str = "5000k"
    audio_bitrate: str = "192k"
    quality_preset: str = "medium"
    output_format: str = "mp4"
    enable_hardware_acceleration: bool = False
    enable_two_pass_encoding: bool = False


class FFmpegRenderer:
    """FFmpeg 렌더러 클래스"""
    
    def __init__(self, config: Optional[RenderConfig] = None):
        """
        FFmpeg 렌더러 초기화
        
        Args:
            config: 렌더링 설정
        """
        self.config = config or RenderConfig()
        self._check_ffmpeg_availability()
    
    def _check_ffmpeg_availability(self) -> bool:
        """FFmpeg 사용 가능 여부 확인"""
        try:
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True, check=True)
            print("✅ FFmpeg 사용 가능")
            print(f"버전: {result.stdout.split('ffmpeg version ')[1].split(' ')[0]}")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ FFmpeg를 찾을 수 없습니다")
            print("🔧 FFmpeg 설치가 필요합니다: https://ffmpeg.org/download.html")
            return False
    
    def render_from_manifest(self, manifest_path: str, audio_path: str, 
                           subtitle_dir: str, output_path: str) -> bool:
        """
        Manifest에서 최종 MP4 렌더링
        
        Args:
            manifest_path: Manifest 파일 경로
            audio_path: 오디오 파일 경로
            subtitle_dir: 자막 이미지 디렉토리
            output_path: 출력 MP4 파일 경로
            
        Returns:
            bool: 성공 여부
        """
        try:
            # Manifest 로드
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest_data = json.load(f)
            
            # 자막 프레임 정보 로드
            subtitle_info_path = os.path.join(subtitle_dir, "subtitle_frames.json")
            if os.path.exists(subtitle_info_path):
                with open(subtitle_info_path, 'r', encoding='utf-8') as f:
                    subtitle_info = json.load(f)
            else:
                print("⚠️ 자막 프레임 정보를 찾을 수 없습니다")
                return False
            
            # 렌더링 실행
            return self._render_video(manifest_data, audio_path, subtitle_info, output_path)
            
        except Exception as e:
            print(f"❌ Manifest 렌더링 실패: {e}")
            return False
    
    def render_from_ssml(self, ssml_path: str, audio_path: str, 
                        subtitle_dir: str, output_path: str) -> bool:
        """
        SSML에서 최종 MP4 렌더링
        
        Args:
            ssml_path: SSML 파일 경로
            audio_path: 오디오 파일 경로
            subtitle_dir: 자막 이미지 디렉토리
            output_path: 출력 MP4 파일 경로
            
        Returns:
            bool: 성공 여부
        """
        try:
            # SSML 로드
            with open(ssml_path, 'r', encoding='utf-8') as f:
                ssml_content = f.read()
            
            # 자막 프레임 정보 로드
            subtitle_info_path = os.path.join(subtitle_dir, "subtitle_frames.json")
            if os.path.exists(subtitle_info_path):
                with open(subtitle_info_path, 'r', encoding='utf-8') as f:
                    subtitle_info = json.load(f)
            else:
                print("⚠️ 자막 프레임 정보를 찾을 수 없습니다")
                return False
            
            # 렌더링 실행
            return self._render_video_from_ssml(ssml_content, audio_path, subtitle_info, output_path)
            
        except Exception as e:
            print(f"❌ SSML 렌더링 실패: {e}")
            return False
    
    def _render_video(self, manifest_data: Dict[str, Any], audio_path: str,
                     subtitle_info: Dict[str, Any], output_path: str) -> bool:
        """비디오 렌더링 실행"""
        try:
            # 해상도 추출
            resolution = manifest_data.get("resolution", "1920x1080")
            width, height = map(int, resolution.split('x'))
            
            # 임시 concat 리스트 생성
            concat_list = self._create_concat_list_from_manifest(manifest_data, subtitle_info)
            
            if not concat_list:
                print("❌ concat 리스트 생성 실패")
                return False
            
            # FFmpeg 명령어 구성
            cmd = self._build_ffmpeg_command(concat_list, audio_path, output_path, width, height)
            
            # 렌더링 실행
            print("🎬 FFmpeg 렌더링 시작...")
            print(f"명령어: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            print("✅ 비디오 렌더링 완료!")
            print(f"출력 파일: {output_path}")
            
            # 임시 파일 정리
            self._cleanup_temp_files(concat_list)
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ FFmpeg 실행 실패: {e}")
            print(f"오류 출력: {e.stderr}")
            return False
        except Exception as e:
            print(f"❌ 렌더링 실패: {e}")
            return False
    
    def _render_video_from_ssml(self, ssml_content: str, audio_path: str,
                               subtitle_info: Dict[str, Any], output_path: str) -> bool:
        """SSML 기반 비디오 렌더링 실행"""
        try:
            # SSML에서 장면 정보 추출
            scenes = self._extract_scenes_from_ssml(ssml_content)
            
            # 임시 concat 리스트 생성
            concat_list = self._create_concat_list_from_ssml(scenes, subtitle_info)
            
            if not concat_list:
                print("❌ concat 리스트 생성 실패")
                return False
            
            # 기본 해상도 사용
            width, height = 1920, 1080
            
            # FFmpeg 명령어 구성
            cmd = self._build_ffmpeg_command(concat_list, audio_path, output_path, width, height)
            
            # 렌더링 실행
            print("🎬 SSML 기반 FFmpeg 렌더링 시작...")
            print(f"명령어: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            print("✅ SSML 기반 비디오 렌더링 완료!")
            print(f"출력 파일: {output_path}")
            
            # 임시 파일 정리
            self._cleanup_temp_files(concat_list)
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ FFmpeg 실행 실패: {e}")
            print(f"오류 출력: {e.stderr}")
            return False
        except Exception as e:
            print(f"❌ SSML 렌더링 실패: {e}")
            return False
    
    def _create_concat_list_from_manifest(self, manifest_data: Dict[str, Any], 
                                         subtitle_info: Dict[str, Any]) -> Optional[str]:
        """Manifest에서 concat 리스트 생성"""
        try:
            # 임시 파일 생성
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
            
            scenes = manifest_data.get("scenes", [])
            frames = subtitle_info.get("frames", [])
            
            # 장면별로 프레임 매핑
            for scene in scenes:
                scene_id = scene.get("id", "")
                scene_type = scene.get("type", "")
                
                if scene_type == "conversation":
                    # conversation 타입은 2개 화면
                    screen1_frames = [f for f in frames if f["scene_id"] == scene_id and f["screen_type"] == "screen1"]
                    screen2_frames = [f for f in frames if f["scene_id"] == scene_id and f["screen_type"] == "screen2"]
                    
                    if screen1_frames:
                        frame = screen1_frames[0]
                        # 절대 경로로 변환
                        abs_path = os.path.abspath(frame['output_path'])
                        temp_file.write(f"file '{abs_path}'\n")
                        temp_file.write(f"duration {frame['duration']}\n")
                    
                    if screen2_frames:
                        frame = screen2_frames[0]
                        # 절대 경로로 변환
                        abs_path = os.path.abspath(frame['output_path'])
                        temp_file.write(f"file '{abs_path}'\n")
                        temp_file.write(f"duration {frame['duration']}\n")
                
                elif scene_type in ["intro", "ending"]:
                    # intro/ending 타입은 1개 화면
                    scene_frames = [f for f in frames if f["scene_id"] == scene_id]
                    
                    if scene_frames:
                        frame = scene_frames[0]
                        # 절대 경로로 변환
                        abs_path = os.path.abspath(frame['output_path'])
                        temp_file.write(f"file '{abs_path}'\n")
                        temp_file.write(f"duration {frame['duration']}\n")
            
            # 마지막 프레임은 duration 없이 (FFmpeg concat demuxer 특성)
            if frames:
                last_frame = frames[-1]
                # 절대 경로로 변환
                abs_path = os.path.abspath(last_frame['output_path'])
                temp_file.write(f"file '{abs_path}'\n")
            
            temp_file.close()
            return temp_file.name
            
        except Exception as e:
            print(f"❌ concat 리스트 생성 실패: {e}")
            return None
    
    def _create_concat_list_from_ssml(self, scenes: List[Dict[str, Any]], 
                                     subtitle_info: Dict[str, Any]) -> Optional[str]:
        """SSML에서 concat 리스트 생성"""
        try:
            # 임시 파일 생성
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
            
            frames = subtitle_info.get("frames", [])
            
            # 프레임 순서대로 concat 리스트 작성
            for frame in frames:
                temp_file.write(f"file '{frame['output_path']}'\n")
                temp_file.write(f"duration {frame['duration']}\n")
            
            # 마지막 프레임은 duration 없이
            if frames:
                last_frame = frames[-1]
                temp_file.write(f"file '{last_frame['output_path']}'\n")
            
            temp_file.close()
            return temp_file.name
            
        except Exception as e:
            print(f"❌ SSML concat 리스트 생성 실패: {e}")
            return None
    
    def _extract_scenes_from_ssml(self, ssml_content: str) -> List[Dict[str, Any]]:
        """SSML에서 장면 정보 추출"""
        scenes = []
        
        # mark 태그에서 장면 정보 추출
        import re
        mark_pattern = r'<mark name="([^"]+)"\s*/>'
        marks = re.findall(mark_pattern, ssml_content)
        
        current_scene = None
        for mark in marks:
            if "scene_" in mark:
                parts = mark.split("_")
                if len(parts) >= 2:
                    scene_num = parts[1]
                    if current_scene != scene_num:
                        current_scene = scene_num
                        scenes.append({
                            "id": f"scene_{scene_num}",
                            "type": "conversation",
                            "sequence": int(scene_num)
                        })
        
        return scenes
    
    def _build_ffmpeg_command(self, concat_list: str, audio_path: str, 
                             output_path: str, width: int, height: int) -> List[str]:
        """FFmpeg 명령어 구성"""
        cmd = ['ffmpeg', '-y']  # -y: 기존 파일 덮어쓰기
        
        # 입력 파일들
        cmd.extend(['-f', 'concat', '-safe', '0', '-i', concat_list])
        
        # 오디오 파일이 유효한 경우에만 추가
        if audio_path and os.path.exists(audio_path) and os.path.getsize(audio_path) > 100:
            cmd.extend(['-i', audio_path])
            has_audio = True
        else:
            has_audio = False
        
        # 오디오가 없는 경우 무음 소스 추가
        if not has_audio:
            cmd.extend(['-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100'])
        
        # 비디오 필터
        video_filters = []
        
        # 해상도 조정
        video_filters.append(f'scale={width}:{height}:force_original_aspect_ratio=decrease')
        video_filters.append(f'pad={width}:{height}:(ow-iw)/2:(oh-ih)/2')
        
        # 품질 최적화
        if self.config.quality_preset != "medium":
            video_filters.append(f'fps={self.config.fps}')
        
        # 필터 적용
        if video_filters:
            cmd.extend(['-vf', ','.join(video_filters)])
        
        # 코덱 및 품질 설정
        cmd.extend(['-c:v', self.config.video_codec])
        cmd.extend(['-b:v', self.config.video_bitrate])
        
        # 오디오 코덱 설정
        if has_audio:
            cmd.extend(['-c:a', self.config.audio_codec])
            cmd.extend(['-b:a', self.config.audio_bitrate])
            cmd.extend(['-shortest'])  # 오디오와 비디오 중 짧은 것에 맞춤
        else:
            cmd.extend(['-c:a', 'aac'])
            cmd.extend(['-b:a', '128k'])
        
        # 품질 프리셋
        if self.config.video_codec == "libx264":
            cmd.extend(['-preset', self.config.quality_preset])
        
        # 하드웨어 가속
        if self.config.enable_hardware_acceleration:
            cmd.extend(['-hwaccel', 'auto'])
        
        # 출력 설정
        cmd.extend(['-pix_fmt', 'yuv420p'])
        
        # 출력 파일
        cmd.append(output_path)
        
        return cmd
    
    def _cleanup_temp_files(self, concat_list: str):
        """임시 파일 정리"""
        try:
            if os.path.exists(concat_list):
                os.remove(concat_list)
                print(f"✅ 임시 파일 정리: {concat_list}")
        except Exception as e:
            print(f"⚠️ 임시 파일 정리 실패: {e}")
    
    def optimize_quality(self, input_path: str, output_path: str, 
                        target_bitrate: str = "8000k") -> bool:
        """
        비디오 품질 최적화
        
        Args:
            input_path: 입력 비디오 파일 경로
            output_path: 출력 비디오 파일 경로
            target_bitrate: 목표 비트레이트
            
        Returns:
            bool: 성공 여부
        """
        try:
            # 2-pass 인코딩으로 품질 최적화
            if self.config.enable_two_pass_encoding:
                return self._two_pass_encoding(input_path, output_path, target_bitrate)
            else:
                return self._single_pass_encoding(input_path, output_path, target_bitrate)
                
        except Exception as e:
            print(f"❌ 품질 최적화 실패: {e}")
            return False
    
    def _single_pass_encoding(self, input_path: str, output_path: str, 
                            target_bitrate: str) -> bool:
        """단일 패스 인코딩"""
        cmd = [
            'ffmpeg', '-y',
            '-i', input_path,
            '-c:v', 'libx264',
            '-preset', 'slow',  # 품질 우선
            '-crf', '18',       # 고품질
            '-b:v', target_bitrate,
            '-c:a', 'aac',
            '-b:a', '256k',
            '-pix_fmt', 'yuv420p',
            output_path
        ]
        
        print("🎬 단일 패스 품질 최적화 시작...")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        print("✅ 단일 패스 품질 최적화 완료!")
        return True
    
    def _two_pass_encoding(self, input_path: str, output_path: str, 
                          target_bitrate: str) -> bool:
        """2패스 인코딩"""
        # 1차 패스
        pass1_cmd = [
            'ffmpeg', '-y',
            '-i', input_path,
            '-c:v', 'libx264',
            '-preset', 'slow',
            '-b:v', target_bitrate,
            '-pass', '1',
            '-f', 'null',
            '/dev/null' if os.name != 'nt' else 'NUL'
        ]
        
        print("🎬 2패스 인코딩 1차 패스 시작...")
        subprocess.run(pass1_cmd, check=True, capture_output=True, text=True)
        
        # 2차 패스
        pass2_cmd = [
            'ffmpeg', '-y',
            '-i', input_path,
            '-c:v', 'libx264',
            '-preset', 'slow',
            '-b:v', target_bitrate,
            '-pass', '2',
            '-c:a', 'aac',
            '-b:a', '256k',
            '-pix_fmt', 'yuv420p',
            output_path
        ]
        
        print("🎬 2패스 인코딩 2차 패스 시작...")
        subprocess.run(pass2_cmd, check=True, capture_output=True, text=True)
        
        # 임시 파일 정리
        for temp_file in ['ffmpeg2pass-0.log', 'ffmpeg2pass-0.log.mbtree']:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        
        print("✅ 2패스 인코딩 품질 최적화 완료!")
        return True
    
    def get_video_info(self, video_path: str) -> Dict[str, Any]:
        """비디오 파일 정보 조회"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            info = json.loads(result.stdout)
            
            return {
                "duration": float(info.get("format", {}).get("duration", 0)),
                "size": int(info.get("format", {}).get("size", 0)),
                "bitrate": int(info.get("format", {}).get("bit_rate", 0)),
                "streams": info.get("streams", [])
            }
            
        except Exception as e:
            print(f"⚠️ 비디오 정보 조회 실패: {e}")
            return {}
    
    def create_preview(self, input_path: str, output_path: str, 
                      duration: int = 10) -> bool:
        """
        비디오 프리뷰 생성
        
        Args:
            input_path: 입력 비디오 파일 경로
            output_path: 출력 프리뷰 파일 경로
            duration: 프리뷰 길이 (초)
            
        Returns:
            bool: 성공 여부
        """
        try:
            cmd = [
                'ffmpeg', '-y',
                '-i', input_path,
                '-t', str(duration),
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '23',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-pix_fmt', 'yuv420p',
                output_path
            ]
            
            print(f"🎬 {duration}초 프리뷰 생성 시작...")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            print("✅ 프리뷰 생성 완료!")
            return True
            
        except Exception as e:
            print(f"❌ 프리뷰 생성 실패: {e}")
            return False
