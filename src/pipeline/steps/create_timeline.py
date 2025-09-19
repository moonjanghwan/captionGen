"""
타임라인 생성 모듈

매니페스트, 오디오 타이밍 정보, 이미지 시퀀스를 종합하여
최종 비디오 렌더링에 필요한 타임라인 JSON을 생성합니다.
"""

import os
import json
import glob
import wave
import struct
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from ..core.context import PipelineContext


@dataclass
class TimelineEntry:
    """타임라인 엔트리"""
    scene_id: str
    start_time: float
    end_time: float
    duration: float
    image_path: str
    scene_type: str
    sequence: int


@dataclass
class TimelineData:
    """타임라인 데이터"""
    resolution: str
    final_audio_path: str
    timeline: List[TimelineEntry]
    total_duration: float


class TimelineGenerator:
    """타임라인 생성기"""
    
    def __init__(self):
        self.timeline_entries = []
    
    def _get_english_script_type(self, script_type: str) -> str:
        """스크립트 타입을 영문으로 변환"""
        script_type_mapping = {
            "회화": "conversation",
            "대화": "dialogue",
            "인트로": "intro",
            "엔딩": "ending"
        }
        return script_type_mapping.get(script_type, script_type.lower())
    
    def _get_audio_duration(self, audio_path: str) -> float:
        """오디오 파일의 실제 길이를 측정 (초 단위)"""
        try:
            if not os.path.exists(audio_path):
                return 0.0
            
            import subprocess
            result = subprocess.run(
                ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', audio_path],
                capture_output=True, text=True, check=True
            )
            duration = float(result.stdout.strip())
            return round(duration, 2)
            
        except Exception as e:
            print(f"⚠️ 오디오 길이 측정 실패: {e}")
            # ffprobe 실패 시 기존의 파일 크기 기반 추정 로직을 fallback으로 사용
            try:
                if audio_path.lower().endswith('.mp3'):
                    file_size = os.path.getsize(audio_path)
                    bitrate = 128 * 1000
                    duration = (file_size * 8) / bitrate
                    return round(duration, 2)
            except Exception as fallback_e:
                print(f"⚠️ Fallback 오디오 길이 측정 실패: {fallback_e}")

            return 0.0
    
    def _create_default_timing(self, manifest_data: Dict) -> Dict:
        """기본 타이밍 데이터 생성 (타이밍 파일이 없을 때 사용)"""
        try:
            scenes = manifest_data.get('scenes', [])
            segments = []
            current_time = 0.0
            
            for scene in scenes:
                scene_type = scene.get('type', 'conversation')
                sequence = scene.get('sequence', 1)
                
                if scene_type == 'conversation':
                    # 회화의 경우 실제 텍스트 길이를 기반으로 추정
                    native_script = scene.get('native_script', '')
                    learning_script = scene.get('learning_script', '')
                    reading_script = scene.get('reading_script', '')
                    
                    # 텍스트 길이 기반 duration 추정 (한글: 약 3자/초, 영어: 약 5자/초)
                    screen1_duration = max(2.0, len(native_script) * 0.3)  # 최소 2초
                    screen2_duration = max(3.0, (len(learning_script) + len(reading_script)) * 0.3)  # 최소 3초
                    
                    segments.extend([
                        {
                            "name": f"scene_{sequence}_screen1_start_to_scene_{sequence}_screen1_end",
                            "start_time": current_time,
                            "end_time": current_time + screen1_duration,
                            "duration": screen1_duration
                        },
                        {
                            "name": f"scene_{sequence}_screen2_start_to_scene_{sequence}_screen2_end", 
                            "start_time": current_time + screen1_duration + 1.0,  # 1초 간격
                            "end_time": current_time + screen1_duration + 1.0 + screen2_duration,
                            "duration": screen2_duration
                        }
                    ])
                    current_time += screen1_duration + 1.0 + screen2_duration + 1.0  # 1초 간격
                else:
                    # 인트로/엔딩의 경우 텍스트 길이 기반
                    full_script = scene.get('full_script', '')
                    duration = max(3.0, len(full_script) * 0.3)  # 최소 3초
                    
                    segments.append({
                        "name": f"scene_{sequence}_start_to_scene_{sequence}_end",
                        "start_time": current_time,
                        "end_time": current_time + duration,
                        "duration": duration
                    })
                    current_time += duration + 1.0  # 1초 간격
            
            return {
                "segments": segments,
                "total_duration": current_time
            }
            
        except Exception as e:
            print(f"❌ 기본 타이밍 생성 실패: {e}")
            return {"segments": [], "total_duration": 0.0}
    
    def _create_audio_based_timing(self, manifest_data: Dict, audio_path: str) -> Dict:
        """실제 오디오 파일을 기반으로 타이밍 데이터 생성"""
        try:
            audio_duration = self._get_audio_duration(audio_path)
            if audio_duration <= 0:
                print("⚠️ 오디오 길이를 측정할 수 없어 기본 타이밍을 사용합니다.")
                return self._create_default_timing(manifest_data)
            
            scenes = manifest_data.get('scenes', [])
            segments = []
            current_time = 0.0
            
            # 총 장면 수 계산
            total_scenes = len(scenes)
            if total_scenes == 0:
                return {"segments": [], "total_duration": 0.0}
            
            # 각 장면에 할당할 시간 계산 (오디오 길이를 장면 수로 나눔)
            time_per_scene = audio_duration / total_scenes
            
            for scene in scenes:
                scene_type = scene.get('type', 'conversation')
                sequence = scene.get('sequence', 1)
                
                if scene_type == 'conversation':
                    # 회화의 경우 screen1(40%), screen2(60%) 비율로 분할
                    # 무음 기간을 고려하여 실제 오디오 시간에서 1초를 빼고 분할
                    available_time = time_per_scene - 1.0  # 1초 무음 기간 제외
                    screen1_duration = available_time * 0.4
                    screen2_duration = available_time * 0.6
                    
                    segments.extend([
                        {
                            "name": f"scene_{sequence}_screen1_start_to_scene_{sequence}_screen1_end",
                            "start_time": current_time,
                            "end_time": current_time + screen1_duration,
                            "duration": screen1_duration
                        },
                        {
                            "name": f"scene_{sequence}_screen2_start_to_scene_{sequence}_screen2_end", 
                            "start_time": current_time + screen1_duration + 1.0,  # 1초 무음 기간
                            "end_time": current_time + screen1_duration + 1.0 + screen2_duration,
                            "duration": screen2_duration
                        }
                    ])
                    current_time += time_per_scene
                else:
                    # 인트로/엔딩의 경우 전체 시간 사용
                    segments.append({
                        "name": f"scene_{sequence}_start_to_scene_{sequence}_end",
                        "start_time": current_time,
                        "end_time": current_time + time_per_scene,
                        "duration": time_per_scene
                    })
                    current_time += time_per_scene
            
            print(f"🎵 오디오 기반 타이밍 생성: 총 {audio_duration:.2f}초, {len(segments)}개 세그먼트")
            return {
                "segments": segments,
                "total_duration": audio_duration
            }
            
        except Exception as e:
            print(f"❌ 오디오 기반 타이밍 생성 실패: {e}")
            return self._create_default_timing(manifest_data)
    
    def _apply_conversation_timing_matching(self, raw_segments: List[Dict]) -> List[Dict]:
        """
        제작 사양서에 따른 회화 비디오 타이밍 매칭 적용
        
        화자 : 원어화자, 학습어 화자 1,2,3,4 
        대화 순번 : 다음과 같이 재생하며 화자간, 행간에는 1초의 무음을 넣어준다.
            1. 원어화자 - 원어             화면 1   원어 화자 시작 시간 ~ 종료 시간
            2. 학습어 화자 1 - 학습어       화면 2   학습어 화자 1 시작 시간 ~ 학습어 화자 4 종료시간
            3. 학습어 화자 2 - 학습어       화면 2
            4. 학습어 화자 3 - 학습어       화면 2
            5. 학습어 화자 4 - 학습어       화면 2
        """
        try:
            print("🎬 제작 사양서에 따른 회화 타이밍 매칭 적용...")
            
            # 세그먼트를 장면별로 그룹화
            scene_groups = {}
            for segment in raw_segments:
                scene_info = self._parse_segment_name(segment.get('name', ''))
                if scene_info:
                    sequence = scene_info['sequence']
                    screen_type = scene_info.get('screen_type', '')
                    
                    if sequence not in scene_groups:
                        scene_groups[sequence] = {}
                    scene_groups[sequence][screen_type] = segment
            
            # 각 장면별로 타이밍 매칭 적용
            matched_segments = []
            for sequence in sorted(scene_groups.keys()):
                scene_data = scene_groups[sequence]
                
                # 화면 1: 원어화자 - 원어 (원어 화자 시작 시간 ~ 종료 시간)
                if 'screen1' in scene_data:
                    screen1_segment = scene_data['screen1'].copy()
                    screen1_segment['name'] = f"kor-chn_{sequence:03d}_screen1.png"
                    screen1_segment['scene_type'] = "conversation"
                    screen1_segment['sequence'] = sequence
                    screen1_segment['screen_type'] = "screen1"
                    matched_segments.append(screen1_segment)
                    print(f"   ✅ 화면 1 (원어): scene_{sequence} ({screen1_segment['start_time']:.2f}s ~ {screen1_segment['end_time']:.2f}s)")
                
                # 화면 2: 학습어 화자 1,2,3,4 - 학습어 (학습어 화자 1 시작 시간 ~ 학습어 화자 4 종료 시간)
                if 'screen2' in scene_data:
                    screen2_segment = scene_data['screen2'].copy()
                    screen2_segment['name'] = f"kor-chn_{sequence:03d}_screen2.png"
                    screen2_segment['scene_type'] = "conversation"
                    screen2_segment['sequence'] = sequence
                    screen2_segment['screen_type'] = "screen2"
                    matched_segments.append(screen2_segment)
                    print(f"   ✅ 화면 2 (학습어): scene_{sequence} ({screen2_segment['start_time']:.2f}s ~ {screen2_segment['end_time']:.2f}s)")
            
            print(f"🎬 회화 타이밍 매칭 완료: {len(matched_segments)}개 세그먼트")
            return matched_segments
            
        except Exception as e:
            print(f"❌ 회화 타이밍 매칭 실패: {e}")
            import traceback
            traceback.print_exc()
            return raw_segments  # 실패 시 원본 반환
    
    def _parse_segment_name(self, segment_name: str) -> Optional[Dict]:
        """세그먼트 이름에서 장면 정보 추출"""
        try:
            # 예: "scene_1_screen1_start_to_scene_1_screen1_end" -> {"sequence": 1, "screen_type": "screen1"}
            if "_start_to_" in segment_name:
                # 시작 부분만 파싱
                start_part = segment_name.split("_start_to_")[0]
                parts = start_part.split("_")
                
                if len(parts) >= 3 and parts[0] == "scene":
                    sequence = int(parts[1])
                    screen_type = parts[2] if len(parts) > 2 else ""
                    
                    return {
                        "sequence": sequence,
                        "screen_type": screen_type,
                        "scene_type": "conversation" if screen_type else "intro"
                    }
            
            return None
            
        except (ValueError, IndexError) as e:
            print(f"❌ 세그먼트 이름 파싱 실패: {segment_name} - {e}")
            return None
    
    def _get_image_path_for_segment(self, context: PipelineContext, sequence: int, screen_type: str) -> Optional[str]:
        """세그먼트에 해당하는 이미지 파일 경로 반환"""
        try:
            if screen_type:
                # 회화의 경우: screen1, screen2
                if screen_type in ["screen1", "screen2"]:
                    # 새로운 파일명 형식 사용: kor-chn_001_screen1.png
                    image_filename = f"{context.identifier}_{sequence:03d}_{screen_type}.png"
                    image_path = os.path.join(context.paths.conversation_dir, image_filename)
                    
                    # 파일이 존재하는지 확인
                    if os.path.exists(image_path):
                        return image_path
                    else:
                        print(f"⚠️ 이미지 파일이 없습니다: {image_path}")
                        return None
            else:
                # 인트로/엔딩의 경우
                image_filename = f"{context.identifier}_{sequence:03d}.png"
                image_path = os.path.join(context.paths.intro_ending_dir, image_filename)
                
                # 파일이 존재하는지 확인
                if os.path.exists(image_path):
                    return image_path
                else:
                    print(f"⚠️ 이미지 파일이 없습니다: {image_path}")
                    return None
            
            return None
            
        except Exception as e:
            print(f"❌ 이미지 경로 생성 실패: {e}")
            return None
    
    def generate_timeline(self, context: PipelineContext) -> Optional[str]:
        """
        타임라인 생성
        
        Args:
            context: 파이프라인 컨텍스트
            
        Returns:
            str: 생성된 타임라인 파일 경로
        """
        try:
            print(f"🎬 타임라인 생성 시작: {context.identifier}")
            
            # 1. 입력 파일 로드
            manifest_data = self._load_manifest(context)
            timing_data = self._load_timing(context)
            
            if not manifest_data:
                print("❌ 매니페스트 파일을 찾을 수 없습니다.")
                return None
            
            # 타이밍 파일이 없어도 기본 타임라인 생성 가능
            if not timing_data:
                print("⚠️ 타이밍 파일을 찾을 수 없습니다.")
                
                # 오디오 파일이 있으면 실제 길이를 기반으로 타이밍 생성
                audio_path = self._get_final_audio_path(context)
                if audio_path and os.path.exists(audio_path):
                    print("🎵 오디오 파일을 기반으로 타이밍을 생성합니다.")
                    timing_data = self._create_audio_based_timing(manifest_data, audio_path)
                else:
                    print("📝 텍스트 길이를 기반으로 기본 타이밍을 생성합니다.")
                    timing_data = self._create_default_timing(manifest_data)
            
            # 2. 타임라인 초기화
            final_audio_path = self._get_final_audio_path(context)
            timeline_data = TimelineData(
                resolution=context.manifest.resolution or "1920x1080",
                final_audio_path=final_audio_path,
                timeline=[],
                total_duration=0.0
            )
            
            # 실제 오디오 파일의 길이를 측정하여 total_duration 설정
            if final_audio_path and os.path.exists(final_audio_path):
                try:
                    import subprocess
                    result = subprocess.run(['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', final_audio_path], capture_output=True, text=True)
                    actual_duration = float(result.stdout.strip())
                    timeline_data.total_duration = actual_duration
                    print(f"🎵 실제 오디오 파일 길이 사용: {actual_duration:.2f}초 (무음 포함)")
                except Exception as e:
                    print(f"⚠️ 오디오 길이 측정 실패: {e}, 타이밍 파일의 total_duration 사용")
                    # 타이밍 파일의 total_duration 사용
                    if timing_data and 'total_duration' in timing_data:
                        timeline_data.total_duration = timing_data['total_duration']
                        print(f"🎵 타이밍 파일의 total_duration 사용: {timing_data['total_duration']:.2f}초")
            else:
                print(f"⚠️ 오디오 파일을 찾을 수 없습니다: {final_audio_path}")
                # 타이밍 파일의 total_duration 사용
                if timing_data and 'total_duration' in timing_data:
                    timeline_data.total_duration = timing_data['total_duration']
                    print(f"🎵 타이밍 파일의 total_duration 사용: {timing_data['total_duration']:.2f}초")
            
            # 3. 타이밍 세그먼트 순회 및 매칭
            timing_segments = []
            
            # segments 배열이 직접 있는 경우 (우선순위 1)
            if 'segments' in timing_data:
                print("📊 segments 배열을 사용합니다...")
                raw_segments = timing_data.get('segments', [])
                
                # 회화 비디오의 경우 제작 사양서에 따른 타이밍 매칭 적용
                if context.script_type in ["회화", "대화"]:
                    timing_segments = self._apply_conversation_timing_matching(raw_segments)
                else:
                    timing_segments = raw_segments
            
            # scenes 배열이 있으면 segments로 변환 (우선순위 2)
            elif 'scenes' in timing_data:
                print("📊 scenes 배열을 segments로 변환합니다...")
                for scene in timing_data['scenes']:
                    sequence = scene.get('sequence', 1)
                    timings = scene.get('timings', {})
                    
                    # screen1 세그먼트
                    if 'screen1' in timings:
                        screen1_timing = timings['screen1']
                        timing_segments.append({
                            "name": f"scene_{sequence}_screen1_start_to_scene_{sequence}_screen1_end",
                            "start_time": screen1_timing.get('start', 0) / 1000.0,  # ms를 초로 변환
                            "end_time": screen1_timing.get('end', 0) / 1000.0,
                            "duration": (screen1_timing.get('end', 0) - screen1_timing.get('start', 0)) / 1000.0,
                            "scene_type": "conversation",
                            "sequence": sequence,
                            "screen_type": "screen1"
                        })
                    
                    # screen2 세그먼트
                    if 'screen2' in timings:
                        screen2_timing = timings['screen2']
                        timing_segments.append({
                            "name": f"scene_{sequence}_screen2_start_to_scene_{sequence}_screen2_end",
                            "start_time": screen2_timing.get('start', 0) / 1000.0,  # ms를 초로 변환
                            "end_time": screen2_timing.get('end', 0) / 1000.0,
                            "duration": (screen2_timing.get('end', 0) - screen2_timing.get('start', 0)) / 1000.0,
                            "scene_type": "conversation",
                            "sequence": sequence,
                            "screen_type": "screen2"
                        })
            
            # marks 배열이 있으면 segments로 변환 (우선순위 3 - 마지막)
            elif 'marks' in timing_data:
                print("📊 marks 배열을 segments로 변환합니다...")
                marks = timing_data['marks']
                
                # marks를 쌍으로 그룹화 (start, end)
                i = 0
                while i < len(marks) - 1:
                    start_mark = marks[i]
                    end_mark = marks[i + 1]
                    
                    if start_mark['name'].endswith('_start') and end_mark['name'].endswith('_end'):
                        # 세그먼트 이름에서 장면 정보 추출
                        segment_name = f"{start_mark['name']}_to_{end_mark['name']}"
                        
                        # 장면 번호와 스크린 타입 추출
                        name_parts = start_mark['name'].split('_')
                        if len(name_parts) >= 3:
                            sequence = int(name_parts[1])
                            screen_type = name_parts[2]
                            
                            timing_segments.append({
                                "name": segment_name,
                                "start_time": start_mark['position'] / 1000.0,  # ms를 초로 변환
                                "end_time": end_mark['position'] / 1000.0,
                                "duration": (end_mark['position'] - start_mark['position']) / 1000.0,
                                "scene_type": "conversation",
                                "sequence": sequence,
                                "screen_type": screen_type
                            })
                    
                    i += 2  # start, end 쌍으로 처리하므로 2씩 증가
            
            print(f"   - 총 {len(timing_segments)}개의 타이밍 세그먼트를 처리합니다...")
            
            for segment in timing_segments:
                segment_name = segment.get('name', '')
                start_time = segment.get('start_time', 0.0)
                end_time = segment.get('end_time', 0.0)
                duration = segment.get('duration', 0.0)
                
                # 4. 세그먼트 이름에서 장면 정보 추출
                scene_info = self._parse_segment_name(segment_name)
                if not scene_info:
                    print(f"⚠️ 세그먼트 이름을 파싱할 수 없어 '{segment_name}'을 건너뜁니다.")
                    continue
                
                scene_sequence = scene_info['sequence']
                screen_type = scene_info.get('screen_type', '')
                
                # 5. 이미지 파일 경로 생성 및 확인 (name 필드에서 직접 추출)
                # name 필드가 이미 완전한 파일명을 포함하고 있음 (예: kor-chn_001_screen1.png)
                image_filename = segment.get('name', '')
                if not image_filename:
                    print(f"⚠️ 세그먼트에 name 필드가 없어 '{segment_name}'을 건너뜁니다.")
                    continue
                
                # 회화의 경우 conversation 디렉토리에서 이미지 찾기
                if screen_type in ["screen1", "screen2"]:
                    image_path = os.path.join(context.paths.conversation_dir, image_filename)
                else:
                    # 인트로/엔딩의 경우
                    image_path = os.path.join(context.paths.intro_ending_dir, image_filename)
                
                if not os.path.exists(image_path):
                    print(f"⚠️ 이미지 파일이 없어 '{segment_name}'을 건너뜁니다. 경로: {image_path}")
                    continue
                
                # 6. 타임라인 엔트리 생성
                entry = TimelineEntry(
                    scene_id=segment_name,
                    start_time=start_time,
                    end_time=end_time,
                    duration=duration,
                    image_path=image_path,
                    scene_type=scene_info.get('scene_type', 'conversation'),
                    sequence=scene_sequence
                )
                
                timeline_data.timeline.append(entry)
                # total_duration은 실제 오디오 파일 길이를 사용하므로 여기서는 업데이트하지 않음
                print(f"   -> 타임라인 추가: {segment_name} ({start_time:.2f}s ~ {end_time:.2f}s)")
            
            # 7. 타임라인 파일 저장
            # total_duration이 0이면 실제 오디오 파일 길이를 다시 측정
            if timeline_data.total_duration <= 0:
                if final_audio_path and os.path.exists(final_audio_path):
                    try:
                        import subprocess
                        result = subprocess.run(['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', final_audio_path], capture_output=True, text=True)
                        actual_duration = float(result.stdout.strip())
                        timeline_data.total_duration = actual_duration
                        print(f"🎵 최종 오디오 파일 길이 사용: {actual_duration:.2f}초")
                    except Exception as e:
                        print(f"⚠️ 오디오 길이 측정 실패: {e}")
                        # 세그먼트 최대 end_time 사용
                        max_end_time = 0.0
                        for entry in timeline_data.timeline:
                            max_end_time = max(max_end_time, entry.end_time)
                        timeline_data.total_duration = max_end_time
                        print(f"⚠️ 세그먼트 최대 end_time 사용: {max_end_time:.1f}초")
                else:
                    # 세그먼트 최대 end_time 사용
                    max_end_time = 0.0
                    for entry in timeline_data.timeline:
                        max_end_time = max(max_end_time, entry.end_time)
                    timeline_data.total_duration = max_end_time
                    print(f"⚠️ 세그먼트 최대 end_time 사용: {max_end_time:.1f}초")
            
            timeline_path = self._save_timeline(context, timeline_data)
            
            if timeline_path:
                print(f"✅ 타임라인 생성 완료: {timeline_path}")
                print(f"   - 총 {len(timeline_data.timeline)}개 엔트리")
                print(f"   - 총 재생시간: {timeline_data.total_duration:.1f}초")
            
            return timeline_path
            
        except Exception as e:
            print(f"❌ 타임라인 생성 실패: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _load_manifest(self, context: PipelineContext) -> Optional[Dict]:
        """매니페스트 파일 로드"""
        try:
            english_script_type = self._get_english_script_type(context.script_type)
            
            manifest_path = os.path.join(
                context.paths.manifest_dir,
                f"{context.identifier}_{english_script_type}.json"
            )
            
            if not os.path.exists(manifest_path):
                print(f"❌ 매니페스트 파일이 없습니다: {manifest_path}")
                return None
            
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest_data = json.load(f)
            
            print(f"✅ 매니페스트 로드 완료: {manifest_path}")
            return manifest_data
            
        except Exception as e:
            print(f"❌ 매니페스트 로드 실패: {e}")
            return None
    
    def _load_timing(self, context: PipelineContext) -> Optional[Dict]:
        """정확한 타이밍 파일 로드 (세그먼트별 오디오 기반)"""
        try:
            english_script_type = self._get_english_script_type(context.script_type)
            
            # 정확한 타이밍 파일 경로 (세그먼트별 오디오 기반)
            precise_timing_path = os.path.join(
                context.paths.timing_dir,
                f"{context.identifier}_{english_script_type}.json"
            )
            
            # 기존 정확한 타이밍 파일이 있으면 사용
            if os.path.exists(precise_timing_path):
                with open(precise_timing_path, 'r', encoding='utf-8') as f:
                    timing_data = json.load(f)
                    print(f"✅ 정확한 타이밍 파일 로드: {precise_timing_path}")
                    print(f"   - 총 {len(timing_data.get('segments', []))}개 세그먼트")
                    print(f"   - 총 재생시간: {timing_data.get('total_duration', 0):.2f}초")
                    return timing_data
            
            # 정확한 타이밍 파일이 없으면 None 반환 (기본 타이밍 생성)
            print(f"⚠️ 정확한 타이밍 파일이 없습니다: {precise_timing_path}")
            return None
            
        except Exception as e:
            print(f"❌ 타이밍 파일 로드 실패: {e}")
            return None
    
    
    
    def _get_final_audio_path(self, context: PipelineContext) -> str:
        """최종 오디오 파일 경로 반환"""
        try:
            english_script_type = self._get_english_script_type(context.script_type)
            
            # 1. mp3 디렉토리에서 찾기
            mp3_path = os.path.join(
                context.paths.output_dir,
                "mp3",
                f"{context.identifier}_{english_script_type}.mp3"
            )
            if os.path.exists(mp3_path):
                return mp3_path
            
            # 2. audio 디렉토리에서 찾기
            audio_path = os.path.join(
                context.paths.audio_dir,
                f"{context.identifier}_{english_script_type}.mp3"
            )
            if os.path.exists(audio_path):
                return audio_path
            
            # 3. fallback: audio.mp3
            fallback_path = os.path.join(context.paths.audio_dir, "audio.mp3")
            if os.path.exists(fallback_path):
                return fallback_path
            
            return ""
            
        except Exception:
            return ""
    
    def _save_timeline(self, context: PipelineContext, timeline_data: TimelineData) -> Optional[str]:
        """타임라인 파일 저장"""
        try:
            # 타임라인 디렉토리 생성
            timeline_dir = os.path.join(context.paths.output_dir, "timeline")
            os.makedirs(timeline_dir, exist_ok=True)
            
            english_script_type = self._get_english_script_type(context.script_type)
            
            # 파일명 생성
            timeline_filename = f"{context.identifier}_{english_script_type}.json"
            timeline_path = os.path.join(timeline_dir, timeline_filename)
            
            # 타임라인 데이터를 JSON으로 변환
            timeline_json = {
                "resolution": timeline_data.resolution,
                "final_audio_path": timeline_data.final_audio_path,
                "total_duration": timeline_data.total_duration,
                "timeline": [
                    {
                        "scene_id": entry.scene_id,
                        "start_time": entry.start_time,
                        "end_time": entry.end_time,
                        "duration": entry.duration,
                        "image_path": entry.image_path,
                        "scene_type": entry.scene_type,
                        "sequence": entry.sequence
                    }
                    for entry in timeline_data.timeline
                ]
            }
            
            # 파일 저장
            with open(timeline_path, 'w', encoding='utf-8') as f:
                json.dump(timeline_json, f, ensure_ascii=False, indent=2)
            
            print(f"📁 타임라인 저장: {timeline_path}")
            return timeline_path
            
        except Exception as e:
            print(f"❌ 타임라인 저장 실패: {e}")
            return None


def run(context: PipelineContext) -> Optional[str]:
    """
    타임라인 생성 실행
    
    Args:
        context: 파이프라인 컨텍스트
        
    Returns:
        str: 생성된 타임라인 파일 경로
    """
    generator = TimelineGenerator()
    return generator.generate_timeline(context)
