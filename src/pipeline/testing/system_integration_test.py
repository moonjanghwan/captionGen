"""
전체 시스템 통합 테스트

파이프라인의 모든 컴포넌트가 올바르게 통합되어 작동하는지 검증하는 테스트 시스템입니다.
"""

import os
import json
import tempfile
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from ..settings.sync_manager import SettingSyncManager
from ..settings.debugger import SettingDebugger
# from ..renderers.improved_renderer import ImprovedImageRenderer  # 모듈이 없어서 주석 처리
from ..core.context import PipelineContext
from ..manifest.models import Manifest, Scene, SceneContent
from .setting_reflection_test import SettingReflectionTest


class SystemIntegrationTest:
    """전체 시스템 통합 테스트 클래스"""
    
    def __init__(self, test_log_file: str = "system_integration_test.log"):
        self.test_log_file = test_log_file
        self.test_results: List[Dict[str, Any]] = []
        
        # 테스트용 컴포넌트 초기화
        self.sync_manager = SettingSyncManager("test_sync.log")
        self.debugger = SettingDebugger(test_log_file)
        # self.improved_renderer = ImprovedImageRenderer(self.sync_manager, "test_renderer_debug.log")  # 모듈이 없어서 주석 처리
        self.setting_test = SettingReflectionTest("test_setting_reflection.log")
        
        # 테스트 통계
        self.test_stats = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'test_duration': 0.0
        }
        
        # 테스트용 임시 디렉토리
        self.temp_dir = None
    
    def setup_test_environment(self) -> str:
        """테스트 환경 설정"""
        try:
            # 임시 디렉토리 생성
            self.temp_dir = tempfile.mkdtemp(prefix="captiongen_test_")
            self._log(f"테스트 환경 설정: {self.temp_dir}")
            
            # 테스트용 설정 추가
            self._setup_test_settings()
            
            # 테스트용 Manifest 생성
            self._setup_test_manifest()
            
            return self.temp_dir
            
        except Exception as e:
            self._log(f"테스트 환경 설정 실패: {e}")
            return ""
    
    def cleanup_test_environment(self) -> None:
        """테스트 환경 정리"""
        try:
            if self.temp_dir and os.path.exists(self.temp_dir):
                import shutil
                shutil.rmtree(self.temp_dir)
                self._log(f"테스트 환경 정리 완료: {self.temp_dir}")
            
            # 렌더러 정리
            if self.improved_renderer:
                self.improved_renderer.cleanup()
            
        except Exception as e:
            self._log(f"테스트 환경 정리 실패: {e}")
    
    def _setup_test_settings(self) -> None:
        """테스트용 설정 설정"""
        test_settings = {
            'common': {
                'bg': {'enabled': True, 'color': '#000000', 'alpha': 0.2, 'margin': 2, 'type': '이미지', 'value': ''},
                'shadow': {'enabled': True, 'thick': 4, 'color': '#000000', 'blur': 4, 'offx': 3, 'offy': 3, 'alpha': 1.0, 'useBlur': True},
                'border': {'enabled': True, 'thick': 4, 'color': '#000000'}
            },
            'tabs': {
                '회화 설정': {
                    '행수': 4,
                    '비율': '16:9',
                    '해상도': '1920x1080',
                    'rows': [
                        {'행': '순번', 'x': 100, 'y': 200, 'w': 100, '크기(pt)': 60, '폰트(pt)': 'Noto Sans KR', '색상': '#FFFFFF', '굵기': True, '좌우 정렬': 'center', '상하 정렬': 'center', '바탕': False, '쉐도우': True, '외곽선': True},
                        {'행': '원어', 'x': 100, 'y': 400, 'w': 1800, '크기(pt)': 80, '폰트(pt)': 'Noto Sans KR', '색상': '#FFFFFF', '굵기': False, '좌우 정렬': 'center', '상하 정렬': 'center', '바탕': False, '쉐도우': True, '외곽선': True},
                        {'행': '학습어', 'x': 100, 'y': 600, 'w': 1800, '크기(pt)': 80, '폰트(pt)': 'Noto Sans KR', '색상': '#FFFF00', '굵기': False, '좌우 정렬': 'center', '상하 정렬': 'center', '바탕': False, '쉐도우': True, '외곽선': True},
                        {'행': '읽기', 'x': 100, 'y': 800, 'w': 1800, '크기(pt)': 60, '폰트(pt)': 'Noto Sans KR', '색상': '#00FF00', '굵기': False, '좌우 정렬': 'center', '상하 정렬': 'center', '바탕': False, '쉐도우': True, '외곽선': True}
                    ]
                },
                '인트로 설정': {
                    '행수': 1,
                    '비율': '16:9',
                    '해상도': '1920x1080',
                    'rows': [
                        {'행': '1행', 'x': 100, 'y': 500, 'w': 1820, '크기(pt)': 80, '폰트(pt)': 'Noto Sans KR', '색상': '#FFFFFF', '굵기': False, '좌우 정렬': 'center', '상하 정렬': 'center', '바탕': False, '쉐도우': True, '외곽선': True}
                    ]
                },
                '엔딩 설정': {
                    '행수': 1,
                    '비율': '16:9',
                    '해상도': '1920x1080',
                    'rows': [
                        {'행': '1행', 'x': 100, 'y': 1000, 'w': 1820, '크기(pt)': 90, '폰트(pt)': 'Noto Sans KR', '색상': '#FFFFFF', '굵기': False, '좌우 정렬': 'center', '상하 정렬': 'center', '바탕': False, '쉐도우': True, '외곽선': True}
                    ]
                }
            }
        }
        
        self.sync_manager.update_settings(test_settings, "test_setup")
        self._log("테스트용 설정 설정 완료")
    
    def _setup_test_manifest(self) -> None:
        """테스트용 Manifest 생성"""
        # 테스트용 씬 데이터
        self.test_scenes = [
            Scene(
                id="scene_001",
                type="conversation",
                sequence=1,
                native_script="你好",
                learning_script="안녕하세요",
                reading_script="니하오"
            ),
            Scene(
                id="scene_002",
                type="intro",
                full_script="**중국어 기초 회화**를 시작합니다."
            ),
            Scene(
                id="scene_003",
                type="ending",
                full_script="수고하셨습니다. 다음에 또 만나요!"
            )
        ]
        
        self.test_manifest = Manifest(
            project_name="test_project",
            resolution="1920x1080",
            scenes=self.test_scenes
        )
        
        self._log("테스트용 Manifest 생성 완료")
    
    def run_all_integration_tests(self) -> Dict[str, bool]:
        """모든 통합 테스트 실행"""
        import time
        start_time = time.time()
        
        self._log("=== 전체 시스템 통합 테스트 시작 ===")
        
        # 테스트 환경 설정
        test_dir = self.setup_test_environment()
        if not test_dir:
            self._log("❌ 테스트 환경 설정 실패")
            return {}
        
        results = {}
        
        try:
            # 1. 설정 시스템 통합 테스트
            results.update(self._test_settings_integration())
            
            # 2. 렌더링 시스템 통합 테스트
            results.update(self._test_rendering_integration())
            
            # 3. 파이프라인 컨텍스트 통합 테스트
            results.update(self._test_pipeline_context_integration())
            
            # 4. End-to-End 통합 테스트
            results.update(self._test_end_to_end_integration())
            
        finally:
            # 테스트 환경 정리
            self.cleanup_test_environment()
        
        # 테스트 시간 기록
        self.test_stats['test_duration'] = time.time() - start_time
        
        self._log(f"=== 통합 테스트 완료: {self.test_stats['passed_tests']}/{self.test_stats['total_tests']} 통과 ===")
        return results
    
    def _test_settings_integration(self) -> Dict[str, bool]:
        """설정 시스템 통합 테스트"""
        self._log("--- 설정 시스템 통합 테스트 ---")
        results = {}
        
        # 설정 동기화 테스트
        test_name = "settings_sync_integration"
        try:
            # 설정 변경
            new_settings = {
                'common': {
                    'bg': {'enabled': False, 'color': '#FF0000', 'alpha': 0.5, 'margin': 5, 'type': '색상', 'value': ''},
                    'shadow': {'enabled': False, 'thick': 2, 'color': '#00FF00', 'blur': 2, 'offx': 1, 'offy': 1, 'alpha': 0.8, 'useBlur': False},
                    'border': {'enabled': False, 'thick': 2, 'color': '#0000FF'}
                }
            }
            
            # 설정 업데이트
            success = self.sync_manager.update_settings(new_settings, "integration_test")
            
            # 현재 설정 확인
            current_settings = self.sync_manager.get_current_settings()
            merged_settings = self.sync_manager.get_merged_settings()
            
            # 검증
            is_valid = (success and 
                       current_settings is not None and 
                       merged_settings is not None and
                       'common' in current_settings)
            
            results[test_name] = is_valid
            self._record_test_result(test_name, is_valid, "설정 동기화 통합 테스트")
            
        except Exception as e:
            self._log(f"설정 동기화 테스트 실패: {e}")
            results[test_name] = False
            self._record_test_result(test_name, False, f"설정 동기화 테스트 실패: {e}")
        
        return results
    
    def _test_rendering_integration(self) -> Dict[str, bool]:
        """렌더링 시스템 통합 테스트"""
        self._log("--- 렌더링 시스템 통합 테스트 ---")
        results = {}
        
        # 회화 이미지 렌더링 테스트
        test_name = "conversation_rendering_integration"
        try:
            text_data = {
                'order': '1',
                'native_script': '你好',
                'learning_script': '안녕하세요',
                'reading_script': '니하오'
            }
            
            output_path = os.path.join(self.temp_dir, "test_conversation.png")
            resolution = (1920, 1080)
            
            # 렌더링 실행
            success = self.improved_renderer.render_image(
                "회화", text_data, output_path, resolution
            )
            
            # 결과 검증
            is_valid = success and os.path.exists(output_path)
            
            results[test_name] = is_valid
            self._record_test_result(test_name, is_valid, "회화 이미지 렌더링 통합 테스트")
            
        except Exception as e:
            self._log(f"회화 렌더링 테스트 실패: {e}")
            results[test_name] = False
            self._record_test_result(test_name, False, f"회화 렌더링 테스트 실패: {e}")
        
        # 인트로 이미지 렌더링 테스트
        test_name = "intro_rendering_integration"
        try:
            text_data = "**중국어 기초 회화**를 시작합니다."
            
            output_path = os.path.join(self.temp_dir, "test_intro.png")
            resolution = (1920, 1080)
            
            # 렌더링 실행
            success = self.improved_renderer.render_image(
                "인트로", text_data, output_path, resolution
            )
            
            # 결과 검증
            is_valid = success and os.path.exists(output_path)
            
            results[test_name] = is_valid
            self._record_test_result(test_name, is_valid, "인트로 이미지 렌더링 통합 테스트")
            
        except Exception as e:
            self._log(f"인트로 렌더링 테스트 실패: {e}")
            results[test_name] = False
            self._record_test_result(test_name, False, f"인트로 렌더링 테스트 실패: {e}")
        
        return results
    
    def _test_pipeline_context_integration(self) -> Dict[str, bool]:
        """파이프라인 컨텍스트 통합 테스트"""
        self._log("--- 파이프라인 컨텍스트 통합 테스트 ---")
        results = {}
        
        test_name = "pipeline_context_integration"
        try:
            # PipelineContext 생성
            context = PipelineContext.create(
                project_name="test_project",
                identifier="test_001",
                manifest=self.test_manifest,
                settings=self.sync_manager.get_current_settings()
            )
            
            # 컨텍스트 검증
            is_valid = (
                context.project_name == "test_project" and
                context.identifier == "test_001" and
                context.manifest is not None and
                context.settings is not None and
                len(context.manifest.scenes) == 3
            )
            
            results[test_name] = is_valid
            self._record_test_result(test_name, is_valid, "파이프라인 컨텍스트 통합 테스트")
            
        except Exception as e:
            self._log(f"파이프라인 컨텍스트 테스트 실패: {e}")
            results[test_name] = False
            self._record_test_result(test_name, False, f"파이프라인 컨텍스트 테스트 실패: {e}")
        
        return results
    
    def _test_end_to_end_integration(self) -> Dict[str, bool]:
        """End-to-End 통합 테스트"""
        self._log("--- End-to-End 통합 테스트 ---")
        results = {}
        
        test_name = "end_to_end_integration"
        try:
            # 전체 파이프라인 시뮬레이션
            # 1. 설정 로드
            settings = self.sync_manager.get_current_settings()
            
            # 2. Manifest 처리
            manifest = self.test_manifest
            
            # 3. 각 씬별 렌더링
            rendering_success = True
            for scene in manifest.scenes:
                if scene.type == "conversation":
                    text_data = {
                        'order': str(scene.sequence),
                        'native_script': scene.native_script,
                        'learning_script': scene.learning_script,
                        'reading_script': scene.reading_script
                    }
                    output_path = os.path.join(self.temp_dir, f"test_{scene.id}.png")
                    success = self.improved_renderer.render_image(
                        "회화", text_data, output_path, (1920, 1080)
                    )
                    rendering_success = rendering_success and success
                
                elif scene.type in ["intro", "ending"]:
                    text_data = scene.full_script
                    output_path = os.path.join(self.temp_dir, f"test_{scene.id}.png")
                    success = self.improved_renderer.render_image(
                        scene.type, text_data, output_path, (1920, 1080)
                    )
                    rendering_success = rendering_success and success
            
            # 4. 결과 검증
            is_valid = rendering_success
            
            results[test_name] = is_valid
            self._record_test_result(test_name, is_valid, "End-to-End 통합 테스트")
            
        except Exception as e:
            self._log(f"End-to-End 테스트 실패: {e}")
            results[test_name] = False
            self._record_test_result(test_name, False, f"End-to-End 테스트 실패: {e}")
        
        return results
    
    def _record_test_result(self, test_name: str, passed: bool, description: str) -> None:
        """테스트 결과 기록"""
        test_result = {
            'test_name': test_name,
            'passed': passed,
            'description': description,
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(test_result)
        
        self.test_stats['total_tests'] += 1
        if passed:
            self.test_stats['passed_tests'] += 1
            self._log(f"✅ {test_name}: 통과")
        else:
            self.test_stats['failed_tests'] += 1
            self._log(f"❌ {test_name}: 실패")
    
    def _log(self, message: str) -> None:
        """로그 기록"""
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] {message}"
        
        try:
            with open(self.test_log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry + '\n')
        except Exception as e:
            print(f"로그 기록 실패: {e}")
        
        print(log_entry)
    
    def generate_integration_report(self) -> str:
        """통합 테스트 보고서 생성"""
        try:
            report = []
            report.append("=== 전체 시스템 통합 테스트 보고서 ===")
            report.append(f"생성 시간: {datetime.now()}")
            report.append("")
            
            # 테스트 통계
            report.append("통합 테스트 통계:")
            report.append(f"  - 총 테스트: {self.test_stats['total_tests']}개")
            report.append(f"  - 통과: {self.test_stats['passed_tests']}개")
            report.append(f"  - 실패: {self.test_stats['failed_tests']}개")
            report.append(f"  - 성공률: {(self.test_stats['passed_tests'] / self.test_stats['total_tests'] * 100) if self.test_stats['total_tests'] > 0 else 0:.1f}%")
            report.append(f"  - 테스트 시간: {self.test_stats['test_duration']:.3f}초")
            report.append("")
            
            # 테스트 결과 상세
            report.append("통합 테스트 결과 상세:")
            for result in self.test_results:
                status = "✅ 통과" if result['passed'] else "❌ 실패"
                report.append(f"  - {result['test_name']}: {status}")
                report.append(f"    설명: {result['description']}")
                report.append(f"    실행 시간: {result['timestamp']}")
                report.append("")
            
            # 렌더링 통계
            if self.improved_renderer:
                render_stats = self.improved_renderer.get_render_stats()
                report.append("렌더링 통계:")
                report.append(f"  - 총 렌더링: {render_stats['total_renders']}회")
                report.append(f"  - 성공: {render_stats['successful_renders']}회")
                report.append(f"  - 실패: {render_stats['failed_renders']}회")
                report.append(f"  - 성공률: {render_stats['success_rate']:.1f}%")
                report.append(f"  - 평균 렌더링 시간: {render_stats['average_render_time']:.3f}초")
                report.append("")
            
            return '\n'.join(report)
            
        except Exception as e:
            return f"통합 테스트 보고서 생성 실패: {e}"
    
    def export_integration_results(self, filepath: str) -> bool:
        """통합 테스트 결과 내보내기"""
        try:
            export_data = {
                'export_time': datetime.now().isoformat(),
                'test_stats': self.test_stats,
                'test_results': self.test_results,
                'renderer_stats': self.improved_renderer.get_render_stats() if self.improved_renderer else None
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
            
            self._log(f"통합 테스트 결과 내보내기 완료: {filepath}")
            return True
            
        except Exception as e:
            self._log(f"통합 테스트 결과 내보내기 실패: {e}")
            return False
    
    def get_integration_summary(self) -> Dict[str, Any]:
        """통합 테스트 요약 정보 반환"""
        return {
            'total_tests': self.test_stats['total_tests'],
            'passed_tests': self.test_stats['passed_tests'],
            'failed_tests': self.test_stats['failed_tests'],
            'success_rate': (self.test_stats['passed_tests'] / self.test_stats['total_tests'] * 100) if self.test_stats['total_tests'] > 0 else 0,
            'test_duration': self.test_stats['test_duration'],
            'results_count': len(self.test_results)
        }
