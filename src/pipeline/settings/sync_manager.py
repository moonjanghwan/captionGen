"""
실시간 설정 동기화 시스템

UI 설정 변경을 실시간으로 감지하고 파이프라인에 반영하는 시스템입니다.
Observer 패턴을 사용하여 설정 변경사항을 자동으로 동기화합니다.
"""

import json
import os
from typing import Dict, Any, List, Callable, Optional
from datetime import datetime
from .merger import SettingMerger
from .validator import SettingValidator
from .schemas import MergedSettings


class SettingObserver:
    """설정 변경 감지자 인터페이스"""
    
    def on_settings_changed(self, changes: Dict[str, Any]) -> None:
        """설정 변경 시 호출되는 메서드"""
        pass
    
    def on_setting_validated(self, validation_result: Dict[str, Any]) -> None:
        """설정 검증 완료 시 호출되는 메서드"""
        pass


class SettingSyncManager:
    """실시간 설정 동기화 관리자"""
    
    def __init__(self, log_file: str = "setting_sync.log"):
        self.observers: List[SettingObserver] = []
        self.current_settings: Dict[str, Any] = {}
        self.merged_settings: Optional[MergedSettings] = None
        self.log_file = log_file
        self.enabled = True
        
        # 설정 관리 컴포넌트
        self.merger = SettingMerger()
        self.validator = SettingValidator()
        
        # 설정 변경 히스토리
        self.change_history: List[Dict[str, Any]] = []
        self.max_history_size = 100
    
    def register_observer(self, observer: SettingObserver) -> None:
        """설정 변경 감지자 등록"""
        if observer not in self.observers:
            self.observers.append(observer)
            self._log(f"관찰자 등록: {type(observer).__name__}")
    
    def unregister_observer(self, observer: SettingObserver) -> None:
        """설정 변경 감지자 해제"""
        if observer in self.observers:
            self.observers.remove(observer)
            self._log(f"관찰자 해제: {type(observer).__name__}")
    
    def update_settings(self, new_settings: Dict[str, Any], source: str = "unknown") -> bool:
        """
        설정 업데이트 및 알림
        
        Args:
            new_settings: 새로운 설정 딕셔너리
            source: 설정 변경 소스 (UI, 파일, API 등)
            
        Returns:
            업데이트 성공 여부
        """
        try:
            if not self.enabled:
                self._log("설정 동기화가 비활성화되어 있습니다.")
                return False
            
            old_settings = self.current_settings.copy()
            
            # 설정 병합 및 검증
            self.current_settings = self._merge_and_validate(new_settings)
            
            # 변경사항 감지
            changes = self._detect_changes(old_settings, self.current_settings)
            
            if changes:
                # 변경 히스토리 기록
                self._record_change(changes, source)
                
                # 관찰자들에게 알림
                self._notify_observers(changes)
                
                self._log(f"설정 업데이트 완료: {len(changes)}개 변경사항, 소스: {source}")
                return True
            else:
                self._log("설정 변경사항이 없습니다.")
                return False
                
        except Exception as e:
            self._log(f"설정 업데이트 실패: {e}", "ERROR")
            return False
    
    def get_current_settings(self) -> Dict[str, Any]:
        """현재 설정 반환"""
        return self.current_settings.copy()
    
    def get_merged_settings(self) -> Optional[MergedSettings]:
        """병합된 설정 객체 반환"""
        return self.merged_settings
    
    def get_common_settings(self) -> Dict[str, Any]:
        """공통 설정 반환"""
        return self.current_settings.get('common', {})
    
    def get_script_settings(self, script_type: str) -> Dict[str, Any]:
        """스크립트 타입별 설정 반환"""
        tabs = self.current_settings.get('tabs', {})
        return tabs.get(script_type, {})
    
    def get_user_settings(self, script_type: str) -> Dict[str, Any]:
        """사용자 설정 반환 (현재는 빈 딕셔너리)"""
        # 실제 구현에서는 사용자별 설정을 저장소에서 가져옴
        return {}
    
    def detect_changes(self, old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
        """설정 변경사항 감지"""
        changes = {}
        
        # 공통 설정 변경 감지
        old_common = old.get('common', {})
        new_common = new.get('common', {})
        common_changes = self._detect_dict_changes(old_common, new_common)
        if common_changes:
            changes['common'] = common_changes
        
        # 스크립트 타입별 설정 변경 감지
        old_tabs = old.get('tabs', {})
        new_tabs = new.get('tabs', {})
        tabs_changes = self._detect_dict_changes(old_tabs, new_tabs)
        if tabs_changes:
            changes['tabs'] = tabs_changes
        
        return changes
    
    def _merge_and_validate(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """설정 병합 및 검증"""
        try:
            # 기본 설정 정의
            common_settings = settings.get('common', {})
            script_settings = settings.get('tabs', {})
            user_settings = {}
            
            # 설정 병합
            self.merged_settings = self.merger.merge_settings(
                common_settings, script_settings, user_settings
            )
            
            # 검증된 설정을 딕셔너리로 변환
            validated_settings = self.validator.validate_settings(settings)
            
            return validated_settings
            
        except Exception as e:
            self._log(f"설정 병합/검증 실패: {e}", "ERROR")
            return settings
    
    def _detect_changes(self, old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
        """설정 변경사항 감지 (내부 메서드)"""
        return self.detect_changes(old, new)
    
    def _detect_dict_changes(self, old_dict: Dict[str, Any], new_dict: Dict[str, Any]) -> Dict[str, Any]:
        """딕셔너리 변경사항 감지"""
        changes = {}
        
        # 새로운 키 또는 변경된 값
        for key, value in new_dict.items():
            if key not in old_dict or old_dict[key] != value:
                changes[key] = {'old': old_dict.get(key), 'new': value}
        
        # 삭제된 키
        for key in old_dict:
            if key not in new_dict:
                changes[key] = {'old': old_dict[key], 'new': None}
        
        return changes
    
    def _notify_observers(self, changes: Dict[str, Any]) -> None:
        """관찰자들에게 변경사항 알림"""
        for observer in self.observers:
            try:
                observer.on_settings_changed(changes)
            except Exception as e:
                self._log(f"관찰자 알림 실패: {type(observer).__name__}, 오류: {e}", "ERROR")
    
    def _record_change(self, changes: Dict[str, Any], source: str) -> None:
        """변경 히스토리 기록"""
        change_record = {
            'timestamp': datetime.now().isoformat(),
            'source': source,
            'changes': changes,
            'settings_snapshot': self.current_settings.copy()
        }
        
        self.change_history.append(change_record)
        
        # 히스토리 크기 제한
        if len(self.change_history) > self.max_history_size:
            self.change_history = self.change_history[-self.max_history_size:]
    
    def _log(self, message: str, level: str = "INFO") -> None:
        """로그 기록"""
        if not self.enabled:
            return
        
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] [{level}] {message}"
        
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry + '\n')
        except Exception as e:
            print(f"로그 기록 실패: {e}")
    
    def get_change_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """변경 히스토리 반환"""
        return self.change_history[-limit:] if limit > 0 else self.change_history
    
    def export_settings(self, filepath: str) -> bool:
        """현재 설정을 파일로 내보내기"""
        try:
            export_data = {
                'timestamp': datetime.now().isoformat(),
                'settings': self.current_settings,
                'merged_settings': self.merged_settings.__dict__ if self.merged_settings else None,
                'change_history': self.change_history[-10:]  # 최근 10개 변경사항
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
            
            self._log(f"설정 내보내기 완료: {filepath}")
            return True
            
        except Exception as e:
            self._log(f"설정 내보내기 실패: {e}", "ERROR")
            return False
    
    def import_settings(self, filepath: str) -> bool:
        """파일에서 설정 가져오기"""
        try:
            if not os.path.exists(filepath):
                self._log(f"설정 파일을 찾을 수 없습니다: {filepath}", "ERROR")
                return False
            
            with open(filepath, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            settings = import_data.get('settings', {})
            if settings:
                return self.update_settings(settings, f"import:{filepath}")
            
            self._log(f"설정 파일에 유효한 설정이 없습니다: {filepath}", "ERROR")
            return False
            
        except Exception as e:
            self._log(f"설정 가져오기 실패: {e}", "ERROR")
            return False
    
    def enable_sync(self) -> None:
        """설정 동기화 활성화"""
        self.enabled = True
        self._log("설정 동기화 활성화")
    
    def disable_sync(self) -> None:
        """설정 동기화 비활성화"""
        self.enabled = False
        self._log("설정 동기화 비활성화")
    
    def clear_history(self) -> None:
        """변경 히스토리 초기화"""
        self.change_history.clear()
        self._log("변경 히스토리 초기화")
    
    def get_sync_status(self) -> Dict[str, Any]:
        """동기화 상태 정보 반환"""
        return {
            'enabled': self.enabled,
            'observers_count': len(self.observers),
            'history_size': len(self.change_history),
            'has_merged_settings': self.merged_settings is not None,
            'log_file': self.log_file
        }
