"""
오디오 생성 시스템

사양서에 따른 SSML 기반 TTS 및 오디오 세그먼트 분석을 제공합니다.
"""

__version__ = "1.0.0"
__author__ = "CaptionGen Team"
__description__ = "SSML 기반 오디오 생성 및 타이밍 분석 시스템"

from .ssml_builder import SSMLBuilder
from .generator import AudioGenerator
from .segmenter import AudioSegmenter, AudioSegment

__all__ = [
    "SSMLBuilder",
    "AudioGenerator", 
    "AudioSegmenter",
    "AudioSegment"
]
