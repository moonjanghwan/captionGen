"""
자막 이미지 생성기

SSML mark 태그 기반으로 정확한 타이밍에 맞춰 PNG 시퀀스를 자동 생성합니다.
"""

import os
import json
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from PIL import Image # Added missing import for Image

from .text_renderer import TextRenderer


@dataclass
class SubtitleFrame:
    """자막 프레임 정보"""
    frame_number: int
    start_time: float
    end_time: float
    duration: float
    scene_id: str
    screen_type: str
    content: List[str]
    output_path: str


class SubtitleGenerator:
    """자막 이미지 생성 클래스"""
    
    def __init__(self, settings: Dict[str, Any]):
        """
        자막 생성기 초기화
        
        Args:
            settings: UI에서 전달된 전체 설정
        """
        self.text_renderer = TextRenderer(settings)
        self.frames = []
        self.output_dir = ""
        self.resolution = (1920, 1080)
    
    def generate_from_manifest(self, manifest_data: Dict[str, Any], 
                             output_dir: str, fps: int = 30) -> List[SubtitleFrame]:
        """
        Manifest에서 자막 이미지 시퀀스 생성
        
        Args:
            manifest_data: Manifest 데이터
            output_dir: 출력 디렉토리
            fps: 프레임 레이트
            
        Returns:
            List[SubtitleFrame]: 생성된 프레임 정보 리스트
        """
        self.output_dir = output_dir
        self.resolution = self._parse_resolution(manifest_data.get("resolution", "1920x1080"))
        
        # 출력 디렉토리 생성
        os.makedirs(output_dir, exist_ok=True)
        
        # 장면별 자막 이미지 생성
        scenes = manifest_data.get("scenes", [])
        frame_counter = 0
        
        for scene in scenes:
            scene_type = scene.get("type", "")
            
            if scene_type == "conversation":
                frames = self._generate_conversation_frames(scene, frame_counter, fps)
                self.frames.extend(frames)
                frame_counter += len(frames)
            elif scene_type == "intro":
                frames = self._generate_intro_frames(scene, frame_counter, fps)
                self.frames.extend(frames)
                frame_counter += len(frames)
            elif scene_type == "ending":
                frames = self._generate_ending_frames(scene, frame_counter, fps)
                self.frames.extend(frames)
                frame_counter += len(frames)
        
        # 프레임 정보 저장
        self._save_frame_info()
        
        return self.frames
    
    def _parse_resolution(self, resolution_str: str) -> Tuple[int, int]:
        """해상도 문자열을 튜플로 변환"""
        try:
            width, height = map(int, resolution_str.split('x'))
            return width, height
        except:
            return (1920, 1080)
    
    def _generate_conversation_frames(self, scene: Dict[str, Any], 
                                    start_frame: int, fps: int) -> List[SubtitleFrame]:
        """conversation 타입 장면의 프레임 생성"""
        frames = []
        sequence = scene.get("sequence", 1)
        scene_id = scene.get("id", f"conversation_{sequence}")
        
        # 화면 1: 순번 + 원어
        screen1_frame = self._create_conversation_screen1_frame(
            scene, start_frame, fps, scene_id
        )
        frames.append(screen1_frame)
        
        # 화면 2: 순번 + 원어 + 학습어 + 읽기
        screen2_frame = self._create_conversation_screen2_frame(
            scene, start_frame + 1, fps, scene_id
        )
        frames.append(screen2_frame)
        
        return frames
    
    def _create_conversation_screen1_frame(self, scene: Dict[str, Any], 
                                         frame_number: int, fps: int, 
                                         scene_id: str) -> SubtitleFrame:
        """conversation 화면 1 프레임 생성"""
        sequence = scene.get("sequence", 1)
        native_script = scene.get("native_script", "")
        
        # 예상 지속 시간 (원어 발음 + 1초 무음)
        duration = self._estimate_speech_duration(native_script) + 1.0
        
        # Get line settings from config
        rows_cfg = self.text_renderer.config.get("tabs", {}).get("회화 설정", {}).get("rows", [])
        seq_cfg = next((row for row in rows_cfg if row.get("행") == "순번"), {})
        native_cfg = next((row for row in rows_cfg if row.get("행") == "원어"), {})
        line_settings = [seq_cfg, native_cfg]

        # 이미지 생성
        image = self.text_renderer.render_conversation_screen1(
            sequence, native_script, self.resolution[0], self.resolution[1], line_settings
        )
        
        # 파일 저장
        output_path = os.path.join(self.output_dir, f"{scene_id}_screen1_{frame_number:04d}.png")
        self.text_renderer.save_image(image, output_path)
        
        return SubtitleFrame(
            frame_number=frame_number,
            start_time=frame_number / fps,
            end_time=(frame_number + duration * fps) / fps,
            duration=duration,
            scene_id=scene_id,
            screen_type="screen1",
            content=[str(sequence), native_script],
            output_path=output_path
        )
    
    def _create_conversation_screen2_frame(self, scene: Dict[str, Any], 
                                         frame_number: int, fps: int, 
                                         scene_id: str) -> SubtitleFrame:
        """conversation 화면 2 프레임 생성"""
        sequence = scene.get("sequence", 1)
        native_script = scene.get("native_script", "")
        learning_script = scene.get("learning_script", "")
        reading_script = scene.get("reading_script", "")
        
        # 예상 지속 시간 (4명의 학습어 발음 + 3초 무음)
        duration = self._estimate_speech_duration(learning_script) * 4 + 3.0
        
        # Get line settings from config
        rows_cfg = self.text_renderer.config.get("tabs", {}).get("회화 설정", {}).get("rows", [])
        seq_cfg = next((row for row in rows_cfg if row.get("행") == "순번"), {})
        native_cfg = next((row for row in rows_cfg if row.get("행") == "원어"), {})
        learning_cfg = next((row for row in rows_cfg if row.get("행") == "학습어"), {})
        reading_cfg = next((row for row in rows_cfg if row.get("행") == "읽기"), {})
        line_settings = [seq_cfg, native_cfg, learning_cfg, reading_cfg]

        # 이미지 생성
        image = self.text_renderer.render_conversation_screen2(
            sequence, native_script, learning_script, reading_script,
            self.resolution[0], self.resolution[1], line_settings
        )
        
        # 파일 저장
        output_path = os.path.join(self.output_dir, f"{scene_id}_screen2_{frame_number:04d}.png")
        self.text_renderer.save_image(image, output_path)
        
        return SubtitleFrame(
            frame_number=frame_number,
            start_time=frame_number / fps,
            end_time=(frame_number + duration * fps) / fps,
            duration=duration,
            scene_id=scene_id,
            screen_type="screen2",
            content=[str(sequence), native_script, learning_script, reading_script],
            output_path=output_path
        )
    
    def _generate_intro_frames(self, scene: Dict[str, Any], 
                              start_frame: int, fps: int) -> List[SubtitleFrame]:
        """intro 타입 장면의 프레임 생성"""
        scene_id = scene.get("id", "intro")
        full_script = scene.get("full_script", "")
        
        # 예상 지속 시간
        duration = self._estimate_speech_duration(full_script)
        
        # Get line settings from config
        rows_cfg = self.text_renderer.config.get("tabs", {}).get("인트로 설정", {}).get("rows", [])
        line_settings = rows_cfg

        # 이미지 생성
        image = self.text_renderer.render_intro_ending(
            full_script, self.resolution[0], self.resolution[1], "intro", line_settings
        )
        
        # 파일 저장
        output_path = os.path.join(self.output_dir, f"{scene_id}_{start_frame:04d}.png")
        self.text_renderer.save_image(image, output_path)
        
        frame = SubtitleFrame(
            frame_number=start_frame,
            start_time=start_frame / fps,
            end_time=(start_frame + duration * fps) / fps,
            duration=duration,
            scene_id=scene_id,
            screen_type="intro",
            content=[full_script],
            output_path=output_path
        )
        
        return [frame]
    
    def _generate_ending_frames(self, scene: Dict[str, Any], 
                               start_frame: int, fps: int) -> List[SubtitleFrame]:
        """ending 타입 장면의 프레임 생성"""
        scene_id = scene.get("id", "ending")
        full_script = scene.get("full_script", "")
        
        # 예상 지속 시간
        duration = self._estimate_speech_duration(full_script)
        
        # Get line settings from config
        rows_cfg = self.text_renderer.config.get("tabs", {}).get("엔딩 설정", {}).get("rows", [])
        line_settings = rows_cfg

        # 이미지 생성
        image = self.text_renderer.render_intro_ending(
            full_script, self.resolution[0], self.resolution[1], "ending", line_settings
        )
        
        # 파일 저장
        output_path = os.path.join(self.output_dir, f"{scene_id}_{start_frame:04d}.png")
        self.text_renderer.save_image(image, output_path)
        
        frame = SubtitleFrame(
            frame_number=start_frame,
            start_time=start_frame / fps,
            end_time=(start_frame + duration * fps) / fps,
            duration=duration,
            scene_id=scene_id,
            screen_type="ending",
            content=[full_script],
            output_path=output_path
        )
        
        return [frame]
    
    def _estimate_speech_duration(self, text: str) -> float:
        """텍스트 발음 지속 시간 추정 (초)"""
        # 간단한 추정 로직
        # 한글: 약 0.3초/음절, 영어: 약 0.2초/단어, 한자: 약 0.4초/자
        duration = 0
        
        for char in text:
            if '\u4e00' <= char <= '\u9fff':  # 한자
                duration += 0.4
            elif '\uac00' <= char <= '\ud7af':  # 한글
                duration += 0.3
            elif '\u0041' <= char <= '\u005a' or '\u0061' <= char <= '\u007a':  # 영문
                duration += 0.1
            else:
                duration += 0.2
        
        # 최소 지속 시간 보장
        return max(duration, 2.0)
    
    def generate_from_ssml_marks(self, ssml_content: str, output_dir: str, 
                                fps: int = 30) -> List[SubtitleFrame]:
        """
        SSML mark 태그에서 자막 이미지 시퀀스 생성
        
        Args:
            ssml_content: SSML 내용
            output_dir: 출력 디렉토리
            fps: 프레임 레이트
            
        Returns:
            List[SubtitleFrame]: 생성된 프레임 정보 리스트
        """
        self.output_dir = output_dir
        
        # 출력 디렉토리 생성
        os.makedirs(output_dir, exist_ok=True)
        
        # mark 태그 분석
        marks = self._extract_marks_from_ssml(ssml_content)
        
        # 프레임 생성
        frames = []
        frame_counter = 0
        
        for i in range(0, len(marks) - 1, 2):
            start_mark = marks[i]
            end_mark = marks[i + 1]
            
            if self._is_valid_mark_pair(start_mark, end_mark):
                frame = self._create_frame_from_marks(
                    start_mark, end_mark, frame_counter, fps
                )
                if frame:
                    frames.append(frame)
                    frame_counter += 1
        
        self.frames = frames
        self._save_frame_info()
        
        return frames
    
    def _extract_marks_from_ssml(self, ssml_content: str) -> List[Dict[str, Any]]:
        """SSML에서 mark 태그 추출"""
        marks = []
        mark_pattern = r'<mark name="([^"]+)"\s*/>'
        
        for match in re.finditer(mark_pattern, ssml_content):
            mark_name = match.group(1)
            position = match.start()
            
            # mark 타입 분석
            mark_type = self._analyze_mark_type(mark_name)
            scene_id = self._extract_scene_id(mark_name)
            
            marks.append({
                "name": mark_name,
                "position": position,
                "type": mark_type,
                "scene_id": scene_id
            })
        
        return marks
    
    def _analyze_mark_type(self, mark_name: str) -> str:
        """mark 이름을 분석하여 타입 반환"""
        if "screen1" in mark_name:
            return "screen1"
        elif "screen2" in mark_name:
            return "screen2"
        elif "intro" in mark_name:
            return "intro"
        elif "ending" in mark_name:
            return "ending"
        else:
            return "general"
    
    def _extract_scene_id(self, mark_name: str) -> str:
        """mark 이름에서 장면 ID 추출"""
        if "scene_" in mark_name:
            parts = mark_name.split("_")
            if len(parts) >= 2:
                return parts[1]
        return "unknown"
    
    def _is_valid_mark_pair(self, start_mark: Dict[str, Any], 
                           end_mark: Dict[str, Any]) -> bool:
        """두 mark가 유효한 시작-끝 쌍인지 확인"""
        start_name = start_mark["name"]
        end_name = end_mark["name"]
        
        # 같은 장면의 같은 타입인지 확인
        if start_mark["scene_id"] != end_mark["scene_id"]:
            return False
        
        # 시작과 끝 패턴 확인
        if "start" in start_name and "end" in end_name:
            # screen1_start와 screen1_end
            if "screen1" in start_name and "screen1" in end_name:
                return True
            # screen2_start와 screen2_end
            elif "screen2" in start_name and "screen2" in end_name:
                return True
            # intro_start와 intro_end
            elif "intro" in start_name and "intro" in end_name:
                return True
            # ending_start와 ending_end
            elif "ending" in start_name and "ending" in end_name:
                return True
        
        return False
    
    def _create_frame_from_marks(self, start_mark: Dict[str, Any], 
                                end_mark: Dict[str, Any], frame_number: int, 
                                fps: int) -> Optional[SubtitleFrame]:
        """mark 쌍으로부터 프레임 생성"""
        try:
            scene_id = start_mark["scene_id"]
            mark_type = start_mark["type"]
            
            # 예상 지속 시간 (위치 기반 추정)
            duration = self._estimate_duration_from_marks(start_mark, end_mark)
            
            # 더미 이미지 생성 (실제로는 SSML 내용을 분석해야 함)
            image = Image.new('RGBA', self.resolution, "#000000")
            
            # 파일 저장
            output_path = os.path.join(self.output_dir, f"{scene_id}_{mark_type}_{frame_number:04d}.png")
            self.text_renderer.save_image(image, output_path)
            
            return SubtitleFrame(
                frame_number=frame_number,
                start_time=frame_number / fps,
                end_time=(frame_number + duration * fps) / fps,
                duration=duration,
                scene_id=scene_id,
                screen_type=mark_type,
                content=[f"Frame {frame_number}"],
                output_path=output_path
            )
            
        except Exception as e:
            print(f"프레임 생성 실패: {e}")
            return None
    
    def _estimate_duration_from_marks(self, start_mark: Dict[str, Any], 
                                    end_mark: Dict[str, Any]) -> float:
        """mark 위치로부터 지속 시간 추정"""
        # 위치 기반 대략적 추정
        start_pos = start_mark["position"]
        end_pos = end_mark["position"]
        
        # SSML 길이 대비 위치 비율로 시간 추정
        # 실제로는 TTS API 응답의 정확한 시간 사용 필요
        
        # 기본값 반환
        if "screen1" in start_mark["name"]:
            return 5.0  # 화면 1: 원어 + 1초 무음
        elif "screen2" in start_mark["name"]:
            return 19.0  # 화면 2: 4명의 학습어 + 3초 무음
        else:
            return 10.0  # 기본값
    
    def _save_frame_info(self):
        """프레임 정보를 JSON 파일로 저장"""
        frame_info = {
            "total_frames": len(self.frames),
            "resolution": f"{self.resolution[0]}x{self.resolution[1]}",
            "output_directory": self.output_dir,
            "frames": [
                {
                    "frame_number": frame.frame_number,
                    "start_time": frame.start_time,
                    "end_time": frame.end_time,
                    "duration": frame.duration,
                    "scene_id": frame.scene_id,
                    "screen_type": frame.screen_type,
                    "content": frame.content,
                    "output_path": frame.output_path
                }
                for frame in self.frames
            ]
        }
        
        output_path = os.path.join(self.output_dir, "subtitle_frames.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(frame_info, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 프레임 정보 저장: {output_path}")
    
    def create_ffmpeg_concat_list(self, output_path: str) -> bool:
        """FFmpeg concat 리스트 파일 생성"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                for frame in self.frames:
                    f.write(f"file '{frame.output_path}'\n")
                    f.write(f"duration {frame.duration}\n")
                
                # 마지막 프레임은 duration 없이 (FFmpeg concat demuxer 특성)
                if self.frames:
                    last_frame = self.frames[-1]
                    f.write(f"file '{last_frame.output_path}'\n")
            
            print(f"✅ FFmpeg concat 리스트 생성: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ FFmpeg concat 리스트 생성 실패: {e}")
            return False
    
    def get_frame_summary(self) -> Dict[str, Any]:
        """프레임 요약 정보 반환"""
        if not self.frames:
            return {}
        
        total_duration = sum(frame.duration for frame in self.frames)
        scene_types = {}
        
        for frame in self.frames:
            scene_type = frame.screen_type
            if scene_type not in scene_types:
                scene_types[scene_type] = 0
            scene_types[scene_type] += 1
        
        return {
            "total_frames": len(self.frames),
            "total_duration": total_duration,
            "scene_types": scene_types,
            "resolution": f"{self.resolution[0]}x{self.resolution[1]}",
            "output_directory": self.output_dir
        }
