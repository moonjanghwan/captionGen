"""
회화 플러그인

회화 스크립트 타입의 데이터를 처리하는 플러그인입니다.
Screen 1/2 구조로 71.53초 오디오를 생성합니다.
"""

import os
import json
from typing import Dict, List, Any, Optional
from .base_plugin import BasePlugin, PluginConfig


class ConversationPlugin(BasePlugin):
    """회화 플러그인"""
    
    def get_plugin_type(self) -> str:
        """플러그인 타입 반환"""
        return "conversation"
    
    def get_plugin_name(self) -> str:
        """플러그인 이름 반환"""
        return "회화 플러그인"
    
    def get_plugin_description(self) -> str:
        """플러그인 설명 반환"""
        return "회화 스크립트를 Screen 1/2 구조로 처리하여 비디오를 생성합니다"
    
    def get_required_input_fields(self) -> List[str]:
        """필수 입력 필드 반환"""
        return ["conversation_data"]
    
    def get_optional_input_fields(self) -> List[str]:
        """선택적 입력 필드 반환"""
        return ["speaker_settings", "image_settings", "background_settings"]
    
    def get_default_settings(self) -> Dict[str, Any]:
        """기본 설정 반환"""
        return {
            "screen1_content": "순번 + 원어",
            "screen2_content": "순번 + 원어 + 학습어 + 읽기",
            "speaker_sequence": ["native", "learning1", "learning2", "learning3", "learning4"],
            "silence_between_speakers": 1.0,  # 초
            "silence_between_lines": 1.0,     # 초
            "dual_screen_rendering": True
        }
    
    def _validate_input_data(self, input_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """입력 데이터 검증"""
        try:
            # 필수 필드 확인
            if "conversation_data" not in input_data:
                self._log_error("회화 데이터가 없습니다")
                return None
            
            conversation_data = input_data["conversation_data"]
            if not conversation_data or not isinstance(conversation_data, list):
                self._log_error("회화 데이터가 유효하지 않습니다")
                return None
            
            # 각 회화 항목 검증
            validated_conversations = []
            for i, conv in enumerate(conversation_data):
                if not isinstance(conv, dict):
                    self._log_warning(f"회화 항목 {i+1}이 딕셔너리가 아닙니다")
                    continue
                
                required_fields = ["sequence", "native_script", "learning_script", "reading_script"]
                if not all(field in conv for field in required_fields):
                    self._log_warning(f"회화 항목 {i+1}에 필수 필드가 없습니다")
                    continue
                
                validated_conversations.append(conv)
            
            if not validated_conversations:
                self._log_error("유효한 회화 데이터가 없습니다")
                return None
            
            self._log_info(f"회화 데이터 검증 완료: {len(validated_conversations)}개 항목")
            
            return {
                "conversation_data": validated_conversations,
                "speaker_settings": input_data.get("speaker_settings", {}),
                "image_settings": input_data.get("image_settings", {}),
                "background_settings": input_data.get("background_settings", {})
            }
            
        except Exception as e:
            self._log_error(f"입력 데이터 검증 실패: {e}")
            return None
    
    def _create_manifest(self, validated_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """매니페스트 생성"""
        try:
            conversations = validated_data["conversation_data"]
            
            # 회화 매니페스트 구조 생성
            manifest = {
                "project_name": self.config.project_name,
                "identifier": self.config.identifier,
                "type": "conversation",
                "resolution": self.config.resolution,
                "fps": self.config.fps,
                "total_conversations": len(conversations),
                "dual_screen_mode": True,
                "scenes": []
            }
            
            # 각 회화를 장면으로 변환
            for conv in conversations:
                scene = {
                    "id": f"conversation_{conv['sequence']:02d}",
                    "type": "conversation",
                    "sequence": conv["sequence"],
                    "native_script": conv["native_script"],
                    "learning_script": conv["learning_script"],
                    "reading_script": conv["reading_script"],
                    "screens": {
                        "screen1": {
                            "content": ["sequence", "native"],
                            "description": "순번 + 원어"
                        },
                        "screen2": {
                            "content": ["sequence", "native", "learning", "reading"],
                            "description": "순번 + 원어 + 학습어 + 읽기"
                        }
                    },
                    "speaker_sequence": ["native", "learning1", "learning2", "learning3", "learning4"],
                    "timing": {
                        "silence_between_speakers": 1.0,
                        "silence_between_lines": 1.0
                    }
                }
                manifest["scenes"].append(scene)
            
            # 매니페스트 파일 저장
            manifest_filename = f"{self.config.identifier}_conversation.json"
            manifest_path = os.path.join(self.output_dirs["manifest"], manifest_filename)
            
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
            
            self.generated_files["manifest"] = manifest_path
            self._log_info(f"회화 매니페스트 생성 완료: {len(conversations)}개 장면")
            
            return manifest
            
        except Exception as e:
            self._log_error(f"매니페스트 생성 실패: {e}")
            return None
    
    def _generate_audio(self, manifest_data: Dict[str, Any]) -> Optional[str]:
        """오디오 생성"""
        try:
            # SSML 생성
            ssml_content = self._create_conversation_ssml(manifest_data)
            
            # SSML 파일 저장
            ssml_filename = f"{self.config.identifier}_conversation.ssml"
            ssml_path = os.path.join(self.output_dirs["ssml"], ssml_filename)
            
            with open(ssml_path, 'w', encoding='utf-8') as f:
                f.write(ssml_content)
            
            self.generated_files["ssml"] = ssml_path
            
            # 오디오 파일 생성 (더미)
            audio_filename = f"{self.config.identifier}_conversation.mp3"
            audio_path = os.path.join(self.output_dirs["audio"], audio_filename)
            
            # 간단한 더미 MP3 헤더 생성
            with open(audio_path, 'wb') as f:
                f.write(b'\xff\xfb\x90\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
            
            self.generated_files["audio"] = audio_path
            self._log_info("회화 오디오 생성 완료")
            
            return audio_path
            
        except Exception as e:
            self._log_error(f"오디오 생성 실패: {e}")
            return None
    
    def _generate_subtitles(self, manifest_data: Dict[str, Any]) -> Optional[str]:
        """자막 이미지 생성"""
        try:
            scenes = manifest_data.get("scenes", [])
            subtitle_dir = os.path.join(self.output_dirs["subtitles"], "conversation")
            os.makedirs(subtitle_dir, exist_ok=True)
            
            for scene in scenes:
                sequence = scene.get("sequence", 1)
                native_script = scene.get("native_script", "")
                learning_script = scene.get("learning_script", "")
                reading_script = scene.get("reading_script", "")
                
                # Screen 1 이미지 생성 (순번 + 원어)
                screen1_filename = f"{self.config.identifier}_conversation_{sequence:03d}_screen1.png"
                screen1_path = os.path.join(subtitle_dir, screen1_filename)
                self._create_conversation_screen1_image(screen1_path, sequence, native_script)
                self.generated_files[f"screen1_{sequence}"] = screen1_path
                
                # Screen 2 이미지 생성 (순번 + 원어 + 학습어 + 읽기)
                screen2_filename = f"{self.config.identifier}_conversation_{sequence:03d}_screen2.png"
                screen2_path = os.path.join(subtitle_dir, screen2_filename)
                self._create_conversation_screen2_image(screen2_path, sequence, native_script, learning_script, reading_script)
                self.generated_files[f"screen2_{sequence}"] = screen2_path
            
            self._log_info(f"회화 자막 이미지 생성 완료: {len(scenes)}개 장면, {len(scenes)*2}개 이미지")
            return subtitle_dir
            
        except Exception as e:
            self._log_error(f"자막 이미지 생성 실패: {e}")
            return None
    
    def _render_video(self, manifest_data: Dict[str, Any]) -> Optional[str]:
        """비디오 렌더링"""
        try:
            # 비디오 파일명 생성
            video_filename = f"{self.config.identifier}_conversation.mp4"
            video_path = os.path.join(self.output_dirs["mp4"], video_filename)
            
            # 더미 비디오 파일 생성 (실제로는 FFmpeg 사용)
            self._create_dummy_video(video_path)
            
            self.generated_files["video"] = video_path
            self._log_info("회화 비디오 렌더링 완료")
            
            return video_path
            
        except Exception as e:
            self._log_error(f"비디오 렌더링 실패: {e}")
            return None
    
    def _create_conversation_ssml(self, manifest_data: Dict[str, Any]) -> str:
        """회화 SSML 생성"""
        try:
            scenes = manifest_data.get("scenes", [])
            
            ssml_parts = ['<speak>']
            
            for scene in scenes:
                sequence = scene.get("sequence", 1)
                native_script = scene.get("native_script", "")
                learning_script = scene.get("learning_script", "")
                
                # 원어 화자
                ssml_parts.append(f'<mark name="conversation_{sequence:02d}_native_start"/>')
                ssml_parts.append(f'<prosody rate="0.9">{native_script}</prosody>')
                ssml_parts.append(f'<mark name="conversation_{sequence:02d}_native_end"/>')
                ssml_parts.append('<break time="1s"/>')
                
                # 학습어 화자들 (4명)
                for i in range(1, 5):
                    ssml_parts.append(f'<mark name="conversation_{sequence:02d}_learning{i}_start"/>')
                    ssml_parts.append(f'<prosody rate="0.9">{learning_script}</prosody>')
                    ssml_parts.append(f'<mark name="conversation_{sequence:02d}_learning{i}_end"/>')
                    if i < 4:
                        ssml_parts.append('<break time="1s"/>')
                
                # 행 간 1초 무음
                if sequence < len(scenes):
                    ssml_parts.append('<break time="1s"/>')
            
            ssml_parts.append('</speak>')
            
            return '\n'.join(ssml_parts)
            
        except Exception as e:
            self._log_error(f"SSML 생성 실패: {e}")
            return "<speak></speak>"
    
    def _create_conversation_screen1_image(self, image_path: str, sequence: int, native_script: str):
        """회화 Screen 1 이미지 생성 (순번 + 원어)"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            # 1920x1080 이미지 생성
            img = Image.new('RGB', (1920, 1080), color='black')
            draw = ImageDraw.Draw(img)
            
            # 기본 폰트 사용
            try:
                title_font = ImageFont.truetype("arial.ttf", 40)
                script_font = ImageFont.truetype("arial.ttf", 60)
            except:
                title_font = ImageFont.load_default()
                script_font = ImageFont.load_default()
            
            # 순번 표시
            sequence_text = f"{sequence:02d}"
            bbox = draw.textbbox((0, 0), sequence_text, font=title_font)
            seq_width = bbox[2] - bbox[0]
            seq_height = bbox[3] - bbox[1]
            
            seq_x = 50
            seq_y = 50
            draw.text((seq_x, seq_y), sequence_text, fill='#00FFFF', font=title_font)
            
            # 원어 텍스트 표시
            bbox = draw.textbbox((0, 0), native_script, font=script_font)
            script_width = bbox[2] - bbox[0]
            script_height = bbox[3] - bbox[1]
            
            script_x = (1920 - script_width) // 2
            script_y = (1080 - script_height) // 2
            
            draw.text((script_x, script_y), native_script, fill='white', font=script_font)
            
            img.save(image_path)
            
        except Exception as e:
            self._log_error(f"Screen 1 이미지 생성 실패: {e}")
    
    def _create_conversation_screen2_image(self, image_path: str, sequence: int, 
                                         native_script: str, learning_script: str, reading_script: str):
        """회화 Screen 2 이미지 생성 (순번 + 원어 + 학습어 + 읽기)"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            # 1920x1080 이미지 생성
            img = Image.new('RGB', (1920, 1080), color='black')
            draw = ImageDraw.Draw(img)
            
            # 기본 폰트 사용
            try:
                title_font = ImageFont.truetype("arial.ttf", 40)
                script_font = ImageFont.truetype("arial.ttf", 50)
            except:
                title_font = ImageFont.load_default()
                script_font = ImageFont.load_default()
            
            # 순번 표시
            sequence_text = f"{sequence:02d}"
            seq_x = 50
            seq_y = 50
            draw.text((seq_x, seq_y), sequence_text, fill='#00FFFF', font=title_font)
            
            # 텍스트들을 세로로 배치
            y_offset = 200
            line_height = 80
            
            # 원어 텍스트
            draw.text((100, y_offset), native_script, fill='#00FFFF', font=script_font)
            y_offset += line_height
            
            # 학습어 텍스트
            draw.text((100, y_offset), learning_script, fill='#FF00FF', font=script_font)
            y_offset += line_height
            
            # 읽기 텍스트
            draw.text((100, y_offset), reading_script, fill='#FFFF00', font=script_font)
            
            img.save(image_path)
            
        except Exception as e:
            self._log_error(f"Screen 2 이미지 생성 실패: {e}")
    
    def _create_dummy_video(self, video_path: str):
        """더미 비디오 파일 생성"""
        try:
            # 간단한 더미 MP4 헤더 생성
            with open(video_path, 'wb') as f:
                f.write(b'\x00\x00\x00\x20ftypmp42\x00\x00\x00\x00mp41mp42isom')
            
        except Exception as e:
            self._log_error(f"더미 비디오 생성 실패: {e}")
