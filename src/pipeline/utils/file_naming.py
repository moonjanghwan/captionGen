"""
파일명 규칙 관리자

프로젝트별 출력 파일명 규칙을 관리하고 체계적인 파일 경로를 생성합니다.
"""

import os
import re
from typing import Dict, List, Any, Optional
from datetime import datetime


class FileNamingManager:
    """파일명 규칙 관리 클래스"""
    
    def __init__(self, base_output_dir: str = "output"):
        """
        파일명 관리자 초기화
        
        Args:
            base_output_dir: 기본 출력 디렉토리
        """
        self.base_output_dir = base_output_dir
        self.sanitize_pattern = re.compile(r'[^\w\s\-_]')
    
    def sanitize_project_name(self, project_name: str) -> str:
        """
        프로젝트 이름을 파일명 규칙에 맞게 정리
        
        Args:
            project_name: 원본 프로젝트 이름
            
        Returns:
            str: 정리된 프로젝트 이름
        """
        # 특수문자 제거 및 공백을 언더스코어로 변환
        sanitized = self.sanitize_pattern.sub('_', project_name)
        sanitized = re.sub(r'\s+', '_', sanitized)
        sanitized = re.sub(r'_+', '_', sanitized)
        sanitized = sanitized.strip('_')
        
        # 길이 제한 (100자)
        if len(sanitized) > 100:
            sanitized = sanitized[:100].rstrip('_')
        
        return sanitized
    
    def create_project_structure(self, project_name: str) -> Dict[str, str]:
        """
        프로젝트별 폴더 구조 생성
        
        Args:
            project_name: 프로젝트 이름
            
        Returns:
            Dict[str, str]: 폴더 경로 정보
        """
        sanitized_name = self.sanitize_project_name(project_name)
        
        # 프로젝트 루트 디렉토리
        project_root = os.path.join(self.base_output_dir, sanitized_name)
        
        # 하위 디렉토리들
        directories = {
            "project_root": project_root,
            "manifest": os.path.join(project_root, "manifest"),
            "audio": os.path.join(project_root, "audio"),
            "subtitles": os.path.join(project_root, "subtitles"),
            "video": os.path.join(project_root, "video"),
            "reports": os.path.join(project_root, "reports"),
            "temp": os.path.join(project_root, "temp")
        }
        
        # 디렉토리 생성
        for dir_path in directories.values():
            os.makedirs(dir_path, exist_ok=True)
        
        return directories
    
    def generate_manifest_filename(self, project_name: str) -> str:
        """Manifest 파일명 생성"""
        sanitized_name = self.sanitize_project_name(project_name)
        return f"{sanitized_name}_manifest.json"
    
    def generate_ssml_filename(self, project_name: str) -> str:
        """SSML 파일명 생성"""
        sanitized_name = self.sanitize_project_name(project_name)
        return f"{sanitized_name}_ssml.txt"
    
    def generate_audio_filename(self, project_name: str) -> str:
        """오디오 파일명 생성"""
        sanitized_name = self.sanitize_project_name(project_name)
        return f"{sanitized_name}_audio.mp3"
    
    def generate_timing_filename(self, project_name: str) -> str:
        """타이밍 정보 파일명 생성"""
        sanitized_name = self.sanitize_project_name(project_name)
        return f"{sanitized_name}_timing.json"
    
    def generate_subtitle_frame_filename(self, project_name: str, scene_id: str, 
                                       screen_type: str, frame_number: int) -> str:
        """자막 프레임 파일명 생성"""
        sanitized_name = self.sanitize_project_name(project_name)
        return f"{sanitized_name}_{scene_id}_{screen_type}_{frame_number:04d}.png"
    
    def generate_subtitle_info_filename(self, project_name: str) -> str:
        """자막 정보 파일명 생성"""
        sanitized_name = self.sanitize_project_name(project_name)
        return f"{sanitized_name}_subtitle_frames.json"
    
    def generate_concat_list_filename(self, project_name: str) -> str:
        """FFmpeg concat 리스트 파일명 생성"""
        sanitized_name = self.sanitize_project_name(project_name)
        return f"{sanitized_name}_concat_list.txt"
    
    def generate_final_video_filename(self, project_name: str) -> str:
        """최종 비디오 파일명 생성"""
        sanitized_name = self.sanitize_project_name(project_name)
        return f"{sanitized_name}_final.mp4"
    
    def generate_preview_filename(self, project_name: str) -> str:
        """프리뷰 파일명 생성"""
        sanitized_name = self.sanitize_project_name(project_name)
        return f"{sanitized_name}_preview.mp4"
    
    def generate_optimized_video_filename(self, project_name: str) -> str:
        """최적화된 비디오 파일명 생성"""
        sanitized_name = self.sanitize_project_name(project_name)
        return f"{sanitized_name}_optimized.mp4"
    
    def generate_pipeline_report_filename(self, project_name: str) -> str:
        """파이프라인 보고서 파일명 생성"""
        sanitized_name = self.sanitize_project_name(project_name)
        return f"{sanitized_name}_pipeline_report.json"
    
    def generate_execution_log_filename(self, project_name: str) -> str:
        """실행 로그 파일명 생성"""
        sanitized_name = self.sanitize_project_name(project_name)
        return f"{sanitized_name}_execution_log.txt"
    
    def generate_debug_info_filename(self, project_name: str) -> str:
        """디버그 정보 파일명 생성"""
        sanitized_name = self.sanitize_project_name(project_name)
        return f"{sanitized_name}_debug_info.json"
    
    def get_full_path(self, base_dir: str, filename: str) -> str:
        """전체 파일 경로 생성"""
        return os.path.join(base_dir, filename)
    
    def create_timestamped_filename(self, base_filename: str, extension: str = "") -> str:
        """타임스탬프가 포함된 파일명 생성"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if extension:
            return f"{base_filename}_{timestamp}.{extension}"
        else:
            return f"{base_filename}_{timestamp}"
    
    def cleanup_temp_files(self, project_name: str, keep_recent: int = 3) -> bool:
        """
        임시 파일 정리 (최근 N개만 유지)
        
        Args:
            project_name: 프로젝트 이름
            keep_recent: 유지할 최근 파일 수
            
        Returns:
            bool: 정리 성공 여부
        """
        try:
            temp_dir = os.path.join(self.base_output_dir, 
                                  self.sanitize_project_name(project_name), "temp")
            
            if not os.path.exists(temp_dir):
                return True
            
            # 임시 파일 목록
            temp_files = []
            for filename in os.listdir(temp_dir):
                file_path = os.path.join(temp_dir, filename)
                if os.path.isfile(file_path):
                    temp_files.append((file_path, os.path.getmtime(file_path)))
            
            # 수정 시간순 정렬
            temp_files.sort(key=lambda x: x[1], reverse=True)
            
            # 최근 파일을 제외하고 삭제
            for file_path, _ in temp_files[keep_recent:]:
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"⚠️ 임시 파일 삭제 실패: {file_path}, 오류: {e}")
            
            return True
            
        except Exception as e:
            print(f"❌ 임시 파일 정리 실패: {e}")
            return False
    
    def get_project_summary(self, project_name: str) -> Dict[str, Any]:
        """
        프로젝트 파일 요약 정보 반환
        
        Args:
            project_name: 프로젝트 이름
            
        Returns:
            Dict[str, Any]: 프로젝트 요약 정보
        """
        try:
            project_root = os.path.join(self.base_output_dir, 
                                      self.sanitize_project_name(project_name))
            
            if not os.path.exists(project_root):
                return {"error": "프로젝트를 찾을 수 없습니다"}
            
            summary = {
                "project_name": project_name,
                "sanitized_name": self.sanitize_project_name(project_name),
                "project_root": project_root,
                "directories": {},
                "files": {},
                "total_size": 0
            }
            
            # 디렉토리 정보
            for dir_name in ["manifest", "audio", "subtitles", "video", "reports", "temp"]:
                dir_path = os.path.join(project_root, dir_name)
                if os.path.exists(dir_path):
                    summary["directories"][dir_name] = {
                        "path": dir_path,
                        "exists": True,
                        "file_count": len([f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))])
                    }
                else:
                    summary["directories"][dir_name] = {
                        "path": dir_path,
                        "exists": False,
                        "file_count": 0
                    }
            
            # 파일 정보
            for root, dirs, files in os.walk(project_root):
                for file in files:
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, project_root)
                    
                    try:
                        file_size = os.path.getsize(file_path)
                        summary["total_size"] += file_size
                        
                        summary["files"][relative_path] = {
                            "size": file_size,
                            "size_mb": round(file_size / (1024 * 1024), 2)
                        }
                    except Exception:
                        pass
            
            return summary
            
        except Exception as e:
            return {"error": f"프로젝트 요약 생성 실패: {e}"}
