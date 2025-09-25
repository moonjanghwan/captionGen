"""
Manifest 파일을 파싱하고 검증하는 Parser 클래스
"""

import json
import os
from typing import Dict, List, Optional, Union, Tuple
from pathlib import Path

from .models import Manifest, Scene, DialogueLine
from .validator import ManifestValidator


class ManifestParser:
    """Manifest 파일을 파싱하고 검증하는 클래스"""
    
    def __init__(self):
        self.validator = ManifestValidator()
        self._parsed_manifests: Dict[str, Manifest] = {}
    
    def parse_file(self, file_path: str) -> Manifest:
        """파일에서 Manifest를 파싱"""
        try:
            # 파일 존재 확인
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Manifest 파일을 찾을 수 없습니다: {file_path}")
            
            # JSON 파일 읽기
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Manifest 객체 생성
            manifest = Manifest.from_dict(data)
            
            # 검증 수행
            validation_result = self.validator.validate(manifest)
            if not validation_result.is_valid:
                raise ValueError(f"Manifest 검증 실패: {validation_result.errors}")
            
            # 캐시에 저장
            self._parsed_manifests[file_path] = manifest
            
            return manifest
            
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON 파싱 오류: {e}")
        except Exception as e:
            raise ValueError(f"Manifest 파싱 오류: {e}")
    
    def parse_string(self, json_string: str) -> Manifest:
        """JSON 문자열에서 Manifest를 파싱"""
        try:
            data = json.loads(json_string)
            manifest = Manifest.from_dict(data)
            
            # 검증 수행
            validation_result = self.validator.validate(manifest)
            if not validation_result.is_valid:
                raise ValueError(f"Manifest 검증 실패: {validation_result.errors}")
            
            return manifest
            
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON 파싱 오류: {e}")
        except Exception as e:
            raise ValueError(f"Manifest 파싱 오류: {e}")
    
    def parse_dict(self, data: dict) -> Manifest:
        """딕셔너리에서 Manifest를 파싱"""
        try:
            manifest = Manifest.from_dict(data)
            
            # 검증 수행
            validation_result = self.validator.validate(manifest)
            if not validation_result.is_valid:
                raise ValueError(f"Manifest 검증 실패: {validation_result.errors}")
            
            return manifest
            
        except Exception as e:
            raise ValueError(f"Manifest 파싱 오류: {e}")
    
    def save_manifest(self, manifest: Manifest, file_path: str) -> None:
        """Manifest를 파일로 저장"""
        try:
            # 디렉토리 생성
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # JSON으로 저장
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(manifest.to_dict(), f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            raise ValueError(f"Manifest 저장 오류: {e}")
    
    def get_cached_manifest(self, file_path: str) -> Optional[Manifest]:
        """캐시된 Manifest 반환"""
        return self._parsed_manifests.get(file_path)
    
    def clear_cache(self) -> None:
        """캐시 클리어"""
        self._parsed_manifests.clear()
    
    def validate_file(self, file_path: str) -> Tuple[bool, List[str]]:
        """파일의 Manifest 유효성 검사"""
        try:
            manifest = self.parse_file(file_path)
            return True, []
        except ValueError as e:
            return False, [str(e)]
        except Exception as e:
            return False, [f"예상치 못한 오류: {e}"]
    
    def get_manifest_info(self, manifest: Manifest) -> Dict[str, Union[str, int, float]]:
        """Manifest 정보 요약 반환"""
        return {
            "project_name": manifest.project_name,
            "resolution": manifest.resolution,
            "total_scenes": len(manifest.scenes),
            "scene_types": {
                scene_type: len(manifest.get_scenes_by_type(scene_type))
                for scene_type in ["intro", "conversation", "dialogue", "ending"]
            },
            "estimated_duration": manifest.get_total_duration_estimate(),
            "has_background": manifest.default_background is not None
        }
    
    def create_template_manifest(self, project_name: str) -> Manifest:
        """템플릿 Manifest 생성"""
        template_data = {
            "project_name": project_name,
            "resolution": "1920x1080",
            "default_background": None,
            "scenes": [
                {
                    "id": "intro_01",
                    "type": "intro",
                    "text": "프로젝트 소개 문구를 입력하세요."
                },
                {
                    "id": "conversation_01",
                    "type": "conversation",
                    "sequence": 1,
                    "native_script": "원어 문장을 입력하세요.",
                    "learning_script": "학습어 문장을 입력하세요.",
                    "reading_script": "읽기 문장을 입력하세요."
                },
                {
                    "id": "ending_01",
                    "type": "ending",
                    "text": "마무리 문구를 입력하세요."
                }
            ]
        }
        
        return self.parse_dict(template_data)
    
    def merge_manifests(self, manifests: List[Manifest]) -> Manifest:
        """여러 Manifest를 병합"""
        if not manifests:
            raise ValueError("병합할 Manifest가 없습니다")
        
        # 첫 번째 Manifest를 기본으로 사용
        base_manifest = manifests[0]
        
        # 모든 장면을 수집
        all_scenes = []
        scene_id_counter = 1
        
        for manifest in manifests:
            for scene in manifest.scenes:
                # ID 충돌 방지를 위해 새로운 ID 생성
                new_id = f"{scene.type}_{scene_id_counter:02d}"
                scene.id = new_id
                all_scenes.append(scene)
                scene_id_counter += 1
        
        # 병합된 Manifest 생성
        merged_data = {
            "project_name": f"{base_manifest.project_name}_merged",
            "resolution": base_manifest.resolution,
            "default_background": base_manifest.default_background,
            "scenes": all_scenes
        }
        
        return self.parse_dict(merged_data)
    
    def create_manifest(self, script_type: str, script_data: Dict[str, any]) -> Dict[str, any]:
        """
        스크립트 데이터로부터 Manifest 생성
        
        Args:
            script_type: 스크립트 타입 (conversation, intro, ending)
            script_data: 스크립트 데이터
            
        Returns:
            Dict[str, any]: Manifest 데이터
        """
        try:
            project_name = script_data.get("project_name", "untitled_project")
            manifest_data = {
                "project_name": project_name,
                "identifier": script_data.get("identifier", project_name),
                "resolution": "1920x1080",
                "default_background": None,
                "scenes": []
            }
            
            if script_type in ["conversation", "dialogue"]:
                # 대화 스크립트 처리
                scenes = script_data.get("scenes", [])
                for i, scene_data in enumerate(scenes, 1):
                    scene = {
                        "id": f"conversation_{i:02d}",
                        "type": "conversation",
                        "sequence": i,
                        "native_script": scene_data.get("native_script", ""),
                        "learning_script": scene_data.get("learning_script", ""),
                        "reading_script": scene_data.get("reading_script", ""),
                        "order": scene_data.get("order", str(i))
                    }
                    manifest_data["scenes"].append(scene)
                    
            elif script_type in ["intro", "인트로"]:
                # 인트로 스크립트 처리
                intro_text = script_data.get("script_text", script_data.get("intro_text", ""))
                scene = {
                    "id": "intro_01",
                    "type": "intro",
                    "full_script": intro_text
                }
                manifest_data["scenes"].append(scene)
                
            elif script_type in ["ending", "엔딩"]:
                # 엔딩 스크립트 처리
                ending_text = script_data.get("script_text", script_data.get("ending_text", ""))
                scene = {
                    "id": "ending_01",
                    "type": "ending",
                    "full_script": ending_text
                }
                manifest_data["scenes"].append(scene)
            
            return manifest_data
            
        except Exception as e:
            print(f"❌ Manifest 생성 중 오류: {e}")
            raise