import os
import subprocess
import tempfile
import json
from typing import List, Dict, Optional
import ffmpeg

class FFmpegRenderer:
    def __init__(self):
        self._check_ffmpeg_availability()

    def _check_ffmpeg_availability(self):
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        except FileNotFoundError:
            raise FileNotFoundError("FFmpeg is not installed or not in the system's PATH.")
    
    def _load_timing_data(self, project_name: str, identifier: str, video_type: str) -> Optional[Dict]:
        """깔끔한 타이밍 데이터 로드"""
        try:
            # 스크립트 타입을 영문으로 변환
            script_type_mapping = {
                "intro": "intro",
                "ending": "ending", 
                "conversation": "conversation"
            }
            english_script_type = script_type_mapping.get(video_type, video_type)
            
            # 깔끔한 타이밍 파일 경로 우선 시도
            clean_timing_path = os.path.join("output", project_name, identifier, "timing", f"{identifier}_{english_script_type}_clean.json")
            legacy_timing_path = os.path.join("output", project_name, identifier, f"{identifier}_{english_script_type}.json")
            
            # 깔끔한 타이밍 파일이 있으면 사용
            if os.path.exists(clean_timing_path):
                with open(clean_timing_path, 'r', encoding='utf-8') as f:
                    timing_data = json.load(f)
                print(f"✅ 깔끔한 타이밍 데이터 로드: {clean_timing_path}")
                return timing_data
            # 기존 타이밍 파일이 있으면 사용
            elif os.path.exists(legacy_timing_path):
                with open(legacy_timing_path, 'r', encoding='utf-8') as f:
                    timing_data = json.load(f)
                print(f"✅ 기존 타이밍 데이터 로드: {legacy_timing_path}")
                return timing_data
            else:
                print(f"⚠️ 타이밍 파일을 찾을 수 없습니다: {clean_timing_path} 또는 {legacy_timing_path}")
                return None
        except Exception as e:
            print(f"❌ 타이밍 데이터 로드 실패: {e}")
            return None

    def render_scene_video(self, audio_path: str, subtitle_frames: List[Dict], output_path: str, resolution: str, default_background: str):
        width, height = map(int, resolution.split('x'))
        
        total_duration = sum(f['duration'] for f in subtitle_frames)
        if total_duration == 0:
            print("Warning: Total duration is zero. Cannot render video.")
            return

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as concat_file:
            for frame in subtitle_frames:
                concat_file.write(f"file '{os.path.abspath(frame['output_path'])}'\n")
                concat_file.write(f"duration {frame['duration']}\n")
            # The last image needs to be specified again without duration
            if subtitle_frames:
                concat_file.write(f"file '{os.path.abspath(subtitle_frames[-1]['output_path'])}'\n")
            concat_list_path = concat_file.name

        try:
            background_input = ffmpeg.input(default_background, loop=1, t=total_duration).filter('scale', width, height)
            image_input = ffmpeg.input(concat_list_path, f='concat', safe=0, r='30')
            audio_input = ffmpeg.input(audio_path)

            video_stream = ffmpeg.overlay(background_input, image_input, x='(W-w)/2', y='(H-h)/2')

            (ffmpeg
                .output(video_stream, audio_input, output_path, vcodec='libx264', acodec='aac', pix_fmt='yuv420p', shortest=None)
                .run(overwrite_output=True, quiet=True))
        finally:
            if os.path.exists(concat_list_path):
                os.remove(concat_list_path)

    def merge_videos(self, video_paths: List[str], output_path: str):
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as concat_file:
            for path in video_paths:
                concat_file.write(f"file '{os.path.abspath(path)}'\n")
            concat_list_path = concat_file.name
        
        try:
            (ffmpeg
                .input(concat_list_path, f='concat', safe=0)
                .output(output_path, c='copy')
                .run(overwrite_output=True, quiet=True))
        finally:
            if os.path.exists(concat_list_path):
                os.remove(concat_list_path)

    def create_conversation_video(self, conversation_data: List[Dict], audio_path: str, 
                                 subtitle_dir: str, output_path: str, resolution: str, 
                                 background_path: str) -> bool:
        """
        회화 비디오 생성 - 제작 사양서에 따른 타이밍 적용
        """
        try:
            width, height = map(int, resolution.split('x'))
            
            # 1. 실제 생성된 회화 이미지 파일들 찾기
            import glob
            screen1_pattern = os.path.join(subtitle_dir, "kor-chn_*_screen1.png")
            screen2_pattern = os.path.join(subtitle_dir, "kor-chn_*_screen2.png")
            
            screen1_files = sorted(glob.glob(screen1_pattern))
            screen2_files = sorted(glob.glob(screen2_pattern))
            
            if not screen1_files and not screen2_files:
                print(f"❌ 회화 이미지 파일을 찾을 수 없습니다: {subtitle_dir}")
                return False
            
            print(f"📁 회화 이미지 파일 발견 - Screen1: {len(screen1_files)}개, Screen2: {len(screen2_files)}개")
            
            # 2. 깔끔한 타이밍 정보 로드 및 생성
            timing_data = self._load_timing_data("kor-chn", "kor-chn", "conversation")
            video_segments = []
            
            if timing_data and 'segments' in timing_data:
                # 깔끔한 타이밍 구조 사용
                print(f"✅ 깔끔한 타이밍 구조 사용: {len(timing_data['segments'])}개 세그먼트")
                
                for segment in timing_data['segments']:
                    image_file = segment.get('image_file')
                    duration = segment.get('duration', 1.0)
                    screen_type = segment.get('screen_type', 'unknown')
                    sequence = segment.get('sequence', 1)
                    
                    # 이미지 파일 존재 확인
                    if os.path.exists(image_file):
                        video_segments.append({
                            'type': screen_type,
                            'image_path': image_file,
                            'start_time': segment.get('start_time', 0.0),
                            'duration': duration,
                            'sequence': sequence
                        })
                        print(f"  📊 {screen_type} 타이밍 사용: {os.path.basename(image_file)} - {duration}초")
                    else:
                        print(f"  ❌ 이미지 파일 없음: {image_file}")
            else:
                # 기본 타이밍 사용 (기존 방식)
                print(f"⚠️ 깔끔한 타이밍 데이터가 없습니다. 기본 타이밍을 사용합니다.")
                current_time = 0.0
                max_scenes = max(len(screen1_files), len(screen2_files))
                
                for i in range(max_scenes):
                    # Screen1 처리
                    if i < len(screen1_files):
                        screen1_duration = 2.0  # 원어 재생 시간 (기본값)
                        print(f"  ⚠️ Screen1 기본 타이밍 사용: {os.path.basename(screen1_files[i])} - {screen1_duration}초")
                        
                        video_segments.append({
                            'type': 'screen1',
                            'image_path': screen1_files[i],
                            'start_time': current_time,
                            'duration': screen1_duration,
                            'sequence': i + 1
                        })
                        current_time += screen1_duration
                        
                        # 무음 1초
                        current_time += 1.0
                    
                    # Screen2 처리
                    if i < len(screen2_files):
                        screen2_duration = 4.0  # 학습어 + 읽기 재생 시간 (기본값)
                        print(f"  ⚠️ Screen2 기본 타이밍 사용: {os.path.basename(screen2_files[i])} - {screen2_duration}초")
                        
                        video_segments.append({
                            'type': 'screen2',
                            'image_path': screen2_files[i],
                            'start_time': current_time,
                            'duration': screen2_duration,
                            'sequence': i + 1
                        })
                        current_time += screen2_duration
                        
                        # 무음 1초 (마지막 장면 제외)
                        if i < max_scenes - 1:
                            current_time += 1.0
            
            if not video_segments:
                print("❌ 회화 비디오 세그먼트가 없습니다.")
                return False
            
            # 3. concat 리스트 생성
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as concat_file:
                for segment in video_segments:
                    if os.path.exists(segment['image_path']):
                        concat_file.write(f"file '{os.path.abspath(segment['image_path'])}'\n")
                        concat_file.write(f"duration {segment['duration']}\n")
                # 마지막 이미지 다시 추가 (duration 없이)
                if video_segments:
                    concat_file.write(f"file '{os.path.abspath(video_segments[-1]['image_path'])}'\n")
                concat_list_path = concat_file.name
            
            # 4. 오디오 파일 확인
            has_audio = audio_path and os.path.exists(audio_path)
            if not has_audio:
                print(f"❌ 회화 오디오 파일이 없습니다: {audio_path}")
                return False
            
            # 5. 비디오 렌더링 (자막 이미지만 사용, 배경 이미지 불필요)
            print(f"🎬 자막 이미지만 사용하여 비디오 생성 (배경 이미지 불필요)")
            image_input = ffmpeg.input(concat_list_path, f='concat', safe=0, r='30')
            audio_input = ffmpeg.input(audio_path)
            
            # 자막 이미지에 해상도 적용
            video_stream = image_input.filter('scale', width, height)
            
            (ffmpeg
                .output(video_stream, audio_input, output_path, vcodec='libx264', acodec='aac', pix_fmt='yuv420p', shortest=None)
                .run(overwrite_output=True, quiet=True))
            
            print(f"✅ 회화 비디오 생성 완료: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ 회화 비디오 생성 실패: {e}")
            print(f"🔍 디버그 정보:")
            print(f"  - conversation_data: {conversation_data}")
            print(f"  - audio_path: {audio_path}")
            print(f"  - subtitle_dir: {subtitle_dir}")
            print(f"  - output_path: {output_path}")
            print(f"  - resolution: {resolution}")
            print(f"  - background_path: {background_path}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            if 'concat_list_path' in locals() and os.path.exists(concat_list_path):
                os.remove(concat_list_path)

    def create_intro_ending_video(self, sentences: List[str], audio_path: str, 
                                 subtitle_dir: str, output_path: str, resolution: str,
                                 background_path: str, video_type: str = "intro") -> bool:
        """
        인트로/엔딩 비디오 생성 - 문장별 이미지를 타이밍에 맞춰 생성
        """
        try:
            width, height = map(int, resolution.split('x'))
            
            # 1. 실제 생성된 이미지 파일들 찾기
            video_segments = []
            current_time = 0.0
            
            # 실제 파일명 패턴으로 이미지 찾기
            import glob
            image_pattern = os.path.join(subtitle_dir, f"kor-chn_{video_type}_*.png")
            image_files = sorted(glob.glob(image_pattern))
            
            if not image_files:
                print(f"❌ {video_type} 이미지 파일을 찾을 수 없습니다: {image_pattern}")
                return False
            
            print(f"📁 {video_type} 이미지 파일 {len(image_files)}개 발견")
            
            # 타이밍 정보 로드 시도
            timing_data = self._load_timing_data(project_name, identifier, video_type)
            
            for i, image_path in enumerate(image_files):
                # 타이밍 정보가 있으면 사용, 없으면 기본값 사용
                if timing_data and i < len(timing_data.get('segments', [])):
                    segment = timing_data['segments'][i]
                    sentence_duration = segment.get('duration', 3.0)
                    print(f"  📊 타이밍 사용: {os.path.basename(image_path)} - {sentence_duration}초")
                else:
                    sentence_duration = 3.0
                    print(f"  ⚠️ 기본 타이밍 사용: {os.path.basename(image_path)} - {sentence_duration}초")
                
                video_segments.append({
                    'image_path': image_path,
                    'start_time': current_time,
                    'duration': sentence_duration,
                    'sentence': f"{video_type} {i+1}"
                })
                current_time += sentence_duration
                
                # 문장간 무음 1초 (마지막 문장 제외)
                if i < len(image_files) - 1:
                    current_time += 1.0
            
            if not video_segments:
                print(f"❌ {video_type} 비디오 세그먼트가 없습니다.")
                return False
            
            # 2. concat 리스트 생성
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as concat_file:
                for segment in video_segments:
                    concat_file.write(f"file '{os.path.abspath(segment['image_path'])}'\n")
                    concat_file.write(f"duration {segment['duration']}\n")
                # 마지막 이미지 다시 추가 (duration 없이)
                if video_segments:
                    concat_file.write(f"file '{os.path.abspath(video_segments[-1]['image_path'])}'\n")
                concat_list_path = concat_file.name
            
            # 3. 오디오 파일 확인 (선택적)
            has_audio = audio_path and os.path.exists(audio_path)
            if not has_audio:
                print(f"⚠️ 오디오 파일이 없습니다: {audio_path}")
            
            # 4. 비디오 렌더링 (자막 이미지만 사용, 배경 이미지 불필요)
            print(f"🎬 자막 이미지만 사용하여 {video_type} 비디오 생성 (배경 이미지 불필요)")
            image_input = ffmpeg.input(concat_list_path, f='concat', safe=0, r='30')
            
            # 자막 이미지에 해상도 적용
            video_stream = image_input.filter('scale', width, height)
            
            if has_audio:
                audio_input = ffmpeg.input(audio_path)
                (ffmpeg
                    .output(video_stream, audio_input, output_path, vcodec='libx264', acodec='aac', pix_fmt='yuv420p', shortest=None)
                    .run(overwrite_output=True, quiet=True))
            else:
                (ffmpeg
                    .output(video_stream, output_path, vcodec='libx264', pix_fmt='yuv420p')
                    .run(overwrite_output=True, quiet=True))
            
            print(f"✅ {video_type} 비디오 생성 완료: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ {video_type} 비디오 생성 실패: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            if 'concat_list_path' in locals() and os.path.exists(concat_list_path):
                os.remove(concat_list_path)

    def create_final_merged_video(self, intro_path: str, conversation_path: str, 
                                 ending_path: str, output_path: str) -> bool:
        """
        최종 비디오 병합 - 인트로 + 회화 + 엔딩
        """
        try:
            video_paths = []
            
            # 존재하는 비디오 파일만 추가
            if intro_path and os.path.exists(intro_path):
                video_paths.append(intro_path)
            if conversation_path and os.path.exists(conversation_path):
                video_paths.append(conversation_path)
            if ending_path and os.path.exists(ending_path):
                video_paths.append(ending_path)
            
            if not video_paths:
                print("❌ 병합할 비디오 파일이 없습니다.")
                return False
            
            # 비디오 병합
            self.merge_videos(video_paths, output_path)
            print(f"✅ 최종 비디오 병합 완료: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ 최종 비디오 병합 실패: {e}")
            return False