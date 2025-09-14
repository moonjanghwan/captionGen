"""
설정 검증 및 정규화 시스템

UI에서 전달받은 설정 값들을 검증하고 정규화합니다.
"""

import re
import os
from typing import Dict, Any, List, Optional, Tuple
from .schemas import (
    BackgroundSettings, ShadowSettings, BorderSettings, 
    RowSettings, ScriptTypeSettings, CommonSettings, ImageGenerationSettings
)


class SettingValidator:
    """설정 검증 및 정규화 클래스"""
    
    def __init__(self):
        self.color_pattern = re.compile(r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$')
        self.resolution_pattern = re.compile(r'^\d+x\d+$')
        self.aspect_ratio_pattern = re.compile(r'^\d+:\d+$')
    
    def validate_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """설정 값 검증 및 정규화"""
        validated = {}
        
        # 공통 설정 검증
        if 'common' in settings:
            validated['common'] = self.validate_common_settings(settings['common'])
        
        # 스크립트 타입별 설정 검증
        if 'tabs' in settings:
            validated['tabs'] = self.validate_script_types(settings['tabs'])
        
        return validated
    
    def validate_common_settings(self, common_settings: Dict[str, Any]) -> Dict[str, Any]:
        """공통 설정 검증"""
        validated = {}
        
        # 배경 설정 검증
        if 'bg' in common_settings:
            validated['bg'] = self.validate_background(common_settings['bg'])
        
        # 쉐도우 설정 검증
        if 'shadow' in common_settings:
            validated['shadow'] = self.validate_shadow(common_settings['shadow'])
        
        # 외곽선 설정 검증
        if 'border' in common_settings:
            validated['border'] = self.validate_border(common_settings['border'])
        
        return validated
    
    def validate_background(self, bg_settings: Dict[str, Any]) -> Dict[str, Any]:
        """배경 설정 검증"""
        validated = {
            'enabled': bool(bg_settings.get('enabled', True)),
            'color': self.validate_color(bg_settings.get('color', '#000000')),
            'alpha': max(0.0, min(1.0, float(bg_settings.get('alpha', 0.2)))),
            'margin': max(0, int(bg_settings.get('margin', 2))),
            'type': str(bg_settings.get('type', '이미지')),
            'value': str(bg_settings.get('value', ''))
        }
        
        # 이미지 파일 경로 검증
        if validated['type'] == '이미지' and validated['value']:
            if not os.path.exists(validated['value']):
                print(f"⚠️ 배경 이미지 파일을 찾을 수 없습니다: {validated['value']}")
                validated['value'] = ""
        
        return validated
    
    def validate_shadow(self, shadow_settings: Dict[str, Any]) -> Dict[str, Any]:
        """그림자 설정 검증"""
        validated = {
            'enabled': bool(shadow_settings.get('enabled', True)),
            'thick': max(0, int(shadow_settings.get('thick', 4))),
            'color': self.validate_color(shadow_settings.get('color', '#000000')),
            'blur': max(0, int(shadow_settings.get('blur', 4))),
            'offx': int(shadow_settings.get('offx', 3)),
            'offy': int(shadow_settings.get('offy', 3)),
            'alpha': max(0.0, min(1.0, float(shadow_settings.get('alpha', 1.0)))),
            'useBlur': bool(shadow_settings.get('useBlur', True))
        }
        return validated
    
    def validate_border(self, border_settings: Dict[str, Any]) -> Dict[str, Any]:
        """외곽선 설정 검증"""
        validated = {
            'enabled': bool(border_settings.get('enabled', True)),
            'thick': max(0, int(border_settings.get('thick', 4))),
            'color': self.validate_color(border_settings.get('color', '#000000'))
        }
        return validated
    
    def validate_script_types(self, tabs_settings: Dict[str, Any]) -> Dict[str, Any]:
        """스크립트 타입별 설정 검증"""
        validated = {}
        
        for tab_name, tab_data in tabs_settings.items():
            validated[tab_name] = self.validate_script_type(tab_name, tab_data)
        
        return validated
    
    def validate_script_type(self, tab_name: str, tab_data: Dict[str, Any]) -> Dict[str, Any]:
        """개별 스크립트 타입 설정 검증"""
        validated = {
            '행수': max(1, int(tab_data.get('행수', 1))),
            '비율': self.validate_aspect_ratio(tab_data.get('비율', '16:9')),
            '해상도': self.validate_resolution(tab_data.get('해상도', '1920x1080')),
            'rows': []
        }
        
        # 행 설정 검증
        rows_data = tab_data.get('rows', [])
        for i, row_data in enumerate(rows_data):
            validated['rows'].append(self.validate_row_settings(row_data))
        
        # 행 수에 맞게 기본 행 추가
        while len(validated['rows']) < validated['행수']:
            validated['rows'].append(self.get_default_row_settings())
        
        return validated
    
    def validate_row_settings(self, row_data: Dict[str, Any]) -> Dict[str, Any]:
        """행 설정 검증"""
        validated = {
            '행': str(row_data.get('행', '')),
            'x': max(0, int(row_data.get('x', 0))),
            'y': max(0, int(row_data.get('y', 0))),
            'w': max(1, int(row_data.get('w', 100))),
            '크기(pt)': max(8, int(row_data.get('크기(pt)', 24))),
            '폰트(pt)': str(row_data.get('폰트(pt)', 'Noto Sans KR')),
            '색상': self.validate_color(row_data.get('색상', '#FFFFFF')),
            '굵기': str(row_data.get('굵기', 'Bold')),  # 문자열로 유지
            '좌우 정렬': self.validate_h_align(row_data.get('좌우 정렬', 'center')),
            '상하 정렬': self.validate_v_align(row_data.get('상하 정렬', 'center')),
            '바탕': str(row_data.get('바탕', 'False')),  # 문자열로 유지
            '쉐도우': str(row_data.get('쉐도우', 'False')),  # 문자열로 유지
            '외곽선': str(row_data.get('외곽선', 'False'))  # 문자열로 유지
        }
        return validated
    
    def validate_color(self, color: str) -> str:
        """색상 값 검증"""
        if not color:
            return '#000000'
        
        if not color.startswith('#'):
            color = '#' + color
        
        if len(color) == 4:  # #RGB -> #RRGGBB
            color = f"#{color[1]}{color[1]}{color[2]}{color[2]}{color[3]}{color[3]}"
        
        if not self.color_pattern.match(color):
            return '#000000'
        
        return color.upper()
    
    def validate_resolution(self, resolution: str) -> str:
        """해상도 값 검증"""
        if not resolution:
            return '1920x1080'
        
        if not self.resolution_pattern.match(resolution):
            return '1920x1080'
        
        # 해상도 값 범위 검증
        try:
            width, height = map(int, resolution.split('x'))
            if width < 100 or height < 100 or width > 7680 or height > 4320:
                return '1920x1080'
        except ValueError:
            return '1920x1080'
        
        return resolution
    
    def validate_aspect_ratio(self, aspect_ratio: str) -> str:
        """화면 비율 값 검증"""
        if not aspect_ratio:
            return '16:9'
        
        if not self.aspect_ratio_pattern.match(aspect_ratio):
            return '16:9'
        
        # 일반적인 화면 비율 검증
        valid_ratios = ['16:9', '4:3', '21:9', '1:1', '3:2', '5:4']
        if aspect_ratio not in valid_ratios:
            return '16:9'
        
        return aspect_ratio
    
    def validate_h_align(self, align: str) -> str:
        """좌우 정렬 값 검증"""
        align_lower = align.lower()
        valid_aligns = ['left', 'center', 'right']
        return align_lower if align_lower in valid_aligns else 'center'
    
    def validate_v_align(self, align: str) -> str:
        """상하 정렬 값 검증"""
        align_lower = align.lower()
        valid_aligns = ['top', 'center', 'bottom']
        return align_lower if align_lower in valid_aligns else 'center'
    
    def get_default_row_settings(self) -> Dict[str, Any]:
        """기본 행 설정 반환"""
        return {
            '행': '',
            'x': 0,
            'y': 0,
            'w': 100,
            '크기(pt)': 24,
            '폰트(pt)': 'Noto Sans KR',
            '색상': '#FFFFFF',
            '굵기': False,
            '좌우 정렬': 'center',
            '상하 정렬': 'center',
            '바탕': False,
            '쉐도우': False,
            '외곽선': False
        }
    
    def validate_font_path(self, font_name: str) -> Optional[str]:
        """폰트 경로 검증"""
        font_paths = {
            "Noto Sans KR": "~/Library/Fonts/NotoSansKR-Regular.ttf",
            "KoPubWorld돋움체": "~/Library/Fonts/KoPubWorld Dotum Medium.ttf",
            "KoPubWorld바탕체": "~/Library/Fonts/KoPubWorld Batang Medium.ttf",
            "Arial": "~/Library/Fonts/Arial.ttf",
            "Times New Roman": "~/Library/Fonts/Times New Roman.ttf"
        }
        
        font_path = font_paths.get(font_name)
        if font_path:
            expanded_path = os.path.expanduser(font_path)
            if os.path.exists(expanded_path):
                return expanded_path
        
        return None
    
    def get_validation_report(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """설정 검증 보고서 생성"""
        report = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'validated_settings': {}
        }
        
        try:
            validated = self.validate_settings(settings)
            report['validated_settings'] = validated
        except Exception as e:
            report['valid'] = False
            report['errors'].append(f"설정 검증 실패: {e}")
        
        return report
