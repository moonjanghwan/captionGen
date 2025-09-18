"""
설정 반영 테스트 시스템

UI 설정이 파이프라인에 올바르게 반영되는지 검증하는 테스트 시스템입니다.
"""

import json
import os
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from ..settings.sync_manager import SettingSyncManager
from ..settings.debugger import SettingDebugger
from ..settings.merger import SettingMerger
from ..settings.validator import SettingValidator
# ImprovedImageRenderer는 삭제됨 - PNGRenderer 사용


class SettingReflectionTest:
    """설정 반영 테스트 클래스"""
    
    def __init__(self, test_log_file: str = "setting_reflection_test.log"):
        self.test_cases: List[Dict[str, Any]] = []
        self.test_results: List[Dict[str, Any]] = []
        self.log_file = test_log_file
        
        # 테스트용 컴포넌트 초기화
        self.sync_manager = SettingSyncManager("test_sync.log")
        self.debugger = SettingDebugger(test_log_file)
        self.merger = SettingMerger()
        self.validator = SettingValidator()
        
        # 테스트 통계
        self.test_stats = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'test_duration': 0.0
        }
    
    def add_test_case(self, script_type: str, expected_settings: Dict[str, Any], 
                     test_name: str = None) -> None:
        """테스트 케이스 추가"""
        test_case = {
            'test_name': test_name or f"test_{script_type}_{len(self.test_cases)}",
            'script_type': script_type,
            'expected': expected_settings,
            'created_at': datetime.now().isoformat()
        }
        self.test_cases.append(test_case)
        self._log(f"테스트 케이스 추가: {test_case['test_name']}")
    
    def add_default_test_cases(self) -> None:
        """기본 테스트 케이스들 추가"""
        # 회화 설정 테스트
        conversation_settings = {
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
                }
            }
        }
        self.add_test_case("회화", conversation_settings, "회화_기본_설정_테스트")
        
        # 인트로 설정 테스트
        intro_settings = {
            'common': {
                'bg': {'enabled': True, 'color': '#000000', 'alpha': 0.2, 'margin': 2, 'type': '이미지', 'value': ''},
                'shadow': {'enabled': True, 'thick': 4, 'color': '#000000', 'blur': 4, 'offx': 3, 'offy': 3, 'alpha': 1.0, 'useBlur': True},
                'border': {'enabled': True, 'thick': 4, 'color': '#000000'}
            },
            'tabs': {
                '인트로 설정': {
                    '행수': 1,
                    '비율': '16:9',
                    '해상도': '1920x1080',
                    'rows': [
                        {'행': '1행', 'x': 100, 'y': 500, 'w': 1820, '크기(pt)': 80, '폰트(pt)': 'Noto Sans KR', '색상': '#FFFFFF', '굵기': False, '좌우 정렬': 'center', '상하 정렬': 'center', '바탕': False, '쉐도우': True, '외곽선': True}
                    ]
                }
            }
        }
        self.add_test_case("인트로", intro_settings, "인트로_기본_설정_테스트")
        
        # 엔딩 설정 테스트
        ending_settings = {
            'common': {
                'bg': {'enabled': True, 'color': '#000000', 'alpha': 0.2, 'margin': 2, 'type': '이미지', 'value': ''},
                'shadow': {'enabled': True, 'thick': 4, 'color': '#000000', 'blur': 4, 'offx': 3, 'offy': 3, 'alpha': 1.0, 'useBlur': True},
                'border': {'enabled': True, 'thick': 4, 'color': '#000000'}
            },
            'tabs': {
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
        self.add_test_case("엔딩", ending_settings, "엔딩_기본_설정_테스트")
        
        # 썸네일 설정 테스트
        thumbnail_settings = {
            'common': {
                'bg': {'enabled': True, 'color': '#000000', 'alpha': 0.2, 'margin': 2, 'type': '이미지', 'value': ''},
                'shadow': {'enabled': True, 'thick': 4, 'color': '#000000', 'blur': 4, 'offx': 3, 'offy': 3, 'alpha': 1.0, 'useBlur': True},
                'border': {'enabled': True, 'thick': 4, 'color': '#000000'}
            },
            'tabs': {
                '썸네일 설정': {
                    '행수': 4,
                    '비율': '16:9',
                    '해상도': '1920x1080',
                    'rows': [
                        {'행': '1행', 'x': 100, 'y': 200, 'w': 1800, '크기(pt)': 60, '폰트(pt)': 'Noto Sans KR', '색상': '#FFFFFF', '굵기': True, '좌우 정렬': 'center', '상하 정렬': 'center', '바탕': False, '쉐도우': True, '외곽선': True},
                        {'행': '2행', 'x': 100, 'y': 400, 'w': 1800, '크기(pt)': 60, '폰트(pt)': 'Noto Sans KR', '색상': '#FFFFFF', '굵기': True, '좌우 정렬': 'center', '상하 정렬': 'center', '바탕': False, '쉐도우': True, '외곽선': True},
                        {'행': '3행', 'x': 100, 'y': 600, 'w': 1800, '크기(pt)': 60, '폰트(pt)': 'Noto Sans KR', '색상': '#FFFFFF', '굵기': True, '좌우 정렬': 'center', '상하 정렬': 'center', '바탕': False, '쉐도우': True, '외곽선': True},
                        {'행': '4행', 'x': 100, 'y': 800, 'w': 1800, '크기(pt)': 60, '폰트(pt)': 'Noto Sans KR', '색상': '#FFFFFF', '굵기': True, '좌우 정렬': 'center', '상하 정렬': 'center', '바탕': False, '쉐도우': True, '외곽선': True}
                    ]
                }
            }
        }
        self.add_test_case("썸네일", thumbnail_settings, "썸네일_기본_설정_테스트")
    
    def run_all_tests(self) -> Dict[str, bool]:
        """모든 테스트 실행"""
        import time
        start_time = time.time()
        
        self._log("=== 설정 반영 테스트 시작 ===")
        results = {}
        
        for test_case in self.test_cases:
            test_name = test_case['test_name']
            script_type = test_case['script_type']
            expected = test_case['expected']
            
            self._log(f"테스트 실행: {test_name}")
            
            try:
                # 실제 설정 로드
                actual = self._load_actual_settings(script_type, expected)
                
                # 비교
                is_match = self._compare_settings(expected, actual)
                results[test_name] = is_match
                
                # 결과 기록
                test_result = {
                    'test_name': test_name,
                    'script_type': script_type,
                    'passed': is_match,
                    'expected': expected,
                    'actual': actual,
                    'timestamp': datetime.now().isoformat()
                }
                self.test_results.append(test_result)
                
                if is_match:
                    self._log(f"✅ 테스트 통과: {test_name}")
                    self.test_stats['passed_tests'] += 1
                else:
                    self._log(f"❌ 테스트 실패: {test_name}")
                    self._log_mismatch(test_name, expected, actual)
                    self.test_stats['failed_tests'] += 1
                
                self.test_stats['total_tests'] += 1
                
            except Exception as e:
                self._log(f"❌ 테스트 오류: {test_name}, 오류: {e}")
                results[test_name] = False
                self.test_stats['failed_tests'] += 1
                self.test_stats['total_tests'] += 1
        
        # 테스트 시간 기록
        self.test_stats['test_duration'] = time.time() - start_time
        
        self._log(f"=== 테스트 완료: {self.test_stats['passed_tests']}/{self.test_stats['total_tests']} 통과 ===")
        return results
    
    def _load_actual_settings(self, script_type: str, input_settings: Dict[str, Any]) -> Dict[str, Any]:
        """실제 설정 로드 (병합 및 검증 과정 시뮬레이션)"""
        try:
            # 설정 동기화 관리자에 설정 업데이트
            self.sync_manager.update_settings(input_settings, f"test_{script_type}")
            
            # 현재 설정 가져오기
            current_settings = self.sync_manager.get_current_settings()
            
            # 병합된 설정 가져오기
            merged_settings = self.sync_manager.get_merged_settings()
            
            if merged_settings:
                # 병합된 설정을 딕셔너리로 변환
                actual = {
                    'common': {
                        'bg': merged_settings.common.bg.__dict__,
                        'shadow': merged_settings.common.shadow.__dict__,
                        'border': merged_settings.common.border.__dict__
                    },
                    'tabs': {}
                }
                
                # 스크립트 타입별 설정 변환
                for tab_name, script_settings in merged_settings.script_types.items():
                    actual['tabs'][tab_name] = {
                        '행수': script_settings.row_count,
                        '비율': script_settings.aspect_ratio,
                        '해상도': script_settings.resolution,
                        'rows': [row.__dict__ for row in script_settings.rows]
                    }
                
                return actual
            
            return current_settings
            
        except Exception as e:
            self._log(f"설정 로드 실패: {e}")
            return {}
    
    def _compare_settings(self, expected: Dict[str, Any], actual: Dict[str, Any]) -> bool:
        """설정 비교"""
        try:
            # 공통 설정 비교
            if 'common' in expected and 'common' in actual:
                if not self._compare_dict_recursive(expected['common'], actual['common']):
                    return False
            
            # 스크립트 타입별 설정 비교
            if 'tabs' in expected and 'tabs' in actual:
                if not self._compare_dict_recursive(expected['tabs'], actual['tabs']):
                    return False
            
            return True
            
        except Exception as e:
            self._log(f"설정 비교 오류: {e}")
            return False
    
    def _compare_dict_recursive(self, expected: Dict[str, Any], actual: Dict[str, Any]) -> bool:
        """딕셔너리 재귀 비교"""
        for key, expected_value in expected.items():
            if key not in actual:
                return False
            
            actual_value = actual[key]
            
            if isinstance(expected_value, dict) and isinstance(actual_value, dict):
                if not self._compare_dict_recursive(expected_value, actual_value):
                    return False
            elif isinstance(expected_value, list) and isinstance(actual_value, list):
                if not self._compare_list_recursive(expected_value, actual_value):
                    return False
            else:
                if expected_value != actual_value:
                    return False
        
        return True
    
    def _compare_list_recursive(self, expected: List[Any], actual: List[Any]) -> bool:
        """리스트 재귀 비교"""
        if len(expected) != len(actual):
            return False
        
        for i, expected_item in enumerate(expected):
            actual_item = actual[i]
            
            if isinstance(expected_item, dict) and isinstance(actual_item, dict):
                if not self._compare_dict_recursive(expected_item, actual_item):
                    return False
            elif isinstance(expected_item, list) and isinstance(actual_item, list):
                if not self._compare_list_recursive(expected_item, actual_item):
                    return False
            else:
                if expected_item != actual_item:
                    return False
        
        return True
    
    def _log_mismatch(self, test_name: str, expected: Dict[str, Any], actual: Dict[str, Any]) -> None:
        """설정 불일치 로깅"""
        self._log(f"설정 불일치 - {test_name}:")
        self._log(f"예상값: {json.dumps(expected, indent=2, ensure_ascii=False)}")
        self._log(f"실제값: {json.dumps(actual, indent=2, ensure_ascii=False)}")
    
    def _log(self, message: str) -> None:
        """로그 기록"""
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] {message}"
        
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry + '\n')
        except Exception as e:
            print(f"로그 기록 실패: {e}")
        
        print(log_entry)
    
    def generate_test_report(self) -> str:
        """테스트 보고서 생성"""
        try:
            report = []
            report.append("=== 설정 반영 테스트 보고서 ===")
            report.append(f"생성 시간: {datetime.now()}")
            report.append("")
            
            # 테스트 통계
            report.append("테스트 통계:")
            report.append(f"  - 총 테스트: {self.test_stats['total_tests']}개")
            report.append(f"  - 통과: {self.test_stats['passed_tests']}개")
            report.append(f"  - 실패: {self.test_stats['failed_tests']}개")
            report.append(f"  - 성공률: {(self.test_stats['passed_tests'] / self.test_stats['total_tests'] * 100) if self.test_stats['total_tests'] > 0 else 0:.1f}%")
            report.append(f"  - 테스트 시간: {self.test_stats['test_duration']:.3f}초")
            report.append("")
            
            # 테스트 결과 상세
            report.append("테스트 결과 상세:")
            for result in self.test_results:
                status = "✅ 통과" if result['passed'] else "❌ 실패"
                report.append(f"  - {result['test_name']}: {status}")
                report.append(f"    스크립트 타입: {result['script_type']}")
                report.append(f"    실행 시간: {result['timestamp']}")
                if not result['passed']:
                    report.append(f"    예상값: {json.dumps(result['expected'], indent=4, ensure_ascii=False)}")
                    report.append(f"    실제값: {json.dumps(result['actual'], indent=4, ensure_ascii=False)}")
                report.append("")
            
            return '\n'.join(report)
            
        except Exception as e:
            return f"보고서 생성 실패: {e}"
    
    def export_test_results(self, filepath: str) -> bool:
        """테스트 결과 내보내기"""
        try:
            export_data = {
                'export_time': datetime.now().isoformat(),
                'test_stats': self.test_stats,
                'test_results': self.test_results,
                'test_cases': self.test_cases
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
            
            self._log(f"테스트 결과 내보내기 완료: {filepath}")
            return True
            
        except Exception as e:
            self._log(f"테스트 결과 내보내기 실패: {e}")
            return False
    
    def clear_test_results(self) -> None:
        """테스트 결과 초기화"""
        self.test_results.clear()
        self.test_stats = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'test_duration': 0.0
        }
        self._log("테스트 결과 초기화 완료")
    
    def get_test_summary(self) -> Dict[str, Any]:
        """테스트 요약 정보 반환"""
        return {
            'total_tests': self.test_stats['total_tests'],
            'passed_tests': self.test_stats['passed_tests'],
            'failed_tests': self.test_stats['failed_tests'],
            'success_rate': (self.test_stats['passed_tests'] / self.test_stats['total_tests'] * 100) if self.test_stats['total_tests'] > 0 else 0,
            'test_duration': self.test_stats['test_duration'],
            'test_cases_count': len(self.test_cases),
            'results_count': len(self.test_results)
        }
