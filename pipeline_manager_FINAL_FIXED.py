"""
통합 파이프라인 매니저

Manifest부터 최종 MP4까지 전체 파이프라인을 관리하고 조율합니다.
"""

import os
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from ..manifest import ManifestParser
from ..audio import AudioGenerator
from ..steps.create_subtitles import run as create_subtitles_run
from ..steps.create_timeline import run as create_timeline_run
from ..core.context import PipelineContext
from .renderer import FFmpegRenderer


@dataclass
class PipelineConfig:
    """파이프라인 설정"""
    output_directory: str = "output"
    enable_audio_generation: bool = True
    enable_subtitle_generation: bool = True
    enable_video_rendering: bool = True


class PipelineManager:
    """통합 파이프라인 매니저"""
    
    def __init__(self, config: Optional[PipelineConfig] = None, root=None):
        self.root = root
        if isinstance(config, PipelineConfig):
            self.config = config
        else:
            self.config = PipelineConfig()
        self.manifest_parser = ManifestParser()
        self.audio_generator = AudioGenerator()
        self.ffmpeg_renderer = FFmpegRenderer()

    def run_manifest_creation(self, ui_data: Dict[str, Any]) -> Dict[str, Any]:
        """1. Manifest 생성"""
        try:
            project_name = ui_data.get('project_name', '')
            identifier = ui_data.get('identifier', '')
            script_type = ui_data.get('script_type', '회화')
            
            if not project_name or not identifier:
                return {
                    'success': False,
                    'errors': ['프로젝트명과 식별자가 필요합니다.'],
                    'generated_files': {}
                }
            
            output_dir = os.path.join("output", project_name, identifier)
            os.makedirs(output_dir, exist_ok=True)
            
            manifest_data, manifest_path = self.create_manifest(script_type, ui_data)
            
            if not manifest_path:
                return {
                    'success': False,
                    'errors': ['매니페스트 생성 실패'],
                    'generated_files': {}
                }
            
            return {
                'success': True,
                'generated_files': {'manifest': manifest_path},
                'errors': []
            }
            
        except Exception as e:
            return {
                'success': False,
                'errors': [f'매니페스트 생성 중 오류: {str(e)}'],
                'generated_files': {}
            }

    def run_timing_based_video_rendering(self, ui_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        타이밍 JSON을 직접 사용한 비디오 렌더링
        """
        try:
            project_name = ui_data.get('project_name', '')
            identifier = ui_data.get('identifier', '')
            script_type = ui_data.get('script_type', '회화')
            
            if not project_name or not identifier:
                return {"success": False, "message": "프로젝트명과 식별자가 필요합니다."}
            
            output_dir = f"output/{project_name}/{identifier}"
            
            english_script_type = {"회화": "conversation", "대화": "conversation", "인트로": "intro", "엔딩": "ending"}.get(script_type, script_type)
            timing_path = os.path.join(output_dir, "timing", f"{identifier}_{english_script_type}.json")
            
            if not os.path.exists(timing_path):
                return {"success": False, "message": f"타이밍 파일을 찾을 수 없습니다: {timing_path}"}
            
            image_dir = os.path.join(output_dir, "conversation") if script_type in ["회화", "대화"] else os.path.join(output_dir, "intro_ending")
            
            if not os.path.exists(image_dir):
                return {"success": False, "message": f"이미지 디렉토리를 찾을 수 없습니다: {image_dir}"}
            
            video_dir = os.path.join(output_dir, "mp4")
            os.makedirs(video_dir, exist_ok=True)
            output_video_path = os.path.join(video_dir, f"{project_name}_{english_script_type}.mp4")
            
            success = self.ffmpeg_renderer.create_video_from_timing(
                timing_path, output_video_path, image_dir
            )
            
            if success and os.path.exists(output_video_path):
                return {
                    "success": True,
                    "message": f"타이밍 기반 비디오 생성 완료: {output_video_path}",
                    "video_path": output_video_path
                }
            else:
                return {"success": False, "message": "타이밍 기반 비디오 생성 실패"}
                
        except Exception as e:
            return {"success": False, "message": f"오류: {e}"}

    def run_audio_generation(self, ui_data: Dict[str, Any], output_text=None) -> Dict[str, Any]:
        """2. 오디오 및 타이밍 통합 생성"""
        return self.create_audio(ui_data.get('script_type', '회화'), ui_data, output_text)

    def run_subtitle_creation(self, ui_data: Dict[str, Any], output_text=None) -> Dict[str, Any]:
        """3. 자막 이미지 생성"""
        return self.create_subtitles(ui_data.get('script_type', '회화'), output_text)

    def run_timeline_creation(self, ui_data: Dict[str, Any], output_text=None) -> Dict[str, Any]:
        """4. 타임라인 생성"""
        return self.create_timeline(ui_data.get('script_type', '회화'), output_text)

    def run_video_rendering(self, ui_data: Dict[str, Any], output_text=None) -> Dict[str, Any]:
        """5. 비디오 렌더링"""
        try:
            project_name = ui_data.get('project_name', '')
            identifier = ui_data.get('identifier', '')
            script_type = ui_data.get('script_type', '회화')
            
            if not project_name or not identifier:
                return {'success': False, 'errors': ['프로젝트명과 식별자가 필요합니다.']}

            output_dir = os.path.join("output", project_name, identifier)
            manifest_path = os.path.join(output_dir, "manifest", f"{identifier}_{script_type}.json")
            timeline_path = os.path.join(output_dir, "timeline", f"{identifier}_{script_type}.json")

            if not os.path.exists(manifest_path) or not os.path.exists(timeline_path):
                return {'success': False, 'errors': ['매니페스트 또는 타임라인 파일이 없습니다.']}

            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest_data = json.load(f)

            video_path = self._render_video(manifest_data, output_dir, script_type)
            if not video_path:
                return {'success': False, 'errors': ['비디오 렌더링 실패']}
            
            return {'success': True, 'generated_files': {'video': video_path}}
        except Exception as e:
            return {'success': False, 'errors': [f'비디오 렌더링 중 오류: {str(e)}']}

    def run_pipeline_from_ui_data(self, ui_data: Dict[str, Any]) -> Dict[str, Any]:
        """UI 데이터를 받아서 파이프라인을 실행하고 결과를 반환"""
        try:
            project_name = ui_data.get('project_name', '')
            identifier = ui_data.get('identifier', '')
            script_type = ui_data.get('script_type', '회화')
            
            if not project_name or not identifier:
                return {'success': False, 'errors': ['프로젝트명과 식별자가 필요합니다.']}
            
            output_dir = os.path.join("output", project_name, identifier)
            os.makedirs(output_dir, exist_ok=True)
            
            # 1. Manifest 생성
            manifest_data, manifest_path = self.create_manifest(script_type, ui_data)
            if not manifest_path:
                return {'success': False, 'errors': ['매니페스트 생성 실패']}

            # 2. 오디오 및 타이밍 생성
            audio_path = None
            if ui_data.get('enable_audio_generation', True):
                audio_result = self.create_audio(script_type, ui_data)
                if audio_result.get('success'):
                    audio_path = audio_result.get('generated_files', {}).get('audio')
                else:
                    return audio_result # Error

            # 3. 자막 이미지 생성
            if ui_data.get('enable_subtitle_generation', True):
                subtitle_result = self.create_subtitles(script_type, ui_data)
                if not subtitle_result.get('success'):
                    return subtitle_result # Error

            # 4. 타임라인 생성
            timeline_result = self.create_timeline(script_type, ui_data)
            if not timeline_result.get('success'):
                return timeline_result # Error

            # 5. 비디오 렌더링
            video_path = None
            if ui_data.get('enable_video_rendering', True):
                render_result = self.run_video_rendering(ui_data)
                if render_result.get('success'):
                    video_path = render_result.get('generated_files', {}).get('video')
                else:
                    return render_result # Error

            return {'success': True, 'generated_files': {'video': video_path}}

        except Exception as e:
            return {'success': False, 'errors': [f'파이프라인 실행 중 오류: {str(e)}']}
    
    def _render_video(self, manifest_data: Dict, output_dir: str, script_type: str) -> Optional[str]:
        """Helper for rendering a single video type"""
        try:
            project_name = manifest_data.get('project_name', 'project')
            identifier = manifest_data.get('identifier', project_name)
            video_dir = os.path.join(output_dir, "video")
            os.makedirs(video_dir, exist_ok=True)

            english_script_type = {"회화": "conversation", "대화": "conversation", "인트로": "intro", "엔딩": "ending"}.get(script_type, script_type)
            timeline_path = os.path.join(output_dir, "timeline", f"{identifier}_{english_script_type}.json")
            
            if not os.path.exists(timeline_path):
                print(f"🔥🔥🔥 [오류] 타임라인 파일을 찾을 수 없습니다: {timeline_path}")
                return None

            output_video_path = os.path.join(video_dir, f"{project_name}_{english_script_type}.mp4")
            
            success = self.ffmpeg_renderer.create_conversation_video(
                [], "", "", output_video_path, "1920x1080", ""
            )
            
            return output_video_path if success else None
        except Exception as e:
            print(f"❌ _render_video 실패: {e}")
            return None

    def create_final_merged_video(self, project_name: str, identifier: str, output_dir: str) -> Optional[str]:
        """개별 비디오들을 병합하여 최종 비디오 생성"""
        try:
            video_dir = os.path.join(output_dir, "video")
            intro_path = os.path.join(video_dir, f"{project_name}_intro.mp4")
            conversation_path = os.path.join(video_dir, f"{project_name}_conversation.mp4")
            ending_path = os.path.join(video_dir, f"{project_name}_ending.mp4")
            
            existing_videos = []
            if os.path.exists(intro_path): existing_videos.append(intro_path)
            if os.path.exists(conversation_path): existing_videos.append(conversation_path)
            if os.path.exists(ending_path): existing_videos.append(ending_path)
            
            if not existing_videos:
                print("❌ 병합할 비디오 파일이 없습니다.")
                return None
            
            final_path = os.path.join(video_dir, f"{project_name}_final.mp4")
            
            success = self.ffmpeg_renderer.create_final_merged_video(
                intro_path if os.path.exists(intro_path) else None,
                conversation_path if os.path.exists(conversation_path) else None,
                ending_path if os.path.exists(ending_path) else None,
                final_path
            )
            
            return final_path if success else None
        except Exception as e:
            print(f"❌ 최종 비디오 병합 실패: {e}")
            return None

    def _log_to_widget(self, message: str, level: str = "INFO", widget: Optional[Any] = None):
        """콘솔과 UI 텍스트 위젯에 로그를 출력합니다."""
        log_message = f"[{level}] {message}"
        print(log_message)
        if widget:
            try:
                widget.insert("end", f"{log_message}\n")
                widget.see("end")
            except Exception as e:
                print(f"UI 위젯에 로깅 실패: {e}")
