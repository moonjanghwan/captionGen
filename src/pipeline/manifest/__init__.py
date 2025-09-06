"""
Manifest 파싱/검증 모듈

이 모듈은 비디오 제작을 위한 Manifest 파일을 파싱하고 검증하는 기능을 제공합니다.
"""

from .models import (
    Manifest,
    Scene,
    DialogueLine,
    ConversationScene,
    IntroEndingScene,
    DialogueScene
)

from .parser import ManifestParser
from .validator import ManifestValidator, ValidationResult, ValidationError
from .generator import ManifestGenerator

__all__ = [
    # Models
    'Manifest',
    'Scene', 
    'DialogueLine',
    'ConversationScene',
    'IntroEndingScene',
    'DialogueScene',
    
    # Parser
    'ManifestParser',
    
    # Validator
    'ManifestValidator',
    'ValidationResult',
    'ValidationError',
    
    # Generator
    'ManifestGenerator'
]

# 버전 정보
__version__ = "1.0.0"
__author__ = "CaptionGen Team"
__description__ = "Manifest 파싱/검증 시스템"
