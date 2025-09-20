"""
파이프라인 모듈

자동화된 비디오 생성 파이프라인을 제공합니다.
"""

__version__ = "1.0.0"
__author__ = "CaptionGen Team"
__description__ = "자동화된 비디오 생성 파이프라인"

# Manifest 시스템
from .manifest import ManifestParser, ManifestValidator, ManifestGenerator

# 오디오 시스템
from .audio import SSMLBuilder, AudioGenerator, AudioSegmenter

# 자막 시스템
# TextRenderer와 SubtitleGenerator는 삭제됨 - PNGRenderer 사용
from .renderers import PNGRenderer

# 설정 시스템
from .settings import (
    SettingValidator, SettingMerger, MergedSettings,
    BackgroundSettings, ShadowSettings, BorderSettings, RowSettings,
    ScriptTypeSettings, CommonSettings, ImageGenerationSettings,
    SettingSyncManager, SettingObserver, SettingDebugger
)

# FFmpeg 시스템
from .ffmpeg import FFmpegRenderer, PipelineManager

# UI 통합 시스템

# 플러그인 시스템
from .plugins import (
    BasePlugin, PluginResult, PluginConfig,
    PluginManager, IntroPlugin, ConversationPlugin, EndingPlugin
)
from .plugin_based_manager import PluginBasedPipelineManager

# 테스트 시스템
from .testing import TestRunner, SettingReflectionTest, SystemIntegrationTest, PerformanceTest

# 유틸리티
from .utils import FileNamingManager, ProgressLogger

__all__ = [
    # Manifest
    "ManifestParser",
    "ManifestValidator", 
    "ManifestGenerator",
    
    # Audio
    "SSMLBuilder",
    "AudioGenerator",
    "AudioSegmenter",
    
    # Subtitle (TextRenderer와 SubtitleGenerator는 삭제됨)
    "PNGRenderer",
    
    # Settings
    "SettingValidator",
    "SettingMerger",
    "MergedSettings",
    "BackgroundSettings",
    "ShadowSettings",
    "BorderSettings",
    "RowSettings",
    "ScriptTypeSettings",
    "CommonSettings",
    "ImageGenerationSettings",
    "SettingSyncManager",
    "SettingObserver",
    "SettingDebugger",
    
    # FFmpeg
    "FFmpegRenderer",
    "PipelineManager",
    
    # UI Integration
    "UIIntegratedPipelineManager",
    "UIPipelineConfig",
    
    # Plugin System
    "BasePlugin",
    "PluginResult", 
    "PluginConfig",
    "PluginManager",
    "IntroPlugin",
    "ConversationPlugin",
    "EndingPlugin",
    "PluginBasedPipelineManager",
    
    # 테스트 시스템
    "TestRunner",
    "SettingReflectionTest",
    "SystemIntegrationTest",
    "PerformanceTest",
    
    # Utils
    "FileNamingManager",
    "ProgressLogger"
]
