"""
플러그인 통합 어댑터

기존 시스템과 플러그인 시스템을 연결하는 어댑터입니다.
기존 UI와 API 호환성을 유지하면서 플러그인 시스템을 사용할 수 있도록 합니다.
"""

import os
import json
import time
from typing import Dict, List, Any, Optional, Callable
from .plugin_manager import PluginManager
from .base_plugin import PluginConfig, PluginResult


class PluginIntegrationAdapter:
    """플러그인 통합 어댑터"""
    
    def __init__(self, output_directory: str = "output"):
        """
        어댑터 초기화
        
        Args:
            output_directory: 출력 디렉토리
        """
        self.output_directory = output_directory
        
        # 콜백 함수들 먼저 초기화
        self.progress_callback: Optional[Callable] = None
        self.log_callback: Optional[Callable] = None
        
        self.plugin_manager = PluginManager()
        
        # 플러그인 등록
        self._register_plugins()
    
    def _register_plugins(self):
        """플러그인 등록"""
        try:
            from .intro_plugin import IntroPlugin
            from .conversation_plugin import ConversationPlugin
            from .ending_plugin import EndingPlugin
            
            self.plugin_manager.register_plugin(IntroPlugin)
            self.plugin_manager.register_plugin(ConversationPlugin)
            self.plugin_manager.register_plugin(EndingPlugin)
            
            registered_count = len(self.plugin_manager.get_registered_plugins())
            self._log_info(f"플러그인 등록 완료: {registered_count}개")
            
        except Exception as e:
            self._log_error(f"플러그인 등록 실패: {e}")
            import traceback
            traceback.print_exc()
    
    def set_progress_callback(self, callback: Callable):
        """진행 상황 콜백 함수 설정"""
        self.progress_callback = callback
        self.plugin_manager.set_progress_callback(callback)
    
    def set_log_callback(self, callback: Callable):
        """로그 콜백 함수 설정"""
        self.log_callback = callback
        self.plugin_manager.set_log_callback(callback)
    
    def run_legacy_pipeline(self, ui_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        기존 UI 데이터로부터 플러그인 기반 파이프라인 실행
        
        Args:
            ui_data: UI에서 입력받은 데이터
            
        Returns:
            실행 결과
        """
        try:
            self._log_info("플러그인 기반 파이프라인 실행 시작")
            
            # UI 데이터를 플러그인별 데이터로 변환
            plugin_data = self._convert_ui_data_to_plugin_data(ui_data)
            
            # 프로젝트 설정
            project_name = ui_data.get("project_name", "default_project")
            identifier = ui_data.get("identifier", "default_identifier")
            
            # 플러그인 설정 생성
            plugin_config = PluginConfig(
                project_name=project_name,
                identifier=identifier,
                output_directory=os.path.join(self.output_directory, project_name, identifier)
            )
            
            # 플러그인 인스턴스 생성
            self._create_plugin_instances(plugin_config)
            
            # 플러그인 실행
            results = self._execute_plugins(plugin_data)
            
            # 결과 병합
            merged_result = self.plugin_manager.merge_plugin_results(results)
            
            # 기존 형식으로 변환
            legacy_result = self._convert_plugin_results_to_legacy_format(merged_result)
            
            self._log_info("플러그인 기반 파이프라인 실행 완료")
            return legacy_result
            
        except Exception as e:
            self._log_error(f"파이프라인 실행 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "generated_files": {},
                "execution_time": 0
            }
    
    def run_auto_generation(self, ui_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        자동 생성 실행 (인트로 → 회화 → 엔딩)
        
        Args:
            ui_data: UI에서 입력받은 데이터
            
        Returns:
            실행 결과
        """
        try:
            self._log_info("자동 생성 실행 시작")
            
            # UI 데이터를 플러그인별 데이터로 변환
            plugin_data = self._convert_ui_data_to_plugin_data(ui_data)
            
            # 프로젝트 설정
            project_name = ui_data.get("project_name", "default_project")
            identifier = ui_data.get("identifier", "default_identifier")
            
            # 플러그인 설정 생성
            plugin_config = PluginConfig(
                project_name=project_name,
                identifier=identifier,
                output_directory=os.path.join(self.output_directory, project_name, identifier)
            )
            
            # 플러그인 인스턴스 생성
            self._create_plugin_instances(plugin_config)
            
            # 자동 생성 실행
            results = self.plugin_manager.run_auto_generation(plugin_data)
            
            # 결과 병합
            merged_result = self.plugin_manager.merge_plugin_results(results)
            
            # 기존 형식으로 변환
            legacy_result = self._convert_plugin_results_to_legacy_format(merged_result)
            
            self._log_info("자동 생성 실행 완료")
            return legacy_result
            
        except Exception as e:
            self._log_error(f"자동 생성 실행 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "generated_files": {},
                "execution_time": 0
            }
    
    def run_single_plugin(self, plugin_type: str, ui_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        단일 플러그인 실행
        
        Args:
            plugin_type: 플러그인 타입 (intro, conversation, ending)
            ui_data: UI에서 입력받은 데이터
            
        Returns:
            실행 결과
        """
        try:
            self._log_info(f"단일 플러그인 실행 시작: {plugin_type}")
            
            # UI 데이터를 플러그인별 데이터로 변환
            plugin_data = self._convert_ui_data_to_plugin_data(ui_data)
            
            # 프로젝트 설정
            project_name = ui_data.get("project_name", "default_project")
            identifier = ui_data.get("identifier", "default_identifier")
            
            # 플러그인 설정 생성
            plugin_config = PluginConfig(
                project_name=project_name,
                identifier=identifier,
                output_directory=os.path.join(self.output_directory, project_name, identifier)
            )
            
            # 플러그인 인스턴스 생성
            plugin_instance = self.plugin_manager.create_plugin_instance(plugin_type, plugin_config)
            if not plugin_instance:
                return {
                    "success": False,
                    "error": f"플러그인 인스턴스 생성 실패: {plugin_type}",
                    "generated_files": {},
                    "execution_time": 0
                }
            
            # 플러그인 실행
            result = self.plugin_manager.run_plugin(plugin_type, plugin_data)
            
            if result:
                # 기존 형식으로 변환
                legacy_result = self._convert_single_plugin_result_to_legacy_format(result)
                self._log_info(f"단일 플러그인 실행 완료: {plugin_type}")
                return legacy_result
            else:
                return {
                    "success": False,
                    "error": f"플러그인 실행 실패: {plugin_type}",
                    "generated_files": {},
                    "execution_time": 0
                }
                
        except Exception as e:
            self._log_error(f"단일 플러그인 실행 실패: {plugin_type} - {e}")
            return {
                "success": False,
                "error": str(e),
                "generated_files": {},
                "execution_time": 0
            }
    
    def _convert_ui_data_to_plugin_data(self, ui_data: Dict[str, Any]) -> Dict[str, Any]:
        """UI 데이터를 플러그인별 데이터로 변환"""
        try:
            plugin_data = {}
            
            # 인트로 데이터
            if "intro_script" in ui_data:
                plugin_data["intro_script"] = ui_data["intro_script"]
            
            # 회화 데이터
            if "conversation_data" in ui_data:
                plugin_data["conversation_data"] = ui_data["conversation_data"]
            elif "scenes" in ui_data:
                # 기존 scenes 데이터를 conversation_data로 변환
                conversation_data = []
                for scene in ui_data["scenes"]:
                    if scene.get("type") == "conversation":
                        conversation_data.append({
                            "sequence": scene.get("sequence", 1),
                            "native_script": scene.get("native_script", ""),
                            "learning_script": scene.get("learning_script", ""),
                            "reading_script": scene.get("reading_script", "")
                        })
                plugin_data["conversation_data"] = conversation_data
            
            # 엔딩 데이터
            if "ending_script" in ui_data:
                plugin_data["ending_script"] = ui_data["ending_script"]
            
            # 공통 설정
            plugin_data["speaker_settings"] = ui_data.get("speaker_settings", {})
            plugin_data["image_settings"] = ui_data.get("image_settings", {})
            plugin_data["background_settings"] = ui_data.get("background_settings", {})
            
            return plugin_data
            
        except Exception as e:
            self._log_error(f"UI 데이터 변환 실패: {e}")
            return {}
    
    def _create_plugin_instances(self, plugin_config: PluginConfig):
        """플러그인 인스턴스 생성"""
        try:
            registered_plugins = self.plugin_manager.get_registered_plugins()
            
            for plugin_type in registered_plugins:
                self.plugin_manager.create_plugin_instance(plugin_type, plugin_config)
            
            self._log_info(f"플러그인 인스턴스 생성 완료: {len(registered_plugins)}개")
            
        except Exception as e:
            self._log_error(f"플러그인 인스턴스 생성 실패: {e}")
    
    def _execute_plugins(self, plugin_data: Dict[str, Any]) -> Dict[str, PluginResult]:
        """플러그인 실행"""
        try:
            results = {}
            registered_plugins = self.plugin_manager.get_registered_plugins()
            
            for plugin_type in registered_plugins:
                # 해당 플러그인에 필요한 데이터가 있는지 확인
                if self._has_required_data_for_plugin(plugin_type, plugin_data):
                    result = self.plugin_manager.run_plugin(plugin_type, plugin_data)
                    results[plugin_type] = result
                else:
                    self._log_warning(f"플러그인 {plugin_type}에 필요한 데이터가 없어 건너뜁니다")
            
            return results
            
        except Exception as e:
            self._log_error(f"플러그인 실행 실패: {e}")
            return {}
    
    def _has_required_data_for_plugin(self, plugin_type: str, plugin_data: Dict[str, Any]) -> bool:
        """플러그인에 필요한 데이터가 있는지 확인"""
        try:
            plugin_info = self.plugin_manager.get_plugin_info(plugin_type)
            if not plugin_info:
                return False
            
            required_fields = plugin_info.get("required_input_fields", [])
            
            for field in required_fields:
                if field not in plugin_data or not plugin_data[field]:
                    return False
            
            return True
            
        except Exception as e:
            self._log_error(f"데이터 확인 실패: {plugin_type} - {e}")
            return False
    
    def _convert_plugin_results_to_legacy_format(self, merged_result: Dict[str, Any]) -> Dict[str, Any]:
        """플러그인 결과를 기존 형식으로 변환"""
        try:
            return {
                "success": merged_result.get("success", False),
                "project_name": "default_project",  # 실제로는 설정에서 가져와야 함
                "output_directory": self.output_directory,
                "generated_files": merged_result.get("total_generated_files", {}),
                "execution_time": merged_result.get("total_execution_time", 0),
                "errors": merged_result.get("total_errors", []),
                "warnings": merged_result.get("total_warnings", []),
                "plugin_results": merged_result.get("plugin_results", {})
            }
            
        except Exception as e:
            self._log_error(f"결과 변환 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "generated_files": {},
                "execution_time": 0
            }
    
    def _convert_single_plugin_result_to_legacy_format(self, result: PluginResult) -> Dict[str, Any]:
        """단일 플러그인 결과를 기존 형식으로 변환"""
        try:
            return {
                "success": result.success,
                "plugin_type": result.plugin_type,
                "generated_files": result.generated_files,
                "execution_time": result.execution_time,
                "errors": result.errors,
                "warnings": result.warnings,
                "metadata": result.metadata
            }
            
        except Exception as e:
            self._log_error(f"단일 결과 변환 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "generated_files": {},
                "execution_time": 0
            }
    
    def get_plugin_summary(self) -> Dict[str, Any]:
        """플러그인 시스템 요약 정보 반환"""
        return self.plugin_manager.get_plugin_summary()
    
    def get_available_plugins(self) -> List[Dict[str, Any]]:
        """사용 가능한 플러그인 목록 반환"""
        try:
            plugins = []
            registered_plugins = self.plugin_manager.get_registered_plugins()
            
            for plugin_type in registered_plugins:
                plugin_info = self.plugin_manager.get_plugin_info(plugin_type)
                if plugin_info:
                    plugins.append(plugin_info)
            
            return plugins
            
        except Exception as e:
            self._log_error(f"플러그인 목록 조회 실패: {e}")
            return []
    
    def _log_info(self, message: str, data: Optional[Dict] = None):
        """정보 로그 출력"""
        if self.log_callback:
            self.log_callback("INFO", f"[PluginIntegration] {message}", data)
        else:
            print(f"[PLUGIN_INTEGRATION] {message}")
    
    def _log_warning(self, message: str, data: Optional[Dict] = None):
        """경고 로그 출력"""
        if self.log_callback:
            self.log_callback("WARNING", f"[PluginIntegration] {message}", data)
        else:
            print(f"[PLUGIN_INTEGRATION] WARNING: {message}")
    
    def _log_error(self, message: str, data: Optional[Dict] = None):
        """에러 로그 출력"""
        if self.log_callback:
            self.log_callback("ERROR", f"[PluginIntegration] {message}", data)
        else:
            print(f"[PLUGIN_INTEGRATION] ERROR: {message}")
