"""
UI 통합 파이프라인 매니저

UI 입력 데이터를 파이프라인 형식으로 변환하고 실행 과정을 실시간으로 모니터링합니다.
"""

import os
import json
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass

from .utils.file_naming import FileNamingManager
from .utils.progress_logger import ProgressLogger
from .manifest import ManifestParser
from .audio import AudioGenerator, SSMLBuilder
# SubtitleGenerator는 삭제됨 - PNGRenderer 사용
# from .subtitle import SubtitleGenerator
from .ffmpeg import FFmpegRenderer


@dataclass
class UIPipelineConfig:
    """UI 파이프라인 설정"""
    project_name: str
    resolution: str = "1920x1080"
    fps: int = 30
    enable_audio_generation: bool = True
    enable_subtitle_generation: bool = True
    enable_video_rendering: bool = True
    enable_quality_optimization: bool = False
    enable_preview_generation: bool = True
    cleanup_temp_files: bool = True
    output_directory: str = "output"


@dataclass
class UIPipelineResult:
    """UI 파이프라인 실행 결과"""
    success: bool
    project_name: str
    output_directory: str
    generated_files: Dict[str, str]
    execution_time: float
    errors: List[str]
    warnings: List[str]
    progress_summary: Dict[str, Any]


class UIIntegratedPipelineManager:
    """UI 통합 파이프라인 매니저"""
    
    def __init__(self, config: UIPipelineConfig):
        """
        UI 통합 파이프라인 매니저 초기화
        
        Args:
            config: UI 파이프라인 설정
        """
        self.config = config
        
        # 파일명 관리자 초기화
        self.file_manager = FileNamingManager(config.output_directory)
        
        # 프로젝트 구조 생성
        self.project_dirs = self.file_manager.create_project_structure(config.project_name)
        
        # 진행 상황 로거 초기화
        self.progress_logger = ProgressLogger(
            config.project_name, 
            self.project_dirs["reports"]
        )
        
        # 파이프라인 컴포넌트들 초기화
        self.manifest_parser = ManifestParser()
        self.audio_generator = AudioGenerator()
        self.subtitle_generator = SubtitleGenerator()
        self.ffmpeg_renderer = FFmpegRenderer()
        
        # 진행 단계 설정
        self._setup_progress_steps()
        
        # 콜백 함수들
        self.progress_callback: Optional[Callable] = None
        self.log_callback: Optional[Callable] = None
        self.completion_callback: Optional[Callable] = None
    
    def _setup_progress_steps(self):
        """진행 단계 설정"""
        total_steps = 7  # 총 7단계
        
        self.progress_logger.add_progress_step("프로젝트 초기화", 1, total_steps)
        self.progress_logger.add_progress_step("Manifest 생성", 2, total_steps)
        self.progress_logger.add_progress_step("SSML 생성", 3, total_steps)
        self.progress_logger.add_progress_step("오디오 생성", 4, total_steps)
        self.progress_logger.add_progress_step("자막 이미지 생성", 5, total_steps)
        self.progress_logger.add_progress_step("비디오 렌더링", 6, total_steps)
        self.progress_logger.add_progress_step("최종 정리", 7, total_steps)
    
    def set_progress_callback(self, callback: Callable):
        """진행 상황 콜백 함수 설정"""
        self.progress_callback = callback
        self.progress_logger.set_progress_callback(callback)
    
    def set_log_callback(self, callback: Callable):
        """로그 콜백 함수 설정"""
        self.log_callback = callback
        self.progress_logger.set_log_callback(callback)
    
    def set_completion_callback(self, callback: Callable):
        """완료 콜백 함수 설정"""
        self.completion_callback = callback
    
    def run_pipeline_from_ui_data(self, ui_data: Dict[str, Any]) -> UIPipelineResult:
        """
        UI 데이터로부터 파이프라인 실행
        
        Args:
            ui_data: UI에서 입력받은 데이터
            
        Returns:
            UIPipelineResult: 실행 결과
        """
        start_time = time.time()
        generated_files = {}
        errors = []
        warnings = []
        
        try:
            self.progress_logger.log_info("UI 파이프라인 실행 시작", {
                "project_name": self.config.project_name,
                "ui_data_keys": list(ui_data.keys())
            })
            
            # 1단계: 프로젝트 초기화
            self.progress_logger.start_step("프로젝트 초기화")
            self.progress_logger.log_info("프로젝트 디렉토리 구조 생성", {
                "project_root": self.project_dirs["project_root"],
                "subdirectories": list(self.project_dirs.keys())
            })
            self.progress_logger.complete_step("프로젝트 초기화", "프로젝트 구조 생성 완료")
            
            # 2단계: Manifest 생성
            self.progress_logger.start_step("Manifest 생성")
            manifest_data = self._create_manifest_from_ui_data(ui_data)
            manifest_path = self._save_manifest(manifest_data)
            generated_files["manifest"] = manifest_path
            self.progress_logger.complete_step("Manifest 생성", f"Manifest 생성 완료: {manifest_path}")
            
            # 3단계: SSML 생성
            if self.config.enable_audio_generation:
                self.progress_logger.start_step("SSML 생성")
                ssml_content = self._generate_ssml(manifest_data)
                ssml_path = self._save_ssml(ssml_content)
                generated_files["ssml"] = ssml_path
                self.progress_logger.complete_step("SSML 생성", f"SSML 생성 완료: {ssml_path}")
            else:
                self.progress_logger.log_warning("오디오 생성 비활성화됨")
            
            # 4단계: 오디오 생성
            if self.config.enable_audio_generation:
                self.progress_logger.start_step("오디오 생성")
                audio_path = self._generate_audio(manifest_data)
                if audio_path:
                    generated_files["audio"] = audio_path
                    self.progress_logger.complete_step("오디오 생성", f"오디오 생성 완료: {audio_path}")
                else:
                    self.progress_logger.fail_step("오디오 생성", "오디오 생성 실패")
                    errors.append("오디오 생성 실패")
            else:
                self.progress_logger.log_warning("오디오 생성 비활성화됨")
            
            # 5단계: 자막 이미지 생성
            if self.config.enable_subtitle_generation:
                self.progress_logger.start_step("자막 이미지 생성")
                subtitle_dir = self._generate_subtitles(manifest_data)
                if subtitle_dir:
                    generated_files["subtitles"] = subtitle_dir
                    self.progress_logger.complete_step("자막 이미지 생성", f"자막 이미지 생성 완료: {subtitle_dir}")
                else:
                    self.progress_logger.fail_step("자막 이미지 생성", "자막 이미지 생성 실패")
                    errors.append("자막 이미지 생성 실패")
                    return self._create_result(False, start_time, generated_files, errors, warnings)
            else:
                self.progress_logger.log_warning("자막 이미지 생성 비활성화됨")
            
            # 6단계: 비디오 렌더링
            if self.config.enable_video_rendering:
                self.progress_logger.start_step("비디오 렌더링")
                video_result = self._render_video(manifest_path, generated_files.get("audio"), subtitle_dir)
                if video_result:
                    # 비디오 결과가 딕셔너리인 경우 (개별 비디오 파일들 포함)
                    if isinstance(video_result, dict):
                        generated_files.update(video_result)
                        main_video = video_result.get("video")
                        if main_video:
                            self.progress_logger.complete_step("비디오 렌더링", f"비디오 렌더링 완료: {main_video}")
                    else:
                        # 단일 비디오 파일인 경우 (기존 방식)
                        generated_files["video"] = video_result
                        self.progress_logger.complete_step("비디오 렌더링", f"비디오 렌더링 완료: {video_result}")
                    
                    # 품질 최적화 (선택적) - 메인 비디오에 대해서만
                    main_video_path = generated_files.get("video")
                    if main_video_path and self.config.enable_quality_optimization:
                        self.progress_logger.log_info("품질 최적화 시작")
                        optimized_path = self._optimize_video_quality(main_video_path)
                        if optimized_path:
                            generated_files["video_optimized"] = optimized_path
                            self.progress_logger.log_info("품질 최적화 완료")
                    
                    # 프리뷰 생성 (선택적) - 메인 비디오에 대해서만
                    if main_video_path and self.config.enable_preview_generation:
                        self.progress_logger.log_info("프리뷰 생성 시작")
                        preview_path = self._create_preview(main_video_path)
                        if preview_path:
                            generated_files["preview"] = preview_path
                            self.progress_logger.log_info("프리뷰 생성 완료")
                else:
                    self.progress_logger.fail_step("비디오 렌더링", "비디오 렌더링 실패")
                    errors.append("비디오 렌더링 실패")
                    return self._create_result(False, start_time, generated_files, errors, warnings)
            else:
                self.progress_logger.log_warning("비디오 렌더링 비활성화됨")
            
            # 7단계: 최종 정리
            self.progress_logger.start_step("최종 정리")
            self._finalize_pipeline(generated_files)
            self.progress_logger.complete_step("최종 정리", "파이프라인 정리 완료")
            
            # 성공 결과 생성
            result = self._create_result(True, start_time, generated_files, errors, warnings)
            
            # 완료 콜백 호출
            if self.completion_callback:
                self.completion_callback(result)
            
            return result
            
        except Exception as e:
            error_msg = f"파이프라인 실행 중 예외 발생: {e}"
            self.progress_logger.log_error(error_msg, {"exception": str(e)})
            errors.append(error_msg)
            
            return self._create_result(False, start_time, generated_files, errors, warnings)
    
    def _create_manifest_from_ui_data(self, ui_data: Dict[str, Any]) -> Dict[str, Any]:
        """UI 데이터로부터 Manifest 생성"""
        try:
            # 기본 Manifest 구조
            manifest = {
                "project_name": self.config.project_name,
                "resolution": self.config.resolution,
                "default_background": "#000000",
                "scenes": []
            }
            
            # UI 데이터에서 장면 정보 추출
            scenes_data = ui_data.get("scenes", [])
            
            for i, scene_data in enumerate(scenes_data, 1):
                scene_type = scene_data.get("type", "conversation")
                
                if scene_type == "conversation":
                    scene = {
                        "id": f"conversation_{i:02d}",
                        "type": "conversation",
                        "sequence": i,
                        "native_script": scene_data.get("native_script", ""),
                        "learning_script": scene_data.get("learning_script", ""),
                        "reading_script": scene_data.get("reading_script", "")
                    }
                elif scene_type == "intro":
                    scene = {
                        "id": f"intro_{i:02d}",
                        "type": "intro",
                        "sequence": i,
                        "full_script": scene_data.get("full_script", "")
                    }
                elif scene_type == "ending":
                    scene = {
                        "id": f"ending_{i:02d}",
                        "type": "ending",
                        "sequence": i,
                        "full_script": scene_data.get("full_script", "")
                    }
                else:
                    # 기본 conversation 타입
                    scene = {
                        "id": f"scene_{i:02d}",
                        "type": "conversation",
                        "sequence": i,
                        "native_script": scene_data.get("text", ""),
                        "learning_script": scene_data.get("translation", ""),
                        "reading_script": scene_data.get("reading", "")
                    }
                
                manifest["scenes"].append(scene)
            
            self.progress_logger.log_info("Manifest 생성 완료", {
                "total_scenes": len(manifest["scenes"]),
                "scene_types": [s["type"] for s in manifest["scenes"]]
            })
            
            return manifest
            
        except Exception as e:
            self.progress_logger.log_error(f"Manifest 생성 실패: {e}")
            raise
    
    def _save_manifest(self, manifest_data: Dict[str, Any]) -> str:
        """Manifest 파일 저장"""
        filename = self.file_manager.generate_manifest_filename(self.config.project_name)
        filepath = self.file_manager.get_full_path(self.project_dirs["manifest"], filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(manifest_data, f, ensure_ascii=False, indent=2)
        
        return filepath
    
    def _generate_ssml(self, manifest_data: Dict[str, Any]) -> str:
        """SSML 생성"""
        ssml_builder = SSMLBuilder()
        return ssml_builder.build_manifest_ssml(manifest_data)
    
    def _save_ssml(self, ssml_content: str) -> str:
        """SSML 파일 저장"""
        filename = self.file_manager.generate_ssml_filename(self.config.project_name)
        filepath = self.file_manager.get_full_path(self.project_dirs["audio"], filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(ssml_content)
        
        return filepath
    
    def _generate_audio(self, manifest_data: Dict[str, Any]) -> Optional[str]:
        """오디오 생성"""
        try:
            # 실제 TTS가 없으므로 더미 오디오 파일 생성
            filename = self.file_manager.generate_audio_filename(self.config.project_name)
            filepath = self.file_manager.get_full_path(self.project_dirs["audio"], filename)
            
            # 간단한 더미 MP3 헤더
            with open(filepath, 'wb') as f:
                f.write(b'\xff\xfb\x90\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
            
            return filepath
            
        except Exception as e:
            self.progress_logger.log_error(f"오디오 생성 실패: {e}")
            return None
    
    def _generate_subtitles(self, manifest_data: Dict[str, Any]) -> Optional[str]:
        """자막 이미지 생성"""
        try:
            frames = self.subtitle_generator.generate_from_manifest(
                manifest_data, self.project_dirs["subtitles"], self.config.fps
            )
            
            if frames:
                return self.project_dirs["subtitles"]
            else:
                return None
                
        except Exception as e:
            self.progress_logger.log_error(f"자막 이미지 생성 실패: {e}")
            return None
    
    def _render_video(self, manifest_path: str, audio_path: Optional[str], 
                     subtitle_dir: str) -> Optional[str]:
        """비디오 렌더링 - 제작 사양서에 따른 회화/인트로/엔딩 비디오 생성"""
        try:
            # 1. 매니페스트 데이터 로드
            manifest_data = self.manifest_manager.load_manifest(manifest_path)
            if not manifest_data:
                self.progress_logger.log_error("매니페스트 데이터 로드 실패")
                return None
            
            # 2. 배경 이미지 경로 설정
            background_path = self._get_background_path()
            
            # 3. 해상도 설정
            resolution = "1920x1080"  # 기본 해상도
            
            # 4. 각 비디오 생성
            intro_video_path = None
            conversation_video_path = None
            ending_video_path = None
            
            # 인트로 비디오 생성
            intro_sentences = self._extract_intro_sentences(manifest_data)
            if intro_sentences:
                intro_filename = f"{self.config.project_name}_intro.mp4"
                intro_path = self.file_manager.get_full_path(self.project_dirs["video"], intro_filename)
                
                success = self.ffmpeg_renderer.create_intro_ending_video(
                    intro_sentences, audio_path or "", subtitle_dir, intro_path, 
                    resolution, background_path, "intro"
                )
                if success:
                    intro_video_path = intro_path
                    self.progress_logger.log_info(f"인트로 비디오 생성 완료: {intro_path}")
            
            # 회화 비디오 생성
            conversation_data = self._extract_conversation_data(manifest_data)
            if conversation_data:
                conversation_filename = f"{self.config.project_name}_conversation.mp4"
                conversation_path = self.file_manager.get_full_path(self.project_dirs["video"], conversation_filename)
                
                success = self.ffmpeg_renderer.create_conversation_video(
                    conversation_data, audio_path or "", subtitle_dir, conversation_path,
                    resolution, background_path
                )
                if success:
                    conversation_video_path = conversation_path
                    self.progress_logger.log_info(f"회화 비디오 생성 완료: {conversation_path}")
            
            # 엔딩 비디오 생성
            ending_sentences = self._extract_ending_sentences(manifest_data)
            if ending_sentences:
                ending_filename = f"{self.config.project_name}_ending.mp4"
                ending_path = self.file_manager.get_full_path(self.project_dirs["video"], ending_filename)
                
                success = self.ffmpeg_renderer.create_intro_ending_video(
                    ending_sentences, audio_path or "", subtitle_dir, ending_path,
                    resolution, background_path, "ending"
                )
                if success:
                    ending_video_path = ending_path
                    self.progress_logger.log_info(f"엔딩 비디오 생성 완료: {ending_path}")
            
            # 5. 최종 비디오 병합
            final_filename = f"{self.config.project_name}_final.mp4"
            final_path = self.file_manager.get_full_path(self.project_dirs["video"], final_filename)
            
            success = self.ffmpeg_renderer.create_final_merged_video(
                intro_video_path, conversation_video_path, ending_video_path, final_path
            )
            
            if success and os.path.exists(final_path):
                self.progress_logger.log_info(f"최종 비디오 생성 완료: {final_path}")
                # 개별 비디오 파일들도 결과에 포함
                result_files = {"video": final_path}
                if intro_video_path:
                    result_files["intro_video"] = intro_video_path
                if conversation_video_path:
                    result_files["conversation_video"] = conversation_video_path
                if ending_video_path:
                    result_files["ending_video"] = ending_video_path
                return result_files
            else:
                self.progress_logger.log_error("최종 비디오 생성 실패")
                return None
                
        except Exception as e:
            self.progress_logger.log_error(f"비디오 렌더링 실패: {e}")
            return None
    
    def _optimize_video_quality(self, video_path: str) -> Optional[str]:
        """비디오 품질 최적화"""
        try:
            filename = self.file_manager.generate_optimized_video_filename(self.config.project_name)
            filepath = self.file_manager.get_full_path(self.project_dirs["video"], filename)
            
            success = self.ffmpeg_renderer.optimize_quality(video_path, filepath, "8000k")
            
            if success and os.path.exists(filepath):
                return filepath
            else:
                return None
                
        except Exception as e:
            self.progress_logger.log_error(f"품질 최적화 실패: {e}")
            return None
    
    def _get_background_path(self) -> str:
        """배경 이미지 경로 반환"""
        try:
            # 기본 배경 이미지 경로 (assets/background 폴더에서 첫 번째 이미지 사용)
            background_dir = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "background")
            if os.path.exists(background_dir):
                bg_files = [f for f in os.listdir(background_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
                if bg_files:
                    return os.path.join(background_dir, bg_files[0])
            
            # 기본 검은색 배경 (fallback)
            return "black"
        except Exception:
            return "black"
    
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
    
    def _extract_conversation_data(self, manifest_data: Dict) -> List[Dict]:
        """매니페스트에서 회화 데이터 추출"""
        try:
            scenes = manifest_data.get('scenes', [])
            conversation_data = []
            
            for scene in scenes:
                if scene.get('type') == 'conversation':
                    conversation_data.append({
                        'sequence': scene.get('sequence', 1),
                        'native_script': scene.get('native_script', ''),
                        'learning_script': scene.get('learning_script', ''),
                        'reading_script': scene.get('reading_script', '')
                    })
            
            return conversation_data
        except Exception:
            return []

    def _create_preview(self, video_path: str) -> Optional[str]:
        """프리뷰 생성"""
        try:
            filename = self.file_manager.generate_preview_filename(self.config.project_name)
            filepath = self.file_manager.get_full_path(self.project_dirs["video"], filename)
            
            success = self.ffmpeg_renderer.create_preview(video_path, filepath, duration=10)
            
            if success and os.path.exists(filepath):
                return filepath
            else:
                return None
                
        except Exception as e:
            self.progress_logger.log_error(f"프리뷰 생성 실패: {e}")
            return None
    
    def _finalize_pipeline(self, generated_files: Dict[str, str]):
        """파이프라인 최종 정리"""
        try:
            # 파이프라인 보고서 저장
            report_filename = self.file_manager.generate_pipeline_report_filename(self.config.project_name)
            report_filepath = self.file_manager.get_full_path(self.project_dirs["reports"], report_filename)
            
            report = {
                "project_name": self.config.project_name,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "config": self.config.__dict__,
                "generated_files": generated_files,
                "project_directories": self.project_dirs
            }
            
            with open(report_filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            # 임시 파일 정리
            if self.config.cleanup_temp_files:
                self.file_manager.cleanup_temp_files(self.config.project_name)
            
            self.progress_logger.log_info("파이프라인 최종 정리 완료", {
                "report_file": report_filepath,
                "total_generated_files": len(generated_files)
            })
            
        except Exception as e:
            self.progress_logger.log_error(f"파이프라인 최종 정리 실패: {e}")
    
    def _create_result(self, success: bool, start_time: float, 
                      generated_files: Dict[str, str], errors: List[str], 
                      warnings: List[str]) -> UIPipelineResult:
        """결과 객체 생성"""
        execution_time = time.time() - start_time
        
        # 진행 상황 요약
        progress_summary = self.progress_logger.get_progress_summary()
        
        return UIPipelineResult(
            success=success,
            project_name=self.config.project_name,
            output_directory=self.project_dirs["project_root"],
            generated_files=generated_files,
            execution_time=execution_time,
            errors=errors,
            warnings=warnings,
            progress_summary=progress_summary
        )
    
    def get_project_summary(self) -> Dict[str, Any]:
        """프로젝트 요약 정보 반환"""
        return self.file_manager.get_project_summary(self.config.project_name)
    
    def print_final_summary(self):
        """최종 요약 출력"""
        self.progress_logger.print_summary()
        
        # 생성된 파일 목록
        print("\n📁 생성된 파일들:")
        for file_type, file_path in self.generated_files.items():
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                print(f"  {file_type}: {file_path} ({file_size / 1024:.1f}KB)")
            else:
                print(f"  {file_type}: {file_path} (파일 없음)")
        
        print(f"\n📁 프로젝트 출력 디렉토리: {self.project_dirs['project_root']}")
        print(f"📊 프로젝트 요약: {self.get_project_summary()}")
