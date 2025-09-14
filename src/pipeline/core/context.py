"""
파이프라인 컨텍스트

파이프라인 실행에 필요한 모든 정보를 담는 컨텍스트 클래스입니다.
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from ..manifest.models import Manifest


@dataclass
class PipelinePaths:
    """파이프라인 경로 관리"""
    base_dir: str
    project_name: str
    identifier: str
    
    def __post_init__(self):
        """경로 초기화"""
        self.output_dir = os.path.join(self.base_dir, self.project_name, self.identifier)
        self.manifest_dir = os.path.join(self.output_dir, "manifest")
        self.timing_dir = os.path.join(self.output_dir, "timing")
        self.mp3_dir = os.path.join(self.output_dir, "mp3")
        self.ssml_dir = os.path.join(self.output_dir, "SSML")
        self.conversation_dir = os.path.join(self.output_dir, "conversation")
        self.intro_dir = os.path.join(self.output_dir, "intro")
        self.ending_dir = os.path.join(self.output_dir, "ending")
        self.thumbnail_dir = os.path.join(self.output_dir, "thumbnail")
        self.dialogue_dir = os.path.join(self.output_dir, "dialogue")
    
    def get_path_for_scene(self, scene_type: str) -> str:
        """장면 타입에 따른 경로 반환"""
        path_map = {
            "conversation": self.conversation_dir,
            "intro": self.intro_dir,
            "ending": self.ending_dir,
            "thumbnail": self.thumbnail_dir,
            "dialogue": self.dialogue_dir
        }
        return path_map.get(scene_type, self.output_dir)


@dataclass
class PipelineSettings:
    """파이프라인 설정"""
    common: Dict[str, Any]
    tabs: Dict[str, Any]


@dataclass
class PipelineContext:
    """파이프라인 실행 컨텍스트"""
    project_name: str
    identifier: str
    manifest: Optional[Manifest]
    settings: PipelineSettings
    paths: PipelinePaths
    script_type: Optional[str] = None
    log_callback: Optional[Any] = None  # UI 로깅을 위한 콜백 함수
    
    @classmethod
    def create(cls, project_name: str, identifier: str, 
               manifest: Optional[Manifest] = None,
               settings: Optional[Dict[str, Any]] = None,
               base_dir: str = "output",
               script_type: Optional[str] = None,
               log_callback: Optional[Any] = None) -> 'PipelineContext':
        """컨텍스트 생성"""
        paths = PipelinePaths(base_dir, project_name, identifier)
        
        if settings is None:
            settings = {"common": {}, "tabs": {}}
        
        pipeline_settings = PipelineSettings(
            common=settings.get("common", {}),
            tabs=settings.get("tabs", {})
        )
        
        return cls(
            project_name=project_name,
            identifier=identifier,
            manifest=manifest,
            settings=pipeline_settings,
            paths=paths,
            script_type=script_type,
            log_callback=log_callback
        )
