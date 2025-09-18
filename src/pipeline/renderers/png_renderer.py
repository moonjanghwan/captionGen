"""
PNG 직접 렌더링 시스템 (v11 - 최종 안정화 버전)

- Scene 기반 통합 렌더링 파이프라인 적용
- 텍스트 좌표, 행간, 색상 처리, 폰트 굵기 등 모든 렌더링 문제 수정
- 회화 장면의 분리된 바탕 박스 문제 해결
- 상세 디버그 로그 및 안정적인 예외 처리 포함
"""
import os
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
    def __init__(self, merged_settings: MergedSettings):
        print("🚀 [진단] PNGRenderer 클래스 초기화 시작...")
        self.merged_settings = merged_settings
        self.fonts = {}
        self._load_fonts()
        self._font_cache = {}
        self._lock = threading.Lock()
        print("✅ [진단] PNGRenderer 초기화 성공!")

    def _load_fonts(self):
        font_paths = {
            "Noto Sans KR": "~/Library/Fonts/NotoSansKR-Regular.ttf",
            "KoPubWorld돋움체": "~/Library/Fonts/KoPubWorld Dotum Medium.ttf",
        }
        for name, path in font_paths.items():
            exp_path = os.path.expanduser(path)
            if os.path.exists(exp_path): self.fonts[name] = exp_path

    def _get_font(self, font_name: str, size: int, weight: str = "Regular") -> ImageFont.FreeTypeFont:
        cache_key = f"{font_name}_{size}_{weight}"
        with self._lock:
            if cache_key in self._font_cache:
                return self._font_cache[cache_key]
        try:
            font_path = self.fonts.get(font_name, "Default")
            if font_path != "Default" and os.path.exists(font_path):
                if weight.lower() == "bold":
                    if "KoPubWorld Dotum" in font_path:
                        bold_path = font_path.replace("Medium", "Bold")
                        if os.path.exists(bold_path): font_path = bold_path
                    elif "NotoSansKR" in font_path:
                         bold_path = font_path.replace("Regular", "Bold")
                         if os.path.exists(bold_path): font_path = bold_path
                
                font = ImageFont.truetype(font_path, size)
                with self._lock: self._font_cache[cache_key] = font
                return font
        except Exception as e:
            print(f"❌ 폰트 로딩 실패: {e}")
        return ImageFont.load_default()

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
        bg_settings = self.merged_settings.get('common', {}).get('tab_backgrounds', {}).get(tab_name, {})
        if not bg_settings or not bg_settings.get('enabled'):
            bg_settings = self.merged_settings.get('common', {}).get('bg', {})
        
        if bg_settings.get('enabled') and bg_settings.get('type') == '이미지' and bg_settings.get('value'):
            path = os.path.expanduser(bg_settings['value'])
            if os.path.exists(path):
                try:
                    return Image.open(path).convert('RGBA').resize((width, height), Image.Resampling.LANCZOS)
                except Exception as e: print(f"⚠️ 배경 이미지 로드 실패: {e}")
        
        color = self._parse_color(bg_settings.get('color', '#000000'))
        return Image.new('RGBA', (width, height), color)

    def render_scene(self, image: Image.Image, scenes: List[Dict[str, Any]]) -> Image.Image:
        all_positions = []
        has_background = any(str(scene.get('settings', {}).get('바탕')).lower() == 'true' for scene in scenes)

        for scene in scenes:
            settings = scene['settings']
            font_weight = str(settings.get('굵기', 'Regular'))
            font = self._get_font(str(settings.get('폰트(pt)')), int(settings.get('크기(pt)', 90)), font_weight)
            lines = self._smart_line_break(str(scene.get('text', '')), int(settings.get('w', 1820)), font)
            if not lines: continue

            ascent, descent = font.getmetrics()
            line_height = ascent + descent
            line_spacing_ratio = float(self.merged_settings.get('common', {}).get('line_spacing', {}).get('ratio', '1.1'))
            line_spacing = line_height * line_spacing_ratio

            total_h = line_height * len(lines) + (line_spacing - line_height) * (len(lines) - 1)

            original_y = int(settings.get('y', 0))
            v_align = str(settings.get('상하 정렬', 'Top')).lower()
            
            y = original_y
            if v_align == "center":
                y = original_y - total_h / 2
            elif v_align == "bottom":
                y = original_y - total_h
            
            for line in lines:
                bbox = font.getbbox(line)
                line_w = bbox[2] - bbox[0]
                text_render_y = y 
                
                x = int(settings.get('x', 0))
                h_align = str(settings.get('좌우 정렬', 'Left')).lower()
                container_w = int(settings.get('w', 1820))
                if h_align == "center": x += (container_w - line_w) / 2
                elif h_align == "right": x += container_w - line_w
                
                all_positions.append({
                    'line': line, 'font': font, 'settings': settings, 'x': x,
                    'y': text_render_y, 'w': line_w, 'h': line_height
                })
                y += line_spacing

        if has_background and all_positions:
            bg_cfg = self.merged_settings.get('common', {}).get('bg', {})
            margin = int(bg_cfg.get('margin', 5))
            min_x = min(p['x'] for p in all_positions) - margin
            max_x = max(p['x'] + p['w'] for p in all_positions) + margin
            min_y = min(p['y'] for p in all_positions) - margin
            max_y = max(p['y'] + p['h'] for p in all_positions) + margin
            
            bg_color = self._parse_color(bg_cfg.get('color', '#333333'), float(bg_cfg.get('alpha', 0.5)))
            
            bg_layer = Image.new('RGBA', image.size, (0, 0, 0, 0))
            ImageDraw.Draw(bg_layer).rectangle((min_x, min_y, max_x, max_y), fill=bg_color)
            image = Image.alpha_composite(image, bg_layer)

        draw = ImageDraw.Draw(image)
        for pos in all_positions:
            x, y, line, font, settings = pos['x'], pos['y'], pos['line'], pos['font'], pos['settings']
            
            if str(settings.get('쉐도우')).lower() == 'true':
                shadow_cfg = self.merged_settings.get('common', {}).get('shadow', {})
                shadow_color = self._parse_color(shadow_cfg.get('color'), float(shadow_cfg.get('alpha', 0.5)))
                sx = x + int(shadow_cfg.get('offx', 2)); sy = y + int(shadow_cfg.get('offy', 2))
                draw.text((sx, sy), line, font=font, fill=shadow_color)

            if str(settings.get('외곽선')).lower() == 'true':
                border_cfg = self.merged_settings.get('common', {}).get('border', {})
                border_color = self._parse_color(border_cfg.get('color'))
                thick = int(border_cfg.get('thick', 2))
                for dx in range(-thick, thick + 1):
                    for dy in range(-thick, thick + 1):
                        if dx != 0 or dy != 0: draw.text((x + dx, y + dy), line, font=font, fill=border_color)

            text_color = str(settings.get('색상', '#FFFFFF'))
            draw.text((x, y), line, font=font, fill=text_color)
            
        return image

    def create_intro_ending_image(self, text: str, output_path: str, resolution: Tuple[int, int], script_type: str) -> bool:
        print(f"🚀 [진단] create_intro_ending_image 호출됨! (타입: {script_type})")
        try:
            tab_name = f"{script_type} 설정"
            settings_tab = self.merged_settings.get('tabs', {}).get(tab_name)
            if not settings_tab:
                print(f"🔥🔥🔥 [오류] '{tab_name}' 설정을 찾을 수 없습니다!")
                return False
                
            scene = [{'text': text, 'settings': settings_tab['rows'][0]}]
            image = self._create_base_image(resolution, tab_name)
            image = self.render_scene(image, scene)
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            image.save(output_path, 'PNG')
            print(f"✅ [성공] {script_type} 이미지 생성 완료: {os.path.basename(output_path)}")
            return True
        except Exception as e:
            print(f"\n🔥🔥🔥 [오류] 이미지 생성 중 심각한 오류 발생!")
            traceback.print_exc()
            return False

    def create_conversation_image(self, conversation_data: dict, output_dir: str, resolution: Tuple[int, int], base_filename: str) -> List[str]:
        print(f"🎨 [회화 이미지 생성] 시작: {base_filename}")
        try:
            tab_name = "회화 설정"
            settings_tab = self.merged_settings.get('tabs', {}).get(tab_name)
            if not settings_tab or not settings_tab.get('rows'):
                print(f"❌ [오류] '{tab_name}' 설정을 찾을 수 없습니다!")
                return []
            
            rows = settings_tab.get('rows', [])
            created_files = []
            
            # 화면 1: 순번, 원어 - 각 씬을 개별적으로 처리
            if len(rows) >= 2:
                screen1_scenes = [
                    {'text': str(conversation_data.get('sequence', '')), 'settings': rows[0]},
                    {'text': conversation_data.get('native_script', ''), 'settings': rows[1]},
                ]
                screen1_path = os.path.join(output_dir, f"{base_filename}_screen1.png")
                print(f"🖼️ [화면 1] 순번+원어 이미지 생성: {screen1_path}")
                
                image1 = self._create_base_image(resolution, tab_name)
                
                # 각 씬을 개별적으로 처리 (인트로/엔딩 방식)
                for scene in screen1_scenes:
                    single_scene = [scene]  # 단일 씬으로 래핑
                    image1 = self.render_scene(image1, single_scene)
                
                os.makedirs(os.path.dirname(screen1_path), exist_ok=True)
                image1.save(screen1_path, 'PNG')
                created_files.append(screen1_path)
                print(f"✅ [화면 1] 생성 완료: {os.path.basename(screen1_path)}")

            # 화면 2: 전체 - 각 씬을 개별적으로 처리
            if len(rows) >= 4:
                screen2_scenes = [
                    {'text': str(conversation_data.get('sequence', '')), 'settings': rows[0]},
                    {'text': conversation_data.get('native_script', ''), 'settings': rows[1]},
                    {'text': conversation_data.get('learning_script', ''), 'settings': rows[2]},
                    {'text': conversation_data.get('reading_script', ''), 'settings': rows[3]},
                ]
                screen2_path = os.path.join(output_dir, f"{base_filename}_screen2.png")
                print(f"🖼️ [화면 2] 순번+원어+학습어+읽기 이미지 생성: {screen2_path}")
                
                image2 = self._create_base_image(resolution, tab_name)
                
                # 각 씬을 개별적으로 처리 (인트로/엔딩 방식)
                for scene in screen2_scenes:
                    single_scene = [scene]  # 단일 씬으로 래핑
                    image2 = self.render_scene(image2, single_scene)
                
                os.makedirs(os.path.dirname(screen2_path), exist_ok=True)
                image2.save(screen2_path, 'PNG')
                created_files.append(screen2_path)
                print(f"✅ [화면 2] 생성 완료: {os.path.basename(screen2_path)}")
            
            print(f"✅ [성공] 회화 이미지 생성 완료: 총 {len(created_files)}개 파일")
            return created_files
            
        except Exception as e:
            print(f"❌ [오류] 회화 이미지 생성 실패: {e}")
            traceback.print_exc()
            return []
    
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