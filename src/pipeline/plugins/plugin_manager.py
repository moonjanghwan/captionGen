"""
플러그인 관리자

플러그인들의 등록, 관리, 실행을 담당하는 중앙 관리자입니다.
"""

import os
import json
import time
from typing import Dict, List, Any, Optional, Type, Callable
from .base_plugin import BasePlugin, PluginConfig, PluginResult


class PluginManager:
    """플러그인 관리자"""
    
    def __init__(self):
        """플러그인 관리자 초기화"""
        self.plugins: Dict[str, Type[BasePlugin]] = {}
        self.plugin_instances: Dict[str, BasePlugin] = {}
        self.plugin_configs: Dict[str, PluginConfig] = {}
        
        # 콜백 함수들
        self.progress_callback: Optional[Callable] = None
        self.log_callback: Optional[Callable] = None
    
    def register_plugin(self, plugin_class: Type[BasePlugin]):
        """
        플러그인 등록
        
        Args:
            plugin_class: 등록할 플러그인 클래스
        """
        try:
            # 임시 인스턴스 생성하여 플러그인 타입 확인
            temp_config = PluginConfig(
                project_name="temp",
                identifier="temp",
                output_directory="temp"
            )
            temp_instance = plugin_class(temp_config)
            plugin_type = temp_instance.get_plugin_type()
            
            self.plugins[plugin_type] = plugin_class
            self._log_info(f"플러그인 등록 완료: {plugin_type} ({plugin_class.__name__})")
            
        except Exception as e:
            self._log_error(f"플러그인 등록 실패: {plugin_class.__name__} - {e}")
            import traceback
            traceback.print_exc()
    
    def unregister_plugin(self, plugin_type: str):
        """
        플러그인 등록 해제
        
        Args:
            plugin_type: 등록 해제할 플러그인 타입
        """
        if plugin_type in self.plugins:
            del self.plugins[plugin_type]
            self._log_info(f"플러그인 등록 해제: {plugin_type}")
        
        if plugin_type in self.plugin_instances:
            del self.plugin_instances[plugin_type]
    
    def get_registered_plugins(self) -> List[str]:
        """등록된 플러그인 타입 목록 반환"""
        return list(self.plugins.keys())
    
    def get_plugin_info(self, plugin_type: str) -> Optional[Dict[str, Any]]:
        """
        플러그인 정보 반환
        
        Args:
            plugin_type: 플러그인 타입
            
        Returns:
            플러그인 정보 딕셔너리 또는 None
        """
        if plugin_type not in self.plugins:
            return None
        
        try:
            # 임시 인스턴스 생성하여 정보 수집
            temp_config = PluginConfig(
                project_name="temp",
                identifier="temp", 
                output_directory="temp"
            )
            temp_instance = self.plugins[plugin_type](temp_config)
            
            return {
                "type": plugin_type,
                "name": temp_instance.get_plugin_name(),
                "description": temp_instance.get_plugin_description(),
                "supported_file_types": temp_instance.get_supported_file_types(),
                "required_input_fields": temp_instance.get_required_input_fields(),
                "optional_input_fields": temp_instance.get_optional_input_fields(),
                "default_settings": temp_instance.get_default_settings()
            }
            
        except Exception as e:
            self._log_error(f"플러그인 정보 수집 실패: {plugin_type} - {e}")
            return None
    
    def create_plugin_instance(self, plugin_type: str, config: PluginConfig) -> Optional[BasePlugin]:
        """
        플러그인 인스턴스 생성
        
        Args:
            plugin_type: 플러그인 타입
            config: 플러그인 설정
            
        Returns:
            플러그인 인스턴스 또는 None
        """
        if plugin_type not in self.plugins:
            self._log_error(f"등록되지 않은 플러그인 타입: {plugin_type}")
            return None
        
        try:
            plugin_instance = self.plugins[plugin_type](config)
            
            # 콜백 함수 설정
            if self.progress_callback:
                plugin_instance.set_progress_callback(self.progress_callback)
            if self.log_callback:
                plugin_instance.set_log_callback(self.log_callback)
            
            # 인스턴스 저장
            self.plugin_instances[plugin_type] = plugin_instance
            self.plugin_configs[plugin_type] = config
            
            self._log_info(f"플러그인 인스턴스 생성 완료: {plugin_type}")
            return plugin_instance
            
        except Exception as e:
            self._log_error(f"플러그인 인스턴스 생성 실패: {plugin_type} - {e}")
            return None
    
    def run_plugin(self, plugin_type: str, input_data: Dict[str, Any]) -> Optional[PluginResult]:
        """
        플러그인 실행
        
        Args:
            plugin_type: 플러그인 타입
            input_data: 입력 데이터
            
        Returns:
            플러그인 실행 결과 또는 None
        """
        if plugin_type not in self.plugin_instances:
            self._log_error(f"플러그인 인스턴스가 없습니다: {plugin_type}")
            return None
        
        try:
            plugin_instance = self.plugin_instances[plugin_type]
            result = plugin_instance.run_plugin(input_data)
            
            if result.success:
                self._log_info(f"플러그인 실행 성공: {plugin_type}")
            else:
                self._log_error(f"플러그인 실행 실패: {plugin_type}")
            
            return result
            
        except Exception as e:
            self._log_error(f"플러그인 실행 중 예외 발생: {plugin_type} - {e}")
            return None
    
    def run_multiple_plugins(self, plugin_types: List[str], input_data: Dict[str, Any]) -> Dict[str, PluginResult]:
        """
        여러 플러그인 순차 실행
        
        Args:
            plugin_types: 실행할 플러그인 타입 목록
            input_data: 입력 데이터
            
        Returns:
            플러그인별 실행 결과 딕셔너리
        """
        results = {}
        
        for plugin_type in plugin_types:
            self._log_info(f"플러그인 실행 시작: {plugin_type}")
            result = self.run_plugin(plugin_type, input_data)
            results[plugin_type] = result
            
            if result and not result.success:
                self._log_error(f"플러그인 실행 실패로 중단: {plugin_type}")
                break
        
        return results
    
    def run_auto_generation(self, input_data: Dict[str, Any]) -> Dict[str, PluginResult]:
        """
        자동 생성 실행 (인트로 → 회화 → 엔딩 순서)
        
        Args:
            input_data: 입력 데이터
            
        Returns:
            플러그인별 실행 결과 딕셔너리
        """
        # 자동 생성 순서 정의
        auto_generation_order = ["intro", "conversation", "ending"]
        
        # 등록된 플러그인만 필터링
        available_plugins = [p for p in auto_generation_order if p in self.plugins]
        
        self._log_info(f"자동 생성 시작: {available_plugins}")
        return self.run_multiple_plugins(available_plugins, input_data)
    
    def merge_plugin_results(self, results: Dict[str, PluginResult]) -> Dict[str, Any]:
        """
        플러그인 결과들을 병합
        
        Args:
            results: 플러그인별 실행 결과
            
        Returns:
            병합된 결과
        """
        merged_result = {
            "success": all(result.success for result in results.values() if result),
            "total_execution_time": sum(result.execution_time for result in results.values() if result),
            "total_generated_files": {},
            "total_errors": [],
            "total_warnings": [],
            "plugin_results": {}
        }
        
        for plugin_type, result in results.items():
            if result:
                merged_result["total_generated_files"].update(result.generated_files)
                merged_result["total_errors"].extend(result.errors)
                merged_result["total_warnings"].extend(result.warnings)
                merged_result["plugin_results"][plugin_type] = {
                    "success": result.success,
                    "execution_time": result.execution_time,
                    "generated_files": result.generated_files,
                    "errors": result.errors,
                    "warnings": result.warnings
                }
        
        return merged_result
    
    def set_progress_callback(self, callback: Callable):
        """진행 상황 콜백 함수 설정"""
        self.progress_callback = callback
        
        # 기존 인스턴스들에도 적용
        for instance in self.plugin_instances.values():
            instance.set_progress_callback(callback)
    
    def set_log_callback(self, callback: Callable):
        """로그 콜백 함수 설정"""
        self.log_callback = callback
        
        # 기존 인스턴스들에도 적용
        for instance in self.plugin_instances.values():
            instance.set_log_callback(callback)
    
    def _log_info(self, message: str, data: Optional[Dict] = None):
        """정보 로그 출력"""
        if self.log_callback:
            self.log_callback("INFO", f"[PluginManager] {message}", data)
        else:
            print(f"[PLUGIN_MANAGER] {message}")
    
    def _log_error(self, message: str, data: Optional[Dict] = None):
        """에러 로그 출력"""
        if self.log_callback:
            self.log_callback("ERROR", f"[PluginManager] {message}", data)
        else:
            print(f"[PLUGIN_MANAGER] ERROR: {message}")
    
    def get_plugin_summary(self) -> Dict[str, Any]:
        """플러그인 시스템 요약 정보 반환"""
        return {
            "registered_plugins": self.get_registered_plugins(),
            "active_instances": list(self.plugin_instances.keys()),
            "plugin_count": len(self.plugins),
            "instance_count": len(self.plugin_instances)
        }
    
    def cleanup_plugin_instances(self):
        """플러그인 인스턴스 정리"""
        self.plugin_instances.clear()
        self.plugin_configs.clear()
        self._log_info("플러그인 인스턴스 정리 완료")
