"""
Manifest 파일의 데이터 구조를 정의하는 Pydantic 모델들
"""

from typing import List, Optional, Union, Literal
from pydantic import BaseModel, Field, field_validator
import re


class DialogueLine(BaseModel):
    """대화 라인을 나타내는 모델"""
    speaker: str = Field(..., description="화자 식별자 (A, B, C 등)")
    text: str = Field(..., description="대사 내용")
    
    @field_validator('speaker')
    @classmethod
    def validate_speaker(cls, v):
        if not re.match(r'^[A-Za-z0-9_]+$', v):
            raise ValueError('화자는 영문자, 숫자, 언더스코어만 사용 가능합니다')
        return v


class ConversationScene(BaseModel):
    """회화 장면을 나타내는 모델"""
    sequence: int = Field(..., description="회화 순서 번호")
    native_script: str = Field(..., description="원어 스크립트")
    learning_script: str = Field(..., description="학습어 스크립트")
    reading_script: str = Field(..., description="읽기 스크립트 (로마자/한글)")


class IntroEndingScene(BaseModel):
    """인트로/엔딩 장면을 나타내는 모델"""
    full_script: str = Field(..., description="전체 스크립트")


class DialogueScene(BaseModel):
    """대화 장면을 나타내는 모델"""
    script: List[DialogueLine] = Field(..., description="대화 스크립트 리스트")
    
    @field_validator('script')
    @classmethod
    def validate_script(cls, v):
        if len(v) < 2:
            raise ValueError('대화 장면은 최소 2개 이상의 대화 라인이 필요합니다')
        return v


class Scene(BaseModel):
    """개별 장면을 나타내는 모델"""
    id: str = Field(..., description="장면 고유 식별자")
    type: Literal["intro", "conversation", "dialogue", "ending"] = Field(..., description="장면 타입")
    
    # 타입별 선택적 속성들
    full_script: Optional[str] = Field(None, description="전체 스크립트 (intro/ending용)")
    sequence: Optional[int] = Field(None, description="순서 번호 (conversation용)")
    native_script: Optional[str] = Field(None, description="원어 스크립트 (conversation용)")
    learning_script: Optional[str] = Field(None, description="학습어 스크립트 (conversation용)")
    reading_script: Optional[str] = Field(None, description="읽기 스크립트 (conversation용)")
    script: Optional[List[DialogueLine]] = Field(None, description="대화 스크립트 (dialogue용)")
    
    @field_validator('*', mode='before')
    @classmethod
    def validate_type_specific_fields(cls, v, info):
        """타입별 필수 필드 검증"""
        if not isinstance(v, dict):
            return v
            
        scene_type = v.get('type')
        
        if scene_type == "intro" or scene_type == "ending":
            if not v.get('full_script'):
                raise ValueError(f'{scene_type} 타입은 full_script가 필요합니다')
                
        elif scene_type == "conversation":
            required_fields = ['sequence', 'native_script', 'learning_script', 'reading_script']
            for field_name in required_fields:
                if not v.get(field_name):
                    raise ValueError(f'conversation 타입은 {field_name}가 필요합니다')
                    
        elif scene_type == "dialogue":
            if not v.get('script'):
                raise ValueError('dialogue 타입은 script가 필요합니다')
                
        return v
    
    @field_validator('id')
    @classmethod
    def validate_id(cls, v):
        """ID 형식 검증"""
        if not re.match(r'^[a-z0-9_]+$', v):
            raise ValueError('ID는 소문자, 숫자, 언더스코어만 사용 가능합니다')
        return v


class Manifest(BaseModel):
    """전체 Manifest 파일을 나타내는 모델"""
    project_name: str = Field(..., description="프로젝트 이름")
    resolution: str = Field(default="1920x1080", description="해상도")
    default_background: Optional[str] = Field(None, description="기본 배경 파일 경로")
    scenes: List[Scene] = Field(..., description="장면 리스트")
    
    @field_validator('resolution')
    @classmethod
    def validate_resolution(cls, v):
        """해상도 형식 검증"""
        if not re.match(r'^\d+x\d+$', v):
            raise ValueError('해상도는 "가로x세로" 형식이어야 합니다 (예: 1920x1080)')
        return v
    
    @field_validator('scenes')
    @classmethod
    def validate_scenes(cls, v):
        """장면 리스트 검증"""
        if not v:
            raise ValueError('최소 하나 이상의 장면이 필요합니다')
        
        # ID 중복 검사
        ids = [scene.id for scene in v]
        if len(ids) != len(set(ids)):
            raise ValueError('장면 ID는 고유해야 합니다')
        
        # conversation 타입의 sequence 중복 검사
        conversation_sequences = [scene.sequence for scene in v if scene.type == "conversation"]
        if len(conversation_sequences) != len(set(conversation_sequences)):
            raise ValueError('conversation 타입의 sequence는 고유해야 합니다')
        
        return v
    
    def get_scenes_by_type(self, scene_type: str) -> List[Scene]:
        """특정 타입의 장면들을 반환"""
        return [scene for scene in self.scenes if scene.type == scene_type]
    
    def get_conversation_scenes_sorted(self) -> List[Scene]:
        """sequence 순으로 정렬된 conversation 장면들을 반환"""
        conversation_scenes = self.get_scenes_by_type("conversation")
        return sorted(conversation_scenes, key=lambda x: x.sequence)
    
    def get_total_duration_estimate(self) -> float:
        """전체 비디오 길이 추정 (초 단위)"""
        # 간단한 추정: 각 장면당 평균 10초
        return len(self.scenes) * 10.0
    
    def to_dict(self) -> dict:
        """딕셔너리 형태로 변환"""
        return self.dict()
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Manifest':
        """딕셔너리에서 Manifest 객체 생성"""
        return cls(**data)
