"""
파이프라인 코어 모델

파이프라인의 핵심 데이터 모델들을 정의합니다.
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from datetime import datetime


@dataclass
class PipelineResult:
    """파이프라인 실행 결과"""
    success: bool
    message: str
    output_path: Optional[str] = None
    error_details: Optional[str] = None
    execution_time: float = 0.0
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class PipelineConfig:
    """파이프라인 설정"""
    output_directory: str = "output"
    temp_directory: str = "temp"
    log_level: str = "INFO"
    max_workers: int = 4
    timeout: int = 300
    
    def __post_init__(self):
        import os
        os.makedirs(self.output_directory, exist_ok=True)
        os.makedirs(self.temp_directory, exist_ok=True)


@dataclass
class ProcessingStep:
    """처리 단계 정보"""
    name: str
    description: str
    status: str = "pending"  # pending, running, completed, failed
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration: float = 0.0
    error_message: Optional[str] = None
    
    def start(self):
        """단계 시작"""
        self.status = "running"
        self.start_time = datetime.now().isoformat()
    
    def complete(self):
        """단계 완료"""
        self.status = "completed"
        self.end_time = datetime.now().isoformat()
        if self.start_time:
            start = datetime.fromisoformat(self.start_time)
            end = datetime.fromisoformat(self.end_time)
            self.duration = (end - start).total_seconds()
    
    def fail(self, error_message: str):
        """단계 실패"""
        self.status = "failed"
        self.end_time = datetime.now().isoformat()
        self.error_message = error_message
        if self.start_time:
            start = datetime.fromisoformat(self.start_time)
            end = datetime.fromisoformat(self.end_time)
            self.duration = (end - start).total_seconds()


@dataclass
class ProcessingContext:
    """처리 컨텍스트"""
    project_name: str
    identifier: str
    config: PipelineConfig
    steps: List[ProcessingStep] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.steps is None:
            self.steps = []
        if self.metadata is None:
            self.metadata = {}
    
    def add_step(self, name: str, description: str) -> ProcessingStep:
        """처리 단계 추가"""
        step = ProcessingStep(name=name, description=description)
        self.steps.append(step)
        return step
    
    def get_step(self, name: str) -> Optional[ProcessingStep]:
        """처리 단계 가져오기"""
        for step in self.steps:
            if step.name == name:
                return step
        return None
    
    def get_completed_steps(self) -> List[ProcessingStep]:
        """완료된 단계들 가져오기"""
        return [step for step in self.steps if step.status == "completed"]
    
    def get_failed_steps(self) -> List[ProcessingStep]:
        """실패한 단계들 가져오기"""
        return [step for step in self.steps if step.status == "failed"]
    
    def get_running_steps(self) -> List[ProcessingStep]:
        """실행 중인 단계들 가져오기"""
        return [step for step in self.steps if step.status == "running"]
    
    def get_pending_steps(self) -> List[ProcessingStep]:
        """대기 중인 단계들 가져오기"""
        return [step for step in self.steps if step.status == "pending"]
