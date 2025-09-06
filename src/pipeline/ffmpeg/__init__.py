"""
FFmpeg 통합 시스템

오디오-비디오 동기화, 최종 MP4 렌더링, 품질 최적화를 제공합니다.
"""

__version__ = "1.0.0"
__author__ = "CaptionGen Team"
__description__ = "FFmpeg 기반 비디오 렌더링 및 품질 최적화 시스템"

from .renderer import FFmpegRenderer, RenderConfig
from .pipeline_manager import PipelineManager, PipelineConfig, PipelineResult

__all__ = [
    "FFmpegRenderer",
    "RenderConfig",
    "PipelineManager",
    "PipelineConfig",
    "PipelineResult"
]
