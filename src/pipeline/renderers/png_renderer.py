"""
PNG 직접 렌더링 시스템

ASS 없이 PIL/Pillow를 사용하여 자막 이미지를 직접 생성합니다.
UI 설정을 직접 적용하여 고품질 PNG 이미지를 생성합니다.
"""

import os
import re
from typing import Dict, Any, List, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont
import textwrap
from dataclasses import dataclass
from ..settings import SettingMerger, SettingValidator, MergedSettings


@dataclass
class TextSettings:
    """텍스트 설정 데이터 클래스"""
    x: int
    y: int
    w: int
    크기: int  # 폰트 크기
    폰트: str
    색상: str
    굵기: bool = False
    좌우정렬: str = "center"  # left, center, right
    상하정렬: str = "center"  # top, center, bottom
    바탕: bool = False
    쉐도우: bool = False
    외곽선: bool = False


@dataclass
class CommonSettings:
    """공통 설정 데이터 클래스"""
    bg: Dict[str, Any]  # 배경 설정
    shadow: Dict[str, Any]  # 그림자 설정
    border: Dict[str, Any]  # 외곽선 설정


class PNGRenderer:
    """PNG 직접 렌더링 클래스"""
    
    def __init__(self, settings: Dict[str, Any]):
        """
        PNG 렌더러 초기화
        
        Args:
            settings: UI에서 전달받은 설정 딕셔너리
        """
        self.raw_settings = settings
        self.fonts = {}
        self._load_fonts()
        
        # 설정 병합 및 검증
        self.setting_merger = SettingMerger()
        self.setting_validator = SettingValidator()
        self.merged_settings = self._process_settings(settings)
    
    def _load_fonts(self):
        """폰트 로딩"""
        font_paths = {
            "Noto Sans KR": "~/Library/Fonts/NotoSansKR-Regular.ttf",
            "KoPubWorld돋움체": "~/Library/Fonts/KoPubWorld Dotum Medium.ttf",
            "KoPubWorld바탕체": "~/Library/Fonts/KoPubWorld Batang Medium.ttf",
            "Arial": "/System/Library/Fonts/Arial.ttf",
            "Times New Roman": "/System/Library/Fonts/Times New Roman.ttf"
        }
        
        for font_name, font_path in font_paths.items():
            expanded_path = os.path.expanduser(font_path)
            if os.path.exists(expanded_path):
                self.fonts[font_name] = expanded_path
            else:
                print(f"⚠️ 폰트 파일을 찾을 수 없습니다: {font_name} ({expanded_path})")
    
    def _get_font(self, font_name: str, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
        """폰트 객체 가져오기"""
        try:
            font_path = self.fonts.get(font_name)
            if font_path and os.path.exists(font_path):
                return ImageFont.truetype(font_path, size)
            else:
                # 기본 폰트 사용
                return ImageFont.load_default()
        except Exception as e:
            print(f"⚠️ 폰트 로딩 실패: {font_name}, 크기: {size}, 오류: {e}")
            return ImageFont.load_default()
    
    def _process_settings(self, settings: Dict[str, Any]) -> MergedSettings:
        """설정 처리 및 병합"""
        try:
            # 기본 설정 정의
            common_settings = settings.get('common', {})
            script_settings = settings.get('tabs', {})
            user_settings = {}  # 사용자 직접 설정 (현재는 빈 딕셔너리)
            
            # 설정 병합
            merged = self.setting_merger.merge_settings(
                common_settings, script_settings, user_settings
            )
            
            print(f"✅ 설정 병합 완료: {len(merged.script_types)}개 스크립트 타입")
            return merged
            
        except Exception as e:
            print(f"⚠️ 설정 처리 실패, 기본 설정 사용: {e}")
            # 기본 설정으로 fallback
            return self._get_default_merged_settings()
    
    def _get_default_merged_settings(self) -> MergedSettings:
        """기본 병합 설정 반환"""
        from ..settings.schemas import (
            BackgroundSettings, ShadowSettings, BorderSettings,
            RowSettings, ScriptTypeSettings, CommonSettings, MergedSettings
        )
        
        # 기본 공통 설정
        common = CommonSettings(
            bg=BackgroundSettings(),
            shadow=ShadowSettings(),
            border=BorderSettings()
        )
        
        # 기본 스크립트 타입 설정
        script_types = {
            '회화 설정': ScriptTypeSettings(
                row_count=4,
                aspect_ratio='16:9',
                resolution='1920x1080',
                rows=[
                    RowSettings(row_name='순번', x=100, y=200, w=100, font_size=60),
                    RowSettings(row_name='원어', x=100, y=400, w=1800, font_size=80),
                    RowSettings(row_name='학습어', x=100, y=600, w=1800, font_size=80, color='#FFFF00'),
                    RowSettings(row_name='읽기', x=100, y=800, w=1800, font_size=60, color='#00FF00')
                ]
            )
        }
        
        return MergedSettings(
            common=common,
            script_types=script_types,
            source_info={'fallback': True}
        )
    
    def _parse_color(self, color_str: str) -> Tuple[int, int, int, int]:
        """색상 문자열을 RGBA 튜플로 변환"""
        if color_str.startswith('#'):
            color_str = color_str[1:]
        
        if len(color_str) == 6:  # RGB
            r = int(color_str[0:2], 16)
            g = int(color_str[2:4], 16)
            b = int(color_str[4:6], 16)
            return (r, g, b, 255)
        elif len(color_str) == 8:  # RGBA
            r = int(color_str[0:2], 16)
            g = int(color_str[2:4], 16)
            b = int(color_str[4:6], 16)
            a = int(color_str[6:8], 16)
            return (r, g, b, a)
        else:
            # 기본 색상 (흰색)
            return (255, 255, 255, 255)
    
    def _parse_markdown_inline(self, text: str) -> List[Dict[str, Any]]:
        """마크다운 인라인 스타일 파싱"""
        segments = []
        current_text = ""
        current_style = {}
        
        i = 0
        while i < len(text):
            if text[i:i+2] == '**':  # 볼드
                if current_text:
                    segments.append({'text': current_text, 'style': current_style.copy()})
                    current_text = ""
                
                # ** 찾기
                end_bold = text.find('**', i+2)
                if end_bold != -1:
                    bold_text = text[i+2:end_bold]
                    bold_style = current_style.copy()
                    bold_style['bold'] = True
                    segments.append({'text': bold_text, 'style': bold_style})
                    i = end_bold + 2
                else:
                    current_text += text[i]
                    i += 1
            elif text[i:i+1] == '*':  # 이탤릭
                if current_text:
                    segments.append({'text': current_text, 'style': current_style.copy()})
                    current_text = ""
                
                # * 찾기
                end_italic = text.find('*', i+1)
                if end_italic != -1:
                    italic_text = text[i+1:end_italic]
                    italic_style = current_style.copy()
                    italic_style['italic'] = True
                    segments.append({'text': italic_text, 'style': italic_style})
                    i = end_italic + 1
                else:
                    current_text += text[i]
                    i += 1
            else:
                current_text += text[i]
                i += 1
        
        if current_text:
            segments.append({'text': current_text, 'style': current_style.copy()})
        
        return segments
    
    def _smart_line_break(self, text: str, max_width: int, font: ImageFont.FreeTypeFont) -> List[str]:
        """스마트 줄바꿈"""
        if not text:
            return [""]
        
        # 마크다운 파싱
        segments = self._parse_markdown_inline(text)
        
        lines = []
        current_line = ""
        current_width = 0
        
        for segment in segments:
            segment_text = segment['text']
            segment_font = self._get_font(
                segment['style'].get('font', 'Noto Sans KR'),
                segment['style'].get('size', 24),
                segment['style'].get('bold', False)
            )
            
            words = segment_text.split(' ')
            for word in words:
                word_width = segment_font.getlength(word + ' ')
                
                if current_width + word_width <= max_width:
                    current_line += word + ' '
                    current_width += word_width
                else:
                    if current_line:
                        lines.append(current_line.strip())
                    current_line = word + ' '
                    current_width = word_width
            
            # 마지막 단어 처리
            if current_line and not current_line.endswith(' '):
                current_line += ' '
        
        if current_line:
            lines.append(current_line.strip())
        
        return lines if lines else [""]
    
    def _simple_line_break(self, text: str, max_width: int, font: ImageFont.FreeTypeFont) -> List[str]:
        """단순한 텍스트 줄바꿈"""
        if not text:
            return [""]
        
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            test_line = current_line + (" " if current_line else "") + word
            
            try:
                # 텍스트 너비 측정
                bbox = font.getbbox(test_line)
                text_width = bbox[2] - bbox[0]
            except:
                # 폰트 bbox가 지원되지 않는 경우 대략적 계산
                text_width = len(test_line) * (font.size // 2)
            
            if text_width <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                    current_line = word
                else:
                    # 단어가 너무 긴 경우 강제로 자름
                    lines.append(word)
                    current_line = ""
        
        if current_line:
            lines.append(current_line)
        
        return lines if lines else [""]
    
    def _draw_text_with_effects(self, draw: ImageDraw.Draw, text: str, position: Tuple[int, int], 
                               row_settings, font: ImageFont.FreeTypeFont) -> None:
        """효과가 적용된 텍스트 그리기"""
        x, y = position
        text_color = self._parse_color(row_settings.color)
        
        # 배경 그리기
        if row_settings.background and self.merged_settings.common.bg.enabled:
            bg_color = self._parse_color(self.merged_settings.common.bg.color)
            text_bbox = draw.textbbox((x, y), text, font=font)
            draw.rectangle(text_bbox, fill=bg_color)
        
        # 그림자 그리기
        if row_settings.shadow and self.merged_settings.common.shadow.enabled:
            shadow_offset = self.merged_settings.common.shadow.offx
            shadow_color = self._parse_color(self.merged_settings.common.shadow.color)
            draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=shadow_color)
        
        # 외곽선 그리기
        if row_settings.border and self.merged_settings.common.border.enabled:
            border_width = self.merged_settings.common.border.thick
            border_color = self._parse_color(self.merged_settings.common.border.color)
            
            # 외곽선을 여러 방향으로 그리기
            for dx in range(-border_width, border_width + 1):
                for dy in range(-border_width, border_width + 1):
                    if dx != 0 or dy != 0:
                        draw.text((x + dx, y + dy), text, font=font, fill=border_color)
        
        # 메인 텍스트 그리기
        draw.text((x, y), text, font=font, fill=text_color)
    
    def render_text_to_image(self, image: Image.Image, text: str, position: Tuple[int, int],
                           font_name: str, font_size: int, font_color: str, max_width: int,
                           align: str = "left", vertical_align: str = "top",
                           stroke_width: int = 0, stroke_color: str = "#000000",
                           shadow_offset: Tuple[int, int] = (0, 0), shadow_color: str = "#000000",
                           background: bool = False, bg_color: str = "#000000") -> Image.Image:
        """텍스트를 이미지에 렌더링"""
        try:
            draw = ImageDraw.Draw(image)
            font = self._get_font(font_name, font_size)
            
            # 스마트 줄바꿈 적용
            if max_width > 0:
                lines = self._simple_line_break(text, max_width, font)
            else:
                lines = text.split('\n')
            
            # 각 줄의 높이 계산
            line_heights = []
            total_height = 0
            for line in lines:
                try:
                    bbox = font.getbbox(line)
                    line_height = bbox[3] - bbox[1]
                except:
                    line_height = font_size
                line_heights.append(line_height)
                total_height += line_height * 1.2  # 줄 간격 추가
            
            # 마지막 줄의 추가 간격 제거
            if line_heights:
                total_height -= line_heights[-1] * 0.2
            
            start_x, start_y = position
            
            # 수직 정렬에 따른 시작 Y 위치 조정
            if vertical_align == "center":
                start_y -= total_height / 2
            elif vertical_align == "bottom":
                start_y -= total_height
            
            current_y = start_y
            
            for i, line in enumerate(lines):
                if not line.strip():  # 빈 줄 건너뛰기
                    current_y += line_heights[i] * 1.2
                    continue
                
                # 텍스트 너비 계산
                try:
                    bbox = font.getbbox(line)
                    line_width = bbox[2] - bbox[0]
                except:
                    line_width = len(line) * (font_size // 2)
                
                # 수평 정렬에 따른 X 위치 계산
                text_x = start_x
                if align == "center":
                    text_x -= line_width / 2
                elif align == "right":
                    text_x -= line_width
                
                # 배경 렌더링
                if background:
                    bg_color_rgba = self._parse_color(bg_color)
                    # 텍스트 영역에 배경 그리기
                    bg_bbox = (text_x - 5, current_y - 5, text_x + line_width + 5, current_y + line_heights[i] + 5)
                    draw.rectangle(bg_bbox, fill=bg_color_rgba)
                
                # 그림자 렌더링
                if shadow_offset[0] != 0 or shadow_offset[1] != 0:
                    draw.text((text_x + shadow_offset[0], current_y + shadow_offset[1]), 
                            line, font=font, fill=shadow_color,
                            stroke_width=stroke_width, stroke_fill=stroke_color)
                
                # 메인 텍스트 렌더링
                draw.text((text_x, current_y), line, font=font, fill=font_color,
                         stroke_width=stroke_width, stroke_fill=stroke_color)
                
                current_y += line_heights[i] * 1.2
            
            return image
            
        except Exception as e:
            print(f"⚠️ 텍스트 렌더링 실패: {e}")
            return image
    
    def create_conversation_image(self, scene_data: Dict[str, Any], output_path: str, 
                                 resolution: Tuple[int, int], settings: Dict[str, Any]) -> bool:
        """회화 이미지 생성 (2개 독립 화면)"""
        try:
            width, height = resolution
            
            # 화면 1: 순번 + 원어
            screen1_path = output_path.replace('.png', '_screen1.png')
            self._create_single_screen(
                scene_data, screen1_path, resolution, "회화 설정",
                show_learning=False, show_reading=False
            )
            
            # 화면 2: 순번 + 원어 + 학습어 + 읽기
            screen2_path = output_path.replace('.png', '_screen2.png')
            self._create_single_screen(
                scene_data, screen2_path, resolution, "회화 설정",
                show_learning=True, show_reading=True
            )
            
            return True
            
        except Exception as e:
            print(f"❌ 회화 이미지 생성 실패: {e}")
            return False
    
    def _create_single_screen(self, scene_data: Dict[str, Any], output_path: str,
                             resolution: Tuple[int, int], script_type: str = "회화 설정",
                             show_learning: bool = False, show_reading: bool = False) -> bool:
        """단일 화면 이미지 생성"""
        try:
            width, height = resolution
            
            # 배경 이미지 생성
            bg_settings = self.merged_settings.common.bg
            if bg_settings.enabled and bg_settings.type == '이미지':
                bg_path = bg_settings.value
                if bg_path and os.path.exists(bg_path):
                    image = Image.open(bg_path).convert('RGBA')
                    image = image.resize((width, height))
                else:
                    image = Image.new('RGBA', (width, height), (0, 0, 0, 255))
            else:
                image = Image.new('RGBA', (width, height), (0, 0, 0, 255))
            
            draw = ImageDraw.Draw(image)
            
            # 텍스트 설정 가져오기
            script_type_settings = self.merged_settings.script_types.get(script_type)
            if not script_type_settings:
                print(f"⚠️ 스크립트 타입 설정을 찾을 수 없습니다: {script_type}")
                return False
            
            rows = script_type_settings.rows
            
            if len(rows) >= 4:
                # 순번 (1행)
                order_row = rows[0]
                order_font = self._get_font(order_row.font_name, order_row.font_size, order_row.bold)
                self._draw_text_with_effects(
                    draw, scene_data.get('order', ''), 
                    (order_row.x, order_row.y), 
                    order_row, order_font
                )
                
                # 원어 (2행)
                native_row = rows[1]
                native_font = self._get_font(native_row.font_name, native_row.font_size, native_row.bold)
                self._draw_text_with_effects(
                    draw, scene_data.get('native_script', ''), 
                    (native_row.x, native_row.y), 
                    native_row, native_font
                )
                
                # 학습어 (3행) - show_learning이 True일 때만
                if show_learning and len(rows) >= 3:
                    learning_row = rows[2]
                    learning_font = self._get_font(learning_row.font_name, learning_row.font_size, learning_row.bold)
                    self._draw_text_with_effects(
                        draw, scene_data.get('learning_script', ''), 
                        (learning_row.x, learning_row.y), 
                        learning_row, learning_font
                    )
                
                # 읽기 (4행) - show_reading이 True일 때만
                if show_reading and len(rows) >= 4:
                    reading_row = rows[3]
                    reading_font = self._get_font(reading_row.font_name, reading_row.font_size, reading_row.bold)
                    self._draw_text_with_effects(
                        draw, scene_data.get('reading_script', ''), 
                        (reading_row.x, reading_row.y), 
                        reading_row, reading_font
                    )
            
            # 이미지 저장
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            image.save(output_path, 'PNG')
            print(f"✅ 이미지 생성 완료: {os.path.basename(output_path)}")
            
            return True
            
        except Exception as e:
            print(f"❌ 단일 화면 이미지 생성 실패: {e}")
            return False
    
    def _parse_row_settings(self, row_data: Dict[str, Any]) -> TextSettings:
        """행 설정 데이터를 TextSettings 객체로 변환"""
        return TextSettings(
            x=row_data.get('x', 0),
            y=row_data.get('y', 0),
            w=row_data.get('w', 100),
            크기=row_data.get('크기(pt)', 24),
            폰트=row_data.get('폰트(pt)', 'Noto Sans KR'),
            색상=row_data.get('색상', '#FFFFFF'),
            굵기=row_data.get('굵기', False),
            좌우정렬=row_data.get('좌우 정렬', 'center'),
            상하정렬=row_data.get('상하 정렬', 'center'),
            바탕=row_data.get('바탕', False),
            쉐도우=row_data.get('쉐도우', False),
            외곽선=row_data.get('외곽선', False)
        )
    
    def create_intro_ending_image(self, text_content: str, output_path: str,
                                 resolution: Tuple[int, int], script_type: str) -> bool:
        """인트로/엔딩 이미지 생성 (MD 인라인 스크립트, 스마트 줄바꿈)"""
        try:
            width, height = resolution
            
            # 배경 이미지 생성
            bg_settings = self.merged_settings.common.bg
            if bg_settings.enabled and bg_settings.type == '이미지':
                bg_path = bg_settings.value
                if bg_path and os.path.exists(bg_path):
                    image = Image.open(bg_path).convert('RGBA')
                    image = image.resize((width, height))
                else:
                    image = Image.new('RGBA', (width, height), (0, 0, 0, 255))
            else:
                image = Image.new('RGBA', (width, height), (0, 0, 0, 255))
            
            # 텍스트 설정 가져오기
            tab_name = f"{script_type} 설정"
            script_type_settings = self.merged_settings.script_types.get(tab_name)
            if not script_type_settings:
                print(f"⚠️ 스크립트 타입 설정을 찾을 수 없습니다: {tab_name}")
                return False
            
            rows = script_type_settings.rows
            
            if rows:
                row_settings = rows[0]
                font = self._get_font(row_settings.font_name, row_settings.font_size, row_settings.bold)
                
                # 스마트 줄바꿈
                wrapped_lines = self._simple_line_break(text_content, row_settings.w, font)
                wrapped_text = '\n'.join(wrapped_lines)
                
                self.render_text_to_image(
                    image=image,
                    text=wrapped_text,
                    position=(row_settings.x, row_settings.y),
                    font_name=row_settings.font_name,
                    font_size=row_settings.font_size,
                    font_color=row_settings.color,
                    max_width=row_settings.w,
                    align=row_settings.h_align,
                    vertical_align=row_settings.v_align,
                    stroke_width=self.merged_settings.common.border.thick if row_settings.border else 0,
                    stroke_color=self.merged_settings.common.border.color if row_settings.border else "#000000",
                    shadow_offset=(self.merged_settings.common.shadow.offx if row_settings.shadow else 0, self.merged_settings.common.shadow.offy if row_settings.shadow else 0),
                    shadow_color=self.merged_settings.common.shadow.color if row_settings.shadow else "#000000",
                    background=row_settings.background,
                    bg_color=self.merged_settings.common.bg.color if row_settings.background else "#000000"
                )
            
            # 이미지 저장
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            image.save(output_path, 'PNG')
            print(f"✅ {script_type} 이미지 생성 완료: {os.path.basename(output_path)}")
            
            return True
            
        except Exception as e:
            print(f"❌ {script_type} 이미지 생성 실패: {e}")
            return False
    
    def create_thumbnail_image(self, ai_data: Dict[str, Any], output_path: str,
                              resolution: Tuple[int, int]) -> bool:
        """썸네일 이미지 생성 (AI JSON 파싱, 3세트, 터미널 출력)"""
        try:
            width, height = resolution
            
            # AI 데이터에서 썸네일 문장 추출
            thumbnail_sets = ai_data.get('thumbnail', [])
            if not thumbnail_sets:
                print("⚠️ AI 데이터에 썸네일 정보가 없습니다.")
                return False
            
            # 3세트 생성
            for i, thumbnail_set in enumerate(thumbnail_sets[:3]):
                set_output_path = output_path.replace('.png', f'_set{i+1}.png')
                
                # 배경 이미지 생성
                bg_settings = self.merged_settings.common.bg
                if bg_settings.enabled and bg_settings.type == '이미지':
                    bg_path = bg_settings.value
                    if bg_path and os.path.exists(bg_path):
                        image = Image.open(bg_path).convert('RGBA')
                        image = image.resize((width, height))
                    else:
                        image = Image.new('RGBA', (width, height), (0, 0, 0, 255))
                else:
                    image = Image.new('RGBA', (width, height), (0, 0, 0, 255))
                
                draw = ImageDraw.Draw(image)
                
                # 텍스트 설정 가져오기
                thumbnail_settings = self.merged_settings.script_types.get('썸네일 설정')
                if not thumbnail_settings:
                    print(f"⚠️ 썸네일 설정을 찾을 수 없습니다")
                    continue
                
                rows = thumbnail_settings.rows
                
                # 4줄 텍스트 처리
                for j, row_settings in enumerate(rows[:4]):
                    if j < len(thumbnail_set):
                        text = thumbnail_set[j]
                        
                        # 폰트 크기 자동 조정
                        font_size = row_settings.font_size
                        font = self._get_font(row_settings.font_name, font_size, row_settings.bold)
                        
                        # 텍스트가 너비를 넘으면 폰트 크기 줄이기
                        while font.getlength(text) > row_settings.w and font_size > 10:
                            font_size -= 2
                            font = self._get_font(row_settings.font_name, font_size, row_settings.bold)
                        
                        # 터미널 출력
                        print(f"썸네일 세트 {i+1}, 줄 {j+1}: {text}")
                        
                        self._draw_text_with_effects(
                            draw, text, (row_settings.x, row_settings.y),
                            row_settings, font
                        )
                
                # 이미지 저장
                os.makedirs(os.path.dirname(set_output_path), exist_ok=True)
                image.save(set_output_path, 'PNG')
                print(f"✅ 썸네일 세트 {i+1} 생성 완료: {os.path.basename(set_output_path)}")
            
            return True
            
        except Exception as e:
            print(f"❌ 썸네일 이미지 생성 실패: {e}")
            return False
