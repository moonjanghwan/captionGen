"""
계층적 설정 관리 시스템

공통 설정, 스크립트별 설정, 사용자 설정을 계층적으로 병합합니다.
"""

from typing import Dict, Any, List, Optional
from .schemas import (
    BackgroundSettings, ShadowSettings, BorderSettings, RowSettings,
    ScriptTypeSettings, CommonSettings, ImageGenerationSettings, MergedSettings
)
from .validator import SettingValidator


class SettingMerger:
    """설정 병합 클래스"""
    
    def __init__(self):
        self.validator = SettingValidator()
    
    def merge_settings(self, common_settings: Dict[str, Any], 
                      script_settings: Dict[str, Any], 
                      user_settings: Dict[str, Any]) -> MergedSettings:
        """
        설정 병합 로직
        
        우선순위 (높음 → 낮음):
        1. 사용자 직접 설정 (UI에서 변경한 값)
        2. 스크립트별 기본 설정
        3. 공통 기본 설정
        4. 시스템 기본값
        """
        # 1단계: 공통 기본 설정 적용
        merged_common = self._merge_common_settings(common_settings)
        
        # 2단계: 스크립트별 설정 적용 (공통 설정 덮어쓰기)
        merged_script_types = self._merge_script_type_settings(script_settings)
        
        # 3단계: 사용자 설정 적용 (최고 우선순위)
        final_settings = self._apply_user_settings(
            merged_common, merged_script_types, user_settings
        )
        
        # 4단계: 설정 검증 및 정규화
        validated_settings = self.validator.validate_settings(final_settings)
        
        # 5단계: MergedSettings 객체 생성
        return self._create_merged_settings(validated_settings)
    
    def _merge_common_settings(self, common_settings: Dict[str, Any]) -> Dict[str, Any]:
        """공통 설정 병합"""
        default_common = {
            'bg': {
                'enabled': True,
                'color': '#000000',
                'alpha': 0.2,
                'margin': 2,
                'type': '이미지',
                'value': ''
            },
            'shadow': {
                'enabled': True,
                'thick': 4,
                'color': '#000000',
                'blur': 4,
                'offx': 3,
                'offy': 3,
                'alpha': 1.0,
                'useBlur': True
            },
            'border': {
                'enabled': True,
                'thick': 4,
                'color': '#000000'
            }
        }
        
        return self._deep_merge(default_common, common_settings)
    
    def _merge_script_type_settings(self, script_settings: Dict[str, Any]) -> Dict[str, Any]:
        """스크립트 타입별 설정 병합"""
        # UI 설정을 그대로 사용 (기본 설정과 병합하지 않음)
        return script_settings
    
    def _apply_user_settings(self, common_settings: Dict[str, Any], 
                           script_settings: Dict[str, Any], 
                           user_settings: Dict[str, Any]) -> Dict[str, Any]:
        """사용자 설정 적용 (최고 우선순위)"""
        final_settings = {
            'common': self._deep_merge(common_settings, user_settings.get('common', {})),
            'tabs': self._deep_merge(script_settings, user_settings.get('tabs', {}))
        }
        
        return final_settings
    
    def _create_merged_settings(self, validated_settings: Dict[str, Any]) -> MergedSettings:
        """MergedSettings 객체 생성"""
        # 공통 설정 변환
        common = CommonSettings(
            bg=BackgroundSettings(**validated_settings['common']['bg']),
            shadow=ShadowSettings(**validated_settings['common']['shadow']),
            border=BorderSettings(**validated_settings['common']['border'])
        )
        
        # 스크립트 타입별 설정 변환
        script_types = {}
        for tab_name, tab_data in validated_settings['tabs'].items():
            rows = []
            for row_data in tab_data['rows']:
                # UI 키를 RowSettings 매개변수로 변환
                converted_row_data = {
                    'row_name': row_data.get('행', ''),
                    'x': int(row_data.get('x', 0)),
                    'y': int(row_data.get('y', 0)),
                    'w': int(row_data.get('w', 100)),
                    'font_size': int(row_data.get('크기(pt)', 24)),
                    'font_name': row_data.get('폰트(pt)', 'KoPubWorldDotum'),
                    'color': row_data.get('색상', '#FFFFFF'),
                    'bold': row_data.get('굵기', 'Bold') == 'Bold',
                    'h_align': row_data.get('좌우 정렬', 'Center').lower(),
                    'v_align': row_data.get('상하 정렬', 'Top').lower(),
                    'background': row_data.get('바탕', 'False') == 'True',
                    'shadow': row_data.get('쉐도우', 'False') == 'True',
                    'border': row_data.get('외곽선', 'False') == 'True'
                }
                
                rows.append(RowSettings(**converted_row_data))
            
            script_types[tab_name] = ScriptTypeSettings(
                row_count=tab_data['행수'],
                aspect_ratio=tab_data['비율'],
                resolution=tab_data['해상도'],
                rows=rows
            )
        
        return MergedSettings(
            common=common,
            script_types=script_types,
            source_info={'merged_at': 'runtime'}
        )
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """딕셔너리 깊은 병합"""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _get_default_script_type_settings(self) -> Dict[str, Dict[str, Any]]:
        """기본 스크립트 타입 설정 반환"""
        return {
            '회화 설정': {
                '행수': 4,
                '비율': '16:9',
                '해상도': '1920x1080',
                'rows': [
                    {
                        '행': '순번',
                        'x': 100, 'y': 200, 'w': 100,
                        '크기(pt)': 60, '폰트(pt)': 'Noto Sans KR',
                        '색상': '#FFFFFF', '굵기': True,
                        '좌우 정렬': 'center', '상하 정렬': 'center',
                        '바탕': False, '쉐도우': True, '외곽선': True
                    },
                    {
                        '행': '원어',
                        'x': 100, 'y': 400, 'w': 1800,
                        '크기(pt)': 80, '폰트(pt)': 'Noto Sans KR',
                        '색상': '#FFFFFF', '굵기': False,
                        '좌우 정렬': 'center', '상하 정렬': 'center',
                        '바탕': False, '쉐도우': True, '외곽선': True
                    },
                    {
                        '행': '학습어',
                        'x': 100, 'y': 600, 'w': 1800,
                        '크기(pt)': 80, '폰트(pt)': 'Noto Sans KR',
                        '색상': '#FFFF00', '굵기': False,
                        '좌우 정렬': 'center', '상하 정렬': 'center',
                        '바탕': False, '쉐도우': True, '외곽선': True
                    },
                    {
                        '행': '읽기',
                        'x': 100, 'y': 800, 'w': 1800,
                        '크기(pt)': 60, '폰트(pt)': 'Noto Sans KR',
                        '색상': '#00FF00', '굵기': False,
                        '좌우 정렬': 'center', '상하 정렬': 'center',
                        '바탕': False, '쉐도우': True, '외곽선': True
                    }
                ]
            },
            '인트로 설정': {
                '행수': 1,
                '비율': '16:9',
                '해상도': '1920x1080',
                'rows': [
                    {
                        '행': '1행',
                        'x': 100, 'y': 500, 'w': 1820,
                        '크기(pt)': 80, '폰트(pt)': 'Noto Sans KR',
                        '색상': '#FFFFFF', '굵기': False,
                        '좌우 정렬': 'center', '상하 정렬': 'center',
                        '바탕': False, '쉐도우': True, '외곽선': True
                    }
                ]
            },
            '엔딩 설정': {
                '행수': 1,
                '비율': '16:9',
                '해상도': '1920x1080',
                'rows': [
                    {
                        '행': '1행',
                        'x': 100, 'y': 1000, 'w': 1820,
                        '크기(pt)': 90, '폰트(pt)': 'Noto Sans KR',
                        '색상': '#FFFFFF', '굵기': False,
                        '좌우 정렬': 'center', '상하 정렬': 'center',
                        '바탕': False, '쉐도우': True, '외곽선': True
                    }
                ]
            },
            '썸네일 설정': {
                '행수': 4,
                '비율': '16:9',
                '해상도': '1920x1080',
                'rows': [
                    {
                        '행': '1행',
                        'x': 100, 'y': 200, 'w': 1800,
                        '크기(pt)': 60, '폰트(pt)': 'Noto Sans KR',
                        '색상': '#FFFFFF', '굵기': True,
                        '좌우 정렬': 'center', '상하 정렬': 'center',
                        '바탕': False, '쉐도우': True, '외곽선': True
                    },
                    {
                        '행': '2행',
                        'x': 100, 'y': 400, 'w': 1800,
                        '크기(pt)': 60, '폰트(pt)': 'Noto Sans KR',
                        '색상': '#FFFFFF', '굵기': True,
                        '좌우 정렬': 'center', '상하 정렬': 'center',
                        '바탕': False, '쉐도우': True, '외곽선': True
                    },
                    {
                        '행': '3행',
                        'x': 100, 'y': 600, 'w': 1800,
                        '크기(pt)': 60, '폰트(pt)': 'Noto Sans KR',
                        '색상': '#FFFFFF', '굵기': True,
                        '좌우 정렬': 'center', '상하 정렬': 'center',
                        '바탕': False, '쉐도우': True, '외곽선': True
                    },
                    {
                        '행': '4행',
                        'x': 100, 'y': 800, 'w': 1800,
                        '크기(pt)': 60, '폰트(pt)': 'Noto Sans KR',
                        '색상': '#FFFFFF', '굵기': True,
                        '좌우 정렬': 'center', '상하 정렬': 'center',
                        '바탕': False, '쉐도우': True, '외곽선': True
                    }
                ]
            }
        }
    
    def get_merge_report(self, common_settings: Dict[str, Any], 
                        script_settings: Dict[str, Any], 
                        user_settings: Dict[str, Any]) -> Dict[str, Any]:
        """설정 병합 보고서 생성"""
        report = {
            'merge_success': True,
            'merged_settings': None,
            'conflicts': [],
            'warnings': [],
            'source_tracking': {}
        }
        
        try:
            merged = self.merge_settings(common_settings, script_settings, user_settings)
            report['merged_settings'] = merged
            report['source_tracking'] = merged.source_info
        except Exception as e:
            report['merge_success'] = False
            report['warnings'].append(f"설정 병합 실패: {e}")
        
        return report
