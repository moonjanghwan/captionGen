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
    
    def __init__(self, config_path: Optional[str] = None):
        """
        텍스트 렌더러 초기화
        
        Args:
            config_path: 텍스트 설정 파일 경로
        """
        self.config = self._load_config(config_path)
        self.fonts = {}
        self._load_fonts()
    
    def _load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """텍스트 설정 로드"""
        default_config = {
            "fonts": {
                "ko": "assets/fonts/NanumGothic.ttf",
                "zh": "assets/fonts/NotoSansCJK-Regular.ttc",
                "en": "assets/fonts/NotoSans-Regular.ttf"
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
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    # 사용자 설정으로 기본 설정 병합
                    self._merge_configs(default_config, user_config)
            except Exception as e:
                print(f"⚠️ 설정 파일 로드 실패: {e}")
        
        return default_config
    
    def _merge_configs(self, base_config: Dict[str, Any], user_config: Dict[str, Any]):
        """설정 병합 (재귀적)"""
        for key, value in user_config.items():
            if key in base_config and isinstance(base_config[key], dict) and isinstance(value, dict):
                self._merge_configs(base_config[key], value)
            else:
                base_config[key] = value
    
    def _load_fonts(self):
        """폰트 로드"""
        for lang, font_path in self.config["fonts"].items():
            try:
                if os.path.exists(font_path):
                    self.fonts[lang] = font_path
                else:
                    print(f"⚠️ 폰트 파일을 찾을 수 없습니다: {font_path}")
            except Exception as e:
                print(f"⚠️ 폰트 로드 실패 ({lang}): {e}")
    
    def _get_font(self, text: str, font_size: int, language: str = "ko") -> Optional[ImageFont.FreeTypeFont]:
        """언어에 따른 폰트 반환"""
        try:
            # 언어 감지
            if any('\u4e00' <= char <= '\u9fff' for char in text):  # 한자
                font_path = self.fonts.get("zh", self.fonts.get("ko"))
            elif any('\uac00' <= char <= '\ud7af' for char in text):  # 한글
                font_path = self.fonts.get("ko")
            elif any('\u0041' <= char <= '\u005a' or '\u0061' <= char <= '\u007a' for char in text):  # 영문
                font_path = self.fonts.get("en", self.fonts.get("ko"))
            else:
                font_path = self.fonts.get("ko")
            
            if font_path:
                return ImageFont.truetype(font_path, font_size)
            else:
                # 기본 폰트 사용
                return ImageFont.load_default()
                
        except Exception as e:
            print(f"⚠️ 폰트 생성 실패: {e}")
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
        language = self._detect_language(text)
        font = self._get_font(text, font_size, language)
        
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
                            settings: Optional[Dict[str, Any]] = None) -> Image.Image:
        """
        여러 줄 텍스트를 이미지로 렌더링
        
        Args:
            lines: 텍스트 줄 리스트
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
        line_spacing = final_settings["line_spacing"]
        padding = final_settings["padding"]
        
        # 각 줄별로 렌더링
        current_y = padding
        for line in lines:
            if not line.strip():
                current_y += font_size + line_spacing
                continue
            
            # 언어별 폰트 선택
            language = self._detect_language(line)
            font = self._get_font(line, font_size, language)
            
            # 텍스트 크기 계산
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            
            # 텍스트 위치 계산
            alignment = final_settings["alignment"]
            if alignment == "center":
                x = (width - text_width) // 2
            elif alignment == "left":
                x = padding
            elif alignment == "right":
                x = width - text_width - padding
            else:
                x = (width - text_width) // 2
            
            # 스트로크 그리기 (테두리)
            stroke_width = final_settings["stroke_width"]
            if stroke_width > 0:
                for dx in range(-stroke_width, stroke_width + 1):
                    for dy in range(-stroke_width, stroke_width + 1):
                        if dx*dx + dy*dy <= stroke_width*stroke_width:
                            draw.text((x + dx, current_y + dy), line, font=font,
                                    fill=final_settings["stroke_color"])
            
            # 메인 텍스트 그리기
            draw.text((x, current_y), line, font=font, fill=final_settings["font_color"])
            
            current_y += font_size + line_spacing
            
            # 높이 초과 시 중단
            if current_y + font_size > height - padding:
                break
        
        return image
    
    def render_conversation_screen1(self, sequence: int, native_script: str,
                                  width: int, height: int) -> Image.Image:
        """
        conversation 화면 1 렌더링 (순번 + 원어)
        
        Args:
            sequence: 순번
            native_script: 원어 텍스트
            width: 이미지 너비
            height: 이미지 높이
            
        Returns:
            PIL Image 객체
        """
        settings = self.config["scene_types"]["conversation"]["screen1"].copy()
        
        # 순번과 원어 텍스트를 별도 줄로 분리
        lines = [
            f"{sequence}",
            native_script
        ]
        
        return self.render_multiline_text(lines, width, height, settings)
    
    def render_conversation_screen2(self, sequence: int, native_script: str,
                                  learning_script: str, reading_script: str,
                                  width: int, height: int) -> Image.Image:
        """
        conversation 화면 2 렌더링 (순번 + 원어 + 학습어 + 읽기)
        
        Args:
            sequence: 순번
            native_script: 원어 텍스트
            learning_script: 학습어 텍스트
            reading_script: 읽기 텍스트
            width: 이미지 너비
            height: 이미지 높이
            
        Returns:
            PIL Image 객체
        """
        settings = self.config["scene_types"]["conversation"]["screen2"].copy()
        
        # 4줄 텍스트 구성
        lines = [
            f"{sequence}",
            native_script,
            learning_script,
            reading_script
        ]
        
        return self.render_multiline_text(lines, width, height, settings)
    
    def render_intro_ending(self, full_script: str, width: int, height: int,
                           scene_type: str = "intro") -> Image.Image:
        """
        intro/ending 장면 렌더링
        
        Args:
            full_script: 전체 스크립트
            width: 이미지 너비
            height: 이미지 높이
            scene_type: 장면 타입 (intro/ending)
            
        Returns:
            PIL Image 객체
        """
        settings = self.config["scene_types"][scene_type].copy()
        
        # 긴 텍스트를 여러 줄로 분할
        lines = self._split_long_text(full_script, width, settings["font_size"])
        
        return self.render_multiline_text(lines, width, height, settings)
    
    def _split_long_text(self, text: str, max_width: int, font_size: int) -> List[str]:
        """긴 텍스트를 여러 줄로 분할"""
        # 간단한 분할 로직 (실제로는 더 정교한 분할 필요)
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            test_line = current_line + " " + word if current_line else word
            # 대략적인 너비 계산 (한글 기준)
            estimated_width = len(test_line) * font_size * 0.6
            
            if estimated_width <= max_width:
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
    
    def get_text_dimensions(self, text: str, font_size: int, language: str = "ko") -> Tuple[int, int]:
        """텍스트 크기 계산"""
        try:
            font = self._get_font(text, font_size, language)
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
