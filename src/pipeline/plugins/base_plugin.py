"""
플러그인 베이스 클래스

모든 스크립트 타입별 플러그인이 상속받아야 하는 기본 클래스입니다.
"""

import os
import json
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass


@dataclass
class PluginConfig:
    """플러그인 설정"""
    project_name: str
    identifier: str
    output_directory: str
    resolution: str = "1920x1080"
    fps: int = 30
    enable_audio_generation: bool = True
    enable_subtitle_generation: bool = True
    enable_video_rendering: bool = True
    cleanup_temp_files: bool = True


@dataclass
class PluginResult:
    """플러그인 실행 결과"""
    success: bool
    plugin_type: str
    execution_time: float
    generated_files: Dict[str, str]
    errors: List[str]
    warnings: List[str]
    metadata: Dict[str, Any]


class BasePlugin(ABC):
    """플러그인 베이스 클래스"""
    
    def __init__(self, config: PluginConfig):
        """
        플러그인 초기화
        
        Args:
            config: 플러그인 설정
        """
        self.config = config
        self.plugin_type = self.get_plugin_type()
        self.generated_files = {}
        self.errors = []
        self.warnings = []
        
        # 콜백 함수들
        self.progress_callback: Optional[Callable] = None
        self.log_callback: Optional[Callable] = None
        
        # 출력 디렉토리 설정
        self._setup_output_directories()
    
    @abstractmethod
    def get_plugin_type(self) -> str:
        """플러그인 타입 반환 (예: 'intro', 'conversation', 'ending')"""
        pass
    
    @abstractmethod
    def get_plugin_name(self) -> str:
        """플러그인 이름 반환"""
        pass
    
    @abstractmethod
    def get_plugin_description(self) -> str:
        """플러그인 설명 반환"""
        pass
    
    def _setup_output_directories(self):
        """출력 디렉토리 설정"""
        self.output_dirs = {
            "manifest": os.path.join(self.config.output_directory, "manifest"),
            "audio": os.path.join(self.config.output_directory, "mp3"),
            "ssml": os.path.join(self.config.output_directory, "SSML"),
            "subtitles": os.path.join(self.config.output_directory, "subtitles"),
            "timeline": os.path.join(self.config.output_directory, "timeline"),
            "video": os.path.join(self.config.output_directory, "video"),
            "mp4": os.path.join(self.config.output_directory, "mp4")
        }
        
        # 디렉토리 생성
        for dir_path in self.output_dirs.values():
            os.makedirs(dir_path, exist_ok=True)
    
    def set_progress_callback(self, callback: Callable):
        """진행 상황 콜백 함수 설정"""
        self.progress_callback = callback
    
    def set_log_callback(self, callback: Callable):
        """로그 콜백 함수 설정"""
        self.log_callback = callback
    
    def _log_info(self, message: str, data: Optional[Dict] = None):
        """정보 로그 출력"""
        if self.log_callback:
            self.log_callback("INFO", message, data)
        else:
            print(f"[{self.plugin_type.upper()}] {message}")
    
    def _log_warning(self, message: str, data: Optional[Dict] = None):
        """경고 로그 출력"""
        self.warnings.append(message)
        if self.log_callback:
            self.log_callback("WARNING", message, data)
        else:
            print(f"[{self.plugin_type.upper()}] WARNING: {message}")
    
    def _log_error(self, message: str, data: Optional[Dict] = None):
        """에러 로그 출력"""
        self.errors.append(message)
        if self.log_callback:
            self.log_callback("ERROR", message, data)
        else:
            print(f"[{self.plugin_type.upper()}] ERROR: {message}")
    
    def _update_progress(self, step: str, progress: float):
        """진행 상황 업데이트"""
        if self.progress_callback:
            self.progress_callback(step, progress)
    
    def run_plugin(self, input_data: Dict[str, Any]) -> PluginResult:
        """
        플러그인 실행
        
        Args:
            input_data: 입력 데이터
            
        Returns:
            PluginResult: 실행 결과
        """
        start_time = time.time()
        
        try:
            self._log_info(f"{self.get_plugin_name()} 플러그인 실행 시작")
            
            # 1. 데이터 검증
            self._update_progress("데이터 검증", 0.1)
            validated_data = self._validate_input_data(input_data)
            if not validated_data:
                return self._create_result(False, start_time)
            
            # 2. 매니페스트 생성
            self._update_progress("매니페스트 생성", 0.2)
            manifest_data = self._create_manifest(validated_data)
            if not manifest_data:
                return self._create_result(False, start_time)
            
            # 3. 오디오 생성
            if self.config.enable_audio_generation:
                self._update_progress("오디오 생성", 0.4)
                audio_result = self._generate_audio(manifest_data)
                if not audio_result:
                    self._log_warning("오디오 생성 실패")
            
            # 4. 자막 이미지 생성
            if self.config.enable_subtitle_generation:
                self._update_progress("자막 이미지 생성", 0.6)
                subtitle_result = self._generate_subtitles(manifest_data)
                if not subtitle_result:
                    self._log_warning("자막 이미지 생성 실패")
            
            # 5. 비디오 렌더링
            if self.config.enable_video_rendering:
                self._update_progress("비디오 렌더링", 0.8)
                video_result = self._render_video(manifest_data)
                if not video_result:
                    self._log_warning("비디오 렌더링 실패")
            
            # 6. 최종 정리
            self._update_progress("최종 정리", 0.9)
            self._finalize_plugin()
            
            self._update_progress("완료", 1.0)
            self._log_info(f"{self.get_plugin_name()} 플러그인 실행 완료")
            
            return self._create_result(True, start_time)
            
        except Exception as e:
            error_msg = f"플러그인 실행 중 예외 발생: {e}"
            self._log_error(error_msg)
            return self._create_result(False, start_time)
    
    @abstractmethod
    def _validate_input_data(self, input_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """입력 데이터 검증"""
        pass
    
    @abstractmethod
    def _create_manifest(self, validated_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """매니페스트 생성"""
        pass
    
    @abstractmethod
    def _generate_audio(self, manifest_data: Dict[str, Any]) -> Optional[str]:
        """오디오 생성"""
        pass
    
    @abstractmethod
    def _generate_subtitles(self, manifest_data: Dict[str, Any]) -> Optional[str]:
        """자막 이미지 생성"""
        pass
    
    @abstractmethod
    def _render_video(self, manifest_data: Dict[str, Any]) -> Optional[str]:
        """비디오 렌더링"""
        pass
    
    def _finalize_plugin(self):
        """플러그인 최종 정리"""
        try:
            # 임시 파일 정리
            if self.config.cleanup_temp_files:
                self._cleanup_temp_files()
            
            # 결과 요약 로그
            self._log_info("플러그인 실행 완료", {
                "generated_files": len(self.generated_files),
                "errors": len(self.errors),
                "warnings": len(self.warnings)
            })
            
        except Exception as e:
            self._log_error(f"플러그인 정리 실패: {e}")
    
    def _cleanup_temp_files(self):
        """임시 파일 정리"""
        # 각 플러그인에서 구현
        pass
    
    def _create_result(self, success: bool, start_time: float) -> PluginResult:
        """결과 객체 생성"""
        execution_time = time.time() - start_time
        
        return PluginResult(
            success=success,
            plugin_type=self.plugin_type,
            execution_time=execution_time,
            generated_files=self.generated_files.copy(),
            errors=self.errors.copy(),
            warnings=self.warnings.copy(),
            metadata={
                "plugin_name": self.get_plugin_name(),
                "plugin_description": self.get_plugin_description(),
                "config": self.config.__dict__
            }
        )
    
    def get_supported_file_types(self) -> List[str]:
        """지원하는 파일 타입 반환"""
        return ["manifest", "audio", "ssml", "subtitles", "timeline", "video"]
    
    def get_required_input_fields(self) -> List[str]:
        """필수 입력 필드 반환"""
        return []
    
    def get_optional_input_fields(self) -> List[str]:
        """선택적 입력 필드 반환"""
        return []
    
    def get_default_settings(self) -> Dict[str, Any]:
        """기본 설정 반환"""
        return {}
    
    def validate_settings(self, settings: Dict[str, Any]) -> List[str]:
        """설정 검증"""
        errors = []
        # 기본 검증 로직
        return errors
