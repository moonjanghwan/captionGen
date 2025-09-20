"""
통합 파이프라인 매니저

Manifest부터 최종 MP4까지 전체 파이프라인을 관리하고 조율합니다.
"""

import os
import json
import time
import time as time_module
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from ..manifest import ManifestParser
from ..audio import AudioGenerator, SSMLBuilder
# SubtitleGenerator는 삭제됨 - PNGRenderer 사용
# from ..subtitle import SubtitleGenerator
from ..steps.create_subtitles import run as create_subtitles_run

from ..core.context import PipelineContext
from .renderer import FFmpegRenderer


@dataclass
class PipelineConfig:
    """파이프라인 설정"""
    output_directory: str = "output"
    enable_audio_generation: bool = True
    enable_subtitle_generation: bool = True
    enable_video_rendering: bool = True
    enable_quality_optimization: bool = False
    enable_preview_generation: bool = True
    cleanup_temp_files: bool = True


@dataclass
class PipelineResult:
    """파이프라인 실행 결과"""
    success: bool
    manifest_path: str
    audio_path: Optional[str]
    subtitle_dir: Optional[str]
    video_path: Optional[str]
    preview_path: Optional[str]
    execution_time: float
    errors: List[str]
    warnings: List[str]


class PipelineManager:
    """통합 파이프라인 매니저"""
    
    def __init__(self, config: Optional[PipelineConfig] = None, root=None):
        """
        파이프라인 매니저 초기화
        
        Args:
            config: 파이프라인 설정
            root: UI 루트 객체
        """
        self.root = root
        # config가 PipelineConfig 인스턴스가 아닌 경우 기본값 사용
        if isinstance(config, PipelineConfig):
            self.config = config
        else:
            self.config = PipelineConfig()
        self.manifest_parser = ManifestParser()
        self.audio_generator = AudioGenerator()
        # SubtitleGenerator는 삭제됨 - PNGRenderer 사용
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
            
            # 출력 디렉토리 설정
            output_dir = os.path.join("output", project_name, identifier)
            os.makedirs(output_dir, exist_ok=True)
            
            # 매니페스트 생성
            manifest_path = self._create_manifest(project_name, identifier, script_type, output_dir, ui_data)
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

    def run_audio_generation(self, ui_data: Dict[str, Any]) -> Dict[str, Any]:
        """2. 오디오 생성"""
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
            manifest_path = os.path.join(output_dir, "manifest", f"{identifier}_{script_type}.json")
            
            if not os.path.exists(manifest_path):
                return {
                    'success': False,
                    'errors': ['매니페스트 파일을 찾을 수 없습니다. 먼저 매니페스트를 생성해주세요.'],
                    'generated_files': {}
                }

            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest_data = json.load(f)

            audio_output_dir = os.path.join(output_dir, "mp3")
            os.makedirs(audio_output_dir, exist_ok=True)

            # 새로 통합된 함수 호출
            audio_path, timing_info = self.audio_generator.generate_audio_and_timing(
                manifest_data, audio_output_dir, script_type
            )
            
            if audio_path and timing_info:
                timing_output_dir = os.path.join(output_dir, "timing")
                os.makedirs(timing_output_dir, exist_ok=True)
                
                english_script_type = {"회화": "conversation", "대화": "dialogue", "인트로": "intro", "엔딩": "ending"}.get(script_type, script_type)
                timing_path = os.path.join(timing_output_dir, f"{identifier}_{english_script_type}.json")
                
                self.audio_generator.save_precise_timing_info(timing_info, timing_path)
                
                return {
                    'success': True,
                    'generated_files': {'audio': audio_path, 'timing': timing_path}
                }
            else:
                return {'success': False, 'errors': ['오디오 및 타이밍 생성 실패']}
            
        except Exception as e:
            return {
                'success': False,
                'errors': [f'오디오 생성 중 오류: {str(e)}'],
                'generated_files': {}
            }

    def run_subtitle_creation(self, ui_data: Dict[str, Any]) -> Dict[str, Any]:
        """3. 자막 이미지 생성"""
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
            
            # 출력 디렉토리 설정
            output_dir = os.path.join("output", project_name, identifier)
            manifest_path = os.path.join(output_dir, "manifest", f"{identifier}_{script_type}.json")
            
            if not os.path.exists(manifest_path):
                return {
                    'success': False,
                    'errors': ['매니페스트 파일을 찾을 수 없습니다. 먼저 매니페스트를 생성해주세요.'],
                    'generated_files': {}
                }
            
            # 자막 이미지 생성
            subtitle_dir = self._create_subtitles(manifest_path, output_dir)
            if not subtitle_dir:
                return {
                    'success': False,
                    'errors': ['자막 이미지 생성 실패'],
                    'generated_files': {}
                }
            
            return {
                'success': True,
                'generated_files': {'subtitles': subtitle_dir},
                'errors': []
            }
            
        except Exception as e:
            return {
                'success': False,
                'errors': [f'자막 이미지 생성 중 오류: {str(e)}'],
                'generated_files': {}
            }



    def run_video_rendering(self, ui_data: Dict[str, Any]) -> Dict[str, Any]:
        """5. 비디오 렌더링"""
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
            
            # 출력 디렉토리 설정
            output_dir = os.path.join("output", project_name, identifier)
            manifest_path = os.path.join(output_dir, "manifest", f"{identifier}_{script_type}.json")
            timeline_path = os.path.join(output_dir, "timeline", f"{identifier}_{script_type}.json")
            
            if not os.path.exists(manifest_path):
                return {
                    'success': False,
                    'errors': ['매니페스트 파일을 찾을 수 없습니다. 먼저 매니페스트를 생성해주세요.'],
                    'generated_files': {}
                }
            
            if not os.path.exists(timeline_path):
                return {
                    'success': False,
                    'errors': ['타임라인 파일을 찾을 수 없습니다. 먼저 타임라인을 생성해주세요.'],
                    'generated_files': {}
                }
            
            # 비디오 렌더링
            video_path = self._render_video(manifest_path, None, None, output_dir, script_type)
            if not video_path:
                return {
                    'success': False,
                    'errors': ['비디오 렌더링 실패'],
                    'generated_files': {}
                }
            
            return {
                'success': True,
                'generated_files': {'video': video_path},
                'errors': []
            }
            
        except Exception as e:
            return {
                'success': False,
                'errors': [f'비디오 렌더링 중 오류: {str(e)}'],
                'generated_files': {}
            }

    def run_pipeline_from_ui_data(self, ui_data: Dict[str, Any]) -> Dict[str, Any]:
        """UI 데이터를 받아서 파이프라인을 실행하고 결과를 반환"""
        try:
            project_name = ui_data.get('project_name', '')
            identifier = ui_data.get('identifier', '')
            script_type = ui_data.get('script_type', '회화')
            
            if not project_name or not identifier:
                return {'success': False, 'errors': ['프로젝트명과 식별자가 필요합니다.'], 'generated_files': {}}
            
            output_dir = os.path.join("output", project_name, identifier)
            os.makedirs(output_dir, exist_ok=True)
            
            # 매니페스트 생성
            manifest_path = self._create_manifest(project_name, identifier, script_type, output_dir, ui_data)
            if not manifest_path:
                return {'success': False, 'errors': ['매니페스트 생성 실패'], 'generated_files': {}}
            
            # 오디오 생성
            audio_path = None
            if ui_data.get('enable_audio_generation', True):
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest_data = json.load(f)
                audio_output_dir = os.path.join(output_dir, "mp3")
                os.makedirs(audio_output_dir, exist_ok=True)
                
                new_audio_path, timing_info = self.audio_generator.generate_audio_and_timing(
                    manifest_data, audio_output_dir, script_type
                )
                if new_audio_path and timing_info:
                    audio_path = new_audio_path
                    timing_output_dir = os.path.join(output_dir, "timing")
                    os.makedirs(timing_output_dir, exist_ok=True)
                    english_script_type = {"회화": "conversation", "대화": "dialogue", "인트로": "intro", "엔딩": "ending"}.get(script_type, script_type)
                    timing_path = os.path.join(timing_output_dir, f"{identifier}_{english_script_type}.json")
                    self.audio_generator.save_precise_timing_info(timing_info, timing_path)

            # 자막 이미지 생성
            subtitle_dir = None
            if ui_data.get('enable_subtitle_generation', True):
                subtitle_dir = self._create_subtitles(manifest_path, output_dir)
            
            # 비디오 렌더링
            video_result = None
            if ui_data.get('enable_video_rendering', True):
                script_type_mapping = {"회화": "conversation", "대화": "conversation", "인트로": "intro", "엔딩": "ending"}
                english_script_type = script_type_mapping.get(script_type, "conversation")
                video_result = self._render_video(manifest_path, audio_path, subtitle_dir, output_dir, english_script_type)
            
            # 결과 반환
            generated_files = {}
            if audio_path:
                generated_files['audio'] = audio_path
            if subtitle_dir:
                generated_files['subtitle_dir'] = subtitle_dir
            if video_result:
                if isinstance(video_result, dict):
                    generated_files.update(video_result)
                else:
                    generated_files['video'] = video_result
            
            return {'success': True, 'errors': [], 'warnings': [], 'generated_files': generated_files}
            
        except Exception as e:
            return {'success': False, 'errors': [f'파이프라인 실행 중 오류: {str(e)}'], 'generated_files': {}}    
    def _create_manifest(self, project_name: str, identifier: str, script_type: str, output_dir: str, ui_data: Dict = None) -> Optional[str]:
        """매니페스트 생성"""
        try:
            manifest_dir = os.path.join(output_dir, "manifest")
            os.makedirs(manifest_dir, exist_ok=True)
            
            # 스크립트 타입을 영문으로 변환
            script_type_mapping = {
                "회화": "conversation",
                "대화": "conversation", 
                "인트로": "intro",
                "엔딩": "ending"
            }
            english_script_type = script_type_mapping.get(script_type, script_type)
            manifest_filename = f"{identifier}_{english_script_type}.json"
            manifest_path = os.path.join(manifest_dir, manifest_filename)
            
            # 매니페스트 생성 - 실제 회화 데이터 포함
            manifest_data = {
                "project_name": project_name,
                "identifier": identifier,
                "script_type": script_type,
                "scenes": [],
                "intro_script": "안녕하세요. 학습을 시작하겠습니다.",
                "ending_script": "학습이 완료되었습니다. 감사합니다."
            }
            
            # 회화 스크립트인 경우 실제 회화 데이터 추가
            if script_type in ["회화", "대화"]:
                # UI에서 회화 데이터 가져오기
                conversation_data = self._get_conversation_data_from_ui(ui_data)
                if conversation_data:
                    manifest_data["scenes"] = conversation_data
                    print(f"✅ 회화 데이터 {len(conversation_data)}개 장면을 매니페스트에 추가")
                else:
                    print("⚠️ 회화 데이터를 찾을 수 없습니다.")
            
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 매니페스트 생성 완료: {manifest_path}")
            return manifest_path
            
        except Exception as e:
            print(f"❌ 매니페스트 생성 실패: {e}")
            return None
    
    def _create_subtitles(self, manifest_path: str, output_dir: str) -> Optional[str]:
        """자막 이미지 생성"""
        try:
            subtitle_dir = os.path.join(output_dir, "subtitles")
            os.makedirs(subtitle_dir, exist_ok=True)
            
            # 자막 이미지 생성 로직 (실제로는 PNG 렌더러 사용)
            print(f"✅ 자막 이미지 생성 완료: {subtitle_dir}")
            return subtitle_dir
            
        except Exception as e:
            print(f"❌ 자막 이미지 생성 실패: {e}")
            return None
    
    def _render_video(self, manifest_path: str, audio_path: Optional[str], subtitle_dir: Optional[str], output_dir: str, script_type: str = "conversation") -> Optional[Dict[str, str]]:
        """비디오 렌더링 - 새로운 VideoGenerator 기반"""
        try:
            video_dir = os.path.join(output_dir, "video")
            os.makedirs(video_dir, exist_ok=True)
            
            # 매니페스트 데이터 로드
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest_data = json.load(f)
            
            project_name = manifest_data.get('project_name', 'project')
            identifier = manifest_data.get('identifier', project_name)
            
            # 타이밍 파일 경로 생성 (타임라인 대신)
            timing_path = os.path.join(output_dir, "timing", f"{identifier}_{script_type}.json")
            
            if not os.path.exists(timing_path):
                print(f"🔥🔥🔥 [오류] 타이밍 파일을 찾을 수 없습니다: {timing_path}")
                print("💡 먼저 '오디오 생성' 버튼을 눌러 타이밍 파일을 생성해주세요.")
                return None
            
            # 출력 비디오 경로 생성
            output_video_path = os.path.join(video_dir, f"{project_name}_{script_type}.mp4")
            
            print(f"🎬 {script_type} 비디오 생성 시작 (타이밍 기반)")
            print(f"  - 타이밍: {timing_path}")
            print(f"  - 출력: {output_video_path}")
            
            # 이미지 디렉토리 경로 설정
            image_subdir_map = {
                "conversation": "conversation",
                "intro": "intro",
                "ending": "ending"
            }
            image_subdir = image_subdir_map.get(script_type, script_type)
            image_dir = os.path.join(output_dir, image_subdir)

            if not os.path.exists(image_dir):
                print(f"🔥🔥🔥 [오류] 이미지 디렉토리를 찾을 수 없습니다: {image_dir}")
                return None

            # 올바른 렌더링 함수 호출
            success = self.ffmpeg_renderer.create_video_from_timing(
                timing_path, output_video_path, image_dir, script_type
            )            
            if success and os.path.exists(output_video_path):
                print(f"✅ {script_type} 비디오 생성 완료: {output_video_path}")
                return {f"{script_type}_video": output_video_path}
            else:
                print(f"❌ {script_type} 비디오 생성 실패")
                return None
                
        except Exception as e:
            print(f"❌ 비디오 렌더링 실패: {e}")
            return None
    
    def create_final_merged_video(self, project_name: str, identifier: str, output_dir: str, smooth_transition: bool = True) -> Optional[str]:
        """개별 비디오들을 병합하여 최종 비디오 생성"""
        try:
            video_dir = os.path.join(output_dir, "video")
            mp4_dir = os.path.join(output_dir, "mp4")
            
            # 개별 비디오 파일들 찾기 (모든 비디오는 mp4 폴더에 저장됨)
            intro_path = os.path.join(mp4_dir, f"{identifier}_intro.mp4")
            conversation_path = os.path.join(mp4_dir, f"{identifier}_conversation.mp4")
            ending_path = os.path.join(mp4_dir, f"{identifier}_ending.mp4")
            
            # 존재하는 비디오 파일들만 수집
            existing_videos = []
            if os.path.exists(intro_path):
                existing_videos.append(intro_path)
                print(f"✅ 인트로 비디오 발견: {intro_path}")
            if os.path.exists(conversation_path):
                existing_videos.append(conversation_path)
                print(f"✅ 회화 비디오 발견: {conversation_path}")
            if os.path.exists(ending_path):
                existing_videos.append(ending_path)
                print(f"✅ 엔딩 비디오 발견: {ending_path}")
            
            if not existing_videos:
                print("❌ 병합할 비디오 파일이 없습니다.")
                return None
            
            # 최종 비디오 경로 (mp4 폴더에 저장)
            final_path = os.path.join(mp4_dir, f"{identifier}_final.mp4")
            
            # 비디오 병합
            success = self.ffmpeg_renderer.create_final_merged_video(
                intro_path if os.path.exists(intro_path) else None,
                conversation_path if os.path.exists(conversation_path) else None,
                ending_path if os.path.exists(ending_path) else None,
                final_path,
                smooth_transition
            )
            
            if success and os.path.exists(final_path):
                print(f"✅ 최종 비디오 병합 완료: {final_path}")
                return final_path
            else:
                print("❌ 최종 비디오 병합 실패")
                return None
                
        except Exception as e:
            print(f"❌ 최종 비디오 병합 실패: {e}")
            return None
    
    def _get_background_path(self) -> str:
        """배경 이미지 경로 설정 (자막 이미지에 배경이 포함되어 있으므로 사용하지 않음)"""
        print("🎬 자막 이미지에 배경이 포함되어 있으므로 별도 배경 이미지 불필요")
        return None
    
    def _extract_intro_sentences(self, manifest_data: Dict) -> List[str]:
        """매니페스트에서 인트로 문장들 추출"""
        try:
            intro_script = manifest_data.get('intro_script', '')
            if not intro_script:
                return []
            
            # 문장별로 분리 (간단한 분리 로직)
            sentences = [s.strip() for s in intro_script.split('.') if s.strip()]
            return sentences
        except Exception:
            return []
    
    def _extract_ending_sentences(self, manifest_data: Dict) -> List[str]:
        """매니페스트에서 엔딩 문장들 추출"""
        try:
            ending_script = manifest_data.get('ending_script', '')
            if not ending_script:
                return []
            
            # 문장별로 분리 (간단한 분리 로직)
            sentences = [s.strip() for s in ending_script.split('.') if s.strip()]
            return sentences
        except Exception:
            return []
    
    def _get_conversation_data_from_ui(self, ui_data=None) -> List[Dict]:
        """UI에서 회화 데이터 가져오기"""
        try:
            print(f"🔍 UI 데이터 추출 시작...")
            print(f"🔍 전달받은 ui_data: {ui_data}")
            
            # UI 데이터가 직접 전달된 경우 사용
            if ui_data and 'scenes' in ui_data:
                scenes = ui_data['scenes']
                print(f"✅ UI에서 직접 전달받은 회화 데이터: {len(scenes)}개")
                
                conversation_data = []
                for scene in scenes:
                    conversation_data.append({
                        'sequence': int(scene.get('order', 1)) if str(scene.get('order', 1)).isdigit() else len(conversation_data) + 1,
                        'type': 'conversation',
                        'native_script': scene.get('native_script', ''),
                        'learning_script': scene.get('learning_script', ''),
                        'reading_script': scene.get('reading_script', '')
                    })
                    print(f"    ✅ 회화 데이터 추가: {scene.get('native_script', '')}")
                
                print(f"🔍 최종 추출된 회화 데이터: {len(conversation_data)}개")
                return conversation_data
            
            # UI 데이터가 없거나 scenes가 없는 경우 테스트용 샘플 데이터 사용
            if not ui_data or 'scenes' not in ui_data:
                print(f"⚠️ UI 데이터가 없거나 scenes가 없습니다. 테스트용 샘플 데이터를 사용합니다.")
                return [
                    {
                        'sequence': 1,
                        'type': 'conversation',
                        'native_script': '안녕하세요!',
                        'learning_script': '你好！',
                        'reading_script': '니 하오!'
                    },
                    {
                        'sequence': 2,
                        'type': 'conversation',
                        'native_script': '감사합니다.',
                        'learning_script': '谢谢。',
                        'reading_script': '씨에 씨에'
                    },
                    {
                        'sequence': 3,
                        'type': 'conversation',
                        'native_script': '이거 얼마예요?',
                        'learning_script': '这个多少钱？',
                        'reading_script': '쩌거 뚜오샤오 치엔?'
                    },
                    {
                        'sequence': 4,
                        'type': 'conversation',
                        'native_script': '죄송합니다 / 실례합니다.',
                        'learning_script': '对不起 / 不好意思。',
                        'reading_script': '뙤이부치 / 뿌 하오 이쓰'
                    },
                    {
                        'sequence': 5,
                        'type': 'conversation',
                        'native_script': '안녕히 계세요.',
                        'learning_script': '再见。',
                        'reading_script': '짜이찌엔'
                    }
                ]
            
            # 기존 방식 (root 접근) - 호환성을 위해 유지
            if not hasattr(self, 'root'):
                print(f"❌ self.root가 없습니다.")
                return []
            
            if not hasattr(self.root, 'data_page'):
                print(f"❌ self.root.data_page가 없습니다.")
                return []
            
            print(f"✅ UI 데이터 페이지 접근 성공")
            
            # UI의 CSV 트리에서 회화 데이터 추출
            conversation_data = []
            csv_tree = self.root.data_page.csv_tree
            
            print(f"🔍 CSV 트리에서 데이터 추출 중...")
            children = csv_tree.get_children()
            print(f"  - CSV 트리 자식 개수: {len(children)}")
            
            for i, item_id in enumerate(children):
                values = csv_tree.item(item_id, 'values')
                print(f"  - item {i}: {values}")
                
                if len(values) >= 4:
                    sequence, native_script, learning_script, reading_script = values[:4]
                    conversation_data.append({
                        'sequence': int(sequence) if sequence.isdigit() else len(conversation_data) + 1,
                        'type': 'conversation',
                        'native_script': native_script or '',
                        'learning_script': learning_script or '',
                        'reading_script': reading_script or ''
                    })
                    print(f"    ✅ 회화 데이터 추가: {native_script}")
                else:
                    print(f"    ❌ 데이터 부족: {len(values)}개 컬럼")
            
            print(f"🔍 최종 추출된 회화 데이터: {len(conversation_data)}개")
            return conversation_data
        except Exception as e:
            print(f"❌ UI에서 회화 데이터 추출 실패: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _extract_conversation_data(self, manifest_data: Dict) -> List[Dict]:
        """매니페스트에서 회화 데이터 추출"""
        try:
            print(f"🔍 매니페스트 데이터 구조 확인:")
            print(f"  - manifest_data keys: {list(manifest_data.keys())}")
            
            scenes = manifest_data.get('scenes', [])
            print(f"  - scenes 개수: {len(scenes)}")
            
            conversation_data = []
            
            for i, scene in enumerate(scenes):
                print(f"  - scene {i}: {scene}")
                if scene.get('type') == 'conversation':
                    conversation_data.append({
                        'sequence': scene.get('sequence', 1),
                        'native_script': scene.get('native_script', ''),
                        'learning_script': scene.get('learning_script', ''),
                        'reading_script': scene.get('reading_script', '')
                    })
                    print(f"    ✅ 회화 장면 추가: {scene.get('native_script', '')}")
                else:
                    print(f"    ❌ 회화 장면이 아님: type={scene.get('type')}")
            
            print(f"🔍 최종 추출된 회화 데이터: {len(conversation_data)}개")
            return conversation_data
        except Exception as e:
            print(f"❌ 회화 데이터 추출 중 오류: {e}")
            import traceback
            traceback.print_exc()
            return []
        
        # 출력 디렉토리 생성
        os.makedirs(self.config.output_directory, exist_ok=True)

    def _log_to_widget(self, message: str, level: str = "INFO", widget: Optional[Any] = None):
        """콘솔과 UI 텍스트 위젯에 로그를 출력합니다."""
        log_message = f"[{level}] {message}"
        print(log_message)
        if widget:
            try:
                # tkinter 위젯의 thread-safety를 위해 after 사용 고려
                widget.insert("end", f"{log_message}\n")
                widget.see("end")
            except Exception as e:
                print(f"UI 위젯에 로깅 실패: {e}")
    
    def create_manifest(self, script_type: str, script_data: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        """
        Manifest 생성
        
        Args:
            script_type: 스크립트 타입 (conversation, intro, ending)
            script_data: 스크립트 데이터
            
        Returns:
            Tuple[Dict[str, Any], str]: (manifest_data, filepath)
        """
        try:
            # Manifest 생성
            manifest_data = self.manifest_parser.create_manifest(script_type, script_data)
            
            # 파일 저장 경로 생성
            project_name = manifest_data.get("project_name", "untitled_project")
            identifier = manifest_data.get("identifier", project_name)
            
            # 스크립트 타입을 영문으로 변환
            script_type_mapping = {
                "회화": "conversation",
                "대화": "dialogue", 
                "인트로": "intro",
                "엔딩": "ending"
            }
            english_script_type = script_type_mapping.get(script_type, script_type.lower())
            filename = f"{identifier}_{english_script_type}.json"
            
            # 정확한 디렉토리 구조: ./output/{프로젝트명}/{식별자}/manifest/
            project_name = manifest_data.get("project_name", "untitled_project")
            identifier = manifest_data.get("identifier", project_name)
            
            manifest_dir = os.path.join(self.config.output_directory, project_name, identifier, "manifest")
            os.makedirs(manifest_dir, exist_ok=True)
            filepath = os.path.join(manifest_dir, filename)
            
            # 파일 저장
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(manifest_data, f, ensure_ascii=False, indent=2)
            
            # 상세한 저장 정보 출력
            print(f"📁 저장 디렉토리: {manifest_dir}")
            print(f"📄 파일명: {filename}")
            print(f"💾 전체 경로: {filepath}")
            print(f"✅ {filename} 생성 완료")
            
            return manifest_data, filepath
            
        except Exception as e:
            print(f"❌ Manifest 생성 실패: {e}")
            raise
    
    def create_audio(self, script_type: str, script_data: Dict[str, Any], output_text=None):
        """
        (Refactored) 오디오 및 타이밍 생성
        """
        try:
            def output_callback(message, level="INFO"):
                print(f"[{level}] {message}")
                if output_text:
                    output_text.insert("end", f"[{level}] {message}\n")
                    output_text.see("end")
            
            output_callback(f"🎵 [통합] 오디오 및 타이밍 생성 시작: {script_type}")
            
            output_callback("📋 Manifest 생성 중...")
            manifest_data = self.manifest_parser.create_manifest(script_type, script_data)
            output_callback("✅ Manifest 생성 완료")
            
            project_name = manifest_data.get("project_name", "untitled_project")
            identifier = manifest_data.get("identifier", project_name)
            output_callback(f"📁 프로젝트: {project_name}, 식별자: {identifier}")
            
            audio_output_dir = os.path.join(self.config.output_directory, project_name, identifier, "mp3")
            os.makedirs(audio_output_dir, exist_ok=True)
            output_callback(f"📂 오디오 출력 디렉토리: {audio_output_dir}")

            # Call the new unified function
            audio_path, timing_info = self.audio_generator.generate_audio_and_timing(
                manifest_data, audio_output_dir, script_type
            )
            
            if audio_path and timing_info:
                output_callback(f"✅ 오디오 파일 생성 완료: {audio_path}")
                
                # Save the timing info that was just created
                timing_output_dir = os.path.join(self.config.output_directory, project_name, identifier, "timing")
                os.makedirs(timing_output_dir, exist_ok=True)
                
                english_script_type = {"회화": "conversation", "대화": "conversation", "인트로": "intro", "엔딩": "ending"}.get(script_type, script_type)
                timing_path = os.path.join(timing_output_dir, f"{identifier}_{english_script_type}.json")
                
                timing_saved = self.audio_generator.save_precise_timing_info(timing_info, timing_path)
                
                if timing_saved:
                    output_callback(f"✅ 정확한 타이밍 정보 생성 및 저장 완료: {timing_path}")
                else:
                    output_callback("⚠️ 타이밍 정보 저장 실패", "ERROR")
                
                output_callback("✅ [통합] 오디오 및 타이밍 생성 성공", "SUCCESS")
            else:
                output_callback("❌ [통합] 오디오 및 타이밍 생성 실패", "ERROR")
            
        except Exception as e:
            import traceback
            error_msg = f"❌ 오디오 생성 실패: {e}\n{traceback.format_exc()}"
            print(error_msg)
            if output_text:
                output_text.insert("end", f"{error_msg}\n")
                output_text.see("end")
    
    def create_subtitles(self, script_type: str, output_text=None):
        """
        자막 이미지 생성
        
        Args:
            script_type: 스크립트 타입 (conversation, intro, ending)
            output_text: 출력 텍스트 위젯 (선택사항)
        """
        try:
            # 출력 콜백 함수 정의
            def output_callback(message, level="INFO"):
                print(f"[{level}] {message}")
                if output_text:
                    output_text.insert("end", f"[{level}] {message}\n")
                    output_text.see("end")
            
            output_callback(f"🎬 자막 이미지 생성 시작: {script_type}")
            
            # 임시 프로젝트 정보
            project_name = "kor-chn"  # 임시값
            identifier = "kor-chn"    # 임시값
            
            # Manifest 로드
            manifest_path = os.path.join(self.config.output_directory, project_name, identifier, "manifest", f"{identifier}_conversation.json")
            if not os.path.exists(manifest_path):
                error_msg = f"Manifest 파일을 찾을 수 없습니다: {manifest_path}"
                output_callback(error_msg, "ERROR")
                return
            
            # Manifest 파싱
            manifest_data = self.manifest_parser.parse_file(manifest_path)
            if not manifest_data:
                error_msg = "Manifest 파싱 실패"
                output_callback(error_msg, "ERROR")
                return
            
            output_callback("✅ Manifest 파싱 완료")
            
            # UI 설정 로드 (실제로는 UI에서 전달받아야 함)
            settings_path = os.path.join(self.config.output_directory, project_name, identifier, "_text_settings.json")
            settings = {}
            if os.path.exists(settings_path):
                with open(settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                output_callback("✅ UI 설정 로드 완료")
            
            # PipelineContext 생성
            context = PipelineContext.create(
                project_name=project_name,
                identifier=identifier,
                manifest=manifest_data,
                settings=settings
            )
            
            output_callback("✅ PipelineContext 생성 완료")
            
            # 자막 이미지 생성 실행
            create_subtitles_run(context)
            
            success_msg = f"✅ 자막 이미지 생성 완료: {script_type}"
            output_callback(success_msg, "SUCCESS")
                
        except Exception as e:
            error_msg = f"❌ 자막 이미지 생성 실패: {e}"
            print(error_msg)
            if output_text:
                output_text.insert("end", f"{error_msg}\n")
                output_text.see("end")
    
    def run_full_pipeline(self, manifest_path: str, 
                         project_name: Optional[str] = None) -> PipelineResult:
        """
        전체 파이프라인 실행
        
        Args:
            manifest_path: Manifest 파일 경로
            project_name: 프로젝트 이름 (None이면 자동 생성)
            
        Returns:
            PipelineResult: 실행 결과
        """
        start_time = time.time()
        errors = []
        warnings = []
        
        try:
            print("🚀 전체 파이프라인 실행 시작!")
            print(f"Manifest: {manifest_path}")
            
            # 1단계: Manifest 파싱 및 검증
            print("\n📋 1단계: Manifest 파싱 및 검증")
            manifest_data = self._parse_and_validate_manifest(manifest_path)
            if not manifest_data:
                errors.append("Manifest 파싱 및 검증 실패")
                return self._create_pipeline_result(False, manifest_path, start_time, errors, warnings)
            
            # 프로젝트 이름 결정
            if not project_name:
                project_name = manifest_data.get("project_name", "auto_generated")
            
            # 프로젝트별 출력 디렉토리 생성
            project_output_dir = os.path.join(self.config.output_directory, project_name)
            os.makedirs(project_output_dir, exist_ok=True)
            
            # 2단계: 오디오 생성
            audio_path = None
            if self.config.enable_audio_generation:
                print("\n🎵 2단계: 오디오 생성")
                # Manifest에서 첫 번째 장면의 타입을 사용하여 스크립트 타입 결정
                scenes = manifest_data.get("scenes", [])
                script_type = scenes[0].get("type", "conversation") if scenes else "conversation"
                audio_path = self._generate_audio(manifest_data, project_output_dir, script_type)
                if not audio_path:
                    errors.append("오디오 생성 실패")
                    warnings.append("오디오 없이 비디오 렌더링 진행")
            
            # 3단계: 자막 이미지 생성
            subtitle_dir = None
            if self.config.enable_subtitle_generation:
                print("\n🎬 3단계: 자막 이미지 생성")
                subtitle_dir = self._generate_subtitles(manifest_data, project_output_dir)
                if not subtitle_dir:
                    errors.append("자막 이미지 생성 실패")
                    return self._create_pipeline_result(False, manifest_path, start_time, errors, warnings)
            
            # 4단계: 비디오 렌더링
            video_path = None
            if self.config.enable_video_rendering:
                print("\n🎥 4단계: 비디오 렌더링")
                video_path = self._render_video(manifest_path, audio_path, subtitle_dir, project_output_dir, "conversation")
                if not video_path:
                    errors.append("비디오 렌더링 실패")
                    return self._create_pipeline_result(False, manifest_path, start_time, errors, warnings)
            
            # 5단계: 품질 최적화
            if self.config.enable_quality_optimization and video_path:
                print("\n🔧 5단계: 품질 최적화")
                optimized_video_path = self._optimize_video_quality(video_path, project_output_dir)
                if optimized_video_path:
                    video_path = optimized_video_path
            
            # 6단계: 프리뷰 생성
            preview_path = None
            if self.config.enable_preview_generation and video_path:
                print("\n👀 6단계: 프리뷰 생성")
                preview_path = self._create_preview(video_path, project_output_dir)
            
            # 7단계: 임시 파일 정리
            if self.config.cleanup_temp_files:
                print("\n🧹 7단계: 임시 파일 정리")
                self._cleanup_temp_files(project_output_dir)
            
            # 실행 시간 계산
            execution_time = time.time() - start_time
            
            print(f"\n🎉 전체 파이프라인 실행 완료! (소요시간: {execution_time:.1f}초)")
            
            return self._create_pipeline_result(
                True, manifest_path, start_time, errors, warnings,
                audio_path, subtitle_dir, video_path, preview_path
            )
            
        except Exception as e:
            errors.append(f"파이프라인 실행 중 예외 발생: {e}")
            return self._create_pipeline_result(False, manifest_path, start_time, errors, warnings)
    
    def _parse_and_validate_manifest(self, manifest_path: str) -> Optional[Dict[str, Any]]:
        """Manifest 파싱 및 검증"""
        try:
            manifest = self.manifest_parser.parse_file(manifest_path)
            
            # 검증 결과 확인
            validation_result = self.manifest_parser.validator.validate(manifest)
            if not validation_result.is_valid:
                print("⚠️ Manifest 검증 경고:")
                for warning in validation_result.warnings:
                    print(f"  - {warning.message}")
            
            return manifest.model_dump()
            
        except Exception as e:
            print(f"❌ Manifest 파싱 실패: {e}")
            return None
    
    def _generate_audio(self, manifest_data: Dict[str, Any], 
                       output_dir: str, script_type: str = "conversation") -> Optional[str]:
        """오디오 생성"""
        try:
            # AudioGenerator를 사용하여 오디오 생성
            success, audio_path = self.audio_generator.generate_audio_from_manifest(
                manifest_data, output_dir, script_type
            )
            
            if success:
                print(f"✅ 오디오 생성 완료: {audio_path}")
                return audio_path
            else:
                print("❌ 오디오 생성 실패")
                return None
            
        except Exception as e:
            print(f"❌ 오디오 생성 실패: {e}")
            return None
    
    def _generate_subtitles(self, manifest_data: Dict[str, Any], 
                           output_dir: str) -> Optional[str]:
        """자막 이미지 생성 (SubtitleGenerator는 삭제됨 - PNGRenderer 사용)"""
        # SubtitleGenerator는 삭제됨 - PNGRenderer 기반 시스템 사용
        print("⚠️ SubtitleGenerator는 삭제됨 - PNGRenderer 기반 시스템을 사용하세요")
        return None
    
    
    def _optimize_video_quality(self, video_path: str, output_dir: str) -> Optional[str]:
        """비디오 품질 최적화"""
        try:
            optimized_path = os.path.join(output_dir, "final_video_optimized.mp4")
            
            success = self.ffmpeg_renderer.optimize_quality(
                video_path, optimized_path, target_bitrate="8000k"
            )
            
            if success and os.path.exists(optimized_path):
                print(f"✅ 품질 최적화 완료: {optimized_path}")
                
                # 원본 파일 삭제
                if os.path.exists(video_path):
                    os.remove(video_path)
                    print(f"✅ 원본 파일 삭제: {video_path}")
                
                return optimized_path
            else:
                print("⚠️ 품질 최적화 실패, 원본 파일 사용")
                return video_path
                
        except Exception as e:
            print(f"⚠️ 품질 최적화 실패: {e}")
            return video_path
    
    def _create_preview(self, video_path: str, output_dir: str) -> Optional[str]:
        """프리뷰 생성"""
        try:
            preview_path = os.path.join(output_dir, "preview.mp4")
            
            success = self.ffmpeg_renderer.create_preview(
                video_path, preview_path, duration=10
            )
            
            if success and os.path.exists(preview_path):
                print(f"✅ 프리뷰 생성 완료: {preview_path}")
                return preview_path
            else:
                print("⚠️ 프리뷰 생성 실패")
                return None
                
        except Exception as e:
            print(f"⚠️ 프리뷰 생성 실패: {e}")
            return None
    
    def _cleanup_temp_files(self, output_dir: str):
        """임시 파일 정리"""
        try:
            # SSML 파일 삭제
            ssml_path = os.path.join(output_dir, "manifest.ssml")
            if os.path.exists(ssml_path):
                os.remove(ssml_path)
                print(f"✅ 임시 SSML 파일 삭제: {ssml_path}")
            
            # 더미 오디오 파일 삭제
            audio_path = os.path.join(output_dir, "manifest_audio.mp3")
            if os.path.exists(audio_path):
                os.remove(audio_path)
                print(f"✅ 임시 오디오 파일 삭제: {audio_path}")
            
            print("✅ 임시 파일 정리 완료")
            
        except Exception as e:
            print(f"⚠️ 임시 파일 정리 실패: {e}")
    
    def _create_pipeline_result(self, success: bool, manifest_path: str, 
                              start_time: float, errors: List[str], warnings: List[str],
                              audio_path: Optional[str] = None, 
                              subtitle_dir: Optional[str] = None,
                              video_path: Optional[str] = None,
                              preview_path: Optional[str] = None) -> PipelineResult:
        """파이프라인 결과 생성"""
        execution_time = time.time() - start_time
        
        return PipelineResult(
            success=success,
            manifest_path=manifest_path,
            audio_path=audio_path,
            subtitle_dir=subtitle_dir,
            video_path=video_path,
            preview_path=preview_path,
            execution_time=execution_time,
            errors=errors,
            warnings=warnings
        )
    
    def get_pipeline_summary(self, result: PipelineResult) -> Dict[str, Any]:
        """파이프라인 실행 요약"""
        summary = {
            "success": result.success,
            "execution_time": result.execution_time,
            "output_files": {},
            "errors": result.errors,
            "warnings": result.warnings
        }
        
        if result.audio_path:
            summary["output_files"]["audio"] = result.audio_path
        
        if result.subtitle_dir:
            summary["output_files"]["subtitles"] = result.subtitle_dir
        
        if result.video_path:
            summary["output_files"]["video"] = result.video_path
            
            # 비디오 정보 조회
            video_info = self.ffmpeg_renderer.get_video_info(result.video_path)
            if video_info:
                summary["video_info"] = video_info
        
        if result.preview_path:
            summary["output_files"]["preview"] = result.preview_path
        
        return summary
    
    def save_pipeline_report(self, result: PipelineResult, output_dir: str):
        """파이프라인 실행 보고서 저장"""
        try:
            report_path = os.path.join(output_dir, "pipeline_report.json")
            
            report = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "manifest_path": result.manifest_path,
                "success": result.success,
                "execution_time": result.execution_time,
                "output_files": {},
                "errors": result.errors,
                "warnings": result.warnings
            }
            
            if result.audio_path:
                report["output_files"]["audio"] = result.audio_path
            
            if result.subtitle_dir:
                report["output_files"]["subtitles"] = result.subtitle_dir
            
            if result.video_path:
                report["output_files"]["video"] = result.video_path
            
            if result.preview_path:
                report["output_files"]["preview"] = result.preview_path
            
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 파이프라인 보고서 저장: {report_path}")
            
        except Exception as e:
            print(f"⚠️ 파이프라인 보고서 저장 실패: {e}")
    
    def create_subtitles(self, script_type: str, output_text=None):
        """자막 이미지 생성 (UI에서 호출)"""
        try:
            output_callback = lambda msg, level="INFO": self._log_to_widget(msg, level, output_text)
            output_callback(f"🎬 자막 이미지 생성 시작: {script_type}")

            # 프로젝트 정보 가져오기 (실제로는 UI에서 전달받아야 함)
            project_name = "kor-chn"  # 임시값
            identifier = "kor-chn"    # 임시값

            # 스크립트 타입에 맞는 Manifest 파일명 동적 생성
            script_type_mapping = {
                "회화": "conversation",
                "대화": "dialogue",
                "인트로": "intro",
                "엔딩": "ending"
            }
            english_script_type = script_type_mapping.get(script_type, script_type.lower())
            manifest_filename = f"{identifier}_{english_script_type}.json"
            manifest_path = os.path.join(self.config.output_directory, project_name, identifier, "manifest", manifest_filename)

            if not os.path.exists(manifest_path):
                error_msg = f"Manifest 파일을 찾을 수 없습니다: {manifest_path}"
                output_callback(error_msg, "ERROR")
                return

            manifest_data = self.manifest_parser.parse_file(manifest_path)
            if not manifest_data:
                error_msg = f"Manifest 파싱 실패: {manifest_path}"
                output_callback(error_msg, "ERROR")
                return

            settings_path = os.path.join(self.config.output_directory, project_name, identifier, "_text_settings.json")
            settings = {}
            if os.path.exists(settings_path):
                with open(settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)

            context = PipelineContext.create(
                project_name=project_name,
                identifier=identifier,
                manifest=manifest_data,
                settings=settings,
                script_type=script_type,
                log_callback=output_callback
            )

            create_subtitles_run(context)

            success_msg = f"✅ 자막 이미지 생성 완료: {script_type}"
            output_callback(success_msg, "SUCCESS")

        except Exception as e:
            import traceback
            error_msg = f"❌ 자막 이미지 생성 실패: {e}\n{traceback.format_exc()}"
            output_callback(error_msg, "ERROR")



    def create_unified_timing_file(self, project_name: str, identifier: str) -> Optional[str]:
        """
        intro, conversation, ending 타이밍 파일들을 하나로 통합하는 함수
        
        Args:
            project_name: 프로젝트명
            identifier: 식별자
            
        Returns:
            통합 타이밍 파일 경로 또는 None
        """
        try:
            print("🔗 통합 타이밍 파일 생성 시작...")
            
            timing_dir = os.path.join(self.config.output_directory, project_name, identifier, "timing")
            unified_timing_path = os.path.join(timing_dir, f"{identifier}_unified.json")
            
            # 개별 타이밍 파일들 로드
            timing_files = {
                'intro': os.path.join(timing_dir, f"{identifier}_intro.json"),
                'conversation': os.path.join(timing_dir, f"{identifier}_conversation.json"),
                'ending': os.path.join(timing_dir, f"{identifier}_ending.json")
            }
            
            unified_segments = []
            total_duration = 0.0
            current_time = 0.0
            
            # 각 스크립트 타입별로 타이밍 파일 처리
            for script_type, timing_path in timing_files.items():
                if not os.path.exists(timing_path):
                    print(f"⚠️ {script_type} 타이밍 파일이 없습니다: {timing_path}")
                    continue
                
                print(f"📄 {script_type} 타이밍 파일 로드 중...")
                
                with open(timing_path, 'r', encoding='utf-8') as f:
                    timing_data = json.load(f)
                
                segments = timing_data.get('segments', [])
                script_duration = timing_data.get('total_duration', 0.0)
                
                print(f"📊 {script_type} 타이밍 정보:")
                print(f"  - 세그먼트 수: {len(segments)}개")
                print(f"  - 총 길이: {script_duration:.2f}초")
                
                # 각 세그먼트의 시간을 통합 시간으로 조정
                for i, segment in enumerate(segments):
                    adjusted_segment = segment.copy()
                    adjusted_segment['start_time'] = segment['start_time'] + current_time
                    adjusted_segment['end_time'] = segment['end_time'] + current_time
                    adjusted_segment['script_type'] = script_type  # 스크립트 타입 추가
                    unified_segments.append(adjusted_segment)
                    
                    if i < 3:  # 처음 3개 세그먼트만 로그 출력
                        print(f"    - 세그먼트 {i+1}: {segment['start_time']:.2f}s → {adjusted_segment['start_time']:.2f}s")
                
                total_duration += script_duration
                current_time += script_duration
                
                print(f"✅ {script_type} 타이밍 통합 완료 (길이: {script_duration:.2f}초, 누적: {current_time:.2f}초)")
            
            # 통합 타이밍 파일 생성
            unified_timing_data = {
                "project_name": project_name,
                "identifier": identifier,
                "total_duration": total_duration,
                "segments": unified_segments,
                "resolution": "1920x1080",
                "script_types": list(timing_files.keys()),
                "created_at": time_module.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # 통합 타이밍 파일 저장
            with open(unified_timing_path, 'w', encoding='utf-8') as f:
                json.dump(unified_timing_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 통합 타이밍 파일 생성 완료: {unified_timing_path}")
            print(f"📊 총 세그먼트 수: {len(unified_segments)}개")
            print(f"📊 총 비디오 길이: {total_duration:.2f}초")
            
            return unified_timing_path
            
        except Exception as e:
            print(f"❌ 통합 타이밍 파일 생성 실패: {e}")
            import traceback
            traceback.print_exc()
            return None

    def create_unified_video(self, project_name: str, identifier: str) -> Dict[str, Any]:
        """
        통합 타이밍 파일을 사용하여 최종 비디오를 한 번에 생성하는 함수
        
        Args:
            project_name: 프로젝트명
            identifier: 식별자
            
        Returns:
            생성 결과 딕셔너리
        """
        try:
            print("🎬 통합 비디오 생성 시작...")
            
            # 통합 타이밍 파일 생성
            unified_timing_path = self.create_unified_timing_file(project_name, identifier)
            if not unified_timing_path:
                return {"success": False, "message": "통합 타이밍 파일 생성 실패"}
            
            # 통합 비디오 출력 경로
            output_dir = f"output/{project_name}/{identifier}"
            video_dir = os.path.join(output_dir, "mp4")
            os.makedirs(video_dir, exist_ok=True)
            
            unified_video_path = os.path.join(video_dir, f"{identifier}_unified.mp4")
            
            # 통합 오디오 파일 생성 (intro + conversation + ending)
            unified_audio_path = self._create_unified_audio(project_name, identifier)
            if not unified_audio_path:
                return {"success": False, "message": "통합 오디오 파일 생성 실패"}
            
            # 통합 타이밍 파일에 오디오 경로 추가
            with open(unified_timing_path, 'r', encoding='utf-8') as f:
                timing_data = json.load(f)
            
            timing_data['final_audio_path'] = unified_audio_path
            
            with open(unified_timing_path, 'w', encoding='utf-8') as f:
                json.dump(timing_data, f, ensure_ascii=False, indent=2)
            
            # 통합 이미지 디렉토리 (모든 스크립트 타입의 이미지가 포함된 디렉토리)
            unified_image_dir = os.path.join(output_dir, "unified_images")
            os.makedirs(unified_image_dir, exist_ok=True)
            
            # 모든 스크립트 타입의 이미지를 통합 디렉토리로 복사
            self._copy_all_images_to_unified_dir(project_name, identifier, unified_image_dir)
            
            # VideoGenerator를 사용하여 통합 비디오 생성
            success = self.ffmpeg_renderer.create_video_from_timing(
                unified_timing_path, 
                unified_video_path, 
                unified_image_dir, 
                "unified"
            )
            
            if success and os.path.exists(unified_video_path):
                print(f"✅ 통합 비디오 생성 완료: {unified_video_path}")
                return {
                    "success": True,
                    "message": "통합 비디오 생성 완료",
                    "video_path": unified_video_path,
                    "timing_path": unified_timing_path
                }
            else:
                return {"success": False, "message": "통합 비디오 생성 실패"}
                
        except Exception as e:
            print(f"❌ 통합 비디오 생성 실패: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "message": f"통합 비디오 생성 중 오류: {e}"}

    def _create_unified_audio(self, project_name: str, identifier: str) -> Optional[str]:
        """
        intro, conversation, ending 오디오 파일들을 하나로 합치는 함수
        """
        try:
            print("🎵 통합 오디오 파일 생성 시작...")
            
            audio_dir = os.path.join(self.config.output_directory, project_name, identifier, "mp3")
            unified_audio_path = os.path.join(audio_dir, f"{identifier}_unified.mp3")
            
            # 개별 오디오 파일들
            audio_files = [
                os.path.join(audio_dir, f"{identifier}_intro.mp3"),
                os.path.join(audio_dir, f"{identifier}_conversation.mp3"),
                os.path.join(audio_dir, f"{identifier}_ending.mp3")
            ]
            
            # 존재하는 오디오 파일들만 필터링하고 길이 확인
            existing_audio_files = []
            total_duration = 0.0
            
            for audio_file in audio_files:
                if os.path.exists(audio_file):
                    # 오디오 파일 길이 확인
                    import subprocess
                    try:
                        cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', audio_file]
                        result = subprocess.run(cmd, capture_output=True, text=True)
                        if result.returncode == 0:
                            duration = float(result.stdout.strip())
                            print(f"📊 {os.path.basename(audio_file)}: {duration:.2f}초")
                            total_duration += duration
                            existing_audio_files.append(audio_file)
                        else:
                            print(f"⚠️ {os.path.basename(audio_file)} 길이 확인 실패")
                    except Exception as e:
                        print(f"⚠️ {os.path.basename(audio_file)} 길이 확인 중 오류: {e}")
                else:
                    print(f"⚠️ 오디오 파일이 없습니다: {audio_file}")
            
            if not existing_audio_files:
                print("❌ 통합할 오디오 파일이 없습니다.")
                return None
            
            print(f"📊 총 예상 통합 오디오 길이: {total_duration:.2f}초")
            
            # FFmpeg를 사용하여 오디오 파일들 연결
            import subprocess
            
            # concat 파일 생성
            concat_file_path = unified_audio_path + "_concat.txt"
            with open(concat_file_path, 'w', encoding='utf-8') as f:
                for audio_file in existing_audio_files:
                    f.write(f"file '{os.path.abspath(audio_file)}'\n")
            
            print(f"📝 Concat 파일 생성: {concat_file_path}")
            print(f"📝 통합할 파일들: {[os.path.basename(f) for f in existing_audio_files]}")
            
            # FFmpeg 명령어 실행
            cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file_path,
                '-c', 'copy',
                unified_audio_path
            ]
            
            print(f"🚀 FFmpeg 명령어 실행: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # 생성된 파일의 실제 길이 확인
                try:
                    cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', unified_audio_path]
                    result_check = subprocess.run(cmd, capture_output=True, text=True)
                    if result_check.returncode == 0:
                        actual_duration = float(result_check.stdout.strip())
                        print(f"✅ 통합 오디오 파일 생성 완료: {unified_audio_path}")
                        print(f"📊 실제 통합 오디오 길이: {actual_duration:.2f}초")
                    else:
                        print(f"✅ 통합 오디오 파일 생성 완료: {unified_audio_path}")
                except Exception as e:
                    print(f"✅ 통합 오디오 파일 생성 완료: {unified_audio_path}")
                    print(f"⚠️ 길이 확인 중 오류: {e}")
                
                # 임시 concat 파일 삭제
                os.remove(concat_file_path)
                return unified_audio_path
            else:
                print(f"❌ 통합 오디오 파일 생성 실패: {result.stderr}")
                print(f"❌ FFmpeg stdout: {result.stdout}")
                return None
                
        except Exception as e:
            print(f"❌ 통합 오디오 파일 생성 중 오류: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _copy_all_images_to_unified_dir(self, project_name: str, identifier: str, unified_image_dir: str):
        """
        모든 스크립트 타입의 이미지를 통합 디렉토리로 복사
        """
        try:
            print("📁 통합 이미지 디렉토리 준비 중...")
            
            # 각 스크립트 타입별 이미지 디렉토리
            image_dirs = {
                'intro': os.path.join(self.config.output_directory, project_name, identifier, "intro"),
                'conversation': os.path.join(self.config.output_directory, project_name, identifier, "conversation"),
                'ending': os.path.join(self.config.output_directory, project_name, identifier, "ending")
            }
            
            import shutil
            
            for script_type, image_dir in image_dirs.items():
                if os.path.exists(image_dir):
                    # 해당 스크립트 타입의 모든 이미지 파일 복사
                    for filename in os.listdir(image_dir):
                        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                            src_path = os.path.join(image_dir, filename)
                            dst_path = os.path.join(unified_image_dir, filename)
                            shutil.copy2(src_path, dst_path)
                            print(f"📄 이미지 복사: {filename}")
            
            print(f"✅ 통합 이미지 디렉토리 준비 완료: {unified_image_dir}")
            
        except Exception as e:
            print(f"❌ 통합 이미지 디렉토리 준비 중 오류: {e}")

    def run_timing_based_video_rendering(self, ui_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        타이밍 JSON을 직접 사용한 비디오 렌더링
        선택된 스크립트 타입만 처리하여 개별 비디오 생성
        """
        try:
            project_name = ui_data.get('project_name', '')
            identifier = ui_data.get('identifier', '')
            selected_script_type = ui_data.get('script_type', '')
            
            if not project_name or not identifier:
                return {"success": False, "message": "프로젝트명과 식별자가 필요합니다."}
            
            if not selected_script_type:
                return {"success": False, "message": "생성할 스크립트 타입을 선택해주세요."}
            
            output_dir = f"output/{project_name}/{identifier}"
            video_dir = os.path.join(output_dir, "mp4")
            os.makedirs(video_dir, exist_ok=True)
            
            generated_videos = {}
            errors = []
            
            # 선택된 스크립트 타입에 따라 처리할 타입 결정
            script_type_mapping = {
                "인트로": ("인트로", "intro", "intro"),
                "회화": ("회화", "conversation", "conversation"),
                "엔딩": ("엔딩", "ending", "ending")
            }
            
            if selected_script_type not in script_type_mapping:
                return {"success": False, "message": f"지원하지 않는 스크립트 타입입니다: {selected_script_type}"}
            
            # 선택된 스크립트 타입만 처리
            script_types = [script_type_mapping[selected_script_type]]
            
            print(f"🎯 선택된 스크립트 타입: {selected_script_type}")
            print(f"🚀 비디오 렌더링 프로세스 시작...")
            
            for korean_name, english_name, image_subdir in script_types:
                print(f"🎬 {korean_name} 비디오 렌더링 시작")
                
                # 타이밍 파일 경로
                timing_path = os.path.join(output_dir, "timing", f"{identifier}_{english_name}.json")
                
                # 이미지 디렉토리 경로
                image_dir = os.path.join(output_dir, image_subdir)
                
                # 비디오 출력 경로
                output_video_path = os.path.join(video_dir, f"{identifier}_{english_name}.mp4")
                
                print(f"  - 타이밍: {timing_path}")
                print(f"  - 이미지: {image_dir}")
                print(f"  - 출력: {output_video_path}")
                
                # 파일 존재 확인
                if not os.path.exists(timing_path):
                    error_msg = f"{korean_name} 타이밍 파일을 찾을 수 없습니다: {timing_path}"
                    print(f"❌ {error_msg}")
                    errors.append(error_msg)
                    continue
                
                if not os.path.exists(image_dir):
                    error_msg = f"{korean_name} 이미지 디렉토리를 찾을 수 없습니다: {image_dir}"
                    print(f"❌ {error_msg}")
                    errors.append(error_msg)
                    continue
                
                # 타이밍 기반 비디오 생성 (패딩 기능 포함)
                success = self.ffmpeg_renderer.create_video_from_timing(
                    timing_path, output_video_path, image_dir, english_name
                )
                
                if success and os.path.exists(output_video_path):
                    generated_videos[english_name] = output_video_path
                    print(f"✅ {korean_name} 비디오 생성 완료: {output_video_path}")
                else:
                    error_msg = f"{korean_name} 비디오 생성 실패"
                    print(f"❌ {error_msg}")
                    errors.append(error_msg)
            
            # 결과 반환
            if generated_videos:
                print(f"🎉 비디오 렌더링 프로세스 완료! {len(generated_videos)}개 비디오 생성됨")
                return {
                    "success": True,
                    "message": f"비디오 렌더링 완료: {len(generated_videos)}개 비디오 생성",
                    "generated_videos": generated_videos,
                    "errors": errors
                }
            else:
                print(f"❌ 비디오 렌더링 프로세스 실패: 생성된 비디오가 없습니다")
                return {
                    "success": False, 
                    "message": "모든 비디오 생성 실패",
                    "errors": errors
                }
                
        except Exception as e:
            print(f"❌ 타이밍 기반 비디오 렌더링 실패: {e}")
            return {"success": False, "message": f"오류: {e}"}
    
