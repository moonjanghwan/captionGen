"""
개선된 이미지 렌더러

설정 기반 렌더링 엔진으로 고급 설정 관리 시스템을 통합한 렌더러입니다.
"""

import os
from typing import Dict, Any, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont
from ..settings.sync_manager import SettingSyncManager, SettingObserver
from ..settings.debugger import SettingDebugger
from ..settings.merger import SettingMerger
from ..settings.validator import SettingValidator
from ..settings.schemas import MergedSettings
from .png_renderer import PNGRenderer


class ImprovedImageRenderer(SettingObserver):
    """개선된 이미지 렌더러"""
    
    def __init__(self, settings_manager: SettingSyncManager, 
                 debug_log_file: str = "improved_renderer_debug.log"):
        self.settings_manager = settings_manager
        self.debugger = SettingDebugger(debug_log_file)
        self.merger = SettingMerger()
        self.validator = SettingValidator()
        
        # 기본 PNG 렌더러
        self.png_renderer: Optional[PNGRenderer] = None
        
        # 렌더링 통계
        self.render_stats = {
            'total_renders': 0,
            'successful_renders': 0,
            'failed_renders': 0,
            'render_times': []
        }
        
        # 설정 동기화 관리자에 등록
        self.settings_manager.register_observer(self)
        
        # 디버그 세션 시작
        self.current_session_id = self.debugger.start_debug_session("improved_renderer")
    
    def on_settings_changed(self, changes: Dict[str, Any]) -> None:
        """설정 변경 시 호출되는 메서드"""
        self.debugger.log_setting_application("settings_changed", changes)
        
        # PNG 렌더러 재초기화 (설정 변경으로 인한)
        if self.png_renderer:
            self._reinitialize_renderer()
    
    def on_setting_validated(self, validation_result: Dict[str, Any]) -> None:
        """설정 검증 완료 시 호출되는 메서드"""
        self.debugger.log_setting_validation(validation_result, {})
    
    def render_image(self, script_type: str, text_data: Dict[str, Any], 
                    output_path: str, resolution: Tuple[int, int]) -> bool:
        """
        개선된 이미지 렌더링
        
        Args:
            script_type: 스크립트 타입 (회화, 인트로, 엔딩, 썸네일)
            text_data: 렌더링할 텍스트 데이터
            output_path: 출력 파일 경로
            resolution: 해상도 (width, height)
            
        Returns:
            렌더링 성공 여부
        """
        import time
        start_time = time.time()
        
        try:
            self.debugger.log_rendering_step("start", script_type, text_data, output_path)
            
            # 1. 설정 로드 및 병합
            settings = self._load_and_merge_settings(script_type)
            self.debugger.log_setting_application("설정 로드", settings)
            
            # 2. 설정 검증
            validated_settings = self._validate_settings(settings)
            self.debugger.log_setting_application("설정 검증", validated_settings)
            
            # 3. 렌더링 컨텍스트 생성
            context = self._create_render_context(validated_settings, text_data, script_type)
            self.debugger.log_setting_application("렌더링 컨텍스트", context)
            
            # 4. 이미지 생성
            success = self._generate_image(context, output_path, resolution)
            
            # 5. 결과 검증
            if success:
                self._validate_output(output_path, validated_settings)
            
            # 렌더링 통계 업데이트
            render_time = time.time() - start_time
            self._update_render_stats(success, render_time)
            
            self.debugger.log_rendering_step("complete", script_type, 
                                           {'success': success, 'render_time': render_time}, output_path)
            
            return success
            
        except Exception as e:
            self.debugger.log_error(f"이미지 렌더링 실패: {str(e)}", {
                'script_type': script_type,
                'text_data': text_data,
                'output_path': output_path
            })
            
            # 렌더링 통계 업데이트
            render_time = time.time() - start_time
            self._update_render_stats(False, render_time)
            
            return False
    
    def _load_and_merge_settings(self, script_type: str) -> Dict[str, Any]:
        """설정 로드 및 병합"""
        try:
            # 공통 설정 로드
            common_settings = self.settings_manager.get_common_settings()
            
            # 스크립트별 설정 로드
            script_settings = self.settings_manager.get_script_settings(script_type)
            
            # 사용자 설정 로드
            user_settings = self.settings_manager.get_user_settings(script_type)
            
            # 설정 병합
            merged_settings = self.merger.merge_settings(
                common_settings, script_settings, user_settings
            )
            
            # 병합 결과 로깅
            self.debugger.log_setting_merge(
                common_settings, script_settings, user_settings, merged_settings
            )
            
            # 딕셔너리 형태로 변환
            return {
                'common': {
                    'bg': merged_settings.common.bg.__dict__,
                    'shadow': merged_settings.common.shadow.__dict__,
                    'border': merged_settings.common.border.__dict__
                },
                'tabs': {
                    script_type: {
                        '행수': merged_settings.script_types[script_type].row_count,
                        '비율': merged_settings.script_types[script_type].aspect_ratio,
                        '해상도': merged_settings.script_types[script_type].resolution,
                        'rows': [row.__dict__ for row in merged_settings.script_types[script_type].rows]
                    }
                }
            }
            
        except Exception as e:
            self.debugger.log_error(f"설정 로드/병합 실패: {e}")
            return {}
    
    def _validate_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """설정 검증"""
        try:
            validated = self.validator.validate_settings(settings)
            validation_result = self.validator.get_validation_report(settings)
            
            self.debugger.log_setting_validation(validation_result, settings)
            
            return validated
            
        except Exception as e:
            self.debugger.log_error(f"설정 검증 실패: {e}")
            return settings
    
    def _create_render_context(self, validated_settings: Dict[str, Any], 
                             text_data: Dict[str, Any], script_type: str) -> Dict[str, Any]:
        """렌더링 컨텍스트 생성"""
        return {
            'script_type': script_type,
            'settings': validated_settings,
            'text_data': text_data,
            'render_timestamp': self.debugger.current_settings.get('timestamp', ''),
            'session_id': self.current_session_id
        }
    
    def _generate_image(self, context: Dict[str, Any], output_path: str, 
                       resolution: Tuple[int, int]) -> bool:
        """이미지 생성"""
        try:
            script_type = context['script_type']
            settings = context['settings']
            text_data = context['text_data']
            
            # PNG 렌더러 초기화 (필요한 경우)
            if not self.png_renderer:
                self._initialize_renderer(settings)
            
            # 스크립트 타입별 렌더링
            if script_type == "회화":
                return self._render_conversation_image(text_data, output_path, resolution)
            elif script_type == "인트로":
                return self._render_intro_image(text_data, output_path, resolution)
            elif script_type == "엔딩":
                return self._render_ending_image(text_data, output_path, resolution)
            elif script_type == "썸네일":
                return self._render_thumbnail_image(text_data, output_path, resolution)
            else:
                self.debugger.log_error(f"지원하지 않는 스크립트 타입: {script_type}")
                return False
                
        except Exception as e:
            self.debugger.log_error(f"이미지 생성 실패: {e}")
            return False
    
    def _render_conversation_image(self, text_data: Dict[str, Any], 
                                 output_path: str, resolution: Tuple[int, int]) -> bool:
        """회화 이미지 렌더링"""
        if not self.png_renderer:
            return False
        
        return self.png_renderer.create_conversation_image(
            text_data, output_path, resolution, self.png_renderer.raw_settings
        )
    
    def _render_intro_image(self, text_data: Dict[str, Any], 
                          output_path: str, resolution: Tuple[int, int]) -> bool:
        """인트로 이미지 렌더링"""
        if not self.png_renderer:
            return False
        
        return self.png_renderer.create_intro_ending_image(
            text_data, output_path, resolution, "인트로"
        )
    
    def _render_ending_image(self, text_data: Dict[str, Any], 
                           output_path: str, resolution: Tuple[int, int]) -> bool:
        """엔딩 이미지 렌더링"""
        if not self.png_renderer:
            return False
        
        return self.png_renderer.create_intro_ending_image(
            text_data, output_path, resolution, "엔딩"
        )
    
    def _render_thumbnail_image(self, text_data: Dict[str, Any], 
                              output_path: str, resolution: Tuple[int, int]) -> bool:
        """썸네일 이미지 렌더링"""
        if not self.png_renderer:
            return False
        
        return self.png_renderer.create_thumbnail_image(
            text_data, output_path, resolution
        )
    
    def _validate_output(self, output_path: str, settings: Dict[str, Any]) -> bool:
        """출력 결과 검증"""
        try:
            if not os.path.exists(output_path):
                self.debugger.log_error(f"출력 파일이 생성되지 않았습니다: {output_path}")
                return False
            
            # 파일 크기 검증
            file_size = os.path.getsize(output_path)
            if file_size == 0:
                self.debugger.log_error(f"출력 파일이 비어있습니다: {output_path}")
                return False
            
            # 이미지 유효성 검증
            try:
                with Image.open(output_path) as img:
                    if img.size[0] == 0 or img.size[1] == 0:
                        self.debugger.log_error(f"이미지 크기가 유효하지 않습니다: {output_path}")
                        return False
            except Exception as e:
                self.debugger.log_error(f"이미지 파일이 손상되었습니다: {output_path}, 오류: {e}")
                return False
            
            self.debugger.log_rendering_step("output_validated", "", 
                                           {'file_size': file_size, 'path': output_path}, output_path)
            return True
            
        except Exception as e:
            self.debugger.log_error(f"출력 검증 실패: {e}")
            return False
    
    def _initialize_renderer(self, settings: Dict[str, Any]) -> None:
        """PNG 렌더러 초기화"""
        try:
            self.png_renderer = PNGRenderer(settings)
            self.debugger.log_setting_application("renderer_initialized", settings)
        except Exception as e:
            self.debugger.log_error(f"렌더러 초기화 실패: {e}")
    
    def _reinitialize_renderer(self) -> None:
        """PNG 렌더러 재초기화"""
        try:
            if self.png_renderer:
                current_settings = self.settings_manager.get_current_settings()
                self.png_renderer = PNGRenderer(current_settings)
                self.debugger.log_setting_application("renderer_reinitialized", current_settings)
        except Exception as e:
            self.debugger.log_error(f"렌더러 재초기화 실패: {e}")
    
    def _update_render_stats(self, success: bool, render_time: float) -> None:
        """렌더링 통계 업데이트"""
        self.render_stats['total_renders'] += 1
        
        if success:
            self.render_stats['successful_renders'] += 1
        else:
            self.render_stats['failed_renders'] += 1
        
        self.render_stats['render_times'].append(render_time)
        
        # 최근 100개 렌더링 시간만 유지
        if len(self.render_stats['render_times']) > 100:
            self.render_stats['render_times'] = self.render_stats['render_times'][-100:]
    
    def get_render_stats(self) -> Dict[str, Any]:
        """렌더링 통계 반환"""
        stats = self.render_stats.copy()
        
        if stats['render_times']:
            stats['average_render_time'] = sum(stats['render_times']) / len(stats['render_times'])
            stats['min_render_time'] = min(stats['render_times'])
            stats['max_render_time'] = max(stats['render_times'])
        else:
            stats['average_render_time'] = 0
            stats['min_render_time'] = 0
            stats['max_render_time'] = 0
        
        stats['success_rate'] = (
            stats['successful_renders'] / stats['total_renders'] * 100 
            if stats['total_renders'] > 0 else 0
        )
        
        return stats
    
    def generate_render_report(self) -> str:
        """렌더링 보고서 생성"""
        try:
            report = []
            report.append("=== 개선된 이미지 렌더러 보고서 ===")
            report.append(f"생성 시간: {self.debugger.current_settings.get('timestamp', 'N/A')}")
            report.append("")
            
            # 렌더링 통계
            stats = self.get_render_stats()
            report.append("렌더링 통계:")
            report.append(f"  - 총 렌더링: {stats['total_renders']}회")
            report.append(f"  - 성공: {stats['successful_renders']}회")
            report.append(f"  - 실패: {stats['failed_renders']}회")
            report.append(f"  - 성공률: {stats['success_rate']:.1f}%")
            report.append(f"  - 평균 렌더링 시간: {stats['average_render_time']:.3f}초")
            report.append(f"  - 최소 렌더링 시간: {stats['min_render_time']:.3f}초")
            report.append(f"  - 최대 렌더링 시간: {stats['max_render_time']:.3f}초")
            report.append("")
            
            # 디버그 정보
            debug_status = self.debugger.get_debug_status()
            report.append("디버그 상태:")
            report.append(f"  - 디버깅 활성화: {debug_status['enabled']}")
            report.append(f"  - 로그 파일: {debug_status['log_file']}")
            report.append(f"  - 세션 수: {debug_status['sessions_count']}")
            report.append("")
            
            # 설정 동기화 상태
            sync_status = self.settings_manager.get_sync_status()
            report.append("설정 동기화 상태:")
            report.append(f"  - 동기화 활성화: {sync_status['enabled']}")
            report.append(f"  - 관찰자 수: {sync_status['observers_count']}")
            report.append(f"  - 변경 히스토리: {sync_status['history_size']}개")
            
            return '\n'.join(report)
            
        except Exception as e:
            return f"보고서 생성 실패: {e}"
    
    def cleanup(self) -> None:
        """리소스 정리"""
        try:
            # 설정 동기화 관리자에서 해제
            self.settings_manager.unregister_observer(self)
            
            # 디버그 세션 종료
            if self.current_session_id:
                self.debugger.end_debug_session(self.current_session_id)
            
            # PNG 렌더러 정리
            self.png_renderer = None
            
        except Exception as e:
            self.debugger.log_error(f"리소스 정리 실패: {e}")
    
    def __del__(self):
        """소멸자"""
        self.cleanup()
