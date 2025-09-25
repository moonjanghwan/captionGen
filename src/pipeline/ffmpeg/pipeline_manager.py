"""
통합 파이프라인 매니저

Manifest부터 최종 MP4까지 전체 파이프라인을 관리하고 조율합니다.
"""

import os
import json
import time
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from src import config
from ..manifest import ManifestParser
from ..audio import AudioGenerator
from ..steps.create_subtitles import run as create_subtitles_run
from ..core.context import PipelineContext
from .renderer import FFmpegRenderer

@dataclass
class PipelineConfig:
    output_directory: str = "output"
    enable_audio_generation: bool = True
    enable_subtitle_generation: bool = True
    enable_video_rendering: bool = True

class PipelineManager:
    def __init__(self, pipeline_config: Optional[PipelineConfig] = None, root=None, log_callback=None):
        self.root = root
        self.log_callback = log_callback if log_callback else print
        self.config = pipeline_config if isinstance(pipeline_config, PipelineConfig) else PipelineConfig()
        self.manifest_parser = ManifestParser()
        self.audio_generator = None
        self.ffmpeg_renderer = FFmpegRenderer()
    
    def _create_audio_generator(self, project_name: str, identifier: str):
        """오디오 생성기를 동적으로 생성하고, 항상 UI와 config.json의 현재 설정을 사용합니다."""
        # 1. Load base audio settings from config.json
        try:
            config_path = os.path.join(config.BASE_DIR, 'config.json')
            with open(config_path, 'r', encoding='utf-8') as f:
                main_config = json.load(f)
            audio_settings = main_config.get("audio_settings", {})
        except (FileNotFoundError, json.JSONDecodeError):
            audio_settings = {}

        # 2. Create config structure and add settings from config.json
        audio_generator_config = {
            "output_directory": config.OUTPUT_PATH,
            "tts": {},
            "audio_settings": audio_settings
        }

        # 3. Always get the latest speaker settings directly from the UI
        if self.root and hasattr(self.root, 'pages') and 'speaker' in self.root.pages:
            speaker_tab = self.root.pages['speaker']
            
            native_display_name = speaker_tab.native_speaker_dropdown.get()
            native_voice_name = next((vd["name"] for vd in getattr(speaker_tab, 'native_voice_details', []) if vd["display_name"] == native_display_name), None)
            audio_generator_config["tts"]["native_voice"] = native_voice_name

            audio_generator_config["tts"]["native_lang_code"] = speaker_tab.native_lang_code
            audio_generator_config["tts"]["learning_lang_code"] = speaker_tab.learning_lang_code

            learner_display_names = [w["dropdown"].get() for w in speaker_tab.learner_speaker_widgets]
            learner_voice_names = []
            for ld_name in learner_display_names:
                found_name = next((vd["name"] for vd in getattr(speaker_tab, 'learner_voice_details', []) if vd["display_name"] == ld_name), None)
                learner_voice_names.append(found_name)

            for i, name in enumerate(learner_voice_names, 1):
                audio_generator_config["tts"][f"learner_{i}_voice"] = name
            
            self.log_callback("✅ UI의 '화자 선택' 탭에서 현재 설정을 가져왔습니다.")
        else:
            self.log_callback("⚠️ '화자 선택' 탭을 찾을 수 없어 화자 정보를 설정할 수 없습니다.", "WARNING")

        # 4. Initialize the AudioGenerator with the combined config
        self.audio_generator = AudioGenerator(audio_generator_config, config.GOOGLE_CREDENTIALS_PATH)

    def _display_api_stats(self, api_stats: dict):
        """API 호출 통계를 UI에 표시합니다."""
        try:
            total_calls = api_stats.get('total_calls', 0)
            successful_calls = api_stats.get('successful_calls', 0)
            failed_calls = api_stats.get('failed_calls', 0)
            retry_attempts = api_stats.get('retry_attempts', 0)
            ssml_fallback_calls = api_stats.get('ssml_fallback_calls', 0)
            text_mode_calls = api_stats.get('text_mode_calls', 0)
            
            # 통계 메시지 생성
            stats_message = f"""
📊 API 호출 통계:
  • 총 API 호출: {total_calls}회
  • 성공: {successful_calls}회
  • 실패: {failed_calls}회
  • 재시도: {retry_attempts}회
  • SSML 폴백: {ssml_fallback_calls}회
  • 텍스트 모드: {text_mode_calls}회
"""
            
            if failed_calls > 0:
                stats_message += f"\n⚠️ {failed_calls}개의 오디오 세그먼트가 실패했습니다."
            
            if ssml_fallback_calls > 0:
                stats_message += f"\n🔄 {ssml_fallback_calls}개의 화자가 SSML을 지원하지 않아 텍스트 모드로 전환되었습니다."
            
            # UI에 로그 메시지로 표시
            self.root.pages['data'].log_message(stats_message)
            
        except Exception as e:
            print(f"API 통계 표시 중 오류: {e}")

    def run_manifest_creation(self, ui_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            project_name = ui_data.get('project_name', '')
            identifier = ui_data.get('identifier', '')
            script_type = ui_data.get('script_type', 'conversation')
            
            if not project_name or not identifier:
                return {'success': False, 'errors': ['프로젝트명과 식별자가 필요합니다.']}
            
            output_dir = os.path.join("output", project_name, identifier)
            os.makedirs(output_dir, exist_ok=True)
            
            # 'all' 타입일 경우 마스터 매니페스트를 생성하도록 _create_manifest 호출
            manifest_path, _ = self._create_manifest(project_name, identifier, script_type, output_dir, ui_data)
            if not manifest_path:
                return {'success': False, 'errors': ['매니페스트 생성 실패']}
            
            return {'success': True, 'generated_files': {'manifest': manifest_path}, 'errors': []}
            
        except Exception as e:
            return {'success': False, 'errors': [f'매니페스트 생성 중 오류: {str(e)}']}
    def run_audio_generation(self, ui_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            project_name = ui_data.get('project_name', '')
            identifier = ui_data.get('identifier', '')
            script_type = ui_data.get('script_type', 'conversation')
            
            if not project_name or not identifier:
                self.log_callback("❌ 오디오 생성 실패: 프로젝트명과 식별자가 필요합니다.")
                return {'success': False, 'errors': ['프로젝트명과 식별자가 필요합니다.']}

            # 1. Manifest 데이터를 파일에서 읽는 대신 메모리에서 생성
            output_dir = os.path.join("output", project_name, identifier)
            _, manifest_data = self._create_manifest(project_name, identifier, script_type, output_dir, ui_data)
            if not manifest_data:
                self.log_callback("❌ 오디오 생성 실패: Manifest 데이터 생성에 실패했습니다.")
                return {'success': False, 'errors': ['Manifest 데이터 생성 실패']}

            # 2. 오디오 생성기 준비
            self._create_audio_generator(project_name, identifier)
            audio_output_dir = os.path.join(output_dir, "mp3")
            os.makedirs(audio_output_dir, exist_ok=True)

            # 3. 스크립트 타입에 따라 적절한 오디오 생성 함수 호출
            scenes = manifest_data.get('scenes', [])
            scenes_for_type = [s for s in scenes if s.get('type') == script_type]
            manifest_data_for_type = manifest_data.copy()
            manifest_data_for_type['scenes'] = scenes_for_type

            if not scenes_for_type:
                self.log_callback(f"⚠️ {script_type} 타입의 장면이 없어 오디오 생성을 건너뜁니다.")
                return {'success': True} # It's not an error, just nothing to do

            if script_type == "conversation":
                audio_result = self.audio_generator.generate_conversation_audio(manifest_data_for_type)
            elif script_type in ["intro", "ending", "title", "keywords"]:
                audio_result = self.audio_generator.generate_intro_ending_audio(manifest_data_for_type, script_type)
            else:
                self.log_callback(f"❌ 오디오 생성 실패: 지원하지 않는 스크립트 타입: {script_type}")
                return {'success': False, 'errors': [f'지원하지 않는 스크립트 타입: {script_type}']}

            if not audio_result.get('success'):
                if self.root and hasattr(self.root, 'pages') and 'data' in self.root.pages:
                    self.root.pages['data'].log_message(f"❌ 오디오 생성 실패: {audio_result.get('error', '알 수 없는 오류')}")
                return {'success': False, 'errors': [f'오디오 생성 실패: {audio_result.get("error", "알 수 없는 오류")}']}

            audio_path = audio_result.get('audio_file')
            timing_info = audio_result.get('timing_info')
            api_stats = audio_result.get('api_stats', {})
            
            # 디버깅: API 통계 확인
            print(f"🔍 디버깅 - API 통계: {api_stats}")
            print(f"🔍 디버깅 - root 존재: {self.root is not None}")
            if self.root:
                print(f"🔍 디버깅 - pages 존재: {hasattr(self.root, 'pages')}")
                if hasattr(self.root, 'pages'):
                    print(f"🔍 디버깅 - data 페이지 존재: {'data' in self.root.pages}")
            
            # API 통계를 UI에 표시
            if api_stats and self.root and hasattr(self.root, 'pages') and 'data' in self.root.pages:
                print("🔍 디버깅 - API 통계 표시 시도")
                self._display_api_stats(api_stats)
            else:
                print("🔍 디버깅 - API 통계 표시 조건 미충족")
            
            if audio_path: # timing_info는 현재 빈 리스트이므로 조건에서 제외
                timing_output_dir = os.path.join(output_dir, "timing")
                os.makedirs(timing_output_dir, exist_ok=True)
                timing_path = os.path.join(timing_output_dir, f"{identifier}_{script_type}.json")
                
                # timing_info가 비어있더라도 파일은 생성할 수 있도록 로직 변경
                with open(timing_path, 'w', encoding='utf-8') as f:
                    json.dump(timing_info, f, ensure_ascii=False, indent=2)

                if self.root and hasattr(self.root, 'pages') and 'data' in self.root.pages:
                    self.root.pages['data'].log_message(f"✅ {script_type.capitalize()} 오디오 생성 완료: {audio_path}")
                return {'success': True, 'generated_files': {'audio': audio_path, 'timing': timing_path}}
            else:
                if self.root and hasattr(self.root, 'pages') and 'data' in self.root.pages:
                    self.root.pages['data'].log_message("❌ 오디오 생성 실패: 오디오 파일 경로를 찾을 수 없습니다.")
                return {'success': False, 'errors': ['오디오 생성 실패']}
            
        except Exception as e:
            if self.root and hasattr(self.root, 'pages') and 'data' in self.root.pages:
                self.root.pages['data'].log_message(f"❌ 오디오 생성 중 오류: {str(e)}")
            return {'success': False, 'errors': [f'오디오 생성 중 오류: {str(e)}']}

    def run_subtitle_creation(self, ui_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            project_name = ui_data.get('project_name', '')
            identifier = ui_data.get('identifier', '')
            script_type = ui_data.get('script_type', 'conversation')
            
            if not project_name or not identifier:
                return {'success': False, 'errors': ['프로젝트명과 식별자가 필요합니다.']}

            # 1. Manifest 데이터를 파일에서 읽는 대신 메모리에서 생성
            output_dir = os.path.join("output", project_name, identifier)
            _, manifest_data = self._create_manifest(project_name, identifier, script_type, output_dir, ui_data)
            if not manifest_data:
                self.log_callback("❌ 자막 이미지 생성 실패: Manifest 데이터 생성에 실패했습니다.")
                return {'success': False, 'errors': ['Manifest 데이터 생성 실패']}
            
            # 2. 컨텍스트 생성 및 실행
            from src.pipeline.core.context import PipelineContext, PipelinePaths, PipelineSettings
            
            script_settings = ui_data.get('script_settings', {})
            context_settings = PipelineSettings(script_settings=script_settings)

            context_paths = PipelinePaths(
                base_dir="output",
                project_name=project_name,
                identifier=identifier
            )

            context = PipelineContext(
                project_name=project_name,
                identifier=identifier,
                manifest=self.manifest_parser.parse_dict(manifest_data),
                settings=context_settings,
                paths=context_paths,
                script_type=script_type,
                log_callback=self.log_callback
            )
            
            result = create_subtitles_run(context) 
            
            if not result.get('success'):
                return {'success': False, 'errors': [f'자막 이미지 생성 실패: {result.get("message", "알 수 없는 오류")}']}
            
            return {'success': True, 'generated_files': {'subtitles': result.get('output_dir')}, 'errors': []}
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {'success': False, 'errors': [f'자막 이미지 생성 중 오류: {str(e)}']}

    def run_video_rendering(self, ui_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            project_name = ui_data.get('project_name', '')
            identifier = ui_data.get('identifier', '')
            script_type = ui_data.get('script_type', 'conversation')
            
            if not project_name or not identifier:
                return {'success': False, 'errors': ['프로젝트명과 식별자가 필요합니다.']}
            
            output_dir = os.path.join("output", project_name, identifier)
            video_path = self._render_video(None, None, None, output_dir, script_type)
            if not video_path:
                return {'success': False, 'errors': ['비디오 렌더링 실패']}
            
            return {'success': True, 'generated_files': {'video': video_path}, 'errors': []}
            
        except Exception as e:
            return {'success': False, 'errors': [f'비디오 렌더링 중 오류: {str(e)}']}

    def _create_manifest(self, project_name: str, identifier: str, script_type: str, output_dir: str, ui_data: Dict = None) -> Optional[Tuple[str, Dict]]:
        try:
            manifest_dir = os.path.join(output_dir, "manifest")
            os.makedirs(manifest_dir, exist_ok=True)

            # 'all' 타입에 따라 파일명 분기
            manifest_filename = f"{identifier}_main.json" if script_type == 'all' else f"{identifier}_{script_type}.json"
            manifest_path = os.path.join(manifest_dir, manifest_filename)

            manifest_data = {
                "project_name": project_name,
                "identifier": identifier,
                "script_type": script_type, # 'all' 또는 개별 타입
                "scenes": []
            }

            all_scenes = []
            if script_type == 'all':
                all_script_data = ui_data.get('script_data', {})
                for actual_script_type, scenes in all_script_data.items():
                    if not scenes: continue
                    # Get settings for this specific script type
                    script_settings = ui_data.get('script_settings', {}).get(actual_script_type, {})
                    for i, scene_data in enumerate(scenes):
                        new_scene = scene_data.copy()
                        new_scene['id'] = new_scene.get('id', f"{actual_script_type}_{i+1}")
                        new_scene['sequence'] = new_scene.get('sequence', i + 1)
                        new_scene['type'] = new_scene.get('type', actual_script_type)
                        new_scene['settings'] = script_settings # Embed settings into scene
                        all_scenes.append(new_scene)
            else:
                scenes = ui_data.get('script_data', [])
                if scenes:
                    script_settings = ui_data.get('script_settings', {}).get(script_type, {})
                    for i, scene_data in enumerate(scenes):
                        new_scene = scene_data.copy()
                        new_scene['id'] = new_scene.get('id', f"{script_type}_{i+1}")
                        new_scene['sequence'] = new_scene.get('sequence', i + 1)
                        new_scene['type'] = new_scene.get('type', script_type)
                        new_scene['settings'] = script_settings # Embed settings into scene
                        all_scenes.append(new_scene)

            manifest_data["scenes"] = all_scenes

            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest_data, f, ensure_ascii=False, indent=2)
            
            return manifest_path, manifest_data
            
        except Exception as e:
            self.log_callback(f"❌ 매니페스트 생성 실패: {e}")
            return None, None
    
    def _create_subtitles(self, manifest_path: str, output_dir: str, ui_data: Dict[str, Any]) -> Optional[str]:
        print("🚀 [자막 생성] _create_subtitles 메서드 시작")
        print(f"🔍 [자막 생성] manifest_path: {manifest_path}")
        print(f"🔍 [자막 생성] output_dir: {output_dir}")
        print(f"🔍 [자막 생성] ui_data keys: {list(ui_data.keys()) if ui_data else 'None'}")
        
        try:
            # 매니페스트 파일 로드
            print("📁 [자막 생성] 매니페스트 파일 로드 시작...")
            if not os.path.exists(manifest_path):
                print(f"❌ [자막 생성] 매니페스트 파일이 존재하지 않습니다: {manifest_path}")
                return None
                
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest_data = json.load(f)
            print(f"✅ [자막 생성] 매니페스트 파일 로드 완료: {len(manifest_data.get('scenes', []))}개 장면")
            
            # 각 타입별 폴더 생성
            conversation_dir = os.path.join(output_dir, "conversation")
            intro_dir = os.path.join(output_dir, "intro")
            ending_dir = os.path.join(output_dir, "ending")
            thumbnail_dir = os.path.join(output_dir, "thumbnail")
            
            os.makedirs(conversation_dir, exist_ok=True)
            os.makedirs(intro_dir, exist_ok=True)
            os.makedirs(ending_dir, exist_ok=True)
            os.makedirs(thumbnail_dir, exist_ok=True)
            
            # 메모리에 있는 이미지 설정 데이터 가져오기
            print("🔍 [자막 생성] UI 참조 확인 중...")
            if not self.root:
                print("❌ [자막 생성] self.root가 None입니다.")
                return None
            if not hasattr(self.root, 'pages'):
                print("❌ [자막 생성] self.root.pages가 없습니다.")
                return None
            if 'image' not in self.root.pages:
                print("❌ [자막 생성] self.root.pages['image']가 없습니다.")
                print(f"🔍 [자막 생성] 사용 가능한 pages: {list(self.root.pages.keys())}")
                return None
            
            print("✅ [자막 생성] 이미지 설정 UI 참조 성공")
            image_tab = self.root.pages['image']
            
            # 메모리에 있는 script_settings에서 설정 가져오기
            print("🔍 [자막 생성] script_settings 확인 중...")
            if not hasattr(image_tab, 'script_settings'):
                print("❌ [자막 생성] image_tab에 script_settings 속성이 없습니다.")
                return None
            if not image_tab.script_settings:
                print("❌ [자막 생성] script_settings가 비어있습니다.")
                print(f"🔍 [자막 생성] script_settings 타입: {type(image_tab.script_settings)}")
                print(f"🔍 [자막 생성] script_settings 내용: {image_tab.script_settings}")
                return None
            
            print(f"✅ [자막 생성] script_settings 확인 완료: {list(image_tab.script_settings.keys())}")
            
            # 현재 스크립트 타입에 해당하는 설정 가져오기
            current_script_type = ui_data.get('script_type', 'conversation')
            print(f"🔍 [자막 생성] 요청된 스크립트 타입: {current_script_type}")
            print(f"🔍 [자막 생성] 사용 가능한 설정 키들: {list(image_tab.script_settings.keys())}")
            
            if current_script_type not in image_tab.script_settings:
                print(f"⚠️ [자막 생성] {current_script_type}에 대한 설정이 메모리에 없습니다. 기본 설정을 사용합니다.")
                current_script_type = "conversation"  # 기본값 사용
            
            script_settings = image_tab.script_settings[current_script_type]
            print(f"✅ [자막 생성] 메모리에서 {current_script_type} 설정 로드 완료")
            print(f"🔍 [자막 생성] 로드된 설정 키들: {list(script_settings.keys())}")
            print(f"🔍 [자막 생성] script_settings 전체 내용: {script_settings}")
            print(f"🔍 [자막 생성] script_settings 타입: {type(script_settings)}")
            print(f"🔍 [자막 생성] script_settings 길이: {len(script_settings) if hasattr(script_settings, '__len__') else 'N/A'}")
            
            # main_background 설정 확인
            if 'main_background' in script_settings:
                print(f"🔍 [자막 생성] main_background 발견: {script_settings['main_background']}")
            else:
                print(f"⚠️ [자막 생성] main_background 키가 없습니다!")
                print(f"🔍 [자막 생성] 사용 가능한 키들: {list(script_settings.keys())}")
            
            # 모든 설정 항목 확인
            print(f"🔍 [자막 생성] === 모든 설정 항목 확인 ===")
            for key, value in script_settings.items():
                print(f"🔍 [자막 생성] {key}: {value}")
            
            # script_settings가 비어있는지 확인
            if not script_settings:
                print(f"⚠️ [자막 생성] script_settings가 비어있습니다!")
                print(f"🔍 [자막 생성] image_tab.script_settings 전체: {image_tab.script_settings}")
                print(f"🔍 [자막 생성] image_tab.script_settings 타입: {type(image_tab.script_settings)}")
                print(f"🔍 [자막 생성] image_tab.script_settings 키들: {list(image_tab.script_settings.keys())}")
            print(f"🔍 [자막 생성] === 설정 항목 확인 완료 ===")
            
            # script_settings가 비어있는 경우 기본 설정으로 초기화
            if not script_settings:
                print(f"⚠️ [자막 생성] script_settings가 비어있어서 기본 설정으로 초기화합니다.")
                script_settings = {
                    "main_background": {"type": "이미지", "value": "/Users/janghwanmoon/Projects/captionGen/assets/background/shubham-dhage-1pK0lHvVaeM-unsplash.jpg"},
                    "line_spacing": {"ratio": 0.8},
                    "background_box": {"type": "없음", "color": "#000000", "alpha": 0.2, "margin": 2},
                    "shadow": {"useBlur": True, "thick": 2, "color": "#000000", "blur": 8, "offx": 2, "offy": 2, "alpha": 0.6},
                    "border": {"thick": 2, "color": "#000000"},
                    "행수": "4", "비율": "16:9", "해상도": "1920x1080",
                    "rows": [
                        {"행": "순번", "x": 50, "y": 50, "w": 1820, "크기(pt)": 80, "폰트(pt)": "KoPubWorld돋움체 Bold", "색상": "#FFFFFF", "좌우 정렬": "Left", "상하 정렬": "Top", "바탕": False, "쉐도우": False, "외곽선": False},
                        {"행": "원어", "x": 50, "y": 150, "w": 1820, "크기(pt)": 100, "폰트(pt)": "KoPubWorld돋움체 Bold", "색상": "#00FFFF", "좌우 정렬": "Center", "상하 정렬": "Top", "바탕": False, "쉐도우": False, "외곽선": False},
                        {"행": "학습어", "x": 50, "y": 450, "w": 1820, "크기(pt)": 100, "폰트(pt)": "Noto Sans KR Bold", "색상": "#FF00FF", "좌우 정렬": "Center", "상하 정렬": "Top", "바탕": False, "쉐도우": False, "외곽선": False},
                        {"행": "읽기", "x": 50, "y": 750, "w": 1820, "크기(pt)": 100, "폰트(pt)": "KoPubWorld돋움체 Bold", "색상": "#FFFF00", "좌우 정렬": "Center", "상하 정렬": "Top", "바탕": False, "쉐도우": False, "외곽선": False},
                    ]
                }
                print(f"✅ [자막 생성] 기본 설정으로 초기화 완료: {script_settings}")
            
            # PNGRenderer 형식으로 변환
            print("🔄 [자막 생성] PNGRenderer 형식으로 변환 시작...")
            print(f"🔍 [자막 생성] script_settings keys: {list(script_settings.keys())}")
            print(f"🔍 [자막 생성] main_background: {script_settings.get('main_background', 'NOT_FOUND')}")
            settings_dict = self._convert_to_png_renderer_format(script_settings)
            print(f"✅ [자막 생성] PNGRenderer 형식 변환 완료")
            print(f"🔍 [자막 생성] 변환된 settings_dict keys: {list(settings_dict.keys())}")
            print(f"🔍 [자막 생성] common.bg: {settings_dict.get('common', {}).get('bg', 'NOT_FOUND')}")
            
            # PNGRenderer 초기화
            print("🚀 [자막 생성] PNGRenderer 초기화 시작...")
            from ..renderers import PNGRenderer
            png_renderer = PNGRenderer(settings_dict)
            print("✅ [자막 생성] PNGRenderer 초기화 완료")
            
            # 해상도 설정
            resolution = (1920, 1080)  # 기본 해상도
            if 'resolution' in manifest_data:
                width, height = map(int, manifest_data['resolution'].split('x'))
                resolution = (width, height)
            
            identifier = manifest_data.get('identifier', 'unknown')
            scenes = manifest_data.get('scenes', [])
            print(f"🔍 매니페스트에서 {len(scenes)}개 장면 발견")
            
            # 회화 이미지 생성
            current_script_type = ui_data.get('script_type', 'conversation')
            if current_script_type == "conversation":
                # conversation 스크립트 타입일 때는 모든 scenes를 conversation으로 처리
                conversation_scenes = scenes
                print(f"🔍 conversation 스크립트 타입: {len(conversation_scenes)}개 장면을 회화로 처리")
            else:
                conversation_scenes = [s for s in scenes if s.get('type') == 'conversation']
                print(f"🔍 다른 스크립트 타입: {len(conversation_scenes)}개 conversation 장면 발견")
            
            for i, scene in enumerate(conversation_scenes):
                scene_data = {
                    'sequence': scene.get('sequence', i+1),
                    'native_script': scene.get('native_script', ''),
                    'learning_script': scene.get('learning_script', ''),
                    'reading_script': scene.get('reading_script', '')
                }
                
                base_filename = f"{identifier}_conversation_{i+1:03d}"
                created_files = png_renderer.create_conversation_image(
                    scene_data, conversation_dir, resolution, base_filename
                )
                
                if created_files:
                    print(f"✅ 회화 이미지 생성: {len(created_files)}개 파일")
            
            # 인트로 이미지 생성
            intro_scenes = [s for s in scenes if s.get('type') == 'intro']
            if intro_scenes:
                full_script = intro_scenes[0].get('full_script', '')
                sentences = [s.strip() for s in full_script.split('\n') if s.strip()]
                
                for i, sentence in enumerate(sentences):
                    output_filename = f"{identifier}_intro_{i+1:03d}.png"
                    output_path = os.path.join(intro_dir, output_filename)
                    
                    success = png_renderer.create_intro_ending_image(
                        sentence, output_path, resolution, "intro"
                    )
                    
                    if success:
                        print(f"✅ 인트로 이미지 생성: {output_filename}")
            
            # 엔딩 이미지 생성
            ending_scenes = [s for s in scenes if s.get('type') == 'ending']
            if ending_scenes:
                full_script = ending_scenes[0].get('full_script', '')
                sentences = [s.strip() for s in full_script.split('\n') if s.strip()]
                
                for i, sentence in enumerate(sentences):
                    output_filename = f"{identifier}_ending_{i+1:03d}.png"
                    output_path = os.path.join(ending_dir, output_filename)
                    
                    success = png_renderer.create_intro_ending_image(
                        sentence, output_path, resolution, "ending"
                    )
                    
                    if success:
                        print(f"✅ 엔딩 이미지 생성: {output_filename}")
            
            print(f"✅ 자막 이미지 생성 완료: {output_dir}")
            return output_dir
            
        except Exception as e:
            print(f"❌ 자막 이미지 생성 실패: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _convert_to_png_renderer_format(self, script_settings: dict) -> dict:
        """ImageTabView의 script_settings를 PNGRenderer 형식으로 변환"""
        try:
            print(f"🔍 변환할 script_settings 구조: {list(script_settings.keys())}")
            
            # 공통 설정 추출
            common_settings = {
                "bg": {
                    "enabled": True,
                    "type": script_settings.get("main_background", {}).get("type", "색상"),
                    "value": script_settings.get("main_background", {}).get("value", "#000000")
                },
                "shadow": {
                    "useBlur": script_settings.get("shadow", {}).get("useBlur", True),
                    "thick": script_settings.get("shadow", {}).get("thick", 2),
                    "color": script_settings.get("shadow", {}).get("color", "#000000"),
                    "blur": script_settings.get("shadow", {}).get("blur", 8),
                    "offx": script_settings.get("shadow", {}).get("offx", 2),
                    "offy": script_settings.get("shadow", {}).get("offy", 2),
                    "alpha": script_settings.get("shadow", {}).get("alpha", 0.6)
                },
                "border": {
                    "thick": script_settings.get("border", {}).get("thick", 2),
                    "color": script_settings.get("border", {}).get("color", "#000000")
                },
                "line_spacing": {
                    "ratio": script_settings.get("line_spacing", {}).get("ratio", 0.8)
                },
                "background_box": {
                    "type": script_settings.get("background_box", {}).get("type", "없음"),
                    "color": script_settings.get("background_box", {}).get("color", "#000000"),
                    "alpha": script_settings.get("background_box", {}).get("alpha", 0.2),
                    "margin": script_settings.get("background_box", {}).get("margin", 2)
                }
            }
            
            # 행 설정 추출
            rows = script_settings.get("rows", [])
            print(f"🔍 script_settings에서 추출된 rows: {len(rows)}개")
            if rows:
                for i, row in enumerate(rows):
                    print(f"🔍 행 {i+1}: {row}")
            else:
                print("⚠️ rows가 비어있습니다!")
            
            # PNGRenderer가 기대하는 형식으로 변환
            result = {
                "common": common_settings,
                "tabs": {
                    "conversation": {"rows": rows},
                    "intro": {"rows": rows},
                    "ending": {"rows": rows},
                    "thumbnail": {"rows": rows}
                }
            }
            
            print(f"✅ PNGRenderer 형식 변환 완료: {len(rows)}개 행, {len(result['tabs'])}개 탭")
            return result
            
        except Exception as e:
            print(f"❌ PNGRenderer 형식 변환 오류: {e}")
            import traceback
            traceback.print_exc()
            return {
                "common": {},
                "tabs": {
                    "conversation": {"rows": []},
                    "intro": {"rows": []},
                    "ending": {"rows": []},
                    "thumbnail": {"rows": []}
                }
            }
    
    def _render_video(self, manifest_path: Optional[str], audio_path: Optional[str], subtitle_dir: Optional[str], output_dir: str, script_type: str) -> Optional[Dict[str, str]]:
        try:
            video_dir = os.path.join(output_dir, "mp4")
            os.makedirs(video_dir, exist_ok=True)
            
            project_name = os.path.basename(os.path.dirname(output_dir))
            identifier = os.path.basename(output_dir)
            
            timing_path = os.path.join(output_dir, "timing", f"{identifier}_{script_type}.json")
            if not os.path.exists(timing_path):
                print(f"🔥🔥🔥 [오류] 타이밍 파일을 찾을 수 없습니다: {timing_path}")
                return None
            
            output_video_path = os.path.join(video_dir, f"{identifier}_{script_type}.mp4")
            image_dir = os.path.join(output_dir, script_type) # Assumes image subdir matches script type

            if not os.path.exists(image_dir):
                print(f"🔥🔥🔥 [오류] 이미지 디렉토리를 찾을 수 없습니다: {image_dir}")
                return None

            success = self.ffmpeg_renderer.create_video_from_timing(timing_path, output_video_path, image_dir, script_type)
            if success and os.path.exists(output_video_path):
                return {f"{script_type}_video": output_video_path}
            else:
                return None
                
        except Exception as e:
            print(f"❌ 비디오 렌더링 실패: {e}")
            return None
    
    def create_final_merged_video(self, project_name: str, identifier: str, output_dir: str, smooth_transition: bool = True) -> Optional[str]:
        try:
            mp4_dir = os.path.join(output_dir, "mp4")
            
            intro_path = os.path.join(mp4_dir, f"{identifier}_intro.mp4")
            conversation_path = os.path.join(mp4_dir, f"{identifier}_conversation.mp4")
            ending_path = os.path.join(mp4_dir, f"{identifier}_ending.mp4")
            
            existing_videos = []
            if os.path.exists(intro_path): existing_videos.append(intro_path)
            if os.path.exists(conversation_path): existing_videos.append(conversation_path)
            if os.path.exists(ending_path): existing_videos.append(ending_path)
            
            if not existing_videos:
                self.log_callback("⚠️ 병합할 비디오 파일이 없습니다.")
                return None
            
            final_path = os.path.join(mp4_dir, f"{identifier}_final.mp4")
            
            success = self.ffmpeg_renderer.create_final_merged_video(
                intro_path if os.path.exists(intro_path) else None,
                conversation_path if os.path.exists(conversation_path) else None,
                ending_path if os.path.exists(ending_path) else None,
                final_path,
                smooth_transition
            )
            
            return final_path if success and os.path.exists(final_path) else None
                
        except Exception as e:
            print(f"❌ 최종 비디오 병합 실패: {e}")
            return None
    
    def _get_conversation_data_from_ui(self, ui_data=None) -> List[Dict]:
        try:
            if ui_data and 'scenes' in ui_data:
                return [{
                    'sequence': int(scene.get('order', i+1)),
                    'type': 'conversation',
                    'native_script': scene.get('native_script', ''),
                    'learning_script': scene.get('learning_script', ''),
                    'reading_script': scene.get('reading_script', '')
                } for i, scene in enumerate(ui_data['scenes'])]
            return []
        except Exception as e:
            print(f"❌ UI에서 데이터 추출 실패: {e}")
            return []

    def run_timing_based_video_rendering(self, ui_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            project_name = ui_data.get('project_name', '')
            identifier = ui_data.get('identifier', '')
            selected_script_type = ui_data.get('script_type', '')
            
            if not project_name or not identifier or not selected_script_type:
                return {"success": False, "message": "프로젝트, 식별자, 스크립트 타입이 필요합니다."}
            
            output_dir = f"output/{project_name}/{identifier}"
            video_dir = os.path.join(output_dir, "mp4")
            os.makedirs(video_dir, exist_ok=True)
            
            generated_videos = {}
            errors = []
            
            script_types_to_render = [selected_script_type]
            
            for script_type in script_types_to_render:
                timing_path = os.path.join(output_dir, "timing", f"{identifier}_{script_type}.json")
                image_dir = os.path.join(output_dir, "subtitles", script_type)
                output_video_path = os.path.join(video_dir, f"{identifier}_{script_type}.mp4")
                
                if not os.path.exists(timing_path):
                    errors.append(f"{script_type} 타이밍 파일을 찾을 수 없습니다: {timing_path}")
                    continue
                
                if not os.path.exists(image_dir):
                    errors.append(f"{script_type} 이미지 디렉토리를 찾을 수 없습니다: {image_dir}")
                    continue
                
                success = self.ffmpeg_renderer.create_video_from_timing(timing_path, output_video_path, image_dir, script_type)
                
                if success and os.path.exists(output_video_path):
                    generated_videos[script_type] = output_video_path
                else:
                    errors.append(f"{script_type} 비디오 생성 실패")
            
            if generated_videos:
                return {"success": True, "generated_videos": generated_videos, "errors": errors}
            else:
                return {"success": False, "message": "모든 비디오 생성 실패", "errors": errors}
                
        except Exception as e:
            return {"success": False, "message": f"오류: {e}"}
