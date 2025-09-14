"""
테스트 실행기 및 보고서 생성 시스템

모든 테스트를 통합하여 실행하고 종합적인 보고서를 생성하는 시스템입니다.
"""

import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from .setting_reflection_test import SettingReflectionTest
from .system_integration_test import SystemIntegrationTest
from .performance_test import PerformanceTest


class TestRunner:
    """통합 테스트 실행기"""
    
    def __init__(self, output_dir: str = "test_results"):
        self.output_dir = output_dir
        self.test_suites: List[Dict[str, Any]] = []
        self.overall_results: Dict[str, Any] = {}
        
        # 출력 디렉토리 생성
        os.makedirs(output_dir, exist_ok=True)
        
        # 테스트 스위트 초기화
        self._initialize_test_suites()
    
    def _initialize_test_suites(self) -> None:
        """테스트 스위트 초기화"""
        self.test_suites = [
            {
                'name': 'setting_reflection_test',
                'class': SettingReflectionTest,
                'description': '설정 반영 테스트',
                'enabled': True
            },
            {
                'name': 'system_integration_test',
                'class': SystemIntegrationTest,
                'description': '시스템 통합 테스트',
                'enabled': True
            },
            {
                'name': 'performance_test',
                'class': PerformanceTest,
                'description': '성능 테스트 및 벤치마크',
                'enabled': True
            }
        ]
    
    def run_all_tests(self, include_performance: bool = True) -> Dict[str, Any]:
        """모든 테스트 실행"""
        print("=" * 80)
        print("🚀 통합 테스트 실행기 시작")
        print("=" * 80)
        
        start_time = datetime.now()
        overall_results = {
            'start_time': start_time.isoformat(),
            'test_suites': {},
            'summary': {
                'total_tests': 0,
                'passed_tests': 0,
                'failed_tests': 0,
                'success_rate': 0.0
            }
        }
        
        # 각 테스트 스위트 실행
        for suite in self.test_suites:
            if not suite['enabled']:
                print(f"⏭️  {suite['description']} 건너뛰기 (비활성화)")
                continue
            
            # 성능 테스트는 선택적으로 실행
            if suite['name'] == 'performance_test' and not include_performance:
                print(f"⏭️  {suite['description']} 건너뛰기 (성능 테스트 제외)")
                continue
            
            print(f"\n📋 {suite['description']} 실행 중...")
            print("-" * 60)
            
            try:
                suite_results = self._run_test_suite(suite)
                overall_results['test_suites'][suite['name']] = suite_results
                
                # 요약 통계 업데이트
                if 'summary' in suite_results:
                    summary = suite_results['summary']
                    overall_results['summary']['total_tests'] += summary.get('total_tests', 0)
                    overall_results['summary']['passed_tests'] += summary.get('passed_tests', 0)
                    overall_results['summary']['failed_tests'] += summary.get('failed_tests', 0)
                
                print(f"✅ {suite['description']} 완료")
                
            except Exception as e:
                print(f"❌ {suite['description']} 실패: {e}")
                overall_results['test_suites'][suite['name']] = {
                    'error': str(e),
                    'status': 'failed'
                }
        
        # 전체 성공률 계산
        if overall_results['summary']['total_tests'] > 0:
            overall_results['summary']['success_rate'] = (
                overall_results['summary']['passed_tests'] / 
                overall_results['summary']['total_tests'] * 100
            )
        
        end_time = datetime.now()
        overall_results['end_time'] = end_time.isoformat()
        overall_results['duration'] = (end_time - start_time).total_seconds()
        
        self.overall_results = overall_results
        
        # 결과 출력
        self._print_summary()
        
        # 보고서 생성
        self._generate_comprehensive_report()
        
        return overall_results
    
    def _run_test_suite(self, suite: Dict[str, Any]) -> Dict[str, Any]:
        """개별 테스트 스위트 실행"""
        suite_name = suite['name']
        suite_class = suite['class']
        
        # 테스트 스위트 인스턴스 생성
        log_file = os.path.join(self.output_dir, f"{suite_name}.log")
        test_instance = suite_class(log_file)
        
        suite_results = {
            'name': suite_name,
            'description': suite['description'],
            'start_time': datetime.now().isoformat(),
            'status': 'running'
        }
        
        try:
            if suite_name == 'setting_reflection_test':
                # 설정 반영 테스트 실행
                test_instance.add_default_test_cases()
                test_results = test_instance.run_all_tests()
                suite_results['test_results'] = test_results
                suite_results['summary'] = test_instance.get_test_summary()
                suite_results['report'] = test_instance.generate_test_report()
                
            elif suite_name == 'system_integration_test':
                # 시스템 통합 테스트 실행
                test_results = test_instance.run_all_integration_tests()
                suite_results['test_results'] = test_results
                suite_results['summary'] = test_instance.get_integration_summary()
                suite_results['report'] = test_instance.generate_integration_report()
                
            elif suite_name == 'performance_test':
                # 성능 테스트 실행
                performance_results = {}
                
                # 렌더링 성능 벤치마크
                print("  🔄 렌더링 성능 벤치마크 실행...")
                rendering_results = test_instance.run_rendering_performance_benchmark(iterations=5)
                performance_results['rendering_benchmark'] = rendering_results
                
                # 메모리 사용량 테스트
                print("  🧠 메모리 사용량 테스트 실행...")
                memory_results = test_instance.run_memory_usage_test(iterations=3)
                performance_results['memory_usage'] = memory_results
                
                # 동시 렌더링 테스트
                print("  ⚡ 동시 렌더링 테스트 실행...")
                concurrent_results = test_instance.run_concurrent_rendering_test(concurrent_count=2)
                performance_results['concurrent_rendering'] = concurrent_results
                
                suite_results['performance_results'] = performance_results
                suite_results['report'] = test_instance.generate_performance_report()
                
                # 성능 테스트 요약
                suite_results['summary'] = {
                    'total_tests': 3,  # 렌더링, 메모리, 동시 렌더링
                    'passed_tests': sum(1 for result in performance_results.values() if result),
                    'failed_tests': sum(1 for result in performance_results.values() if not result),
                    'success_rate': (sum(1 for result in performance_results.values() if result) / 3 * 100) if performance_results else 0
                }
            
            suite_results['end_time'] = datetime.now().isoformat()
            suite_results['status'] = 'completed'
            
            # 개별 보고서 저장
            report_file = os.path.join(self.output_dir, f"{suite_name}_report.txt")
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(suite_results['report'])
            
            # 결과 내보내기
            results_file = os.path.join(self.output_dir, f"{suite_name}_results.json")
            if suite_name == 'setting_reflection_test':
                test_instance.export_test_results(results_file)
            elif suite_name == 'system_integration_test':
                test_instance.export_integration_results(results_file)
            elif suite_name == 'performance_test':
                test_instance.export_performance_results(results_file)
            
            return suite_results
            
        except Exception as e:
            suite_results['error'] = str(e)
            suite_results['status'] = 'failed'
            suite_results['end_time'] = datetime.now().isoformat()
            return suite_results
    
    def _print_summary(self) -> None:
        """테스트 결과 요약 출력"""
        print("\n" + "=" * 80)
        print("📊 테스트 결과 요약")
        print("=" * 80)
        
        summary = self.overall_results['summary']
        print(f"총 테스트: {summary['total_tests']}개")
        print(f"통과: {summary['passed_tests']}개")
        print(f"실패: {summary['failed_tests']}개")
        print(f"성공률: {summary['success_rate']:.1f}%")
        print(f"총 실행 시간: {self.overall_results['duration']:.2f}초")
        
        print("\n📋 테스트 스위트별 결과:")
        for suite_name, suite_results in self.overall_results['test_suites'].items():
            if 'error' in suite_results:
                print(f"  ❌ {suite_name}: 오류 - {suite_results['error']}")
            else:
                suite_summary = suite_results.get('summary', {})
                success_rate = suite_summary.get('success_rate', 0)
                status_icon = "✅" if success_rate >= 80 else "⚠️" if success_rate >= 60 else "❌"
                print(f"  {status_icon} {suite_name}: {success_rate:.1f}% 성공")
    
    def _generate_comprehensive_report(self) -> None:
        """종합 보고서 생성"""
        report_file = os.path.join(self.output_dir, "comprehensive_test_report.txt")
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("🎯 통합 테스트 종합 보고서\n")
                f.write("=" * 80 + "\n")
                f.write(f"생성 시간: {datetime.now()}\n")
                f.write(f"실행 시간: {self.overall_results['start_time']} ~ {self.overall_results['end_time']}\n")
                f.write(f"총 실행 시간: {self.overall_results['duration']:.2f}초\n\n")
                
                # 전체 요약
                summary = self.overall_results['summary']
                f.write("📊 전체 요약\n")
                f.write("-" * 40 + "\n")
                f.write(f"총 테스트: {summary['total_tests']}개\n")
                f.write(f"통과: {summary['passed_tests']}개\n")
                f.write(f"실패: {summary['failed_tests']}개\n")
                f.write(f"성공률: {summary['success_rate']:.1f}%\n\n")
                
                # 테스트 스위트별 상세 결과
                f.write("📋 테스트 스위트별 상세 결과\n")
                f.write("-" * 40 + "\n")
                
                for suite_name, suite_results in self.overall_results['test_suites'].items():
                    f.write(f"\n🔍 {suite_results.get('description', suite_name)}\n")
                    f.write(f"상태: {suite_results.get('status', 'unknown')}\n")
                    
                    if 'error' in suite_results:
                        f.write(f"오류: {suite_results['error']}\n")
                    else:
                        suite_summary = suite_results.get('summary', {})
                        f.write(f"총 테스트: {suite_summary.get('total_tests', 0)}개\n")
                        f.write(f"통과: {suite_summary.get('passed_tests', 0)}개\n")
                        f.write(f"실패: {suite_summary.get('failed_tests', 0)}개\n")
                        f.write(f"성공률: {suite_summary.get('success_rate', 0):.1f}%\n")
                        
                        # 성능 테스트 특별 처리
                        if suite_name == 'performance_test' and 'performance_results' in suite_results:
                            perf_results = suite_results['performance_results']
                            f.write("\n성능 테스트 결과:\n")
                            
                            if 'rendering_benchmark' in perf_results and perf_results['rendering_benchmark']:
                                rendering = perf_results['rendering_benchmark']
                                f.write(f"  - 렌더링 벤치마크: {rendering.get('total_time', 0):.3f}초\n")
                            
                            if 'memory_usage' in perf_results and perf_results['memory_usage']:
                                memory = perf_results['memory_usage']
                                f.write(f"  - 최대 메모리 사용량: {memory.get('peak_memory', 0):.2f}MB\n")
                            
                            if 'concurrent_rendering' in perf_results and perf_results['concurrent_rendering']:
                                concurrent = perf_results['concurrent_rendering']
                                f.write(f"  - 동시 렌더링: {concurrent.get('success_count', 0)}/{concurrent.get('concurrent_count', 0)} 성공\n")
                
                f.write("\n" + "=" * 80 + "\n")
                f.write("📁 상세 보고서 파일들:\n")
                f.write("-" * 40 + "\n")
                f.write("- setting_reflection_test_report.txt: 설정 반영 테스트 상세 보고서\n")
                f.write("- system_integration_test_report.txt: 시스템 통합 테스트 상세 보고서\n")
                f.write("- performance_test_report.txt: 성능 테스트 상세 보고서\n")
                f.write("- *_results.json: 각 테스트의 JSON 결과 파일들\n")
                f.write("- *.log: 각 테스트의 로그 파일들\n")
            
            print(f"\n📄 종합 보고서 생성 완료: {report_file}")
            
        except Exception as e:
            print(f"❌ 종합 보고서 생성 실패: {e}")
    
    def export_overall_results(self, filepath: str = None) -> bool:
        """전체 결과 내보내기"""
        if filepath is None:
            filepath = os.path.join(self.output_dir, "overall_test_results.json")
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.overall_results, f, indent=2, ensure_ascii=False, default=str)
            
            print(f"📊 전체 결과 내보내기 완료: {filepath}")
            return True
            
        except Exception as e:
            print(f"❌ 전체 결과 내보내기 실패: {e}")
            return False
    
    def get_test_summary(self) -> Dict[str, Any]:
        """테스트 요약 정보 반환"""
        return {
            'overall_summary': self.overall_results.get('summary', {}),
            'test_suites_count': len(self.overall_results.get('test_suites', {})),
            'total_duration': self.overall_results.get('duration', 0),
            'output_directory': self.output_dir
        }
