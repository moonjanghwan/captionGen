"""
오디오 세그먼트 분석 및 타이밍 추출

SSML mark 태그를 기반으로 정확한 오디오 세그먼트 타이밍을 추출합니다.
"""

import json
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class AudioSegment:
    """오디오 세그먼트 정보"""
    name: str
    start_time: float
    end_time: float
    duration: float
    type: str
    scene_id: str
    content: str


class AudioSegmenter:
    """오디오 세그먼트 분석 클래스"""
    
    def __init__(self):
        self.segments = []
        self.total_duration = 0.0
    
    def analyze_ssml_marks(self, ssml_content: str) -> List[Dict[str, Any]]:
        """
        SSML에서 mark 태그 분석
        
        Args:
            ssml_content: SSML 내용
            
        Returns:
            List[Dict[str, Any]]: mark 태그 정보 리스트
        """
        marks = []
        
        # mark 태그 찾기
        mark_pattern = r'<mark name="([^"]+)"\s*/>'
        matches = re.finditer(mark_pattern, ssml_content)
        
        for match in matches:
            mark_name = match.group(1)
            position = match.start()
            
            # mark 타입 분석
            mark_type = self._analyze_mark_type(mark_name)
            scene_id = self._extract_scene_id(mark_name)
            
            marks.append({
                "name": mark_name,
                "position": position,
                "type": mark_type,
                "scene_id": scene_id,
                "content": self._extract_content_around_mark(ssml_content, position)
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
        elif "start" in mark_name:
            return "start"
        elif "end" in mark_name:
            return "end"
        else:
            return "general"
    
    def _extract_scene_id(self, mark_name: str) -> str:
        """mark 이름에서 장면 ID 추출"""
        if "scene_" in mark_name:
            parts = mark_name.split("_")
            if len(parts) >= 2:
                return parts[1]
        return ""
    
    def _extract_content_around_mark(self, ssml_content: str, position: int, 
                                   context_size: int = 100) -> str:
        """mark 주변의 내용 추출"""
        start = max(0, position - context_size)
        end = min(len(ssml_content), position + context_size)
        
        content = ssml_content[start:end]
        
        # XML 태그 제거하여 가독성 향상
        content = re.sub(r'<[^>]+>', '', content)
        content = re.sub(r'\s+', ' ', content).strip()
        
        return content
    
    def create_timing_segments(self, marks: List[Dict[str, Any]], 
                             estimated_duration: float) -> List[AudioSegment]:
        """
        mark 태그를 기반으로 타이밍 세그먼트 생성
        
        Args:
            marks: mark 태그 정보 리스트
            estimated_duration: 예상 오디오 길이 (초)
            
        Returns:
            List[AudioSegment]: 타이밍 세그먼트 리스트
        """
        segments = []
        
        # mark들을 시간 순서로 정렬
        sorted_marks = sorted(marks, key=lambda x: x["position"])
        
        # 각 mark 쌍을 찾아서 세그먼트 생성
        for i in range(len(sorted_marks) - 1):
            current_mark = sorted_marks[i]
            next_mark = sorted_marks[i + 1]
            
            # 시작과 끝 mark 쌍 찾기
            if self._is_start_end_pair(current_mark, next_mark):
                segment = self._create_segment_from_marks(
                    current_mark, next_mark, estimated_duration
                )
                if segment:
                    segments.append(segment)
        
        return segments
    
    def _is_start_end_pair(self, mark1: Dict[str, Any], mark2: Dict[str, Any]) -> bool:
        """두 mark가 시작-끝 쌍인지 확인"""
        name1 = mark1["name"]
        name2 = mark2["name"]
        
        # screen1_start와 screen1_end
        if "screen1_start" in name1 and "screen1_end" in name2:
            return True
        
        # screen2_start와 screen2_end
        if "screen2_start" in name1 and "screen2_end" in name2:
            return True
        
        # speaker_start와 speaker_end
        if "start" in name1 and "end" in name2:
            # 같은 화자와 인덱스인지 확인
            if self._same_speaker_index(name1, name2):
                return True
        
        return False
    
    def _same_speaker_index(self, name1: str, name2: str) -> bool:
        """두 mark가 같은 화자와 인덱스를 가리키는지 확인"""
        # speaker_A_0_start와 speaker_A_0_end 같은 패턴
        pattern1 = r'speaker_([A-Z])_(\d+)_start'
        pattern2 = r'speaker_([A-Z])_(\d+)_end'
        
        match1 = re.search(pattern1, name1)
        match2 = re.search(pattern2, name2)
        
        if match1 and match2:
            return (match1.group(1) == match2.group(1) and 
                   match1.group(2) == match2.group(2))
        
        return False
    
    def _create_segment_from_marks(self, start_mark: Dict[str, Any], 
                                 end_mark: Dict[str, Any], 
                                 estimated_duration: float) -> Optional[AudioSegment]:
        """두 mark로부터 세그먼트 생성"""
        try:
            # 위치 기반 상대적 시간 계산
            start_time = self._position_to_time(start_mark["position"], estimated_duration)
            end_time = self._position_to_time(end_mark["position"], estimated_duration)
            
            # 유효한 시간 범위 확인
            if start_time >= end_time:
                return None
            
            duration = end_time - start_time
            
            # 세그먼트 이름 생성
            segment_name = f"{start_mark['name']}_to_{end_mark['name']}"
            
            # 세그먼트 타입 결정
            segment_type = self._determine_segment_type(start_mark, end_mark)
            
            # 장면 ID 추출
            scene_id = start_mark.get("scene_id", "")
            
            # 내용 추출
            content = start_mark.get("content", "")
            
            return AudioSegment(
                name=segment_name,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                type=segment_type,
                scene_id=scene_id,
                content=content
            )
            
        except Exception as e:
            print(f"세그먼트 생성 실패: {e}")
            return None
    
    def _position_to_time(self, position: int, estimated_duration: float) -> float:
        """SSML 내 위치를 시간으로 변환 (대략적 추정)"""
        # 이는 매우 대략적인 추정입니다
        # 실제로는 TTS API의 응답에서 정확한 시간을 얻어야 합니다
        
        # SSML 길이를 기준으로 비례 계산
        # 실제 구현에서는 더 정교한 방법 필요
        
        # 기본값: 위치 기반 선형 추정
        return (position / 1000) * (estimated_duration / 60)  # 대략적 변환
    
    def _determine_segment_type(self, start_mark: Dict[str, Any], 
                               end_mark: Dict[str, Any]) -> str:
        """세그먼트 타입 결정"""
        start_name = start_mark["name"]
        
        if "screen1" in start_name:
            return "screen1"
        elif "screen2" in start_name:
            return "screen2"
        elif "speaker" in start_name:
            return "speaker"
        else:
            return "general"
    
    def generate_timing_json(self, segments: List[AudioSegment], 
                           output_path: str) -> None:
        """타이밍 정보를 JSON 파일로 저장"""
        timing_data = {
            "total_duration": self.total_duration,
            "segments": [
                {
                    "name": seg.name,
                    "start_time": seg.start_time,
                    "end_time": seg.end_time,
                    "duration": seg.duration,
                    "type": seg.type,
                    "scene_id": seg.scene_id,
                    "content": seg.content
                }
                for seg in segments
            ]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(timing_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 타이밍 정보 저장: {output_path}")
    
    def analyze_conversation_timing(self, manifest_data: Dict[str, Any]) -> Dict[str, Any]:
        """conversation 타입 장면의 타이밍 분석"""
        conversation_scenes = [
            scene for scene in manifest_data.get("scenes", [])
            if scene.get("type") == "conversation"
        ]
        
        timing_analysis = {}
        
        for scene in conversation_scenes:
            sequence = scene.get("sequence", 1)
            scene_id = scene.get("id", "")
            
            # 각 장면별 예상 타이밍 계산
            # 실제 구현에서는 TTS API 응답 기반으로 계산
            timing_analysis[scene_id] = {
                "sequence": sequence,
                "screen1": {
                    "start": 0.0,  # 실제 시간으로 대체 필요
                    "end": 5.0,    # 실제 시간으로 대체 필요
                    "duration": 5.0
                },
                "screen2": {
                    "start": 6.0,  # 원어 + 1초 무음 후
                    "end": 25.0,   # 4명의 학습어 + 3초 무음
                    "duration": 19.0
                },
                "total_duration": 25.0
            }
        
        return timing_analysis
    
    def create_ffmpeg_timeline(self, segments: List[AudioSegment]) -> str:
        """FFmpeg 타임라인 명령어 생성"""
        timeline_parts = []
        
        for segment in segments:
            # 각 세그먼트에 대한 FFmpeg 필터 생성
            if segment.type == "screen1":
                timeline_parts.append(
                    f"[0:v]trim=start={segment.start_time}:end={segment.end_time},"
                    f"setpts=PTS-STARTPTS[v{segment.scene_id}_screen1];"
                )
            elif segment.type == "screen2":
                timeline_parts.append(
                    f"[0:v]trim=start={segment.start_time}:end={segment.end_time},"
                    f"setpts=PTS-STARTPTS[v{segment.scene_id}_screen2];"
                )
        
        return ''.join(timeline_parts)
    
    def validate_timing_consistency(self, segments: List[AudioSegment]) -> List[str]:
        """타이밍 일관성 검증"""
        errors = []
        
        # 시간 순서 검증
        sorted_segments = sorted(segments, key=lambda x: x.start_time)
        
        for i in range(len(sorted_segments) - 1):
            current = sorted_segments[i]
            next_seg = sorted_segments[i + 1]
            
            if current.end_time > next_seg.start_time:
                errors.append(
                    f"시간 겹침: {current.name} ({current.end_time}s) > "
                    f"{next_seg.name} ({next_seg.start_time}s)"
                )
        
        # 장면별 화면 순서 검증
        scene_screens = {}
        for segment in segments:
            scene_id = segment.scene_id
            if scene_id not in scene_screens:
                scene_screens[scene_id] = []
            scene_screens[scene_id].append(segment)
        
        for scene_id, screen_segments in scene_screens.items():
            screen1_segments = [s for s in screen_segments if s.type == "screen1"]
            screen2_segments = [s for s in screen_segments if s.type == "screen2"]
            
            if screen1_segments and screen2_segments:
                screen1_end = max(s.end_time for s in screen1_segments)
                screen2_start = min(s.start_time for s in screen2_segments)
                
                if screen1_end >= screen2_start:
                    errors.append(
                        f"장면 {scene_id}: 화면1과 화면2 시간 순서 오류"
                    )
        
        return errors
