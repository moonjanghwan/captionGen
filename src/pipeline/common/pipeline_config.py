"""
파이프라인 설정 관리

파이프라인의 전역 설정과 스크립트 타입별 설정을 통합 관리합니다.
"""

from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from .script_type_manager import ScriptType, ScriptTypeManager


@dataclass
class PipelineSettings:
    """파이프라인 전역 설정"""
    # 기본 경로 설정
    base_output_dir: str = "output"
    temp_dir: str = "temp"
    log_dir: str = "logs"
    
    # 파일명 규칙
    use_timestamp_in_filename: bool = True
    filename_prefix: str = ""
    filename_suffix: str = ""
    
    # 오디오 설정
    default_audio_format: str = "mp3"
    default_audio_quality: str = "high"
    default_sample_rate: int = 44100
    default_bitrate: int = 192
    
    # 비디오 설정
    default_video_format: str = "mp4"
    default_video_codec: str = "libx264"
    default_video_quality: str = "high"
    default_fps: int = 30
    
    # 자막 설정
    default_subtitle_format: str = "png"
    default_subtitle_quality: int = 95
    
    # 처리 설정
    enable_parallel_processing: bool = True
    max_parallel_workers: int = 4
    enable_progress_logging: bool = True
    enable_debug_logging: bool = False
    
    # UI 설정
    auto_save_settings: bool = True
    settings_file_name: str = "_text_settings.json"
    
    # 에러 처리
    max_retry_attempts: int = 3
    retry_delay: float = 1.0
    continue_on_error: bool = False


