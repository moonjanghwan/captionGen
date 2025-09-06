"""
자막 이미지 생성 시스템

SSML mark 태그 기반으로 정확한 타이밍에 맞춰 PNG 시퀀스를 자동 생성합니다.
"""

__version__ = "1.0.0"
__author__ = "CaptionGen Team"
__description__ = "SSML 기반 자막 이미지 생성 및 PNG 시퀀스 시스템"

from .text_renderer import TextRenderer
from .generator import SubtitleGenerator, SubtitleFrame

__all__ = [
    "TextRenderer",
    "SubtitleGenerator",
    "SubtitleFrame"
]
