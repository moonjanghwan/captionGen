"""
스크립트 타입 관리자

각 스크립트 타입(conversation, intro, ending, dialogue)에 따른 처리를 통합 관리합니다.
하나의 변경으로 모든 스크립트 타입에 적용할 수 있는 구조를 제공합니다.
"""

from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum


class ScriptType(Enum):
    """스크립트 타입 열거형"""
    CONVERSATION = "conversation"
    INTRO = "intro"
    ENDING = "ending"
    DIALOGUE = "dialogue"
    THUMBNAIL = "thumbnail"


@dataclass
class ScriptTypeConfig:
    """스크립트 타입별 설정"""
    type: ScriptType
    ui_tab_name: str
    resolution: str
    aspect_ratio: str
    row_count: int
    default_font: str
    default_font_size: int
    default_color: str
    default_alignment: str
    default_effects: Dict[str, bool]
    row_configs: List[Dict[str, Any]]


class ScriptTypeManager:
    """스크립트 타입 관리 클래스"""
    
    def __init__(self):
        """스크립트 타입 관리자 초기화"""
        self.configs = self._initialize_script_configs()
    
    def _initialize_script_configs(self) -> Dict[ScriptType, ScriptTypeConfig]:
        """스크립트 타입별 설정 초기화"""
        configs = {}
        
        # 회화 설정
        configs[ScriptType.CONVERSATION] = ScriptTypeConfig(
            type=ScriptType.CONVERSATION,
            ui_tab_name="회화 설정",
            resolution="1920x1080",
            aspect_ratio="16:9",
            row_count=4,
            default_font="KoPubWorldDotum",
            default_font_size=100,
            default_color="#FFFFFF",
            default_alignment="Center",
            default_effects={"shadow": True, "border": True, "background": False},
            row_configs=[
                {
                    "name": "순번",
                    "x": 150, "y": 50, "w": 1820,
                    "font_size": 100, "color": "#FFFFFF",
                    "alignment": "Left", "vertical_alignment": "Top",
                    "effects": {"shadow": False, "border": True, "background": False}
                },
                {
                    "name": "원어",
                    "x": 50, "y": 150, "w": 1820,
                    "font_size": 120, "color": "#FFFFFF",
                    "alignment": "Center", "vertical_alignment": "Top",
                    "effects": {"shadow": True, "border": False, "background": False}
                },
                {
                    "name": "학습어",
                    "x": 50, "y": 450, "w": 1820,
                    "font_size": 120, "color": "#FF00FF",
                    "alignment": "Center", "vertical_alignment": "Top",
                    "effects": {"shadow": True, "border": True, "background": False}
                },
                {
                    "name": "읽기",
                    "x": 50, "y": 750, "w": 1820,
                    "font_size": 100, "color": "#FFFF00",
                    "alignment": "Center", "vertical_alignment": "Top",
                    "effects": {"shadow": False, "border": True, "background": True}
                }
            ]
        )
        
        # 썸네일 설정
        configs[ScriptType.THUMBNAIL] = ScriptTypeConfig(
            type=ScriptType.THUMBNAIL,
            ui_tab_name="썸네일 설정",
            resolution="1024x768",
            aspect_ratio="16:9",
            row_count=4,
            default_font="Noto Sans KR",
            default_font_size=100,
            default_color="#FFFFFF",
            default_alignment="Center",
            default_effects={"shadow": True, "border": True, "background": False},
            row_configs=[
                {
                    "name": "1행",
                    "x": 30, "y": 50, "w": 964,
                    "font_size": 100, "color": "#FFFFFF",
                    "alignment": "Center", "vertical_alignment": "Top",
                    "effects": {"shadow": True, "border": True, "background": False}
                },
                {
                    "name": "2행",
                    "x": 30, "y": 230, "w": 964,
                    "font_size": 100, "color": "#00FFFF",
                    "alignment": "Center", "vertical_alignment": "Top",
                    "effects": {"shadow": True, "border": True, "background": False}
                },
                {
                    "name": "3행",
                    "x": 30, "y": 410, "w": 964,
                    "font_size": 100, "color": "#FF00FF",
                    "alignment": "Center", "vertical_alignment": "Top",
                    "effects": {"shadow": True, "border": True, "background": False}
                },
                {
                    "name": "4행",
                    "x": 30, "y": 590, "w": 964,
                    "font_size": 100, "color": "#FFFF00",
                    "alignment": "Center", "vertical_alignment": "Top",
                    "effects": {"shadow": True, "border": True, "background": False}
                }
            ]
        )
        
        # 인트로 설정
        configs[ScriptType.INTRO] = ScriptTypeConfig(
            type=ScriptType.INTRO,
            ui_tab_name="인트로 설정",
            resolution="1920x1080",
            aspect_ratio="16:9",
            row_count=1,
            default_font="KoPubWorldDotum",
            default_font_size=90,
            default_color="#FFFFFF",
            default_alignment="Center",
            default_effects={"shadow": True, "border": True, "background": True},
            row_configs=[
                {
                    "name": "1행",
                    "x": 50, "y": 1000, "w": 1820,
                    "font_size": 90, "color": "#FFFFFF",
                    "alignment": "Center", "vertical_alignment": "Bottom",
                    "effects": {"shadow": True, "border": True, "background": True}
                }
            ]
        )
        
        # 엔딩 설정
        configs[ScriptType.ENDING] = ScriptTypeConfig(
            type=ScriptType.ENDING,
            ui_tab_name="엔딩 설정",
            resolution="1920x1080",
            aspect_ratio="16:9",
            row_count=1,
            default_font="KoPubWorldDotum",
            default_font_size=100,
            default_color="#FFFFFF",
            default_alignment="Center",
            default_effects={"shadow": True, "border": True, "background": True},
            row_configs=[
                {
                    "name": "1행",
                    "x": 50, "y": 50, "w": 1820,
                    "font_size": 100, "color": "#FFFFFF",
                    "alignment": "Center", "vertical_alignment": "Middle",
                    "effects": {"shadow": True, "border": True, "background": True}
                }
            ]
        )
        
        # 대화 설정
        configs[ScriptType.DIALOGUE] = ScriptTypeConfig(
            type=ScriptType.DIALOGUE,
            ui_tab_name="대화 설정",
            resolution="1920x1080",
            aspect_ratio="16:9",
            row_count=3,
            default_font="KoPubWorldDotum",
            default_font_size=100,
            default_color="#FFFFFF",
            default_alignment="Left",
            default_effects={"shadow": False, "border": False, "background": False},
            row_configs=[
                {
                    "name": "원어",
                    "x": 50, "y": 250, "w": 1820,
                    "font_size": 100, "color": "#FFFFFF",
                    "alignment": "Left", "vertical_alignment": "Top",
                    "effects": {"shadow": False, "border": False, "background": False}
                },
                {
                    "name": "학습어1",
                    "x": 50, "y": 550, "w": 1820,
                    "font_size": 100, "color": "#FFFFFF",
                    "alignment": "Left", "vertical_alignment": "Top",
                    "effects": {"shadow": False, "border": False, "background": False}
                },
                {
                    "name": "학습어2",
                    "x": 50, "y": 850, "w": 1820,
                    "font_size": 100, "color": "#FFFFFF",
                    "alignment": "Left", "vertical_alignment": "Top",
                    "effects": {"shadow": False, "border": False, "background": False}
                }
            ]
        )
        
        return configs
    
    def get_config(self, script_type: Union[ScriptType, str]) -> Optional[ScriptTypeConfig]:
        """스크립트 타입별 설정 반환"""
        if isinstance(script_type, str):
            try:
                script_type = ScriptType(script_type)
            except ValueError:
                return None
        
        return self.configs.get(script_type)
    
    def get_all_configs(self) -> Dict[ScriptType, ScriptTypeConfig]:
        """모든 스크립트 타입 설정 반환"""
        return self.configs
    
    def update_config(self, script_type: Union[ScriptType, str], 
                     updates: Dict[str, Any]) -> bool:
        """스크립트 타입 설정 업데이트"""
        config = self.get_config(script_type)
        if not config:
            return False
        
        try:
            for key, value in updates.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            return True
        except Exception:
            return False
    
    def get_ui_settings_format(self, script_type: Union[ScriptType, str]) -> Dict[str, Any]:
        """UI 설정 형식으로 변환"""
        config = self.get_config(script_type)
        if not config:
            return {}
        
        return {
            "행수": str(config.row_count),
            "비율": config.aspect_ratio,
            "해상도": config.resolution,
            "rows": [
                {
                    "행": row["name"],
                    "x": str(row["x"]),
                    "y": str(row["y"]),
                    "w": str(row["w"]),
                    "크기(pt)": str(row["font_size"]),
                    "폰트(pt)": config.default_font,
                    "색상": row["color"],
                    "굵기": "Bold",
                    "좌우 정렬": row["alignment"],
                    "상하 정렬": row["vertical_alignment"],
                    "바탕": str(row["effects"]["background"]),
                    "쉐도우": str(row["effects"]["shadow"]),
                    "외곽선": str(row["effects"]["border"])
                }
                for row in config.row_configs
            ]
        }
    
    def apply_global_changes(self, changes: Dict[str, Any]) -> bool:
        """모든 스크립트 타입에 전역 변경사항 적용"""
        try:
            for script_type, config in self.configs.items():
                if "default_font" in changes:
                    config.default_font = changes["default_font"]
                if "default_font_size" in changes:
                    config.default_font_size = changes["default_font_size"]
                if "default_color" in changes:
                    config.default_color = changes["default_color"]
                if "default_alignment" in changes:
                    config.default_alignment = changes["default_alignment"]
                if "default_effects" in changes:
                    config.default_effects.update(changes["default_effects"])
                
                # 행별 설정에도 적용
                for row_config in config.row_configs:
                    if "font_size" in changes:
                        row_config["font_size"] = changes["font_size"]
                    if "color" in changes:
                        row_config["color"] = changes["color"]
                    if "alignment" in changes:
                        row_config["alignment"] = changes["alignment"]
                    if "effects" in changes:
                        row_config["effects"].update(changes["effects"])
            
            return True
        except Exception:
            return False
    
    def get_script_type_by_ui_tab(self, ui_tab_name: str) -> Optional[ScriptType]:
        """UI 탭 이름으로 스크립트 타입 찾기"""
        for script_type, config in self.configs.items():
            if config.ui_tab_name == ui_tab_name:
                return script_type
        return None
    
    def validate_script_data(self, script_type: Union[ScriptType, str], 
                           script_data: Dict[str, Any]) -> Dict[str, Any]:
        """스크립트 데이터 검증 및 정규화"""
        config = self.get_config(script_type)
        if not config:
            return {"valid": False, "error": "Unknown script type"}
        
        validation_result = {"valid": True, "errors": [], "warnings": []}
        
        if script_type == ScriptType.CONVERSATION:
            # 회화 데이터 검증
            if "conversations" not in script_data:
                validation_result["errors"].append("conversations 필드가 필요합니다")
            
            for i, conv in enumerate(script_data.get("conversations", [])):
                required_fields = ["native", "learning", "reading"]
                for field in required_fields:
                    if not conv.get(field):
                        validation_result["warnings"].append(f"conversation {i+1}: {field} 필드가 비어있습니다")
        
        elif script_type in [ScriptType.INTRO, ScriptType.ENDING]:
            # 인트로/엔딩 데이터 검증
            text_field = f"{script_type.value}_text"
            if not script_data.get(text_field):
                validation_result["warnings"].append(f"{text_field} 필드가 비어있습니다")
        
        elif script_type == ScriptType.DIALOGUE:
            # 대화 데이터 검증
            if "dialogue" not in script_data:
                validation_result["errors"].append("dialogue 필드가 필요합니다")
        
        if validation_result["errors"]:
            validation_result["valid"] = False
        
        return validation_result
