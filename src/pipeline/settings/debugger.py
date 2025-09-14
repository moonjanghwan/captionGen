"""
디버깅 및 로깅 시스템

설정 적용 과정을 추적하고 디버깅 정보를 제공하는 시스템입니다.
"""

import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from .schemas import MergedSettings


class SettingDebugger:
    """설정 디버깅 및 로깅 클래스"""
    
    def __init__(self, log_file: str = "setting_debug.log", enabled: bool = True):
        self.log_file = log_file
        self.enabled = enabled
        self.current_settings: Dict[str, Any] = {}
        self.debug_sessions: List[Dict[str, Any]] = []
        self.max_sessions = 50
        
        # 로그 디렉토리 생성
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
    
    def log_setting_application(self, step: str, settings: Dict[str, Any], 
                              context: Optional[Dict[str, Any]] = None) -> None:
        """설정 적용 과정 로깅"""
        if not self.enabled:
            return
        
        try:
            timestamp = datetime.now().isoformat()
            log_entry = {
                'timestamp': timestamp,
                'step': step,
                'settings': settings,
                'context': context or {}
            }
            
            # 현재 설정 업데이트
            self.current_settings = settings.copy()
            
            # 로그 파일에 기록
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
            
            # 디버그 세션에 추가
            self._add_to_session(step, settings, context)
            
        except Exception as e:
            print(f"설정 로깅 실패: {e}")
    
    def log_setting_validation(self, validation_result: Dict[str, Any], 
                             original_settings: Dict[str, Any]) -> None:
        """설정 검증 과정 로깅"""
        if not self.enabled:
            return
        
        try:
            timestamp = datetime.now().isoformat()
            log_entry = {
                'timestamp': timestamp,
                'step': 'validation',
                'original_settings': original_settings,
                'validation_result': validation_result
            }
            
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
            
        except Exception as e:
            print(f"검증 로깅 실패: {e}")
    
    def log_setting_merge(self, common_settings: Dict[str, Any], 
                         script_settings: Dict[str, Any], 
                         user_settings: Dict[str, Any],
                         merged_result: MergedSettings) -> None:
        """설정 병합 과정 로깅"""
        if not self.enabled:
            return
        
        try:
            timestamp = datetime.now().isoformat()
            log_entry = {
                'timestamp': timestamp,
                'step': 'merge',
                'input': {
                    'common': common_settings,
                    'script': script_settings,
                    'user': user_settings
                },
                'output': {
                    'common': {
                        'bg': merged_result.common.bg.__dict__,
                        'shadow': merged_result.common.shadow.__dict__,
                        'border': merged_result.common.border.__dict__
                    },
                    'script_types': {k: {
                        'row_count': v.row_count,
                        'aspect_ratio': v.aspect_ratio,
                        'resolution': v.resolution,
                        'rows': [row.__dict__ for row in v.rows]
                    } for k, v in merged_result.script_types.items()},
                    'source_info': merged_result.source_info
                }
            }
            
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
            
        except Exception as e:
            print(f"병합 로깅 실패: {e}")
    
    def log_error(self, error_message: str, error_context: Optional[Dict[str, Any]] = None) -> None:
        """에러 로깅"""
        if not self.enabled:
            return
        
        try:
            timestamp = datetime.now().isoformat()
            log_entry = {
                'timestamp': timestamp,
                'step': 'error',
                'error_message': error_message,
                'error_context': error_context or {},
                'current_settings': self.current_settings
            }
            
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
            
        except Exception as e:
            print(f"에러 로깅 실패: {e}")
    
    def log_rendering_step(self, step: str, script_type: str, 
                          input_data: Dict[str, Any], output_path: str) -> None:
        """렌더링 단계 로깅"""
        if not self.enabled:
            return
        
        try:
            timestamp = datetime.now().isoformat()
            log_entry = {
                'timestamp': timestamp,
                'step': f'rendering_{step}',
                'script_type': script_type,
                'input_data': input_data,
                'output_path': output_path,
                'settings_used': self.current_settings
            }
            
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
            
        except Exception as e:
            print(f"렌더링 로깅 실패: {e}")
    
    def start_debug_session(self, session_name: str) -> str:
        """디버그 세션 시작"""
        session_id = f"{session_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        session = {
            'session_id': session_id,
            'start_time': datetime.now().isoformat(),
            'steps': [],
            'settings_snapshots': []
        }
        
        self.debug_sessions.append(session)
        
        # 세션 수 제한
        if len(self.debug_sessions) > self.max_sessions:
            self.debug_sessions = self.debug_sessions[-self.max_sessions:]
        
        self.log_setting_application(f"debug_session_start", {'session_id': session_id})
        return session_id
    
    def end_debug_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """디버그 세션 종료"""
        session = self._find_session(session_id)
        if session:
            session['end_time'] = datetime.now().isoformat()
            session['duration'] = self._calculate_duration(session['start_time'], session['end_time'])
            
            self.log_setting_application(f"debug_session_end", {
                'session_id': session_id,
                'duration': session['duration'],
                'steps_count': len(session['steps'])
            })
            
            return session
        
        return None
    
    def _add_to_session(self, step: str, settings: Dict[str, Any], 
                       context: Optional[Dict[str, Any]] = None) -> None:
        """현재 세션에 단계 추가"""
        if not self.debug_sessions:
            return
        
        current_session = self.debug_sessions[-1]
        step_entry = {
            'timestamp': datetime.now().isoformat(),
            'step': step,
            'settings': settings,
            'context': context or {}
        }
        
        current_session['steps'].append(step_entry)
        current_session['settings_snapshots'].append(settings.copy())
    
    def _find_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """세션 ID로 세션 찾기"""
        for session in self.debug_sessions:
            if session['session_id'] == session_id:
                return session
        return None
    
    def _calculate_duration(self, start_time: str, end_time: str) -> float:
        """세션 지속 시간 계산 (초)"""
        try:
            start = datetime.fromisoformat(start_time)
            end = datetime.fromisoformat(end_time)
            return (end - start).total_seconds()
        except Exception:
            return 0.0
    
    def generate_setting_report(self) -> str:
        """설정 적용 보고서 생성"""
        try:
            report = []
            report.append("=== 설정 적용 보고서 ===")
            report.append(f"생성 시간: {datetime.now()}")
            report.append(f"로그 파일: {self.log_file}")
            report.append(f"디버그 활성화: {self.enabled}")
            report.append("")
            
            # 현재 설정 상태
            report.append("현재 설정 상태:")
            report.append(json.dumps(self.current_settings, indent=2, ensure_ascii=False))
            report.append("")
            
            # 최근 디버그 세션
            if self.debug_sessions:
                report.append("최근 디버그 세션:")
                for session in self.debug_sessions[-3:]:  # 최근 3개 세션
                    report.append(f"  - {session['session_id']}: {len(session['steps'])}단계")
                    if 'duration' in session:
                        report.append(f"    지속시간: {session['duration']:.2f}초")
                report.append("")
            
            # 로그 파일 통계
            if os.path.exists(self.log_file):
                file_size = os.path.getsize(self.log_file)
                report.append(f"로그 파일 크기: {file_size:,} bytes")
                
                # 로그 라인 수 계산
                try:
                    with open(self.log_file, 'r', encoding='utf-8') as f:
                        line_count = sum(1 for _ in f)
                    report.append(f"로그 라인 수: {line_count:,}")
                except Exception:
                    report.append("로그 라인 수: 계산 불가")
            
            return '\n'.join(report)
            
        except Exception as e:
            return f"보고서 생성 실패: {e}"
    
    def get_debug_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """특정 디버그 세션 정보 반환"""
        return self._find_session(session_id)
    
    def get_recent_sessions(self, limit: int = 5) -> List[Dict[str, Any]]:
        """최근 디버그 세션 목록 반환"""
        return self.debug_sessions[-limit:] if limit > 0 else self.debug_sessions
    
    def clear_logs(self) -> bool:
        """로그 파일 초기화"""
        try:
            if os.path.exists(self.log_file):
                with open(self.log_file, 'w', encoding='utf-8') as f:
                    f.write("")
            
            self.debug_sessions.clear()
            self.current_settings.clear()
            
            return True
            
        except Exception as e:
            print(f"로그 초기화 실패: {e}")
            return False
    
    def export_debug_data(self, filepath: str) -> bool:
        """디버그 데이터 내보내기"""
        try:
            export_data = {
                'export_time': datetime.now().isoformat(),
                'current_settings': self.current_settings,
                'debug_sessions': self.debug_sessions,
                'log_file_path': self.log_file
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
            
            return True
            
        except Exception as e:
            print(f"디버그 데이터 내보내기 실패: {e}")
            return False
    
    def enable_debugging(self) -> None:
        """디버깅 활성화"""
        self.enabled = True
        self.log_setting_application("debug_enabled", {})
    
    def disable_debugging(self) -> None:
        """디버깅 비활성화"""
        self.log_setting_application("debug_disabled", {})
        self.enabled = False
    
    def get_debug_status(self) -> Dict[str, Any]:
        """디버깅 상태 정보 반환"""
        return {
            'enabled': self.enabled,
            'log_file': self.log_file,
            'sessions_count': len(self.debug_sessions),
            'current_settings_keys': list(self.current_settings.keys()),
            'log_file_exists': os.path.exists(self.log_file),
            'log_file_size': os.path.getsize(self.log_file) if os.path.exists(self.log_file) else 0
        }