@dataclass
class PipelineConfig:
    """파이프라인 설정 클래스"""
    # 프로젝트 정보
    project_name: str = "untitled_project"
    project_version: str = "1.0.0"
    
    # 전역 설정
    settings: PipelineSettings = field(default_factory=PipelineSettings)
    
    # 스크립트 타입 관리자
    script_type_manager: ScriptTypeManager = field(default_factory=ScriptTypeManager)
    
    # 활성화된 기능들
    enable_manifest_generation: bool = True
    enable_audio_generation: bool = True
    enable_subtitle_generation: bool = True
    enable_video_rendering: bool = True
    enable_thumbnail_generation: bool = True
    
    # 사용자 정의 설정
    custom_settings: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """초기화 후 처리"""
        if not self.script_type_manager:
            self.script_type_manager = ScriptTypeManager()
    
    def get_script_type_config(self, script_type: Union[ScriptType, str]) -> Optional[Any]:
        """스크립트 타입별 설정 반환"""
        return self.script_type_manager.get_config(script_type)
    
    def update_script_type_config(self, script_type: Union[ScriptType, str], 
                                 updates: Dict[str, Any]) -> bool:
        """스크립트 타입별 설정 업데이트"""
        return self.script_type_manager.update_config(script_type, updates)
    
    def apply_global_script_changes(self, changes: Dict[str, Any]) -> bool:
        """모든 스크립트 타입에 전역 변경사항 적용"""
        return self.script_type_manager.apply_global_changes(changes)
    
    def get_ui_settings_for_all_types(self) -> Dict[str, Dict[str, Any]]:
        """모든 스크립트 타입의 UI 설정 반환"""
        ui_settings = {}
        for script_type, config in self.script_type_manager.get_all_configs().items():
            ui_settings[config.ui_tab_name] = self.script_type_manager.get_ui_settings_format(script_type)
        return ui_settings
    
    def get_ui_settings_for_type(self, script_type: Union[ScriptType, str]) -> Dict[str, Any]:
        """특정 스크립트 타입의 UI 설정 반환"""
        return self.script_type_manager.get_ui_settings_format(script_type)
    
    def validate_config(self) -> Dict[str, Any]:
        """설정 유효성 검사"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # 프로젝트 이름 검증
        if not self.project_name or len(self.project_name.strip()) == 0:
            validation_result["errors"].append("프로젝트 이름이 필요합니다")
        
        # 경로 검증
        if not self.settings.base_output_dir:
            validation_result["errors"].append("기본 출력 디렉토리가 필요합니다")
        
        # 오디오 설정 검증
        if self.settings.default_sample_rate <= 0:
            validation_result["errors"].append("샘플 레이트는 0보다 커야 합니다")
        
        if self.settings.default_bitrate <= 0:
            validation_result["errors"].append("비트레이트는 0보다 커야 합니다")
        
        # 비디오 설정 검증
        if self.settings.default_fps <= 0:
            validation_result["errors"].append("FPS는 0보다 커야 합니다")
        
        # 병렬 처리 설정 검증
        if self.settings.max_parallel_workers <= 0:
            validation_result["warnings"].append("병렬 워커 수는 0보다 커야 합니다")
        
        if validation_result["errors"]:
            validation_result["valid"] = False
        
        return validation_result
    
    def to_dict(self) -> Dict[str, Any]:
        """설정을 딕셔너리로 변환"""
        return {
            "project_name": self.project_name,
            "project_version": self.project_version,
            "settings": {
                "base_output_dir": self.settings.base_output_dir,
                "temp_dir": self.settings.temp_dir,
                "log_dir": self.settings.log_dir,
                "use_timestamp_in_filename": self.settings.use_timestamp_in_filename,
                "filename_prefix": self.settings.filename_prefix,
                "filename_suffix": self.settings.filename_suffix,
                "default_audio_format": self.settings.default_audio_format,
                "default_audio_quality": self.settings.default_audio_quality,
                "default_sample_rate": self.settings.default_sample_rate,
                "default_bitrate": self.settings.default_bitrate,
                "default_video_format": self.settings.default_video_format,
                "default_video_codec": self.settings.default_video_codec,
                "default_video_quality": self.settings.default_video_quality,
                "default_fps": self.settings.default_fps,
                "default_subtitle_format": self.settings.default_subtitle_format,
                "default_subtitle_quality": self.settings.default_subtitle_quality,
                "enable_parallel_processing": self.settings.enable_parallel_processing,
                "max_parallel_workers": self.settings.max_parallel_workers,
                "enable_progress_logging": self.settings.enable_progress_logging,
                "enable_debug_logging": self.settings.enable_debug_logging,
                "auto_save_settings": self.settings.auto_save_settings,
                "settings_file_name": self.settings.settings_file_name,
                "max_retry_attempts": self.settings.max_retry_attempts,
                "retry_delay": self.settings.retry_delay,
                "continue_on_error": self.settings.continue_on_error
            },
            "enabled_features": {
                "enable_manifest_generation": self.enable_manifest_generation,
                "enable_audio_generation": self.enable_audio_generation,
                "enable_subtitle_generation": self.enable_subtitle_generation,
                "enable_video_rendering": self.enable_video_rendering,
                "enable_thumbnail_generation": self.enable_thumbnail_generation
            },
            "script_type_configs": {
                config.ui_tab_name: self.script_type_manager.get_ui_settings_format(script_type)
                for script_type, config in self.script_type_manager.get_all_configs().items()
            },
            "custom_settings": self.custom_settings
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PipelineConfig':
        """딕셔너리에서 설정 객체 생성"""
        config = cls()
        
        # 기본 정보
        config.project_name = data.get("project_name", "untitled_project")
        config.project_version = data.get("project_version", "1.0.0")
        
        # 설정 정보
        settings_data = data.get("settings", {})
        config.settings = PipelineSettings(
            base_output_dir=settings_data.get("base_output_dir", "output"),
            temp_dir=settings_data.get("temp_dir", "temp"),
            log_dir=settings_data.get("log_dir", "logs"),
            use_timestamp_in_filename=settings_data.get("use_timestamp_in_filename", True),
            filename_prefix=settings_data.get("filename_prefix", ""),
            filename_suffix=settings_data.get("filename_suffix", ""),
            default_audio_format=settings_data.get("default_audio_format", "mp3"),
            default_audio_quality=settings_data.get("default_audio_quality", "high"),
            default_sample_rate=settings_data.get("default_sample_rate", 44100),
            default_bitrate=settings_data.get("default_bitrate", 192),
            default_video_format=settings_data.get("default_video_format", "mp4"),
            default_video_codec=settings_data.get("default_video_codec", "libx264"),
            default_video_quality=settings_data.get("default_video_quality", "high"),
            default_fps=settings_data.get("default_fps", 30),
            default_subtitle_format=settings_data.get("default_subtitle_format", "png"),
            default_subtitle_quality=settings_data.get("default_subtitle_quality", 95),
            enable_parallel_processing=settings_data.get("enable_parallel_processing", True),
            max_parallel_workers=settings_data.get("max_parallel_workers", 4),
            enable_progress_logging=settings_data.get("enable_progress_logging", True),
            enable_debug_logging=settings_data.get("enable_debug_logging", False),
            auto_save_settings=settings_data.get("auto_save_settings", True),
            settings_file_name=settings_data.get("settings_file_name", "_text_settings.json"),
            max_retry_attempts=settings_data.get("max_retry_attempts", 3),
            retry_delay=settings_data.get("retry_delay", 1.0),
            continue_on_error=settings_data.get("continue_on_error", False)
        )
        
        # 활성화된 기능들
        enabled_features = data.get("enabled_features", {})
        config.enable_manifest_generation = enabled_features.get("enable_manifest_generation", True)
        config.enable_audio_generation = enabled_features.get("enable_audio_generation", True)
        config.enable_subtitle_generation = enabled_features.get("enable_subtitle_generation", True)
        config.enable_video_rendering = enabled_features.get("enable_video_rendering", True)
        config.enable_thumbnail_generation = enabled_features.get("enable_thumbnail_generation", True)
        
        # 사용자 정의 설정
        config.custom_settings = data.get("custom_settings", {})
        
        return config
    
    def save_to_file(self, file_path: str) -> bool:
        """설정을 파일로 저장"""
        from .common_functions import CommonFunctions
        return CommonFunctions.save_json_file(file_path, self.to_dict())
    
    @classmethod
    def load_from_file(cls, file_path: str) -> Optional['PipelineConfig']:
        """파일에서 설정 로드"""
        from .common_functions import CommonFunctions
        data = CommonFunctions.load_json_file(file_path)
        if data:
            return cls.from_dict(data)
        return None
