"""
SSML (Speech Synthesis Markup Language) 빌더

사양서에 따른 정확한 타이밍을 위한 SSML 생성 로직을 구현합니다.
"""

from typing import List, Dict, Any, Optional
import re


class SSMLBuilder:
    """SSML 생성 클래스"""
    
    def __init__(self):
        self.voice_configs = {
            "native": {
                "name": "ko-KR-Standard-A",
                "language": "ko-KR",
                "gender": "FEMALE"
            },
            "learner_1": {
                "name": "cmn-CN-Standard-A",
                "language": "cmn-CN", 
                "gender": "FEMALE"
            },
            "learner_2": {
                "name": "cmn-CN-Standard-B",
                "language": "cmn-CN",
                "gender": "MALE"
            },
            "learner_3": {
                "name": "cmn-CN-Standard-C",
                "language": "cmn-CN",
                "gender": "FEMALE"
            },
            "learner_4": {
                "name": "cmn-CN-Standard-D",
                "language": "cmn-CN",
                "gender": "MALE"
            }
        }
    
    def build_conversation_ssml(self, scene_data: Dict[str, Any]) -> str:
        """
        conversation 타입 장면을 위한 SSML 생성
        
        사양서 룰:
        1. 원어 화자 - 원어 (화면 1)
        2. 학습어 화자 1,2,3,4 - 학습어 (화면 2)
        3. 각 화자 간, 행 간에는 1초 무음 삽입
        """
        sequence = scene_data.get("sequence", 1)
        native_script = scene_data.get("native_script", "")
        learning_script = scene_data.get("learning_script", "")
        
        # SSML 시작
        ssml_parts = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<speak version="1.1" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="ko-KR">'
        ]
        
        # 1. 원어 화자 (화면 1용)
        if native_script:
            ssml_parts.append(f'<voice name="{self.voice_configs["native"]["name"]}">')
            ssml_parts.append(f'<mark name="scene_{sequence}_screen1_start"/>')
            ssml_parts.append(f'<prosody rate="medium" pitch="medium">{native_script}</prosody>')
            ssml_parts.append(f'<mark name="scene_{sequence}_screen1_end"/>')
            ssml_parts.append('</voice>')
            
            # 원어 후 1초 무음
            ssml_parts.append('<break time="1s"/>')
        
        # 2. 학습어 화자들 (화면 2용)
        if learning_script:
            # 화면 2 시작 마크
            ssml_parts.append(f'<mark name="scene_{sequence}_screen2_start"/>')
            
            # 학습어 화자 1
            ssml_parts.append(f'<voice name="{self.voice_configs["learner_1"]["name"]}">')
            ssml_parts.append(f'<prosody rate="medium" pitch="medium">{learning_script}</prosody>')
            ssml_parts.append('</voice>')
            ssml_parts.append('<break time="1s"/>')
            
            # 학습어 화자 2
            ssml_parts.append(f'<voice name="{self.voice_configs["learner_2"]["name"]}">')
            ssml_parts.append(f'<prosody rate="medium" pitch="medium">{learning_script}</prosody>')
            ssml_parts.append('</voice>')
            ssml_parts.append('<break time="1s"/>')
            
            # 학습어 화자 3
            ssml_parts.append(f'<voice name="{self.voice_configs["learner_3"]["name"]}">')
            ssml_parts.append(f'<prosody rate="medium" pitch="medium">{learning_script}</prosody>')
            ssml_parts.append('</voice>')
            ssml_parts.append('<break time="1s"/>')
            
            # 학습어 화자 4 (마지막은 무음 없음)
            ssml_parts.append(f'<voice name="{self.voice_configs["learner_4"]["name"]}">')
            ssml_parts.append(f'<prosody rate="medium" pitch="medium">{learning_script}</prosody>')
            ssml_parts.append('</voice>')
            
            # 화면 2 종료 마크
            ssml_parts.append(f'<mark name="scene_{sequence}_screen2_end"/>')
        
        # SSML 종료
        ssml_parts.append('</speak>')
        
        return '\n'.join(ssml_parts)
    
    def build_intro_ending_ssml(self, scene_data: Dict[str, Any]) -> str:
        """intro/ending 타입 장면을 위한 SSML 생성"""
        scene_id = scene_data.get("id", "")
        full_script = scene_data.get("full_script", "")
        
        ssml_parts = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<speak version="1.1" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="ko-KR">'
        ]
        
        if full_script:
            ssml_parts.append(f'<voice name="{self.voice_configs["native"]["name"]}">')
            ssml_parts.append(f'<mark name="{scene_id}_start"/>')
            ssml_parts.append(f'<prosody rate="medium" pitch="medium">{full_script}</prosody>')
            ssml_parts.append(f'<mark name="{scene_id}_end"/>')
            ssml_parts.append('</voice>')
        
        ssml_parts.append('</speak>')
        
        return '\n'.join(ssml_parts)
    
    def build_dialogue_ssml(self, scene_data: Dict[str, Any]) -> str:
        """dialogue 타입 장면을 위한 SSML 생성"""
        scene_id = scene_data.get("id", "")
        script = scene_data.get("script", [])
        
        ssml_parts = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<speak version="1.1" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="ko-KR">'
        ]
        
        for i, line in enumerate(script):
            speaker = line.get("speaker", "")
            text = line.get("text", "")
            
            if text:
                # 화자별 음성 설정
                voice_name = self._get_speaker_voice(speaker)
                
                ssml_parts.append(f'<voice name="{voice_name}">')
                ssml_parts.append(f'<mark name="{scene_id}_speaker_{speaker}_{i}_start"/>')
                ssml_parts.append(f'<prosody rate="medium" pitch="medium">{text}</prosody>')
                ssml_parts.append(f'<mark name="{scene_id}_speaker_{speaker}_{i}_end"/>')
                ssml_parts.append('</voice>')
                
                # 화자 간 무음 (마지막 제외)
                if i < len(script) - 1:
                    ssml_parts.append('<break time="1s"/>')
        
        ssml_parts.append('</speak>')
        
        return '\n'.join(ssml_parts)
    
    def _get_speaker_voice(self, speaker: str) -> str:
        """화자별 음성 설정 반환"""
        speaker_mapping = {
            "A": self.voice_configs["native"]["name"],
            "B": self.voice_configs["learner_1"]["name"],
            "C": self.voice_configs["learner_2"]["name"],
            "D": self.voice_configs["learner_3"]["name"],
            "E": self.voice_configs["learner_4"]["name"]
        }
        
        return speaker_mapping.get(speaker, self.voice_configs["native"]["name"])
    
    def build_manifest_ssml(self, manifest_data: Dict[str, Any]) -> str:
        """전체 Manifest를 위한 통합 SSML 생성"""
        scenes = manifest_data.get("scenes", [])
        
        ssml_parts = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<speak version="1.1" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="ko-KR">'
        ]
        
        for scene in scenes:
            scene_type = scene.get("type", "")
            
            if scene_type == "conversation":
                # conversation 타입은 별도 처리
                ssml_parts.append(self.build_conversation_ssml(scene))
            elif scene_type == "intro":
                ssml_parts.append(self.build_intro_ending_ssml(scene))
            elif scene_type == "ending":
                ssml_parts.append(self.build_intro_ending_ssml(scene))
            elif scene_type == "dialogue":
                ssml_parts.append(self.build_dialogue_ssml(scene))
            
            # 장면 간 무음 (마지막 제외)
            if scene != scenes[-1]:
                ssml_parts.append('<break time="1s"/>')
        
        ssml_parts.append('</speak>')
        
        return '\n'.join(ssml_parts)
    
    def get_mark_timings(self, ssml_content: str) -> List[Dict[str, Any]]:
        """SSML에서 mark 태그 정보 추출"""
        marks = []
        
        # mark 태그 찾기
        mark_pattern = r'<mark name="([^"]+)"\s*/>'
        matches = re.finditer(mark_pattern, ssml_content)
        
        for match in matches:
            mark_name = match.group(1)
            marks.append({
                "name": mark_name,
                "position": match.start(),
                "type": self._analyze_mark_type(mark_name)
            })
        
        return marks
    
    def _analyze_mark_type(self, mark_name: str) -> str:
        """mark 이름을 분석하여 타입 반환"""
        if "screen1" in mark_name:
            return "screen1"
        elif "screen2" in mark_name:
            return "screen2"
        elif "speaker" in mark_name:
            return "speaker"
        else:
            return "general"
    
    def create_ssml_file(self, ssml_content: str, output_path: str) -> None:
        """SSML 파일로 저장"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(ssml_content)
    
    def validate_ssml(self, ssml_content: str) -> bool:
        """SSML 유효성 검사"""
        # 기본 XML 구조 검사
        if not ssml_content.startswith('<?xml'):
            return False
        
        if not ssml_content.endswith('</speak>'):
            return False
        
        # 필수 태그 검사
        required_tags = ['<speak', '</speak>']
        for tag in required_tags:
            if tag not in ssml_content:
                return False
        
        return True
