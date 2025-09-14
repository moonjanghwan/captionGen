"""
타입 안전 설정 스키마

UI 설정을 타입 안전하게 관리하기 위한 dataclass 기반 스키마를 정의합니다.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class BackgroundSettings:
    """배경 설정"""
    enabled: bool = True
    color: str = "#000000"
    alpha: float = 0.2
    margin: int = 2
    type: str = "이미지"
    value: str = ""


@dataclass
class ShadowSettings:
    """그림자 설정"""
    enabled: bool = True
    thick: int = 4
    color: str = "#000000"
    blur: int = 4
    offx: int = 3
    offy: int = 3
    alpha: float = 1.0
    useBlur: bool = True


@dataclass
class BorderSettings:
    """외곽선 설정"""
    enabled: bool = True
    thick: int = 4
    color: str = "#000000"


@dataclass
class RowSettings:
    """행 설정"""
    row_name: str = ""
    x: int = 0
    y: int = 0
    w: int = 100
    font_size: int = 24
    font_name: str = "Noto Sans KR"
    color: str = "#FFFFFF"
    bold: bool = False
    h_align: str = "center"  # left, center, right
    v_align: str = "center"  # top, center, bottom
    background: bool = False
    shadow: bool = False
    border: bool = False


@dataclass
class ScriptTypeSettings:
    """스크립트 타입별 설정"""
    row_count: int = 1
    aspect_ratio: str = "16:9"
    resolution: str = "1920x1080"
    rows: List[RowSettings] = field(default_factory=list)


@dataclass
class CommonSettings:
    """공통 설정"""
    bg: BackgroundSettings = field(default_factory=BackgroundSettings)
    shadow: ShadowSettings = field(default_factory=ShadowSettings)
    border: BorderSettings = field(default_factory=BorderSettings)


@dataclass
class ImageGenerationSettings:
    """이미지 생성 설정"""
    common: CommonSettings = field(default_factory=CommonSettings)
    script_types: Dict[str, ScriptTypeSettings] = field(default_factory=dict)
    
    def get_script_type_settings(self, script_type: str) -> Optional[ScriptTypeSettings]:
        """스크립트 타입별 설정 가져오기"""
        return self.script_types.get(script_type)
    
    def set_script_type_settings(self, script_type: str, settings: ScriptTypeSettings):
        """스크립트 타입별 설정 설정하기"""
        self.script_types[script_type] = settings
    
    def get_row_settings(self, script_type: str, row_index: int) -> Optional[RowSettings]:
        """특정 행 설정 가져오기"""
        script_settings = self.get_script_type_settings(script_type)
        if script_settings and 0 <= row_index < len(script_settings.rows):
            return script_settings.rows[row_index]
        return None
    
    def set_row_settings(self, script_type: str, row_index: int, settings: RowSettings):
        """특정 행 설정 설정하기"""
        script_settings = self.get_script_type_settings(script_type)
        if script_settings:
            while len(script_settings.rows) <= row_index:
                script_settings.rows.append(RowSettings(row_name=f"행{len(script_settings.rows)+1}"))
            script_settings.rows[row_index] = settings


@dataclass
class MergedSettings:
    """병합된 최종 설정"""
    common: CommonSettings
    script_types: Dict[str, ScriptTypeSettings]
    source_info: Dict[str, str] = field(default_factory=dict)  # 설정 출처 추적
    
    def get_effective_settings(self, script_type: str, row_index: int) -> Optional[RowSettings]:
        """효과적인 설정 가져오기 (병합된 결과)"""
        return self.script_types.get(script_type, ScriptTypeSettings()).rows[row_index] if row_index < len(self.script_types.get(script_type, ScriptTypeSettings()).rows) else None
