import os
import re
from typing import Dict, Any, Optional, Tuple, List
from PIL import Image, ImageDraw, ImageFont
import textwrap
from src import config

class TextRenderer:
    def __init__(self, settings: Dict[str, Any]):
        self.config = self._load_config(settings)
        self.fonts = {}

    def _load_config(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        default_config = {
            "fonts": {
                "Noto Sans KR": os.path.expanduser("~/Library/Fonts/NotoSansKR-Regular.ttf"),
                "KoPubWorld돋움체": os.path.expanduser("~/Library/Fonts/KoPubWorld Dotum Medium.ttf"),
                "KoPubWorld바탕체": os.path.expanduser("~/Library/Fonts/KoPubWorld Batang Medium.ttf")
            }
        }
        self._merge_configs(default_config, settings)
        return default_config

    def _merge_configs(self, base, user):
        for key, value in user.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_configs(base[key], value)
            else:
                base[key] = value

    def _get_font(self, font_name: str, size: int, weight: str = "Regular") -> ImageFont.FreeTypeFont:
        if font_name in self.fonts:
            try:
                return ImageFont.truetype(self.fonts[font_name], size)
            except IOError:
                pass

        font_path = self.config.get("fonts", {}).get(font_name)
        if font_path and os.path.exists(font_path):
            self.fonts[font_name] = font_path
            try:
                return ImageFont.truetype(font_path, size)
            except IOError:
                pass
        
        print(f"⚠️ 폰트 파일을 찾을 수 없습니다:{font_name}. 기본 폰트를 사용합니다.")
        return ImageFont.load_default()

    def _parse_styled_text(self, text: str) -> List[Dict]:
        segments = []
        pattern = r'(\*\*.*?\*\*|\[color=.*?\](.*?)\[/color\]|\[size=.*?\](.*?)\[/size\])'
        parts = re.split(pattern, text)
        
        i = 0
        while i < len(parts):
            part = parts[i]
            if not part:
                i += 1
                continue

            if part.startswith('**') and part.endswith('**'):
                segments.append({'text': part[2:-2], 'bold': True})
                i += 4
            elif part.startswith('[color='):
                color = part.split('=')[1].split(']')[0]
                text_content = parts[i+1]
                segments.append({'text': text_content, 'color': color})
                i += 4 # Move past the color tag and content
            elif part.startswith('[size='):
                size = part.split('=')[1].split(']')[0]
                text_content = parts[i+2]
                segments.append({'text': text_content, 'size': int(size)})
                i += 4 # Move past the size tag and content
            else:
                segments.append({'text': part})
                i += 1
        return segments

    def _get_text_dimensions(self, text: str, font: ImageFont.FreeTypeFont) -> Tuple[int, int]:
        """Calculates the width and height of the given text with the specified font."""
        try:
            # For newer Pillow versions
            bbox = font.getbbox(text)
            return bbox[2] - bbox[0], bbox[3] - bbox[1]
        except AttributeError:
            # For older Pillow versions
            return font.getsize(text)

    def _get_wrapped_text_lines(self, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
        """Wraps text to fit within max_width."""
        if not max_width:
            return [text] # No wrapping if max_width is 0 or None

        lines = []
        words = text.split(' ')
        current_line = []
        for word in words:
            test_line = ' '.join(current_line + [word])
            width, _ = self._get_text_dimensions(test_line, font)
            if width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        if current_line:
            lines.append(' '.join(current_line))
        return lines

    def _smart_wrap(self, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> str:
        print(f"--- Smart wrapping text ---")
        print(f"Input text: {text}")
        print(f"Max width: {max_width}")
        if not max_width:
            return text

        words = text.split(' ')
        lines = []
        current_line = []

        while words:
            word = words.pop(0)
            test_line = ' '.join(current_line + [word])
            width, _ = self._get_text_dimensions(test_line, font)

            if width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        if current_line:
            lines.append(' '.join(current_line))

        if len(lines) > 3:
            lines = lines[:3]

        if len(lines) == 2:
            line1 = lines[0]
            line2 = lines[1]
            if len(line1) > len(line2) * 1.5:
                # Try to balance the lines
                all_words = (line1 + ' ' + line2).split(' ')
                best_split = len(all_words) // 2
                line1 = ' '.join(all_words[:best_split])
                line2 = ' '.join(all_words[best_split:])
                lines = [line1, line2]

        return '\n'.join(lines)

    def render_text_to_image(self,
                             image: Image.Image,
                             text: str,
                             position: Tuple[int, int],
                             font_name: str,
                             font_size: int,
                             font_color: str,
                             max_width: int,
                             align: str = "left",
                             vertical_align: str = "top",
                             stroke_width: int = 0,
                             stroke_color: str = "#000000",
                             shadow_offset: Tuple[int, int] = (0, 0),
                             shadow_color: str = "#000000") -> Image.Image:
        print("--- render_text_to_image called ---")
        """
        Renders text onto an image with various styling and alignment options.
        :param image: PIL Image object to draw on.
        :param text: The text string to render.
        :param position: (x, y) coordinates for the text. Interpretation depends on align and vertical_align.
        :param font_name: Name of the font to use.
        :param font_size: Size of the font.
        :param font_color: Color of the font (e.g., "#FFFFFF").
        :param max_width: Maximum width for text wrapping.
        :param align: Horizontal alignment ("left", "center", "right").
        :param vertical_align: Vertical alignment ("top", "bottom", "center").
        :param stroke_width: Stroke width for text outline.
        :param stroke_color: Color of the text outline.
        :param shadow_offset: (dx, dy) offset for text shadow.
        :param shadow_color: Color of the text shadow.
        :return: The modified PIL Image object.
        """
        print(f"Rendering text with settings: align={align}, vertical_align={vertical_align}, stroke_width={stroke_width}, stroke_color={stroke_color}, shadow_offset={shadow_offset}, shadow_color={shadow_color}")
        draw = ImageDraw.Draw(image)
        font = self._get_font(font_name, font_size)

        wrapped_lines = self._get_wrapped_text_lines(text, font, max_width)

        # Calculate total text height
        total_text_height = 0
        line_heights = []
        for line in wrapped_lines:
            _, h = self._get_text_dimensions(line, font)
            line_heights.append(h)
            total_text_height += h * 1.2 # Add some line spacing

        # Adjust total_text_height for the last line's extra spacing
        if line_heights:
            total_text_height -= line_heights[-1] * 0.2 # Remove extra spacing from last line

        start_x, start_y = position

        # Calculate initial y based on vertical alignment
        if vertical_align == "center":
            start_y -= total_text_height / 2
        elif vertical_align == "bottom":
            start_y -= total_text_height
        # If "top", start_y remains as is

        current_y = start_y
        for line in wrapped_lines:
            line_width, line_height = self._get_text_dimensions(line, font)
            
            # Calculate x position based on horizontal alignment
            text_x = start_x
            if align == "center":
                text_x -= line_width / 2
            elif align == "right":
                text_x -= line_width

            # Render shadow
            if shadow_offset[0] != 0 or shadow_offset[1] != 0:
                draw.text((text_x + shadow_offset[0], current_y + shadow_offset[1]), line, font=font, fill=shadow_color,
                          stroke_width=stroke_width, stroke_fill=stroke_color)

            # Render main text
            draw.text((text_x, current_y), line, font=font, fill=font_color,
                      stroke_width=stroke_width, stroke_fill=stroke_color)
            
            current_y += line_height * 1.2 # Move to next line, with spacing
        
        return image

    def render_styled_text(self, draw: ImageDraw.ImageDraw, text_segments: List[Dict], x: int, y: int, base_settings: Dict):
        current_x = x
        for segment in text_segments:
            text = segment.get("text", "")
            font_name = segment.get("font", base_settings.get("폰트(pt)", "KoPubWorld돋움체"))
            size = int(segment.get("size", base_settings.get("크기(pt)", 48)))
            color = segment.get("color", base_settings.get("색상", "#FFFFFF"))
            weight = "Bold" if segment.get("bold") else "Regular"

            font = self._get_font(font_name, size, weight)
            draw.text((current_x, y), text, font=font, fill=color)
            try:
                current_x += draw.textbbox((0,0), text, font=font)[2]
            except:
                current_x += draw.textsize(text, font=font)[0]

    # The original render_multiline_text seems to be a more specific case of what render_text_to_image will do.
    # I will keep it for now, but it might be refactored or removed later if render_text_to_image covers all its use cases.
    def render_multiline_text(self, draw: ImageDraw.ImageDraw, lines: List[str], x: int, y: int, width: int, line_settings: List[Dict]):
        current_y = y
        for i, line in enumerate(lines):
            settings = line_settings[i] if i < len(line_settings) else {}
            font_name = settings.get("폰트(pt)", "KoPubWorld돋움체")
            size = int(settings.get("크기(pt)", 48))
            font = self._get_font(font_name, size)

            wrapped_lines = textwrap.wrap(line, width=int(width / (size * 0.5)), break_long_words=True, replace_whitespace=False)

            for wrapped_line in wrapped_lines:
                segments = self._parse_styled_text(wrapped_line)
                self.render_styled_text(draw, segments, x, current_y, settings)
                try:
                    line_height = font.getbbox("A")[3] - font.getbbox("A")[1]
                except:
                    line_height = font.getsize("A")[1]
                current_y += line_height * 1.2

    def save_image(self, image: Image.Image, output_path: str, format: str = "PNG"):
        """이미지 저장"""
        try:
            image.save(output_path, format)
            return True
        except Exception as e:
            print(f"❌ 이미지 저장 실패: {e}")
            return False