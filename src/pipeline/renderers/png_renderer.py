"""
PNG 직접 렌더링 시스템 (v11 - 최종 안정화 버전)

- Scene 기반 통합 렌더링 파이프라인 적용
- 텍스트 좌표, 행간, 색상 처리, 폰트 굵기 등 모든 렌더링 문제 수정
- 회화 장면의 분리된 바탕 박스 문제 해결
- 상세 디버그 로그 및 안정적인 예외 처리 포함
"""
import os
import json
import traceback
import threading
from typing import Dict, Any, List, Tuple
from PIL import Image, ImageDraw, ImageFont

print("\n\n✅✅✅ png_renderer.py 파일이 성공적으로 로드되었습니다! (v11) ✅✅✅\n\n")

try:
    from ..settings import MergedSettings, RowSettings
except ImportError:
    MergedSettings, RowSettings = dict, dict

class PNGRenderer:
    print("DEBUG_RAW: PNGRenderer class definition loaded. Version 20250924.1")
    def __init__(self, merged_settings: MergedSettings):
        print("🚀 [진단] PNGRenderer 클래스 초기화 시작...")
        self.merged_settings = merged_settings
        self.fonts = {}
        self._load_fonts()
        self._font_cache = {}
        self._lock = threading.Lock()
        print("✅ [진단] PNGRenderer 초기화 성공!")

    def _load_fonts(self):
        try:
            config_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'config.json')
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            font_paths = config_data.get("fonts", {})
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"⚠️ config.json에서 폰트 설정을 불러오는 데 실패했습니다: {e}. 하드코딩된 기본값을 사용합니다.")
            font_paths = {
                "Noto Sans KR": "~/Library/Fonts/NotoSansKR-Regular.ttf",
                "KoPubWorld돋움체": "~/Library/Fonts/KoPubWorld Dotum Medium.ttf",
                "Arial": "/System/Library/Fonts/Arial.ttf",
                "Helvetica": "/System/Library/Fonts/Helvetica.ttc",
                "AppleGothic": "/System/Library/Fonts/AppleGothic.ttf",
            }

        for name, path in font_paths.items():
            exp_path = os.path.expanduser(path)
            if os.path.exists(exp_path): 
                self.fonts[name] = exp_path
                print(f"✅ 폰트 로드 성공: {name} -> {exp_path}")
            else:
                print(f"⚠️ 폰트 파일 없음: {name} -> {exp_path}")
        
        # 폰트가 하나도 없으면 기본 폰트 사용
        if not self.fonts:
            print("⚠️ 사용 가능한 폰트가 없습니다. 기본 폰트를 사용합니다.")
            self.fonts["Default"] = "Default"

    def _get_font(self, font_name: str, size: int) -> ImageFont.FreeTypeFont:
        cache_key = f"{font_name}_{size}"
        with self._lock:
            if cache_key in self._font_cache:
                return self._font_cache[cache_key]
        
        try:
            font_path = self.fonts.get(font_name)
            print(f"🔍 폰트 요청: {font_name} ({size}pt) -> {font_path}")
            
            if font_path and os.path.exists(font_path):
                font = ImageFont.truetype(font_path, size)
                with self._lock: self._font_cache[cache_key] = font
                print(f"✅ 폰트 로드 성공: {font_name} ({size}pt)")
                return font
            else:
                print(f"⚠️ 폰트 파일 없음, 기본 폰트 사용: {font_name}")
        except Exception as e:
            print(f"❌ 폰트 로딩 실패: {e}")
        
        default_font = ImageFont.load_default()
        print(f"🔄 기본 폰트 사용: {font_name}")
        with self._lock: self._font_cache[cache_key] = default_font
        return default_font

    def _parse_color(self, color_str: str, alpha_override: float = None) -> Tuple[int, int, int, int]:
        color_str = str(color_str).strip().lstrip('#')
        try:
            if len(color_str) == 6: r, g, b = (int(color_str[i:i+2], 16) for i in (0, 2, 4)); a = 255
            elif len(color_str) == 8: r, g, b, a = (int(color_str[i:i+2], 16) for i in (0, 2, 4, 6))
            else: r, g, b, a = 255, 255, 255, 255
            if alpha_override is not None: a = int(255 * alpha_override)
            return r, g, b, a
        except (ValueError, TypeError): return 255, 255, 255, 255

    def _smart_line_break(self, text: str, max_width: int, font: ImageFont.FreeTypeFont) -> List[str]:
        if not text: return []
        lines = []
        for raw_line in text.split('\n'):
            words = raw_line.split()
            if not words: continue
            current_line = ""
            for word in words:
                test_line = f"{current_line} {word}".strip()
                if font.getbbox(test_line)[2] <= max_width:
                    current_line = test_line
                else:
                    if current_line: lines.append(current_line)
                    current_line = word
            if current_line: lines.append(current_line)
        return lines if lines else [text]

    def _create_base_image(self, resolution: Tuple[int, int], tab_name: str) -> Image.Image:
        width, height = resolution
        
        # UI 데이터 구조에서 배경 설정 가져오기 (main_background)
        # 현재 탭의 배경 설정을 직접 찾기
        current_tab_settings = self.merged_settings.get(tab_name, {})
        bg_settings = current_tab_settings.get('main_background', {})
        
        bg_type = bg_settings.get('type', '색상')
        bg_value = bg_settings.get('value', '#000000')

        if bg_type == '이미지' and bg_value:
            path = os.path.expanduser(bg_value)
            if os.path.exists(path):
                try:
                    img = Image.open(path).convert('RGBA').resize((width, height), Image.Resampling.LANCZOS)
                    return img
                except Exception as e:
                    print(f"🔥🔥🔥 [오류] 배경 이미지 파일을 여는 데 실패했습니다: {path}")
                    print(f"  - 오류: {e}")
                    pass
        
        color = self._parse_color(bg_value)
        return Image.new('RGBA', (width, height), color)

    def render_scene(self, image: Image.Image, scenes: List[Dict[str, Any]], tab_name: str = 'conversation') -> Image.Image:
        all_positions = []
        # 1. 모든 텍스트의 위치부터 계산
        for scene in scenes:
            settings = scene['settings']
            text = str(scene.get('text', ''))

            # 괄호가 있으면 줄바꿈 처리
            processed_text = text.replace('(', '\n(')

            font = self._get_font(str(settings.get('폰트(pt)')), int(settings.get('크기(pt)', 90)))
            lines = self._smart_line_break(processed_text, int(settings.get('w', 1820)), font)
            if not lines: continue

            # 현재 탭의 행간비 설정 가져오기
            current_tab_settings = self.merged_settings.get(tab_name, {})
            line_spacing_ratio = float(current_tab_settings.get('line_spacing', {}).get('ratio', '1.1'))
            
            # 각 라인의 높이를 폰트 크기에 따라 계산
            line_heights = []
            for line in lines:
                is_paren_line = line.strip().startswith('(') and line.strip().endswith(')')
                font_size = int(settings.get('크기(pt)', 90))
                if is_paren_line:
                    font_size = int(font_size * 0.8) # 20% 축소
                line_font = self._get_font(str(settings.get('폰트(pt)')), font_size)
                ascent, descent = line_font.getmetrics()
                line_heights.append(ascent + descent)

            total_h = sum(line_heights) + (line_spacing_ratio - 1) * sum(line_heights[:-1]) if len(line_heights) > 1 else sum(line_heights)

            original_y = int(settings.get('y', 0))
            v_align = str(settings.get('상하 정렬', 'Top')).lower()
            
            y = original_y
            if v_align == "center": y -= total_h / 2
            elif v_align == "bottom": y -= total_h
            
            for i, line in enumerate(lines):
                is_paren_line = line.strip().startswith('(') and line.strip().endswith(')')
                line_to_draw = line # 괄호를 포함하여 그림
                
                line_settings = settings.copy()
                if is_paren_line:
                    original_size = int(line_settings.get('크기(pt)', 90))
                    line_settings['크기(pt)'] = int(original_size * 0.8) # 20% 축소

                font = self._get_font(str(line_settings.get('폰트(pt)')), int(line_settings.get('크기(pt)', 90)))
                bbox = font.getbbox(line_to_draw)
                line_w = bbox[2] - bbox[0]
                text_render_y = y 
                
                x = int(settings.get('x', 0))
                h_align = str(settings.get('좌우 정렬', 'Left')).lower()
                container_w = int(settings.get('w', 1820))
                if h_align == "center": x += (container_w - line_w) / 2
                elif h_align == "right": x += container_w - line_w
                
                all_positions.append({
                    'line': line_to_draw, 'font': font, 'settings': line_settings, 'x': x,
                    'y': text_render_y, 'w': line_w, 'h': line_heights[i]
                })
                y += line_heights[i] * line_spacing_ratio

        # 2. 바탕 박스 그리기 (텍스트보다 먼저)
        current_tab_settings = self.merged_settings.get(tab_name, {})
        bg_box_cfg = current_tab_settings.get('background_box', {})
        bg_box_type = bg_box_cfg.get('type', '없음')
        
        positions_with_bg = [p for p in all_positions if p['settings'].get('바탕')]

        if bg_box_type != '없음' and positions_with_bg:
            bg_layer = Image.new('RGBA', image.size, (0, 0, 0, 0))
            bg_draw = ImageDraw.Draw(bg_layer)
            margin = int(bg_box_cfg.get('margin', 2))
            bg_color = self._parse_color(bg_box_cfg.get('color', '#000000'), float(bg_box_cfg.get('alpha', 0.2)))

            if bg_box_type == '블록':
                if positions_with_bg:
                    min_x = min(p['x'] for p in positions_with_bg) - margin
                    max_x = max(p['x'] + p['w'] for p in positions_with_bg) + margin
                    min_y = min(p['y'] for p in positions_with_bg) - margin
                    max_y = max(p['y'] + p['h'] for p in positions_with_bg) + margin
                    bg_draw.rectangle((min_x, min_y, max_x, max_y), fill=bg_color)
            else: # 텍스트 또는 전체
                for pos in positions_with_bg:
                    if bg_box_type == '텍스트':
                        rect_coords = (pos['x'] - margin, pos['y'] - margin, pos['x'] + pos['w'] + margin, pos['y'] + pos['h'] + margin)
                        bg_draw.rectangle(rect_coords, fill=bg_color)
                    elif bg_box_type == '전체':
                        rect_coords = (0, pos['y'] - margin, image.width, pos['y'] + pos['h'] + margin)
                        bg_draw.rectangle(rect_coords, fill=bg_color)
            
            image = Image.alpha_composite(image, bg_layer)

        # 3. 텍스트 그리기
        draw = ImageDraw.Draw(image)
        for pos in all_positions:
            x, y, line, font, settings = pos['x'], pos['y'], pos['line'], pos['font'], pos['settings']
            
            if settings.get('쉐도우'):
                current_tab_settings = self.merged_settings.get(tab_name, {})
                shadow_cfg = current_tab_settings.get('shadow', {})
                shadow_color = self._parse_color(shadow_cfg.get('color'), float(shadow_cfg.get('alpha', 0.5)))
                sx = x + int(shadow_cfg.get('offx', 2)); sy = y + int(shadow_cfg.get('offy', 2))
                draw.text((sx, sy), line, font=font, fill=shadow_color)

            if settings.get('외곽선'):
                current_tab_settings = self.merged_settings.get(tab_name, {})
                border_cfg = current_tab_settings.get('border', {})
                border_color = self._parse_color(border_cfg.get('color'))
                thick = int(border_cfg.get('thick', 2))
                for dx in range(-thick, thick + 1):
                    for dy in range(-thick, thick + 1):
                        if dx != 0 or dy != 0: draw.text((x + dx, y + dy), line, font=font, fill=border_color)

            text_color = str(settings.get('색상', '#FFFFFF'))
            draw.text((x, y), line, font=font, fill=text_color)
            
        return image



    def render_image(self, scenes: List[Dict[str, Any]], output_path: str, resolution: Tuple[int, int], tab_name: str) -> bool:
        """
        범용 이미지 렌더링 함수.
        주어진 scenes 데이터를 기반으로 이미지를 생성하고 저장합니다.
        """
        
        try:
            # 실제 이미지 렌더링 로직
            image = self._create_base_image(resolution, tab_name)
            image = self.render_scene(image, scenes, tab_name)
            
            # 이미지 저장
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            image.save(output_path, 'PNG')
            
            return True
        except Exception as e:
            print(f"\n🔥🔥🔥 [오류] 범용 이미지 생성 중 심각한 오류 발생! ({os.path.basename(output_path)})")
            traceback.print_exc()
            return False

    def get_current_settings(self):
        """현재 설정 정보를 반환하는 메서드"""
        try:
            return {
                'common_settings': getattr(self, 'common_settings', {}),
                'tab_settings': getattr(self, 'tab_settings', {}),
                'loaded_fonts': list(self.loaded_fonts.keys()) if hasattr(self, 'loaded_fonts') else []
            }
        except Exception as e:
            print(f"❌ [오류] 설정 정보 조회 실패: {e}")
            return {
                'common_settings': {},
                'tab_settings': {},
                'loaded_fonts': []
            }