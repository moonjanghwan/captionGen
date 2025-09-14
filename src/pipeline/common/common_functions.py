"""
공통 함수 모듈

파이프라인에서 공통으로 사용되는 함수들을 모아놓은 모듈입니다.
"""

import os
import json
import time
from typing import Dict, List, Any, Optional, Union, Callable
from datetime import datetime
import logging


class CommonFunctions:
    """공통 함수 클래스"""
    
    @staticmethod
    def ensure_directory_exists(directory_path: str) -> bool:
        """디렉토리가 존재하지 않으면 생성"""
        try:
            os.makedirs(directory_path, exist_ok=True)
            return True
        except Exception as e:
            logging.error(f"디렉토리 생성 실패: {directory_path}, 오류: {e}")
            return False
    
    @staticmethod
    def save_json_file(file_path: str, data: Dict[str, Any], 
                      indent: int = 2, ensure_ascii: bool = False) -> bool:
        """JSON 파일 저장"""
        try:
            # 디렉토리 생성
            directory = os.path.dirname(file_path)
            CommonFunctions.ensure_directory_exists(directory)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)
            return True
        except Exception as e:
            logging.error(f"JSON 파일 저장 실패: {file_path}, 오류: {e}")
            return False
    
    @staticmethod
    def load_json_file(file_path: str) -> Optional[Dict[str, Any]]:
        """JSON 파일 로드"""
        try:
            if not os.path.exists(file_path):
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"JSON 파일 로드 실패: {file_path}, 오류: {e}")
            return None
    
    @staticmethod
    def create_timestamp() -> str:
        """현재 시간의 타임스탬프 생성"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    @staticmethod
    def create_timestamped_filename(base_name: str, extension: str = "json") -> str:
        """타임스탬프가 포함된 파일명 생성"""
        timestamp = CommonFunctions.create_timestamp()
        return f"{base_name}_{timestamp}.{extension}"
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """파일명 정리 (특수문자 제거)"""
        import re
        # 특수문자 제거 및 공백을 언더스코어로 변환
        sanitized = re.sub(r'[^\w\s\-_.]', '_', filename)
        sanitized = re.sub(r'\s+', '_', sanitized)
        sanitized = re.sub(r'_+', '_', sanitized)
        sanitized = sanitized.strip('_')
        
        # 길이 제한 (100자)
        if len(sanitized) > 100:
            sanitized = sanitized[:100].rstrip('_')
        
        return sanitized
    
    @staticmethod
    def parse_resolution(resolution_str: str) -> tuple:
        """해상도 문자열을 (width, height) 튜플로 변환"""
        try:
            if 'x' in resolution_str:
                width, height = resolution_str.split('x')
                return (int(width), int(height))
            else:
                # 기본값
                return (1920, 1080)
        except Exception:
            return (1920, 1080)
    
    @staticmethod
    def format_resolution(width: int, height: int) -> str:
        """(width, height) 튜플을 해상도 문자열로 변환"""
        return f"{width}x{height}"
    
    @staticmethod
    def calculate_duration_from_timing(timing_data: List[Dict[str, Any]]) -> float:
        """타이밍 데이터로부터 총 재생 시간 계산"""
        if not timing_data:
            return 0.0
        
        total_duration = 0.0
        for timing in timing_data:
            duration = timing.get('duration', 0.0)
            if isinstance(duration, (int, float)):
                total_duration += duration
        
        return total_duration
    
    @staticmethod
    def format_duration(seconds: float) -> str:
        """초를 MM:SS 형식으로 변환"""
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"
    
    @staticmethod
    def validate_file_path(file_path: str) -> bool:
        """파일 경로 유효성 검사"""
        try:
            # 경로가 너무 긴지 확인
            if len(file_path) > 260:  # Windows 경로 길이 제한
                return False
            
            # 금지된 문자 확인
            forbidden_chars = ['<', '>', ':', '"', '|', '?', '*']
            for char in forbidden_chars:
                if char in file_path:
                    return False
            
            return True
        except Exception:
            return False
    
    @staticmethod
    def get_file_size_mb(file_path: str) -> float:
        """파일 크기를 MB 단위로 반환"""
        try:
            if not os.path.exists(file_path):
                return 0.0
            
            size_bytes = os.path.getsize(file_path)
            return round(size_bytes / (1024 * 1024), 2)
        except Exception:
            return 0.0
    
    @staticmethod
    def copy_file_with_progress(src: str, dst: str, 
                              progress_callback: Optional[Callable[[float], None]] = None) -> bool:
        """진행률 콜백과 함께 파일 복사"""
        try:
            import shutil
            
            if not os.path.exists(src):
                return False
            
            # 대상 디렉토리 생성
            dst_dir = os.path.dirname(dst)
            CommonFunctions.ensure_directory_exists(dst_dir)
            
            # 파일 크기 확인
            total_size = os.path.getsize(src)
            
            if total_size < 1024 * 1024:  # 1MB 미만이면 일반 복사
                shutil.copy2(src, dst)
                if progress_callback:
                    progress_callback(100.0)
                return True
            
            # 큰 파일의 경우 청크 단위로 복사
            copied_size = 0
            with open(src, 'rb') as src_file:
                with open(dst, 'wb') as dst_file:
                    while True:
                        chunk = src_file.read(1024 * 1024)  # 1MB 청크
                        if not chunk:
                            break
                        
                        dst_file.write(chunk)
                        copied_size += len(chunk)
                        
                        if progress_callback:
                            progress = (copied_size / total_size) * 100
                            progress_callback(progress)
            
            return True
        except Exception as e:
            logging.error(f"파일 복사 실패: {src} -> {dst}, 오류: {e}")
            return False
    
    @staticmethod
    def retry_operation(operation: Callable, max_retries: int = 3, 
                       delay: float = 1.0, *args, **kwargs) -> Any:
        """작업 재시도"""
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                return operation(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    time.sleep(delay * (2 ** attempt))  # 지수 백오프
                    logging.warning(f"작업 재시도 {attempt + 1}/{max_retries}: {e}")
        
        logging.error(f"작업 최종 실패: {last_exception}")
        raise last_exception
    
    @staticmethod
    def merge_dictionaries(*dicts: Dict[str, Any]) -> Dict[str, Any]:
        """여러 딕셔너리를 병합 (나중에 오는 값이 우선)"""
        result = {}
        for d in dicts:
            if d:
                result.update(d)
        return result
    
    @staticmethod
    def deep_merge_dictionaries(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
        """딕셔너리 깊은 병합"""
        result = dict1.copy()
        
        for key, value in dict2.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = CommonFunctions.deep_merge_dictionaries(result[key], value)
            else:
                result[key] = value
        
        return result
    
    @staticmethod
    def safe_get_nested_value(data: Dict[str, Any], keys: List[str], 
                            default: Any = None) -> Any:
        """중첩된 딕셔너리에서 안전하게 값 가져오기"""
        try:
            current = data
            for key in keys:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return default
            return current
        except Exception:
            return default
    
    @staticmethod
    def safe_set_nested_value(data: Dict[str, Any], keys: List[str], value: Any) -> bool:
        """중첩된 딕셔너리에 안전하게 값 설정하기"""
        try:
            current = data
            for key in keys[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]
            current[keys[-1]] = value
            return True
        except Exception:
            return False
    
    @staticmethod
    def create_progress_tracker(total_steps: int) -> Dict[str, Any]:
        """진행률 추적기 생성"""
        return {
            "total_steps": total_steps,
            "current_step": 0,
            "completed_steps": 0,
            "start_time": time.time(),
            "steps": []
        }
    
    @staticmethod
    def update_progress(tracker: Dict[str, Any], step_name: str, 
                       status: str = "in_progress", details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """진행률 업데이트"""
        current_time = time.time()
        elapsed_time = current_time - tracker["start_time"]
        
        step_info = {
            "name": step_name,
            "status": status,
            "timestamp": current_time,
            "elapsed_time": elapsed_time,
            "details": details or {}
        }
        
        tracker["steps"].append(step_info)
        tracker["current_step"] = len(tracker["steps"])
        
        if status == "completed":
            tracker["completed_steps"] += 1
        
        # 진행률 계산
        progress_percentage = (tracker["completed_steps"] / tracker["total_steps"]) * 100
        
        return {
            "progress_percentage": progress_percentage,
            "current_step": tracker["current_step"],
            "total_steps": tracker["total_steps"],
            "elapsed_time": elapsed_time,
            "step_info": step_info
        }
    
    @staticmethod
    def log_operation(logger: logging.Logger, operation_name: str, 
                     start_message: str = None, end_message: str = None):
        """작업 로깅 데코레이터"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                if start_message:
                    logger.info(f"시작: {start_message}")
                else:
                    logger.info(f"시작: {operation_name}")
                
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    elapsed_time = time.time() - start_time
                    
                    if end_message:
                        logger.info(f"완료: {end_message} (소요시간: {elapsed_time:.2f}초)")
                    else:
                        logger.info(f"완료: {operation_name} (소요시간: {elapsed_time:.2f}초)")
                    
                    return result
                except Exception as e:
                    elapsed_time = time.time() - start_time
                    logger.error(f"실패: {operation_name} (소요시간: {elapsed_time:.2f}초) - {e}")
                    raise
            
            return wrapper
        return decorator
