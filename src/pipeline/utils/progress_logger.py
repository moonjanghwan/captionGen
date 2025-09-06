"""
진행 상황 및 로그 관리자

파이프라인 실행 과정을 실시간으로 모니터링하고 상세한 로그를 관리합니다.
"""

import os
import json
import time
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class LogEntry:
    """로그 엔트리"""
    timestamp: str
    level: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProgressStep:
    """진행 단계 정보"""
    step_name: str
    step_number: int
    total_steps: int
    status: str  # "pending", "running", "completed", "failed"
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    duration: Optional[float] = None
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


class ProgressLogger:
    """진행 상황 및 로그 관리 클래스"""
    
    def __init__(self, project_name: str, log_dir: str):
        """
        진행 상황 로거 초기화
        
        Args:
            project_name: 프로젝트 이름
            log_dir: 로그 저장 디렉토리
        """
        self.project_name = project_name
        self.log_dir = log_dir
        self.logs: List[LogEntry] = []
        self.progress_steps: List[ProgressStep] = []
        self.current_step: Optional[ProgressStep] = None
        self.start_time = time.time()
        
        # 로그 디렉토리 생성
        os.makedirs(log_dir, exist_ok=True)
        
        # 콜백 함수들
        self.progress_callback: Optional[Callable[[ProgressStep], None]] = None
        self.log_callback: Optional[Callable[[LogEntry], None]] = None
    
    def set_progress_callback(self, callback: Callable[[ProgressStep], None]):
        """진행 상황 콜백 함수 설정"""
        self.progress_callback = callback
    
    def set_log_callback(self, callback: Callable[[LogEntry], None]):
        """로그 콜백 함수 설정"""
        self.log_callback = callback
    
    def add_progress_step(self, step_name: str, step_number: int, total_steps: int):
        """진행 단계 추가"""
        step = ProgressStep(
            step_name=step_name,
            step_number=step_number,
            total_steps=total_steps,
            status="pending"
        )
        self.progress_steps.append(step)
    
    def start_step(self, step_name: str):
        """단계 시작"""
        for step in self.progress_steps:
            if step.step_name == step_name:
                step.status = "running"
                step.start_time = time.time()
                step.message = f"{step_name} 시작..."
                self.current_step = step
                
                # 콜백 호출
                if self.progress_callback:
                    self.progress_callback(step)
                
                self.log_info(f"단계 시작: {step_name}", {
                    "step_number": step.step_number,
                    "total_steps": step.total_steps,
                    "status": "running"
                })
                break
    
    def complete_step(self, step_name: str, message: str = "", details: Dict[str, Any] = None):
        """단계 완료"""
        for step in self.progress_steps:
            if step.step_name == step_name:
                step.status = "completed"
                step.end_time = time.time()
                step.duration = step.end_time - step.start_time if step.start_time else None
                step.message = message or f"{step_name} 완료"
                step.details = details or {}
                self.current_step = None
                
                # 콜백 호출
                if self.progress_callback:
                    self.progress_callback(step)
                
                self.log_info(f"단계 완료: {step_name}", {
                    "step_number": step.step_number,
                    "total_steps": step.total_steps,
                    "status": "completed",
                    "duration": step.duration,
                    "details": step.details
                })
                break
    
    def fail_step(self, step_name: str, error_message: str, error_details: Dict[str, Any] = None):
        """단계 실패"""
        for step in self.progress_steps:
            if step.step_name == step_name:
                step.status = "failed"
                step.end_time = time.time()
                step.duration = step.end_time - step.start_time if step.start_time else None
                step.message = f"{step_name} 실패: {error_message}"
                step.details = error_details or {}
                self.current_step = None
                
                # 콜백 호출
                if self.progress_callback:
                    self.progress_callback(step)
                
                self.log_error(f"단계 실패: {step_name}", {
                    "step_number": step.step_number,
                    "total_steps": step.total_steps,
                    "status": "failed",
                    "duration": step.duration,
                    "error_message": error_message,
                    "error_details": error_details
                })
                break
    
    def update_step_progress(self, step_name: str, progress_percent: float, message: str = ""):
        """단계 진행률 업데이트"""
        for step in self.progress_steps:
            if step.step_name == step_name:
                step.message = message or f"{step_name} 진행 중... ({progress_percent:.1f}%)"
                step.details["progress_percent"] = progress_percent
                
                # 콜백 호출
                if self.progress_callback:
                    self.progress_callback(step)
                break
    
    def log_info(self, message: str, details: Dict[str, Any] = None):
        """정보 로그 추가"""
        self._add_log("INFO", message, details)
    
    def log_warning(self, message: str, details: Dict[str, Any] = None):
        """경고 로그 추가"""
        self._add_log("WARNING", message, details)
    
    def log_error(self, message: str, details: Dict[str, Any] = None):
        """에러 로그 추가"""
        self._add_log("ERROR", message, details)
    
    def log_debug(self, message: str, details: Dict[str, Any] = None):
        """디버그 로그 추가"""
        self._add_log("DEBUG", message, details)
    
    def _add_log(self, level: str, message: str, details: Dict[str, Any] = None):
        """로그 엔트리 추가"""
        entry = LogEntry(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            level=level,
            message=message,
            details=details or {}
        )
        
        self.logs.append(entry)
        
        # 콜백 호출
        if self.log_callback:
            self.log_callback(entry)
        
        # 콘솔 출력
        print(f"[{entry.timestamp}] {level}: {message}")
        if details:
            for key, value in details.items():
                print(f"  {key}: {value}")
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """진행 상황 요약 반환"""
        total_steps = len(self.progress_steps)
        completed_steps = len([s for s in self.progress_steps if s.status == "completed"])
        failed_steps = len([s for s in self.progress_steps if s.status == "failed"])
        running_steps = len([s for s in self.progress_steps if s.status == "running"])
        
        total_duration = time.time() - self.start_time
        
        return {
            "project_name": self.project_name,
            "total_steps": total_steps,
            "completed_steps": completed_steps,
            "failed_steps": failed_steps,
            "running_steps": running_steps,
            "pending_steps": total_steps - completed_steps - failed_steps - running_steps,
            "progress_percent": (completed_steps / total_steps * 100) if total_steps > 0 else 0,
            "total_duration": total_duration,
            "current_step": self.current_step.step_name if self.current_step else None,
            "status": "completed" if failed_steps == 0 and completed_steps == total_steps else "failed" if failed_steps > 0 else "running"
        }
    
    def save_execution_log(self) -> str:
        """실행 로그 파일 저장"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.project_name}_execution_log_{timestamp}.txt"
            filepath = os.path.join(self.log_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"프로젝트: {self.project_name}\n")
                f.write(f"실행 시작: {datetime.fromtimestamp(self.start_time).strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"실행 종료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"총 소요시간: {time.time() - self.start_time:.2f}초\n\n")
                
                # 진행 단계 요약
                f.write("=== 진행 단계 요약 ===\n")
                summary = self.get_progress_summary()
                for key, value in summary.items():
                    f.write(f"{key}: {value}\n")
                f.write("\n")
                
                # 상세 진행 단계
                f.write("=== 상세 진행 단계 ===\n")
                for step in self.progress_steps:
                    f.write(f"[{step.step_number}/{step.total_steps}] {step.step_name}\n")
                    f.write(f"  상태: {step.status}\n")
                    f.write(f"  메시지: {step.message}\n")
                    if step.duration:
                        f.write(f"  소요시간: {step.duration:.2f}초\n")
                    if step.details:
                        f.write(f"  상세정보: {json.dumps(step.details, ensure_ascii=False, indent=2)}\n")
                    f.write("\n")
                
                # 로그 엔트리
                f.write("=== 실행 로그 ===\n")
                for entry in self.logs:
                    f.write(f"[{entry.timestamp}] {entry.level}: {entry.message}\n")
                    if entry.details:
                        for key, value in entry.details.items():
                            f.write(f"  {key}: {value}\n")
                    f.write("\n")
            
            self.log_info(f"실행 로그 저장 완료: {filepath}")
            return filepath
            
        except Exception as e:
            self.log_error(f"실행 로그 저장 실패: {e}")
            return ""
    
    def save_debug_info(self) -> str:
        """디버그 정보 파일 저장"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.project_name}_debug_info_{timestamp}.json"
            filepath = os.path.join(self.log_dir, filename)
            
            debug_info = {
                "project_name": self.project_name,
                "timestamp": timestamp,
                "progress_summary": self.get_progress_summary(),
                "progress_steps": [
                    {
                        "step_name": step.step_name,
                        "step_number": step.step_number,
                        "total_steps": step.total_steps,
                        "status": step.status,
                        "start_time": step.start_time,
                        "end_time": step.end_time,
                        "duration": step.duration,
                        "message": step.message,
                        "details": step.details
                    }
                    for step in self.progress_steps
                ],
                "logs": [
                    {
                        "timestamp": entry.timestamp,
                        "level": entry.level,
                        "message": entry.message,
                        "details": entry.details
                    }
                    for entry in self.logs
                ]
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(debug_info, f, ensure_ascii=False, indent=2)
            
            self.log_info(f"디버그 정보 저장 완료: {filepath}")
            return filepath
            
        except Exception as e:
            self.log_error(f"디버그 정보 저장 실패: {e}")
            return ""
    
    def print_progress_bar(self, current: int, total: int, width: int = 50):
        """진행률 바 출력"""
        progress = current / total if total > 0 else 0
        filled_width = int(width * progress)
        bar = "█" * filled_width + "░" * (width - filled_width)
        percent = progress * 100
        
        print(f"\r[{bar}] {percent:6.2f}% ({current}/{total})", end="", flush=True)
        
        if current == total:
            print()  # 줄바꿈
    
    def print_step_status(self):
        """현재 단계 상태 출력"""
        if self.current_step:
            step = self.current_step
            print(f"\n🎬 현재 단계: [{step.step_number}/{step.total_steps}] {step.step_name}")
            print(f"   상태: {step.status}")
            print(f"   메시지: {step.message}")
            if step.start_time:
                elapsed = time.time() - step.start_time
                print(f"   경과시간: {elapsed:.1f}초")
        else:
            print("\n✅ 모든 단계 완료!")
    
    def print_summary(self):
        """최종 요약 출력"""
        summary = self.get_progress_summary()
        
        print("\n" + "="*60)
        print("🎉 파이프라인 실행 완료!")
        print("="*60)
        print(f"프로젝트: {summary['project_name']}")
        print(f"총 단계: {summary['total_steps']}")
        print(f"완료: {summary['completed_steps']}")
        print(f"실패: {summary['failed_steps']}")
        print(f"진행률: {summary['progress_percent']:.1f}%")
        print(f"총 소요시간: {summary['total_duration']:.1f}초")
        print(f"최종 상태: {summary['status']}")
        print("="*60)
        
        if summary['failed_steps'] > 0:
            print("\n❌ 실패한 단계:")
            for step in self.progress_steps:
                if step.status == "failed":
                    print(f"  - {step.step_name}: {step.message}")
        
        print(f"\n📁 로그 파일: {self.log_dir}")
        print(f"📊 실행 로그: {self.save_execution_log()}")
        print(f"🐛 디버그 정보: {self.save_debug_info()}")
