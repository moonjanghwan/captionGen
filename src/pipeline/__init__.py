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
from .subtitle import TextRenderer, SubtitleGenerator

# FFmpeg 시스템
from .ffmpeg import FFmpegRenderer, PipelineManager

# UI 통합 시스템
from .ui_integrated_manager import UIIntegratedPipelineManager, UIPipelineConfig

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
    
    # Subtitle
    "TextRenderer",
    "SubtitleGenerator",
    
    # FFmpeg
    "FFmpegRenderer",
    "PipelineManager",
    
    # UI Integration
    "UIIntegratedPipelineManager",
    "UIPipelineConfig",
    
    # Utils
    "FileNamingManager",
    "ProgressLogger"
]
