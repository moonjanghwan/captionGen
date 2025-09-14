"""
성능 테스트 및 벤치마크 시스템

시스템의 성능을 측정하고 벤치마크를 수행하는 테스트 시스템입니다.
"""

import time
import os
import json
import tempfile
import queue
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from ..settings.sync_manager import SettingSyncManager
from ..settings.debugger import SettingDebugger
from ..renderers.improved_renderer import ImprovedImageRenderer
from ..core.context import PipelineContext
from ..manifest.models import Manifest, Scene, SceneContent


class PerformanceTest:
    """성능 테스트 및 벤치마크 클래스"""
    
    def __init__(self, test_log_file: str = "performance_test.log"):
        self.test_log_file = test_log_file
        self.benchmark_results: List[Dict[str, Any]] = []
        
        # 테스트용 컴포넌트 초기화
        self.sync_manager = SettingSyncManager("test_sync.log")
        self.debugger = SettingDebugger(test_log_file)
        self.improved_renderer = ImprovedImageRenderer(self.sync_manager, "test_renderer_debug.log")
        
        # 성능 통계
        self.performance_stats = {
            'total_benchmarks': 0,
            'average_rendering_time': 0.0,
            'min_rendering_time': float('inf'),
            'max_rendering_time': 0.0,
            'total_rendering_time': 0.0,
            'memory_usage': [],
            'cpu_usage': []
        }
        
        # 테스트용 임시 디렉토리
        self.temp_dir = None
    
    def setup_performance_test_environment(self) -> str:
        """성능 테스트 환경 설정"""
        try:
            # 임시 디렉토리 생성
            self.temp_dir = tempfile.mkdtemp(prefix="captiongen_perf_test_")
            self._log(f"성능 테스트 환경 설정: {self.temp_dir}")
            
            # 테스트용 설정 설정
            self._setup_performance_test_settings()
            
            return self.temp_dir
            
        except Exception as e:
            self._log(f"성능 테스트 환경 설정 실패: {e}")
            return ""
    
    def cleanup_performance_test_environment(self) -> None:
        """성능 테스트 환경 정리"""
        try:
            if self.temp_dir and os.path.exists(self.temp_dir):
                import shutil
                shutil.rmtree(self.temp_dir)
                self._log(f"성능 테스트 환경 정리 완료: {self.temp_dir}")
            
            # 렌더러 정리
            if self.improved_renderer:
                self.improved_renderer.cleanup()
            
        except Exception as e:
            self._log(f"성능 테스트 환경 정리 실패: {e}")
    
    def _setup_performance_test_settings(self) -> None:
        """성능 테스트용 설정 설정"""
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
                }
            }
        }
        
        self.sync_manager.update_settings(test_settings, "performance_test")
        self._log("성능 테스트용 설정 설정 완료")
    
    def run_rendering_performance_benchmark(self, iterations: int = 10) -> Dict[str, Any]:
        """렌더링 성능 벤치마크"""
        self._log(f"--- 렌더링 성능 벤치마크 시작 (반복: {iterations}회) ---")
        
        # 테스트 환경 설정
        test_dir = self.setup_performance_test_environment()
        if not test_dir:
            return {}
        
        try:
            # 테스트 데이터 준비
            test_data = {
                'conversation': {
                    'order': '1',
                    'native_script': '你好，我是小明',
                    'learning_script': '안녕하세요, 저는 샤오밍입니다',
                    'reading_script': '니하오, 워 시 샤오밍'
                },
                'intro': '**중국어 기초 회화**를 시작합니다. 오늘은 인사말을 배워보겠습니다.',
                'ending': '수고하셨습니다. 다음에 또 만나요!'
            }
            
            # 벤치마크 실행
            benchmark_results = {
                'conversation_times': [],
                'intro_times': [],
                'ending_times': [],
                'total_time': 0.0,
                'iterations': iterations
            }
            
            start_time = time.time()
            
            for i in range(iterations):
                self._log(f"반복 {i+1}/{iterations}")
                
                # 회화 렌더링 벤치마크
                conv_time = self._benchmark_conversation_rendering(test_dir, test_data['conversation'], i)
                benchmark_results['conversation_times'].append(conv_time)
                
                # 인트로 렌더링 벤치마크
                intro_time = self._benchmark_intro_rendering(test_dir, test_data['intro'], i)
                benchmark_results['intro_times'].append(intro_time)
                
                # 엔딩 렌더링 벤치마크
                ending_time = self._benchmark_ending_rendering(test_dir, test_data['ending'], i)
                benchmark_results['ending_times'].append(ending_time)
            
            benchmark_results['total_time'] = time.time() - start_time
            
            # 통계 계산
            self._calculate_performance_stats(benchmark_results)
            
            # 결과 기록
            self._record_benchmark_result("rendering_performance", benchmark_results)
            
            self._log(f"렌더링 성능 벤치마크 완료: 총 {benchmark_results['total_time']:.3f}초")
            
            return benchmark_results
            
        finally:
            self.cleanup_performance_test_environment()
    
    def _benchmark_conversation_rendering(self, test_dir: str, test_data: Dict[str, Any], iteration: int) -> float:
        """회화 렌더링 벤치마크"""
        start_time = time.time()
        
        output_path = os.path.join(test_dir, f"perf_conv_{iteration}.png")
        resolution = (1920, 1080)
        
        success = self.improved_renderer.render_image(
            "회화", test_data, output_path, resolution
        )
        
        end_time = time.time()
        render_time = end_time - start_time
        
        if not success:
            self._log(f"회화 렌더링 실패 (반복 {iteration})")
        
        return render_time
    
    def _benchmark_intro_rendering(self, test_dir: str, test_data: str, iteration: int) -> float:
        """인트로 렌더링 벤치마크"""
        start_time = time.time()
        
        output_path = os.path.join(test_dir, f"perf_intro_{iteration}.png")
        resolution = (1920, 1080)
        
        success = self.improved_renderer.render_image(
            "인트로", test_data, output_path, resolution
        )
        
        end_time = time.time()
        render_time = end_time - start_time
        
        if not success:
            self._log(f"인트로 렌더링 실패 (반복 {iteration})")
        
        return render_time
    
    def _benchmark_ending_rendering(self, test_dir: str, test_data: str, iteration: int) -> float:
        """엔딩 렌더링 벤치마크"""
        start_time = time.time()
        
        output_path = os.path.join(test_dir, f"perf_ending_{iteration}.png")
        resolution = (1920, 1080)
        
        success = self.improved_renderer.render_image(
            "엔딩", test_data, output_path, resolution
        )
        
        end_time = time.time()
        render_time = end_time - start_time
        
        if not success:
            self._log(f"엔딩 렌더링 실패 (반복 {iteration})")
        
        return render_time
    
    def _calculate_performance_stats(self, benchmark_results: Dict[str, Any]) -> None:
        """성능 통계 계산"""
        all_times = (
            benchmark_results['conversation_times'] +
            benchmark_results['intro_times'] +
            benchmark_results['ending_times']
        )
        
        if all_times:
            self.performance_stats['average_rendering_time'] = sum(all_times) / len(all_times)
            self.performance_stats['min_rendering_time'] = min(all_times)
            self.performance_stats['max_rendering_time'] = max(all_times)
            self.performance_stats['total_rendering_time'] = sum(all_times)
        
        self.performance_stats['total_benchmarks'] += 1
    
    def _record_benchmark_result(self, benchmark_name: str, results: Dict[str, Any]) -> None:
        """벤치마크 결과 기록"""
        benchmark_record = {
            'benchmark_name': benchmark_name,
            'results': results,
            'timestamp': datetime.now().isoformat(),
            'performance_stats': self.performance_stats.copy()
        }
        self.benchmark_results.append(benchmark_record)
    
    def run_memory_usage_test(self, iterations: int = 5) -> Dict[str, Any]:
        """메모리 사용량 테스트"""
        self._log(f"--- 메모리 사용량 테스트 시작 (반복: {iterations}회) ---")
        
        try:
            import psutil
            import gc
            
            memory_results = {
                'initial_memory': 0,
                'peak_memory': 0,
                'final_memory': 0,
                'memory_increases': [],
                'iterations': iterations
            }
            
            # 초기 메모리 사용량
            process = psutil.Process()
            memory_results['initial_memory'] = process.memory_info().rss / 1024 / 1024  # MB
            
            # 테스트 환경 설정
            test_dir = self.setup_performance_test_environment()
            if not test_dir:
                return {}
            
            try:
                for i in range(iterations):
                    # 메모리 사용량 측정 시작
                    gc.collect()  # 가비지 컬렉션
                    start_memory = process.memory_info().rss / 1024 / 1024
                    
                    # 렌더링 작업 수행
                    test_data = {
                        'order': f'{i+1}',
                        'native_script': f'测试文本 {i+1}',
                        'learning_script': f'테스트 텍스트 {i+1}',
                        'reading_script': f'테스트 {i+1}'
                    }
                    
                    output_path = os.path.join(test_dir, f"memory_test_{i}.png")
                    self.improved_renderer.render_image(
                        "회화", test_data, output_path, (1920, 1080)
                    )
                    
                    # 메모리 사용량 측정 종료
                    end_memory = process.memory_info().rss / 1024 / 1024
                    memory_increase = end_memory - start_memory
                    
                    memory_results['memory_increases'].append(memory_increase)
                    memory_results['peak_memory'] = max(memory_results['peak_memory'], end_memory)
                    
                    self._log(f"반복 {i+1}: 메모리 증가 {memory_increase:.2f}MB")
                
                # 최종 메모리 사용량
                gc.collect()
                memory_results['final_memory'] = process.memory_info().rss / 1024 / 1024
                
                # 결과 기록
                self._record_benchmark_result("memory_usage", memory_results)
                
                self._log(f"메모리 사용량 테스트 완료: 최대 {memory_results['peak_memory']:.2f}MB")
                
                return memory_results
                
            finally:
                self.cleanup_performance_test_environment()
                
        except ImportError:
            self._log("psutil 모듈이 없어 메모리 테스트를 건너뜁니다.")
            return {}
        except Exception as e:
            self._log(f"메모리 사용량 테스트 실패: {e}")
            return {}
    
    def run_concurrent_rendering_test(self, concurrent_count: int = 3) -> Dict[str, Any]:
        """동시 렌더링 테스트"""
        self._log(f"--- 동시 렌더링 테스트 시작 (동시 실행: {concurrent_count}개) ---")
        
        import threading
        import queue
        
        # 테스트 환경 설정
        test_dir = self.setup_performance_test_environment()
        if not test_dir:
            return {}
        
        try:
            results_queue = queue.Queue()
            threads = []
            
            start_time = time.time()
            
            # 동시 렌더링 스레드 생성
            for i in range(concurrent_count):
                thread = threading.Thread(
                    target=self._concurrent_render_worker,
                    args=(test_dir, i, results_queue)
                )
                threads.append(thread)
                thread.start()
            
            # 모든 스레드 완료 대기
            for thread in threads:
                thread.join()
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # 결과 수집
            concurrent_results = {
                'concurrent_count': concurrent_count,
                'total_time': total_time,
                'individual_times': [],
                'success_count': 0,
                'failure_count': 0
            }
            
            while not results_queue.empty():
                result = results_queue.get()
                concurrent_results['individual_times'].append(result['time'])
                if result['success']:
                    concurrent_results['success_count'] += 1
                else:
                    concurrent_results['failure_count'] += 1
            
            # 결과 기록
            self._record_benchmark_result("concurrent_rendering", concurrent_results)
            
            self._log(f"동시 렌더링 테스트 완료: {concurrent_results['success_count']}/{concurrent_count} 성공")
            
            return concurrent_results
            
        finally:
            self.cleanup_performance_test_environment()
    
    def _concurrent_render_worker(self, test_dir: str, worker_id: int, results_queue: queue.Queue) -> None:
        """동시 렌더링 워커"""
        start_time = time.time()
        
        try:
            test_data = {
                'order': f'{worker_id+1}',
                'native_script': f'并发测试 {worker_id+1}',
                'learning_script': f'동시 테스트 {worker_id+1}',
                'reading_script': f'동시 {worker_id+1}'
            }
            
            output_path = os.path.join(test_dir, f"concurrent_{worker_id}.png")
            success = self.improved_renderer.render_image(
                "회화", test_data, output_path, (1920, 1080)
            )
            
            end_time = time.time()
            render_time = end_time - start_time
            
            results_queue.put({
                'worker_id': worker_id,
                'time': render_time,
                'success': success
            })
            
        except Exception as e:
            self._log(f"동시 렌더링 워커 {worker_id} 실패: {e}")
            results_queue.put({
                'worker_id': worker_id,
                'time': 0.0,
                'success': False
            })
    
    def generate_performance_report(self) -> str:
        """성능 테스트 보고서 생성"""
        try:
            report = []
            report.append("=== 성능 테스트 및 벤치마크 보고서 ===")
            report.append(f"생성 시간: {datetime.now()}")
            report.append("")
            
            # 성능 통계
            report.append("성능 통계:")
            report.append(f"  - 총 벤치마크: {self.performance_stats['total_benchmarks']}개")
            report.append(f"  - 평균 렌더링 시간: {self.performance_stats['average_rendering_time']:.3f}초")
            report.append(f"  - 최소 렌더링 시간: {self.performance_stats['min_rendering_time']:.3f}초")
            report.append(f"  - 최대 렌더링 시간: {self.performance_stats['max_rendering_time']:.3f}초")
            report.append(f"  - 총 렌더링 시간: {self.performance_stats['total_rendering_time']:.3f}초")
            report.append("")
            
            # 벤치마크 결과 상세
            report.append("벤치마크 결과 상세:")
            for benchmark in self.benchmark_results:
                report.append(f"  - {benchmark['benchmark_name']}:")
                report.append(f"    실행 시간: {benchmark['timestamp']}")
                
                if 'results' in benchmark:
                    results = benchmark['results']
                    if 'iterations' in results:
                        report.append(f"    반복 횟수: {results['iterations']}")
                    if 'total_time' in results:
                        report.append(f"    총 시간: {results['total_time']:.3f}초")
                    if 'concurrent_count' in results:
                        report.append(f"    동시 실행: {results['concurrent_count']}개")
                        report.append(f"    성공: {results['success_count']}개")
                        report.append(f"    실패: {results['failure_count']}개")
                
                report.append("")
            
            return '\n'.join(report)
            
        except Exception as e:
            return f"성능 테스트 보고서 생성 실패: {e}"
    
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
    
    def export_performance_results(self, filepath: str) -> bool:
        """성능 테스트 결과 내보내기"""
        try:
            export_data = {
                'export_time': datetime.now().isoformat(),
                'performance_stats': self.performance_stats,
                'benchmark_results': self.benchmark_results
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
            
            self._log(f"성능 테스트 결과 내보내기 완료: {filepath}")
            return True
            
        except Exception as e:
            self._log(f"성능 테스트 결과 내보내기 실패: {e}")
            return False
