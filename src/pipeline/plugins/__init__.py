"""
플러그인 시스템

스크립트 타입별 처리 로직을 플러그인으로 분리하여 확장성과 유지보수성을 향상시킵니다.
"""

__version__ = "1.0.0"
__author__ = "CaptionGen Team"
__description__ = "스크립트 타입별 플러그인 시스템"

# 플러그인 베이스 클래스
from .base_plugin import BasePlugin, PluginResult, PluginConfig

# 플러그인 관리자
from .plugin_manager import PluginManager

# 구체적인 플러그인들
from .intro_plugin import IntroPlugin
from .conversation_plugin import ConversationPlugin
from .ending_plugin import EndingPlugin

__all__ = [
    # 베이스 클래스
    "BasePlugin",
    "PluginResult", 
    "PluginConfig",
    
    # 플러그인 관리자
    "PluginManager",
    
    # 구체적인 플러그인들
    "IntroPlugin",
    "ConversationPlugin", 
    "EndingPlugin"
]
