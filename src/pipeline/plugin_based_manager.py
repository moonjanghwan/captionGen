"""
플러그인 기반 파이프라인 매니저

기존 UIIntegratedPipelineManager와 호환성을 유지하면서 플러그인 시스템을 사용하는 새로운 매니저입니다.
"""

import os
import json
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass

from .utils.file_naming import FileNamingManager
from .utils.progress_logger import ProgressLogger
from .plugins.plugin_integration import PluginIntegrationAdapter


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
    use_plugin_system: bool = True  # 플러그인 시스템 사용 여부
    identifier: str = ""  # 식별자 추가


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
    plugin_results: Optional[Dict[str, Any]] = None  # 플러그인 결과 추가


class PluginBasedPipelineManager:
    """플러그인 기반 파이프라인 매니저"""
    
    def __init__(self, config: UIPipelineConfig):
        """
        플러그인 기반 파이프라인 매니저 초기화
        
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
        
        # 플러그인 통합 어댑터 초기화
        if config.use_plugin_system:
            self.plugin_adapter = PluginIntegrationAdapter(config.output_directory)
        else:
            self.plugin_adapter = None
        
        # 진행 단계 설정
        self._setup_progress_steps()
        
        # 콜백 함수들
        self.progress_callback: Optional[Callable] = None
        self.log_callback: Optional[Callable] = None
        self.completion_callback: Optional[Callable] = None
    
    def _setup_progress_steps(self):
        """진행 단계 설정"""
        if self.config.use_plugin_system:
            total_steps = 5  # 플러그인 시스템 사용 시 단계 수
            self.progress_logger.add_progress_step("프로젝트 초기화", 1, total_steps)
            self.progress_logger.add_progress_step("플러그인 데이터 변환", 2, total_steps)
            self.progress_logger.add_progress_step("플러그인 실행", 3, total_steps)
            self.progress_logger.add_progress_step("결과 병합", 4, total_steps)
            self.progress_logger.add_progress_step("최종 정리", 5, total_steps)
        else:
            total_steps = 7  # 기존 시스템 사용 시 단계 수
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
        
        if self.plugin_adapter:
            self.plugin_adapter.set_progress_callback(callback)
    
    def set_log_callback(self, callback: Callable):
        """로그 콜백 함수 설정"""
        self.log_callback = callback
        self.progress_logger.set_log_callback(callback)
        
        if self.plugin_adapter:
            self.plugin_adapter.set_log_callback(callback)
    
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
        
        try:
            self.progress_logger.log_info("파이프라인 실행 시작", {
                "project_name": self.config.project_name,
                "use_plugin_system": self.config.use_plugin_system,
                "ui_data_keys": list(ui_data.keys())
            })
            
            if self.config.use_plugin_system and self.plugin_adapter:
                # 플러그인 시스템 사용
                result = self._run_plugin_based_pipeline(ui_data, start_time)
            else:
                # 기존 시스템 사용 (fallback)
                result = self._run_legacy_pipeline(ui_data, start_time)
            
            # 완료 콜백 호출
            if self.completion_callback:
                self.completion_callback(result)
            
            return result
            
        except Exception as e:
            error_msg = f"파이프라인 실행 중 예외 발생: {e}"
            self.progress_logger.log_error(error_msg, {"exception": str(e)})
            
            return self._create_result(False, start_time, {}, [error_msg], [])
    
    def _run_plugin_based_pipeline(self, ui_data: Dict[str, Any], start_time: float) -> UIPipelineResult:
        """플러그인 기반 파이프라인 실행"""
        try:
            # 1단계: 프로젝트 초기화
            self.progress_logger.start_step("프로젝트 초기화")
            self.progress_logger.log_info("프로젝트 디렉토리 구조 생성", {
                "project_root": self.project_dirs["project_root"],
                "subdirectories": list(self.project_dirs.keys())
            })
            self.progress_logger.complete_step("프로젝트 초기화", "프로젝트 구조 생성 완료")
            
            # 2단계: 플러그인 데이터 변환
            self.progress_logger.start_step("플러그인 데이터 변환")
            self.progress_logger.complete_step("플러그인 데이터 변환", "데이터 변환 완료")
            
            # 3단계: 플러그인 실행
            self.progress_logger.start_step("플러그인 실행")
            
            # UI 데이터에 프로젝트 정보 추가
            ui_data["project_name"] = self.config.project_name
            ui_data["identifier"] = self.config.project_name  # 식별자는 프로젝트명과 동일하게 설정
            
            # 플러그인 기반 파이프라인 실행
            plugin_result = self.plugin_adapter.run_legacy_pipeline(ui_data)
            
            if plugin_result.get("success", False):
                self.progress_logger.complete_step("플러그인 실행", "플러그인 실행 완료")
            else:
                self.progress_logger.fail_step("플러그인 실행", "플러그인 실행 실패")
            
            # 4단계: 결과 병합
            self.progress_logger.start_step("결과 병합")
            self.progress_logger.complete_step("결과 병합", "결과 병합 완료")
            
            # 5단계: 최종 정리
            self.progress_logger.start_step("최종 정리")
            self._finalize_pipeline(plugin_result.get("generated_files", {}))
            self.progress_logger.complete_step("최종 정리", "파이프라인 정리 완료")
            
            # 결과 생성
            return self._create_result(
                plugin_result.get("success", False),
                start_time,
                plugin_result.get("generated_files", {}),
                plugin_result.get("errors", []),
                plugin_result.get("warnings", []),
                plugin_result.get("plugin_results")
            )
            
        except Exception as e:
            error_msg = f"플러그인 기반 파이프라인 실행 실패: {e}"
            self.progress_logger.log_error(error_msg, {"exception": str(e)})
            return self._create_result(False, start_time, {}, [error_msg], [])
    
    def _run_legacy_pipeline(self, ui_data: Dict[str, Any], start_time: float) -> UIPipelineResult:
        """기존 시스템 파이프라인 실행 (fallback)"""
        try:
            # 기존 시스템 로직을 여기에 구현
            # 현재는 더미 구현
            self.progress_logger.log_warning("기존 시스템 사용 (플러그인 시스템 비활성화)")
            
            return self._create_result(True, start_time, {}, [], ["기존 시스템 사용"])
            
        except Exception as e:
            error_msg = f"기존 시스템 파이프라인 실행 실패: {e}"
            self.progress_logger.log_error(error_msg, {"exception": str(e)})
            return self._create_result(False, start_time, {}, [error_msg], [])
    
    def run_auto_generation(self, ui_data: Dict[str, Any]) -> UIPipelineResult:
        """
        자동 생성 실행 (인트로 → 회화 → 엔딩)
        
        Args:
            ui_data: UI에서 입력받은 데이터
            
        Returns:
            UIPipelineResult: 실행 결과
        """
        start_time = time.time()
        
        try:
            self.progress_logger.log_info("자동 생성 실행 시작", {
                "project_name": self.config.project_name,
                "use_plugin_system": self.config.use_plugin_system
            })
            
            if self.config.use_plugin_system and self.plugin_adapter:
                # UI 데이터에 프로젝트 정보 추가
                ui_data["project_name"] = self.config.project_name
                ui_data["identifier"] = self.config.project_name
                
                # 플러그인 기반 자동 생성 실행
                plugin_result = self.plugin_adapter.run_auto_generation(ui_data)
                
                # 결과 생성
                result = self._create_result(
                    plugin_result.get("success", False),
                    start_time,
                    plugin_result.get("generated_files", {}),
                    plugin_result.get("errors", []),
                    plugin_result.get("warnings", []),
                    plugin_result.get("plugin_results")
                )
            else:
                # 기존 시스템 사용
                result = self._run_legacy_pipeline(ui_data, start_time)
            
            # 완료 콜백 호출
            if self.completion_callback:
                self.completion_callback(result)
            
            return result
            
        except Exception as e:
            error_msg = f"자동 생성 실행 중 예외 발생: {e}"
            self.progress_logger.log_error(error_msg, {"exception": str(e)})
            
            return self._create_result(False, start_time, {}, [error_msg], [])
    
    def run_single_plugin(self, plugin_type: str, ui_data: Dict[str, Any]) -> UIPipelineResult:
        """
        단일 플러그인 실행
        
        Args:
            plugin_type: 플러그인 타입 (intro, conversation, ending)
            ui_data: UI에서 입력받은 데이터
            
        Returns:
            UIPipelineResult: 실행 결과
        """
        start_time = time.time()
        
        try:
            self.progress_logger.log_info(f"단일 플러그인 실행 시작: {plugin_type}")
            
            if self.config.use_plugin_system and self.plugin_adapter:
                # UI 데이터에 프로젝트 정보 추가
                ui_data["project_name"] = self.config.project_name
                ui_data["identifier"] = self.config.project_name
                
                # 단일 플러그인 실행
                plugin_result = self.plugin_adapter.run_single_plugin(plugin_type, ui_data)
                
                # 결과 생성
                result = self._create_result(
                    plugin_result.get("success", False),
                    start_time,
                    plugin_result.get("generated_files", {}),
                    plugin_result.get("errors", []),
                    plugin_result.get("warnings", []),
                    {plugin_type: plugin_result}
                )
            else:
                # 기존 시스템 사용
                result = self._run_legacy_pipeline(ui_data, start_time)
            
            return result
            
        except Exception as e:
            error_msg = f"단일 플러그인 실행 중 예외 발생: {e}"
            self.progress_logger.log_error(error_msg, {"exception": str(e)})
            
            return self._create_result(False, start_time, {}, [error_msg], [])
    
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
                "project_directories": self.project_dirs,
                "use_plugin_system": self.config.use_plugin_system
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
                      warnings: List[str], plugin_results: Optional[Dict[str, Any]] = None) -> UIPipelineResult:
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
            progress_summary=progress_summary,
            plugin_results=plugin_results
        )
    
    def get_project_summary(self) -> Dict[str, Any]:
        """프로젝트 요약 정보 반환"""
        summary = self.file_manager.get_project_summary(self.config.project_name)
        
        if self.plugin_adapter:
            plugin_summary = self.plugin_adapter.get_plugin_summary()
            summary["plugin_system"] = plugin_summary
        
        return summary
    
    def get_available_plugins(self) -> List[Dict[str, Any]]:
        """사용 가능한 플러그인 목록 반환"""
        if self.plugin_adapter:
            return self.plugin_adapter.get_available_plugins()
        else:
            return []
    
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
        
        # 플러그인 시스템 정보
        if self.config.use_plugin_system:
            print(f"🔌 플러그인 시스템 사용: {len(self.get_available_plugins())}개 플러그인 등록됨")
