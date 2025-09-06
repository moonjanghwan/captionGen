"""
Manifest의 상세한 검증을 수행하는 Validator 클래스
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import os

from .models import Manifest, Scene


@dataclass
class ValidationError:
    """검증 오류 정보"""
    field: str
    message: str
    scene_id: Optional[str] = None
    severity: str = "error"  # error, warning, info


@dataclass
class ValidationResult:
    """검증 결과"""
    is_valid: bool
    errors: List[ValidationError] = None
    warnings: List[ValidationError] = None
    info: List[ValidationError] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.info is None:
            self.info = []
    
    def add_error(self, field: str, message: str, scene_id: Optional[str] = None):
        """오류 추가"""
        self.errors.append(ValidationError(field, message, scene_id, "error"))
        self.is_valid = False
    
    def add_warning(self, field: str, message: str, scene_id: Optional[str] = None):
        """경고 추가"""
        self.warnings.append(ValidationError(field, message, scene_id, "warning"))
    
    def add_info(self, field: str, message: str, scene_id: Optional[str] = None):
        """정보 추가"""
        self.info.append(ValidationError(field, message, scene_id, "info"))
    
    def get_all_issues(self) -> List[ValidationError]:
        """모든 이슈 반환 (오류, 경고, 정보 순)"""
        return self.errors + self.warnings + self.info
    
    def get_issues_by_severity(self, severity: str) -> List[ValidationError]:
        """심각도별 이슈 반환"""
        return [issue for issue in self.get_all_issues() if issue.severity == severity]
    
    def get_issues_by_scene(self, scene_id: str) -> List[ValidationError]:
        """특정 장면의 이슈 반환"""
        return [issue for issue in self.get_all_issues() if issue.scene_id == scene_id]


class ManifestValidator:
    """Manifest 검증 클래스"""
    
    def __init__(self):
        self.max_scene_count = 100
        self.max_script_length = 1000
        self.supported_resolutions = [
            "1920x1080", "1280x720", "3840x2160",  # 16:9
            "1080x1080", "1440x1440",              # 1:1
            "1080x1920", "720x1280"                # 9:16
        ]
    
    def validate(self, manifest: Manifest) -> ValidationResult:
        """전체 Manifest 검증"""
        result = ValidationResult(is_valid=True)
        
        # 기본 구조 검증
        self._validate_basic_structure(manifest, result)
        
        # 각 장면 검증
        for scene in manifest.scenes:
            self._validate_scene(scene, manifest, result)
        
        # 전체적인 일관성 검증
        self._validate_consistency(manifest, result)
        
        # 비즈니스 로직 검증
        self._validate_business_logic(manifest, result)
        
        return result
    
    def _validate_basic_structure(self, manifest: Manifest, result: ValidationResult):
        """기본 구조 검증"""
        # 프로젝트 이름 검증
        if not manifest.project_name or len(manifest.project_name.strip()) == 0:
            result.add_error("project_name", "프로젝트 이름은 필수입니다")
        elif len(manifest.project_name) > 100:
            result.add_error("project_name", "프로젝트 이름은 100자 이하여야 합니다")
        
        # 해상도 검증
        if manifest.resolution not in self.supported_resolutions:
            result.add_warning("resolution", f"지원되지 않는 해상도입니다: {manifest.resolution}")
        
        # 장면 수 검증
        if len(manifest.scenes) == 0:
            result.add_error("scenes", "최소 하나 이상의 장면이 필요합니다")
        elif len(manifest.scenes) > self.max_scene_count:
            result.add_error("scenes", f"장면 수가 너무 많습니다 (최대 {self.max_scene_count}개)")
        
        # 배경 파일 경로 검증
        if manifest.default_background:
            if not os.path.exists(manifest.default_background):
                result.add_warning("default_background", f"배경 파일을 찾을 수 없습니다: {manifest.default_background}")
    
    def _validate_scene(self, scene: Scene, manifest: Manifest, result: ValidationResult):
        """개별 장면 검증"""
        # ID 형식 검증
        if not scene.id or len(scene.id.strip()) == 0:
            result.add_error("id", "장면 ID는 필수입니다", scene.id)
        elif not scene.id.isalnum() and '_' not in scene.id:
            result.add_error("id", "장면 ID는 영문자, 숫자, 언더스코어만 사용 가능합니다", scene.id)
        
        # 타입별 필수 필드 검증
        if scene.type == "intro" or scene.type == "ending":
            if not scene.full_script:
                result.add_error("full_script", f"{scene.type} 타입은 full_script가 필요합니다", scene.id)
            elif len(scene.full_script) > self.max_script_length:
                result.add_warning("full_script", f"스크립트가 너무 깁니다 (최대 {self.max_script_length}자)", scene.id)
        
        elif scene.type == "conversation":
            required_fields = ["sequence", "native_script", "learning_script", "reading_script"]
            for field_name in required_fields:
                field_value = getattr(scene, field_name)
                if field_value is None:
                    result.add_error(field_name, f"conversation 타입은 {field_name}가 필요합니다", scene.id)
                elif isinstance(field_value, str) and len(field_value) > self.max_script_length:
                    result.add_warning(field_name, f"{field_name}이 너무 깁니다 (최대 {self.max_script_length}자)", scene.id)
            
            # sequence 검증
            if scene.sequence is not None:
                if scene.sequence < 1:
                    result.add_error("sequence", "sequence는 1 이상이어야 합니다", scene.id)
        
        elif scene.type == "dialogue":
            if not scene.script or len(scene.script) == 0:
                result.add_error("script", "dialogue 타입은 script가 필요합니다", scene.id)
            elif len(scene.script) < 2:
                result.add_warning("script", "dialogue는 최소 2개 이상의 대화 라인이 필요합니다", scene.id)
            else:
                # 각 대화 라인 검증
                for i, line in enumerate(scene.script):
                    if not line.speaker or len(line.speaker.strip()) == 0:
                        result.add_error("script", f"대화 라인 {i+1}의 화자가 비어있습니다", scene.id)
                    if not line.text or len(line.text.strip()) == 0:
                        result.add_error("script", f"대화 라인 {i+1}의 텍스트가 비어있습니다", scene.id)
                    elif len(line.text) > self.max_script_length:
                        result.add_warning("script", f"대화 라인 {i+1}의 텍스트가 너무 깁니다", scene.id)
    
    def _validate_consistency(self, manifest: Manifest, result: ValidationResult):
        """일관성 검증"""
        # ID 중복 검사
        scene_ids = [scene.id for scene in manifest.scenes]
        if len(scene_ids) != len(set(scene_ids)):
            result.add_error("scenes", "장면 ID가 중복됩니다")
        
        # conversation sequence 중복 검사
        conversation_sequences = [scene.sequence for scene in manifest.scenes if scene.type == "conversation" and scene.sequence is not None]
        if len(conversation_sequences) != len(set(conversation_sequences)):
            result.add_error("scenes", "conversation 타입의 sequence가 중복됩니다")
        
        # conversation sequence 연속성 검사
        if conversation_sequences:
            sorted_sequences = sorted(conversation_sequences)
            expected_sequences = list(range(1, len(sorted_sequences) + 1))
            if sorted_sequences != expected_sequences:
                result.add_warning("scenes", "conversation sequence가 연속적이지 않습니다")
    
    def _validate_business_logic(self, manifest: Manifest, result: ValidationResult):
        """비즈니스 로직 검증"""
        # intro/ending 장면 검증
        intro_scenes = manifest.get_scenes_by_type("intro")
        ending_scenes = manifest.get_scenes_by_type("ending")
        
        if len(intro_scenes) == 0:
            result.add_warning("scenes", "인트로 장면이 없습니다")
        elif len(intro_scenes) > 1:
            result.add_warning("scenes", "인트로 장면이 여러 개 있습니다")
        
        if len(ending_scenes) == 0:
            result.add_warning("scenes", "엔딩 장면이 없습니다")
        elif len(ending_scenes) > 1:
            result.add_warning("scenes", "엔딩 장면이 여러 개 있습니다")
        
        # conversation 장면 검증
        conversation_scenes = manifest.get_scenes_by_type("conversation")
        if len(conversation_scenes) == 0:
            result.add_warning("scenes", "회화 장면이 없습니다")
        
        # 전체 비디오 길이 추정
        estimated_duration = manifest.get_total_duration_estimate()
        if estimated_duration > 3600:  # 1시간
            result.add_warning("scenes", "예상 비디오 길이가 너무 깁니다 (1시간 이상)")
        elif estimated_duration < 30:  # 30초
            result.add_warning("scenes", "예상 비디오 길이가 너무 짧습니다 (30초 미만)")
    
    def validate_file_paths(self, manifest: Manifest, base_path: str = "") -> ValidationResult:
        """파일 경로 검증"""
        result = ValidationResult(is_valid=True)
        
        # 배경 파일 경로 검증
        if manifest.default_background:
            full_path = os.path.join(base_path, manifest.default_background) if base_path else manifest.default_background
            if not os.path.exists(full_path):
                result.add_warning("default_background", f"배경 파일을 찾을 수 없습니다: {full_path}")
            elif not os.path.isfile(full_path):
                result.add_error("default_background", f"배경 경로가 파일이 아닙니다: {full_path}")
        
        return result
    
    def get_validation_summary(self, result: ValidationResult) -> Dict[str, Any]:
        """검증 결과 요약"""
        return {
            "is_valid": result.is_valid,
            "total_issues": len(result.get_all_issues()),
            "error_count": len(result.errors),
            "warning_count": len(result.warnings),
            "info_count": len(result.info),
            "issues_by_severity": {
                "error": len(result.errors),
                "warning": len(result.warnings),
                "info": len(result.info)
            },
            "issues_by_scene": self._group_issues_by_scene(result)
        }
    
    def _group_issues_by_scene(self, result: ValidationResult) -> Dict[str, List[ValidationError]]:
        """장면별 이슈 그룹화"""
        issues_by_scene = {}
        for issue in result.get_all_issues():
            scene_id = issue.scene_id or "global"
            if scene_id not in issues_by_scene:
                issues_by_scene[scene_id] = []
            issues_by_scene[scene_id].append(issue)
        return issues_by_scene
