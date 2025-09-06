"""
Manifest 파일을 자동으로 생성하고 편집하는 Generator 클래스
"""

import json
import os
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import copy

from .models import Manifest, Scene, DialogueLine
from .parser import ManifestParser


class ManifestGenerator:
    """Manifest 파일을 자동으로 생성하고 편집하는 클래스"""
    
    def __init__(self):
        self.parser = ManifestParser()
        self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict[str, Dict[str, Any]]:
        """기본 템플릿 로드"""
        return {
            "basic_conversation": {
                "name": "기본 회화",
                "description": "인트로, 회화, 엔딩이 포함된 기본 구조",
                "scenes": [
                    {
                        "id": "intro_01",
                        "type": "intro",
                        "full_script": "안녕하세요! 오늘은 기본적인 회화를 배워보겠습니다."
                    },
                    {
                        "id": "conversation_01",
                        "type": "conversation",
                        "sequence": 1,
                        "native_script": "Hello, how are you?",
                        "learning_script": "안녕하세요, 어떻게 지내세요?",
                        "reading_script": "An-nyeong-ha-se-yo, eo-tteo-ke ji-nae-se-yo?"
                    },
                    {
                        "id": "ending_01",
                        "type": "ending",
                        "full_script": "오늘 수업은 여기까지입니다. 감사합니다!"
                    }
                ]
            },
            "dialogue_focused": {
                "name": "대화 중심",
                "description": "여러 화자 간의 대화가 중심인 구조",
                "scenes": [
                    {
                        "id": "intro_01",
                        "type": "intro",
                        "full_script": "오늘은 실제 상황에서 사용할 수 있는 대화를 연습해보겠습니다."
                    },
                    {
                        "id": "dialogue_01",
                        "type": "dialogue",
                        "script": [
                            {"speaker": "A", "text": "어디서 만날까요?"},
                            {"speaker": "B", "text": "역 앞에서 만나요."},
                            {"speaker": "A", "text": "몇 시에요?"},
                            {"speaker": "B", "text": "3시에요."}
                        ]
                    },
                    {
                        "id": "ending_01",
                        "type": "ending",
                        "full_script": "실용적인 대화 연습이었습니다. 다음에 또 만나요!"
                    }
                ]
            },
            "advanced_conversation": {
                "name": "고급 회화",
                "description": "여러 단계의 회화가 포함된 복합 구조",
                "scenes": [
                    {
                        "id": "intro_01",
                        "type": "intro",
                        "full_script": "고급 회화 과정에 오신 것을 환영합니다."
                    },
                    {
                        "id": "conversation_01",
                        "type": "conversation",
                        "sequence": 1,
                        "native_script": "What's your favorite hobby?",
                        "learning_script": "당신의 취미는 무엇인가요?",
                        "reading_script": "Dang-sin-eui chwi-mi-neun mu-eo-sin-ga-yo?"
                    },
                    {
                        "id": "conversation_02",
                        "type": "conversation",
                        "sequence": 2,
                        "native_script": "I like reading books.",
                        "learning_script": "저는 책 읽기를 좋아합니다.",
                        "reading_script": "Jeo-neun chaek ilg-gi-reul jo-a-ham-ni-da."
                    },
                    {
                        "id": "ending_01",
                        "type": "ending",
                        "full_script": "오늘도 유익한 시간이었습니다. 다음에 또 만나요!"
                    }
                ]
            }
        }
    
    def create_from_template(self, template_name: str, project_name: str, 
                           customizations: Optional[Dict[str, Any]] = None) -> Manifest:
        """템플릿에서 Manifest 생성"""
        if template_name not in self.templates:
            raise ValueError(f"템플릿을 찾을 수 없습니다: {template_name}")
        
        template = self.templates[template_name]
        manifest_data = {
            "project_name": project_name,
            "resolution": "1920x1080",
            "default_background": None,
            "scenes": copy.deepcopy(template["scenes"])
        }
        
        # 사용자 정의 적용
        if customizations:
            manifest_data.update(customizations)
        
        return self.parser.parse_dict(manifest_data)
    
    def create_custom_manifest(self, project_name: str, scenes_data: List[Dict[str, Any]]) -> Manifest:
        """사용자 정의 장면으로 Manifest 생성"""
        manifest_data = {
            "project_name": project_name,
            "resolution": "1920x1080",
            "default_background": None,
            "scenes": scenes_data
        }
        
        return self.parser.parse_dict(manifest_data)
    
    def add_scene(self, manifest: Manifest, scene_data: Dict[str, Any]) -> Manifest:
        """장면 추가"""
        new_scene = Scene(**scene_data)
        
        # ID 중복 방지
        existing_ids = [scene.id for scene in manifest.scenes]
        if new_scene.id in existing_ids:
            counter = 1
            base_id = new_scene.id
            while new_scene.id in existing_ids:
                new_scene.id = f"{base_id}_{counter}"
                counter += 1
        
        # 새로운 Manifest 객체 생성 (불변성 유지)
        new_manifest_data = manifest.to_dict()
        new_manifest_data["scenes"].append(scene_data)
        
        return self.parser.parse_dict(new_manifest_data)
    
    def remove_scene(self, manifest: Manifest, scene_id: str) -> Manifest:
        """장면 제거"""
        new_manifest_data = manifest.to_dict()
        new_manifest_data["scenes"] = [
            scene for scene in new_manifest_data["scenes"] 
            if scene["id"] != scene_id
        ]
        
        return self.parser.parse_dict(new_manifest_data)
    
    def update_scene(self, manifest: Manifest, scene_id: str, 
                    updates: Dict[str, Any]) -> Manifest:
        """장면 업데이트"""
        new_manifest_data = manifest.to_dict()
        
        for i, scene in enumerate(new_manifest_data["scenes"]):
            if scene["id"] == scene_id:
                # 업데이트 적용
                scene.update(updates)
                break
        
        return self.parser.parse_dict(new_manifest_data)
    
    def reorder_scenes(self, manifest: Manifest, new_order: List[str]) -> Manifest:
        """장면 순서 변경"""
        # 현재 장면들을 ID로 매핑
        scene_map = {scene.id: scene for scene in manifest.scenes}
        
        # 새로운 순서로 장면 재배열
        new_scenes = []
        for scene_id in new_order:
            if scene_id in scene_map:
                new_scenes.append(scene_map[scene_id])
        
        # 누락된 장면들 추가
        for scene in manifest.scenes:
            if scene.id not in new_order:
                new_scenes.append(scene)
        
        new_manifest_data = manifest.to_dict()
        new_manifest_data["scenes"] = [scene.to_dict() for scene in new_scenes]
        
        return self.parser.parse_dict(new_manifest_data)
    
    def duplicate_scene(self, manifest: Manifest, scene_id: str, 
                       new_id: Optional[str] = None) -> Manifest:
        """장면 복제"""
        # 원본 장면 찾기
        original_scene = None
        for scene in manifest.scenes:
            if scene.id == scene_id:
                original_scene = scene
                break
        
        if not original_scene:
            raise ValueError(f"장면을 찾을 수 없습니다: {scene_id}")
        
        # 새 장면 데이터 생성
        new_scene_data = original_scene.to_dict()
        
        # 새 ID 생성
        if not new_id:
            base_id = original_scene.id
            counter = 1
            while any(scene.id == f"{base_id}_copy_{counter}" for scene in manifest.scenes):
                counter += 1
            new_id = f"{base_id}_copy_{counter}"
        
        new_scene_data["id"] = new_id
        
        return self.add_scene(manifest, new_scene_data)
    
    def convert_scene_type(self, manifest: Manifest, scene_id: str, 
                          new_type: str) -> Manifest:
        """장면 타입 변환"""
        # 원본 장면 찾기
        original_scene = None
        for scene in manifest.scenes:
            if scene.id == scene_id:
                original_scene = scene
                break
        
        if not original_scene:
            raise ValueError(f"장면을 찾을 수 없습니다: {scene_id}")
        
        # 새 타입에 맞는 데이터 구조 생성
        new_scene_data = {"id": scene_id, "type": new_type}
        
        if new_type == "intro" or new_type == "ending":
            # 기존 스크립트가 있으면 사용, 없으면 기본값
            if original_scene.full_script:
                new_scene_data["full_script"] = original_scene.full_script
            else:
                new_scene_data["full_script"] = f"{new_type} 스크립트를 입력하세요."
        
        elif new_type == "conversation":
            # 기존 데이터가 있으면 사용, 없으면 기본값
            new_scene_data.update({
                "sequence": original_scene.sequence or 1,
                "native_script": original_scene.native_script or "원어를 입력하세요.",
                "learning_script": original_scene.learning_script or "학습어를 입력하세요.",
                "reading_script": original_scene.reading_script or "읽기를 입력하세요."
            })
        
        elif new_type == "dialogue":
            # 기존 대화가 있으면 사용, 없으면 기본값
            if original_scene.script:
                new_scene_data["script"] = original_scene.script
            else:
                new_scene_data["script"] = [
                    {"speaker": "A", "text": "대화를 입력하세요."},
                    {"speaker": "B", "text": "대화를 입력하세요."}
                ]
        
        return self.update_scene(manifest, scene_id, new_scene_data)
    
    def get_available_templates(self) -> List[Dict[str, str]]:
        """사용 가능한 템플릿 목록 반환"""
        return [
            {
                "id": template_id,
                "name": template_data["name"],
                "description": template_data["description"]
            }
            for template_id, template_data in self.templates.items()
        ]
    
    def create_template_from_manifest(self, manifest: Manifest, 
                                    template_name: str, 
                                    template_description: str) -> None:
        """Manifest에서 새 템플릿 생성"""
        template_data = {
            "name": template_name,
            "description": template_description,
            "scenes": [scene.to_dict() for scene in manifest.scenes]
        }
        
        template_id = template_name.lower().replace(" ", "_")
        self.templates[template_id] = template_data
    
    def export_manifest_schema(self, output_path: str) -> None:
        """Manifest 스키마를 JSON Schema 형태로 내보내기"""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "Video Manifest Schema",
            "description": "비디오 제작을 위한 Manifest 파일 스키마",
            "type": "object",
            "properties": {
                "project_name": {
                    "type": "string",
                    "description": "프로젝트 이름",
                    "minLength": 1,
                    "maxLength": 100
                },
                "resolution": {
                    "type": "string",
                    "description": "해상도",
                    "enum": ["1920x1080", "1280x720", "3840x2160", "1080x1080", "1440x1440", "1080x1920", "720x1280"]
                },
                "default_background": {
                    "type": "string",
                    "description": "기본 배경 파일 경로"
                },
                "scenes": {
                    "type": "array",
                    "description": "장면 리스트",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "pattern": "^[a-z0-9_]+$"},
                            "type": {"type": "string", "enum": ["intro", "conversation", "dialogue", "ending"]}
                        },
                        "required": ["id", "type"]
                    }
                }
            },
            "required": ["project_name", "scenes"]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(schema, f, ensure_ascii=False, indent=2)
