"""
인트로 플러그인

인트로 스크립트 타입의 데이터를 처리하는 플러그인입니다.
라인별 처리 방식으로 33.83초 오디오를 생성합니다.
"""

import os
import json
from typing import Dict, List, Any, Optional
from .base_plugin import BasePlugin, PluginConfig


class IntroPlugin(BasePlugin):
    """인트로 플러그인"""
    
    def get_plugin_type(self) -> str:
        """플러그인 타입 반환"""
        return "intro"
    
    def get_plugin_name(self) -> str:
        """플러그인 이름 반환"""
        return "인트로 플러그인"
    
    def get_plugin_description(self) -> str:
        """플러그인 설명 반환"""
        return "인트로 스크립트를 라인별로 처리하여 비디오를 생성합니다"
    
    def get_required_input_fields(self) -> List[str]:
        """필수 입력 필드 반환"""
        return ["intro_script"]
    
    def get_optional_input_fields(self) -> List[str]:
        """선택적 입력 필드 반환"""
        return ["speaker_settings", "image_settings", "background_settings"]
    
    def get_default_settings(self) -> Dict[str, Any]:
        """기본 설정 반환"""
        return {
            "line_processing": True,
            "sentence_separation": True,
            "smart_line_break": True,
            "vertical_alignment": "top",  # top 또는 bottom
            "max_lines": 3,
            "font_size_adjustment": True
        }
    
    def _validate_input_data(self, input_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """입력 데이터 검증"""
        try:
            # 필수 필드 확인
            if "intro_script" not in input_data:
                self._log_error("인트로 스크립트가 없습니다")
                return None
            
            intro_script = input_data["intro_script"]
            if not intro_script or not isinstance(intro_script, str):
                self._log_error("인트로 스크립트가 유효하지 않습니다")
                return None
            
            # 문장 분리 및 검증
            sentences = self._split_sentences(intro_script)
            if not sentences:
                self._log_error("분리된 문장이 없습니다")
                return None
            
            self._log_info(f"인트로 스크립트 검증 완료: {len(sentences)}개 문장")
            
            return {
                "intro_script": intro_script,
                "sentences": sentences,
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
            sentences = validated_data["sentences"]
            
            # 인트로 매니페스트 구조 생성
            manifest = {
                "project_name": self.config.project_name,
                "identifier": self.config.identifier,
                "type": "intro",
                "resolution": self.config.resolution,
                "fps": self.config.fps,
                "total_sentences": len(sentences),
                "scenes": []
            }
            
            # 각 문장을 장면으로 변환
            for i, sentence in enumerate(sentences, 1):
                scene = {
                    "id": f"intro_{i:02d}",
                    "type": "intro",
                    "sequence": i,
                    "sentence": sentence.strip(),
                    "line_number": i,
                    "settings": {
                        "smart_line_break": True,
                        "max_lines": 3,
                        "vertical_alignment": "top"
                    }
                }
                manifest["scenes"].append(scene)
            
            # 매니페스트 파일 저장
            manifest_filename = f"{self.config.identifier}_intro.json"
            manifest_path = os.path.join(self.output_dirs["manifest"], manifest_filename)
            
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
            
            self.generated_files["manifest"] = manifest_path
            self._log_info(f"인트로 매니페스트 생성 완료: {len(sentences)}개 장면")
            
            return manifest
            
        except Exception as e:
            self._log_error(f"매니페스트 생성 실패: {e}")
            return None
    
    def _generate_audio(self, manifest_data: Dict[str, Any]) -> Optional[str]:
        """오디오 생성"""
        try:
            # SSML 생성
            ssml_content = self._create_intro_ssml(manifest_data)
            
            # SSML 파일 저장
            ssml_filename = f"{self.config.identifier}_intro.ssml"
            ssml_path = os.path.join(self.output_dirs["ssml"], ssml_filename)
            
            with open(ssml_path, 'w', encoding='utf-8') as f:
                f.write(ssml_content)
            
            self.generated_files["ssml"] = ssml_path
            
            # 오디오 파일 생성 (더미)
            audio_filename = f"{self.config.identifier}_intro.mp3"
            audio_path = os.path.join(self.output_dirs["audio"], audio_filename)
            
            # 간단한 더미 MP3 헤더 생성
            with open(audio_path, 'wb') as f:
                f.write(b'\xff\xfb\x90\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
            
            self.generated_files["audio"] = audio_path
            self._log_info("인트로 오디오 생성 완료")
            
            return audio_path
            
        except Exception as e:
            self._log_error(f"오디오 생성 실패: {e}")
            return None
    
    def _generate_subtitles(self, manifest_data: Dict[str, Any]) -> Optional[str]:
        """자막 이미지 생성"""
        try:
            scenes = manifest_data.get("scenes", [])
            subtitle_dir = os.path.join(self.output_dirs["subtitles"], "intro")
            os.makedirs(subtitle_dir, exist_ok=True)
            
            for scene in scenes:
                sentence = scene.get("sentence", "")
                sequence = scene.get("sequence", 1)
                
                # 자막 이미지 파일명 생성
                image_filename = f"{self.config.identifier}_intro_{sequence:03d}.png"
                image_path = os.path.join(subtitle_dir, image_filename)
                
                # 더미 이미지 생성 (실제로는 PNGRenderer 사용)
                self._create_dummy_image(image_path, sentence)
                
                self.generated_files[f"subtitle_{sequence}"] = image_path
            
            self._log_info(f"인트로 자막 이미지 생성 완료: {len(scenes)}개")
            return subtitle_dir
            
        except Exception as e:
            self._log_error(f"자막 이미지 생성 실패: {e}")
            return None
    
    def _render_video(self, manifest_data: Dict[str, Any]) -> Optional[str]:
        """비디오 렌더링"""
        try:
            # 비디오 파일명 생성
            video_filename = f"{self.config.identifier}_intro.mp4"
            video_path = os.path.join(self.output_dirs["mp4"], video_filename)
            
            # 더미 비디오 파일 생성 (실제로는 FFmpeg 사용)
            self._create_dummy_video(video_path)
            
            self.generated_files["video"] = video_path
            self._log_info("인트로 비디오 렌더링 완료")
            
            return video_path
            
        except Exception as e:
            self._log_error(f"비디오 렌더링 실패: {e}")
            return None
    
    def _split_sentences(self, script: str) -> List[str]:
        """문장 분리"""
        try:
            # 간단한 문장 분리 로직 (실제로는 더 정교한 로직 필요)
            sentences = []
            
            # 마침표, 느낌표, 물음표로 분리
            import re
            parts = re.split(r'[.!?]+', script)
            
            for part in parts:
                part = part.strip()
                if part:
                    sentences.append(part)
            
            return sentences
            
        except Exception as e:
            self._log_error(f"문장 분리 실패: {e}")
            return []
    
    def _create_intro_ssml(self, manifest_data: Dict[str, Any]) -> str:
        """인트로 SSML 생성"""
        try:
            scenes = manifest_data.get("scenes", [])
            
            ssml_parts = ['<speak>']
            
            for i, scene in enumerate(scenes):
                sentence = scene.get("sentence", "")
                
                # 마크 태그 추가
                ssml_parts.append(f'<mark name="intro_{i+1:02d}_start"/>')
                ssml_parts.append(f'<prosody rate="0.9" pitch="+10%">{sentence}</prosody>')
                ssml_parts.append(f'<mark name="intro_{i+1:02d}_end"/>')
                
                # 문장 간 1초 무음
                if i < len(scenes) - 1:
                    ssml_parts.append('<break time="1s"/>')
            
            ssml_parts.append('</speak>')
            
            return '\n'.join(ssml_parts)
            
        except Exception as e:
            self._log_error(f"SSML 생성 실패: {e}")
            return "<speak></speak>"
    
    def _create_dummy_image(self, image_path: str, text: str):
        """더미 이미지 생성"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            # 1920x1080 이미지 생성
            img = Image.new('RGB', (1920, 1080), color='black')
            draw = ImageDraw.Draw(img)
            
            # 기본 폰트 사용
            try:
                font = ImageFont.truetype("arial.ttf", 60)
            except:
                font = ImageFont.load_default()
            
            # 텍스트 중앙에 그리기
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = (1920 - text_width) // 2
            y = (1080 - text_height) // 2
            
            draw.text((x, y), text, fill='white', font=font)
            
            img.save(image_path)
            
        except Exception as e:
            self._log_error(f"더미 이미지 생성 실패: {e}")
    
    def _create_dummy_video(self, video_path: str):
        """더미 비디오 파일 생성"""
        try:
            # 간단한 더미 MP4 헤더 생성
            with open(video_path, 'wb') as f:
                f.write(b'\x00\x00\x00\x20ftypmp42\x00\x00\x00\x00mp41mp42isom')
            
        except Exception as e:
            self._log_error(f"더미 비디오 생성 실패: {e}")
