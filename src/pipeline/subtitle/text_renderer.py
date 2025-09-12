"""
텍스트 렌더러

PIL을 사용하여 텍스트를 이미지로 렌더링하고 다양한 텍스트 설정을 지원합니다.
"""

import os
from typing import Dict, Any, Optional, Tuple, List
from PIL import Image, ImageDraw, ImageFont
import json


class TextRenderer:
    """텍스트 렌더링 클래스"""
    
    def __init__(self, settings: Dict[str, Any], log_callback=None):
        """
        텍스트 렌더러 초기화
        
        Args:
            settings: UI에서 전달된 전체 설정
            log_callback: 로그 메시지를 전달할 콜백 함수
        """
        self.config = self._load_config(settings)
        self.fonts = {}
        self.log_callback = log_callback
        self._load_fonts()
    
    def _load_config(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """텍스트 설정 로드"""
        default_config = {
            "fonts": {
                "Noto Sans KR": "~/Library/Fonts/NotoSansKR-Regular.ttf",
                "KoPubWorld돋움체": "~/Library/Fonts/KoPubWorld Dotum Medium.ttf",
                "KoPubWorld바탕체": "~/Library/Fonts/KoPubWorld Batang Medium.ttf"
            },
            "default_settings": {
                "font_size": 48,
                "font_color": "#FFFFFF",
                "stroke_color": "#000000",
                "stroke_width": 2,
                "background_color": "#000000",
                "padding": 20,
                "line_spacing": 10,
                "alignment": "center"
            },
            "scene_types": {
                "intro": {
                    "font_size": 64,
                    "font_color": "#FFFFFF",
                    "background_color": "#000000"
                },
                "conversation": {
                    "screen1": {
                        "font_size": 56,
                        "font_color": "#FFFFFF",
                        "background_color": "#000000"
                    },
                    "screen2": {
                        "font_size": 48,
                        "font_color": "#FFFFFF",
                        "background_color": "#000000"
                    }
                },
                "ending": {
                    "font_size": 64,
                    "font_color": "#FFFFFF",
                    "background_color": "#000000"
                }
            }
        }
        
        # 사용자 설정으로 기본 설정 병합
        self._merge_configs(default_config, settings)
        return default_config
    
    def _merge_configs(self, base_config: Dict[str, Any], user_config: Dict[str, Any]):
        """설정 병합 (재귀적)"""
        for key, value in user_config.items():
            if key in base_config and isinstance(base_config[key], dict) and isinstance(value, dict):
                self._merge_configs(base_config[key], value)
            else:
                base_config[key] = value
    
    def _log(self, message):
        if self.log_callback:
            self.log_callback(message, "INFO")
        else:
            print(message)

    def _load_fonts(self):
        """폰트 로드 - 실제 사용 시점에 로드되도록 변경"""
        pass
    
    def _get_font(self, text: str, font_size: int, font_name: str = None) -> Optional[ImageFont.FreeTypeFont]:
        """언어에 따른 폰트 반환"""
        try:
            if font_name in self.fonts:
                return ImageFont.truetype(self.fonts[font_name], font_size)

            font_path = self.config["fonts"].get(font_name)
            if font_path:
                font_path = os.path.expanduser(font_path)
                if os.path.exists(font_path):
                    self.fonts[font_name] = font_path
                    return ImageFont.truetype(font_path, font_size)
                else:
                    self._log(f"⚠️ 폰트 파일을 찾을 수 없습니다: {font_path}")

            # 기본 폰트 사용
            return ImageFont.load_default()
                
        except Exception as e:
            self._log(f"⚠️ 폰트 생성 실패: {e}")
            return ImageFont.load_default()
    
    def _detect_language(self, text: str) -> str:
        """텍스트 언어 감지"""
        if any('\u4e00' <= char <= '\u9fff' for char in text):
            return "zh"
        elif any('\uac00' <= char <= '\ud7af' for char in text):
            return "ko"
        elif any('\u0041' <= char <= '\u005a' or '\u0061' <= char <= '\u007a' for char in text):
            return "en"
        else:
            return "ko"
    
    def render_text(self, text: str, width: int, height: int, 
                   settings: Optional[Dict[str, Any]] = None) -> Image.Image:
        """
        텍스트를 이미지로 렌더링
        
        Args:
            text: 렌더링할 텍스트
            width: 이미지 너비
            height: 이미지 높이
            settings: 텍스트 설정
            
        Returns:
            PIL Image 객체
        """
        # 기본 설정과 사용자 설정 병합
        final_settings = self.config["default_settings"].copy()
        if settings:
            final_settings.update(settings)
        
        # 이미지 생성
        image = Image.new('RGBA', (width, height), final_settings["background_color"])
        draw = ImageDraw.Draw(image)
        
        # 폰트 설정
        font_size = final_settings["font_size"]
        font_name = final_settings.get("font")
        font = self._get_font(text, font_size, font_name)
        
        # 텍스트 크기 계산
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # 텍스트 위치 계산
        padding = final_settings["padding"]
        alignment = final_settings["alignment"]
        
        if alignment == "center":
            x = (width - text_width) // 2
        elif alignment == "left":
            x = padding
        elif alignment == "right":
            x = width - text_width - padding
        else:
            x = (width - text_width) // 2
        
        y = (height - text_height) // 2
        
        # 스트로크 그리기 (테두리)
        stroke_width = final_settings["stroke_width"]
        if stroke_width > 0:
            for dx in range(-stroke_width, stroke_width + 1):
                for dy in range(-stroke_width, stroke_width + 1):
                    if dx*dx + dy*dy <= stroke_width*stroke_width:
                        draw.text((x + dx, y + dy), text, font=font, 
                                fill=final_settings["stroke_color"])
        
        # 메인 텍스트 그리기
        draw.text((x, y), text, font=font, fill=final_settings["font_color"])
        
        return image
    
    def render_multiline_text(self, lines: List[str], width: int, height: int,
                            line_settings: List[Dict[str, Any]]) -> Image.Image:
        """
        여러 줄 텍스트를 이미지로 렌더링
        
        Args:
            lines: 텍스트 줄 리스트
            width: 이미지 너비
            height: 이미지 높이
            line_settings: 각 라인별 설정 리스트
            
        Returns:
            PIL Image 객체
        """
        # 이미지 생성
        image = Image.new('RGBA', (width, height), self.config["default_settings"]["background_color"])
        draw = ImageDraw.Draw(image)
        
        padding = self.config["default_settings"]["padding"]
        
        # Calculate total height of the text block
        total_h = 0
        line_heights = []
        for i, line in enumerate(lines):
            settings = line_settings[i] if i < len(line_settings) else self.config["default_settings"]
            font_size = settings.get("font_size", self.config["default_settings"]["font_size"])
            font_name = settings.get("폰트(pt)")
            font = self._get_font(line, font_size, font_name)
            bbox = draw.textbbox((0, 0), line, font=font)
            line_height = bbox[3] - bbox[1]
            line_heights.append(line_height)
            total_h += line_height
        
        line_spacing = self.config["default_settings"]["line_spacing"]
        total_h += (len(lines) - 1) * line_spacing

        # Calculate starting y position
        alignment_v = line_settings[0].get("상하 정렬", "Top") if line_settings else "Top"
        if alignment_v == "Middle":
            current_y = (height - total_h) // 2
        elif alignment_v == "Bottom":
            current_y = height - total_h - padding
        else: # Top
            current_y = padding

        # 각 줄별로 렌더링
        self._log("--- Rendering multiline text ---")
        for i, line in enumerate(lines):
            if not line.strip():
                if i < len(line_settings):
                    font_size = line_settings[i].get("font_size", self.config["default_settings"]["font_size"])
                    line_spacing = line_settings[i].get("line_spacing", self.config["default_settings"]["line_spacing"])
                    current_y += font_size + line_spacing
                continue
            
            settings = line_settings[i] if i < len(line_settings) else self.config["default_settings"]

            self._log(f"  - Line {i}: {line}")
            self._log(f"    Settings: {settings}")

            font_size = int(settings.get("크기(pt)", self.config["default_settings"]["font_size"]))
            font_name = settings.get("폰트(pt)")
            font_color = settings.get("색상", self.config["default_settings"]["font_color"])
            alignment = settings.get("좌우 정렬", self.config["default_settings"]["alignment"])
            stroke_width = int(settings.get("stroke_width", self.config["default_settings"]["stroke_width"]))
            stroke_color = settings.get("stroke_color", self.config["default_settings"]["stroke_color"])
            line_spacing = int(settings.get("line_spacing", self.config["default_settings"]["line_spacing"]))

            # 언어별 폰트 선택
            font = self._get_font(line, font_size, font_name)
            
            # 텍스트 크기 계산
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            
            # 텍스트 위치 계산
            if alignment == "Center":
                x = (width - text_width) // 2
            elif alignment == "Left":
                x = padding
            elif alignment == "Right":
                x = width - text_width - padding
            else:
                x = (width - text_width) // 2
            
            # 스트로크 그리기 (테두리)
            if stroke_width > 0:
                for dx in range(-stroke_width, stroke_width + 1):
                    for dy in range(-stroke_width, stroke_width + 1):
                        if dx*dx + dy*dy <= stroke_width*stroke_width:
                            draw.text((x + dx, current_y + dy), line, font=font,
                                    fill=stroke_color)
            
            # 메인 텍스트 그리기
            draw.text((x, current_y), line, font=font, fill=font_color)
            
            current_y += line_heights[i] + line_spacing
            
            # 높이 초과 시 중단
            if current_y + font_size > height - padding:
                break
        
        return image
    
    def render_conversation_screen1(self, sequence: int, native_script: str,
                                  width: int, height: int, line_settings: List[Dict[str, Any]]) -> Image.Image:
        """
        conversation 화면 1 렌더링 (순번 + 원어)
        
        Args:
            sequence: 순번
            native_script: 원어 텍스트
            width: 이미지 너비
            height: 이미지 높이
            line_settings: 각 라인별 설정 리스트
            
        Returns:
            PIL Image 객체
        """
        lines = [
            f"{sequence}",
            native_script
        ]
        
        return self.render_multiline_text(lines, width, height, line_settings)
    
    def render_conversation_screen2(self, sequence: int, native_script: str,
                                  learning_script: str, reading_script: str,
                                  width: int, height: int, line_settings: List[Dict[str, Any]]) -> Image.Image:
        """
        conversation 화면 2 렌더링 (순번 + 원어 + 학습어 + 읽기)
        
        Args:
            sequence: 순번
            native_script: 원어 텍스트
            learning_script: 학습어 텍스트
            reading_script: 읽기 텍스트
            width: 이미지 너비
            height: 이미지 높이
            line_settings: 각 라인별 설정 리스트
            
        Returns:
            PIL Image 객체
        """
        lines = [
            f"{sequence}",
            native_script,
            learning_script,
            reading_script
        ]
        
        return self.render_multiline_text(lines, width, height, line_settings)
    
    def render_intro_ending(self, full_script: str, width: int, height: int,
                           scene_type: str = "intro", line_settings: List[Dict[str, Any]] = None) -> Image.Image:
        """
        intro/ending 장면 렌더링
        
        Args:
            full_script: 전체 스크립트
            width: 이미지 너비
            height: 이미지 높이
            scene_type: 장면 타입 (intro/ending)
            line_settings: 각 라인별 설정 리스트
            
        Returns:
            PIL Image 객체
        """
        settings = self.config["scene_types"][scene_type].copy()
        if line_settings:
            settings.update(line_settings[0])

        # 긴 텍스트를 여러 줄로 분할
        lines = self._split_long_text(full_script, width, settings.get("w", 1820), settings["font_size"])
        
        # Create a list of settings for each line
        new_line_settings = [settings] * len(lines)

        return self.render_multiline_text(lines, width, height, new_line_settings)
    
    def _split_long_text(self, text: str, max_width: int, w: int, font_size: int) -> List[str]:
        """긴 텍스트를 여러 줄로 분할"""
        # 간단한 분할 로직 (실제로는 더 정교한 분할 필요)
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            test_line = current_line + " " + word if current_line else word
            # 대략적인 너비 계산 (한글 기준)
            estimated_width = len(test_line) * font_size * 0.6
            
            if estimated_width <= w:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        
        return lines if lines else [text]
    
    def save_image(self, image: Image.Image, output_path: str, format: str = "PNG") -> bool:
        """이미지 저장"""
        try:
            image.save(output_path, format)
            return True
        except Exception as e:
            print(f"❌ 이미지 저장 실패: {e}")
            return False
    
    def get_text_dimensions(self, text: str, font_size: int, font_name: str = None) -> Tuple[int, int]:
        """텍스트 크기 계산"""
        try:
            font = self._get_font(text, font_size, font_name)
            if font:
                # 더미 이미지로 크기 계산
                dummy_img = Image.new('RGBA', (1, 1))
                dummy_draw = ImageDraw.Draw(dummy_img)
                bbox = dummy_draw.textbbox((0, 0), text, font=font)
                return bbox[2] - bbox[0], bbox[3] - bbox[1]
        except Exception as e:
            print(f"⚠️ 텍스트 크기 계산 실패: {e}")
        
        # 기본값 반환
        return len(text) * font_size // 2, font_size
