"""
PNG 직접 렌더링 시스템 (v10 - 최종 좌표 및 행간 수정)

- 텍스트 Y 좌표 계산 로직을 단순화하여 바탕 박스와의 위치 불일치 문제 해결
- 행간(line_spacing) 값을 조정하여 자연스러운 줄 간격으로 수정
- 상세 디버그 로그 유지
"""
import os
import traceback
import threading
from typing import Dict, Any, List, Tuple
from PIL import Image, ImageDraw, ImageFont

print("\n\n✅✅✅ png_renderer.py 파일이 성공적으로 로드되었습니다! (v10) ✅✅✅\n\n")

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
            # 🔥🔥🔥 [폰트 굵기 지원] Bold 폰트 로딩 로직 추가 🔥🔥🔥
            font_path = self.fonts.get(font_name, "Default")
            if font_path != "Default" and os.path.exists(font_path):
                # Bold 폰트 파일 경로 생성 시도
                if weight.lower() == "bold":
                    # KoPubWorld돋움체의 경우 Bold 버전 시도
                    if "KoPubWorld돋움체" in font_name:
                        bold_path = font_path.replace("KoPubWorld Dotum Medium.ttf", "KoPubWorld Dotum Bold.ttf")
                        if os.path.exists(bold_path):
                            font_path = bold_path
                            print(f"✅ [폰트] Bold 폰트 로드: {bold_path}")
                        else:
                            print(f"⚠️ [폰트] Bold 폰트 파일을 찾을 수 없음: {bold_path}")
                    # Noto Sans KR의 경우 Bold 버전 시도
                    elif "Noto Sans KR" in font_name:
                        bold_path = font_path.replace("NotoSansKR-Regular.ttf", "NotoSansKR-Bold.ttf")
                        if os.path.exists(bold_path):
                            font_path = bold_path
                            print(f"✅ [폰트] Bold 폰트 로드: {bold_path}")
                        else:
                            print(f"⚠️ [폰트] Bold 폰트 파일을 찾을 수 없음: {bold_path}")
                
                font = ImageFont.truetype(font_path, size)
                with self._lock: self._font_cache[cache_key] = font
                print(f"✅ [폰트] 폰트 로드 성공: {font_name} {size}pt {weight}")
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
        has_background = any(scene.get('settings', {}).get('바탕') == 'True' for scene in scenes)

        for scene in scenes:
            settings = scene['settings']
            # 🔥🔥🔥 [하드코딩 제거] 설정값에서 폰트 크기와 너비 가져오기 🔥🔥🔥
            default_font_size = int(self.merged_settings.get('common', {}).get('default_font_size', 90))
            default_width = int(self.merged_settings.get('common', {}).get('default_width', 1820))
            
            # 🔥🔥🔥 [폰트 굵기 적용] 설정에서 굵기 정보를 가져와서 폰트 로드 🔥🔥🔥
            font_name = str(settings.get('폰트(pt)'))
            font_size = int(settings.get('크기(pt)', default_font_size))
            font_weight = str(settings.get('굵기', 'Regular'))
            font = self._get_font(font_name, font_size, font_weight)
            lines = self._smart_line_break(str(scene.get('text', '')), int(settings.get('w', default_width)), font)
            if not lines: continue

            # --- [핵심 수정 1] 행간(line_spacing) 값 조정 ---
            ascent, descent = font.getmetrics()
            line_height = ascent + descent
            # 🔥🔥🔥 [하드코딩 제거] 설정값에서 행간 비율 가져오기 🔥🔥🔥
            line_spacing_ratio = float(self.merged_settings.get('common', {}).get('line_spacing', {}).get('ratio', '1.2'))
            line_spacing = line_height * line_spacing_ratio

            total_h = line_height * len(lines) + (line_spacing - line_height) * (len(lines) - 1)

            original_y = int(settings.get('y', 0))
            v_align = str(settings.get('상하 정렬', 'Top')).lower()
            
            print(f"📐 [정렬 설정] 상하정렬: {v_align}, 원본 Y: {original_y}, 텍스트 높이: {total_h:.2f}")
            
            y = original_y
            if v_align == "center":
                y = original_y - total_h / 2
                print(f"   -> 중앙 정렬: {original_y} - {total_h:.2f}/2 = {y:.2f}")
            elif v_align == "bottom":
                y = original_y - total_h
                print(f"   -> 하단 정렬: {original_y} - {total_h:.2f} = {y:.2f}")
            else:
                print(f"   -> 상단 정렬: Y = {y} 유지")
            
            # --- [핵심 수정 2] 텍스트 렌더링 Y 좌표 계산 방식 변경 ---
            for line in lines:
                bbox = font.getbbox(line)
                line_w = bbox[2] - bbox[0]
                
                # Pillow는 텍스트를 그릴 때 y좌표를 상단 기준으로 삼으므로 ascent를 더할 필요가 없습니다.
                # 이 부분이 텍스트를 아래로 밀리게 한 원인입니다.
                text_render_y = y 
                
                x = int(settings.get('x', 0))
                h_align = str(settings.get('좌우 정렬', 'Left')).lower()
                # 🔥🔥🔥 [하드코딩 제거] 설정값에서 기본 너비 가져오기 🔥🔥🔥
                default_width = int(self.merged_settings.get('common', {}).get('default_width', 1820))
                line_width = int(settings.get('w', default_width))
                
                print(f"📐 [좌우 정렬] 정렬: {h_align}, 원본 X: {x}, 라인 너비: {line_w:.2f}, 컨테이너 너비: {line_width}")
                
                if h_align == "center": 
                    x += (line_width - line_w) / 2
                    print(f"   -> 중앙 정렬: {x:.2f}")
                elif h_align == "right": 
                    x += line_width - line_w
                    print(f"   -> 우측 정렬: {x:.2f}")
                else:
                    print(f"   -> 좌측 정렬: X = {x} 유지")
                
                # 🔥🔥🔥 [폰트 메트릭 추가] 바탕 박스 계산을 위한 정확한 텍스트 위치 계산 🔥🔥🔥
                ascent, descent = font.getmetrics()
                all_positions.append({
                    'line': line, 'font': font, 'settings': settings, 'x': x,
                    'y': text_render_y, 'w': line_w, 'h': line_height,
                    'ascent': ascent, 'descent': descent,  # 폰트 메트릭 추가
                    'text_top': text_render_y - ascent,    # 텍스트 상단 위치
                    'text_bottom': text_render_y + descent # 텍스트 하단 위치
                })
                y += line_spacing

        # 🔥🔥🔥 [라인별 개별 바탕 박스] 각 라인마다 개별적인 바탕 박스 생성 🔥🔥🔥
        if has_background and all_positions:
            bg_cfg = self.merged_settings.get('common', {}).get('bg', {})
            # 🔥🔥🔥 [하드코딩 제거] 설정값에서 기본 마진 가져오기 🔥🔥🔥
            default_margin = int(self.merged_settings.get('common', {}).get('default_margin', 5))
            margin = int(bg_cfg.get('margin', default_margin))
            
            # 🔥🔥🔥 [하드코딩 제거] 설정값에서 기본 배경 색상과 투명도 가져오기 🔥🔥🔥
            default_bg_color = self.merged_settings.get('common', {}).get('default_bg_color', '#333333')
            default_bg_alpha = float(self.merged_settings.get('common', {}).get('default_bg_alpha', 0.5))
            bg_color = self._parse_color(bg_cfg.get('color', default_bg_color), float(bg_cfg.get('alpha', default_bg_alpha)))
            
            bg_layer = Image.new('RGBA', image.size, (0, 0, 0, 0))
            bg_draw = ImageDraw.Draw(bg_layer)
            
            # 각 라인별로 개별 바탕 박스 생성
            for pos in all_positions:
                if pos['settings'].get('바탕') == 'True':
                    x, y, w, h = pos['x'], pos['y'], pos['w'], pos['h']
                    
                    # 폰트 메트릭을 사용하여 정확한 텍스트 높이 계산
                    font = pos['font']
                    ascent, descent = font.getmetrics()
                    
                    # 텍스트의 실제 상단과 하단 위치 계산
                    text_top = y - ascent
                    text_bottom = y + descent
                    
                    # 🔥🔥🔥 [디버깅] 텍스트 위치 정보 상세 로깅 🔥🔥🔥
                    print(f"🔍 [디버깅] 텍스트: '{pos['line'][:20]}...'")
                    print(f"   - 렌더링 Y: {y}")
                    print(f"   - 폰트 ascent: {ascent}, descent: {descent}")
                    print(f"   - 계산된 text_top: {text_top}, text_bottom: {text_bottom}")
                    print(f"   - pos['text_top']: {pos.get('text_top', 'N/A')}, pos['text_bottom']: {pos.get('text_bottom', 'N/A')}")
                    
                    # 🔥🔥🔥 [정확한 바탕 박스 계산] 계산된 text_top과 text_bottom 사용 🔥🔥🔥
                    line_min_x = x - margin
                    line_max_x = x + w + margin
                    line_min_y = text_top - margin
                    line_max_y = text_bottom + margin
                    
                    print(f"🎨 [라인별 바탕 박스] '{pos['line'][:20]}...' -> ({line_min_x:.1f}, {line_min_y:.1f}, {line_max_x:.1f}, {line_max_y:.1f})")
                    
                    # 개별 라인 바탕 박스 그리기
                    bg_draw.rectangle((line_min_x, line_min_y, line_max_x, line_max_y), fill=bg_color)
            
            image = Image.alpha_composite(image, bg_layer)

        draw = ImageDraw.Draw(image)
        for pos in all_positions:
            x, y, line, font, settings = pos['x'], pos['y'], pos['line'], pos['font'], pos['settings']
            
            if settings.get('쉐도우') == 'True':
                shadow_cfg = self.merged_settings.get('common', {}).get('shadow', {})
                shadow_color = self._parse_color(shadow_cfg.get('color'), float(shadow_cfg.get('alpha')))
                # 🔥🔥🔥 [하드코딩 제거] 설정값에서 기본 그림자 오프셋 가져오기 🔥🔥🔥
                default_shadow_offx = int(self.merged_settings.get('common', {}).get('default_shadow_offx', 2))
                default_shadow_offy = int(self.merged_settings.get('common', {}).get('default_shadow_offy', 2))
                sx = x + int(shadow_cfg.get('offx', default_shadow_offx)); sy = y + int(shadow_cfg.get('offy', default_shadow_offy))
                draw.text((sx, sy), line, font=font, fill=shadow_color)

            if settings.get('외곽선') == 'True':
                border_cfg = self.merged_settings.get('common', {}).get('border', {})
                border_color = self._parse_color(border_cfg.get('color'))
                # 🔥🔥🔥 [하드코딩 제거] 설정값에서 기본 외곽선 두께 가져오기 🔥🔥🔥
                default_border_thick = int(self.merged_settings.get('common', {}).get('default_border_thick', 2))
                thick = int(border_cfg.get('thick', default_border_thick))
                for dx in range(-thick, thick + 1):
                    for dy in range(-thick, thick + 1):
                        if dx != 0 or dy != 0: draw.text((x + dx, y + dy), line, font=font, fill=border_color)

            # 🔥🔥🔥 [텍스트 색상 적용] 설정에서 색상 정보를 가져와서 RGB 튜플로 변환 🔥🔥🔥
            text_color_str = str(settings.get('색상', '#FFFFFF'))
            text_color = self._parse_color(text_color_str)
            print(f"🎨 [텍스트 색상] '{line[:20]}...' -> {text_color_str} -> {text_color}")
            draw.text((x, y), line, font=font, fill=text_color)
            
        return image

    def create_intro_ending_image(self, text: str, output_path: str, resolution: Tuple[int, int], script_type: str) -> bool:
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
    
    def create_conversation_image(self, conversation_data: dict, output_dir: str, resolution: Tuple[int, int], script_type: str = "회화", base_filename: str = None) -> List[str]:
        """회화 이미지 생성 메서드 - 각 행별로 2개의 화면 생성"""
        print(f"🎨 [회화 이미지 생성] {script_type} 이미지 생성 시작")
        print(f"   - 대화 데이터: {conversation_data}")
        print(f"   - 출력 디렉토리: '{output_dir}'")
        print(f"   - 해상도: {resolution}")
        
        try:
            # 회화 설정 탭 사용
            tab_name = f"{script_type} 설정"
            settings_tab = self.merged_settings.get('tabs', {}).get(tab_name)
            if not settings_tab:
                print(f"❌ [오류] '{tab_name}' 설정을 찾을 수 없습니다!")
                return []
            
            if not settings_tab.get('rows'):
                print(f"❌ [오류] '{tab_name}' 설정에 행이 없습니다!")
                return []
            
            created_files = []
            
            # 대화 데이터에서 각 필드 추출
            sequence = conversation_data.get('sequence', 1)
            native_script = conversation_data.get('native_script', '')
            learning_script = conversation_data.get('learning_script', '')
            reading_script = conversation_data.get('reading_script', '')
            
            print(f"📝 [대화 데이터] 순번: {sequence}, 원어: '{native_script}', 학습어: '{learning_script}', 읽기: '{reading_script}'")
            
            # 화면 1: 순번, 원어 텍스트만 표시
            screen1_scenes = []
            if len(settings_tab['rows']) >= 2:
                # 순번 (1행)
                screen1_scenes.append({
                    'text': str(sequence),
                    'settings': settings_tab['rows'][0]  # 순번 행
                })
                # 원어 (2행)
                screen1_scenes.append({
                    'text': native_script,
                    'settings': settings_tab['rows'][1]  # 원어 행
                })
            
            # 화면 2: 순번, 원어, 학습어, 읽기를 모두 표시
            screen2_scenes = []
            if len(settings_tab['rows']) >= 4:
                # 순번 (1행)
                screen2_scenes.append({
                    'text': str(sequence),
                    'settings': settings_tab['rows'][0]  # 순번 행
                })
                # 원어 (2행)
                screen2_scenes.append({
                    'text': native_script,
                    'settings': settings_tab['rows'][1]  # 원어 행
                })
                # 학습어 (3행)
                screen2_scenes.append({
                    'text': learning_script,
                    'settings': settings_tab['rows'][2]  # 학습어 행
                })
                # 읽기 (4행)
                screen2_scenes.append({
                    'text': reading_script,
                    'settings': settings_tab['rows'][3]  # 읽기 행
                })
            
            # 🔥🔥🔥 [파일명 일련번호] base_filename을 사용하여 파일명 생성 🔥🔥🔥
            if not base_filename:
                base_filename = f"{script_type}_{conversation_data.get('sequence', 1):03d}"
            
            # 🔥🔥🔥 [화면별 개별 처리] 인트로/엔딩과 같은 방식으로 각 화면을 개별 처리 🔥🔥🔥
            
            # 화면 1 생성 - 순번과 원어를 각각 개별 씬으로 처리
            if screen1_scenes:
                screen1_filename = f"{base_filename}_screen1.png"
                screen1_path = os.path.join(output_dir, screen1_filename)
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
            
            # 화면 2 생성 - 순번, 원어, 학습어, 읽기를 각각 개별 씬으로 처리
            if screen2_scenes:
                screen2_filename = f"{base_filename}_screen2.png"
                screen2_path = os.path.join(output_dir, screen2_filename)
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
            
            print(f"✅ [성공] {script_type} 이미지 생성 완료: 총 {len(created_files)}개 파일")
            return created_files
            
        except Exception as e:
            print(f"❌ [오류] {script_type} 이미지 생성 실패: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_current_settings(self) -> Dict[str, Any]:
        """현재 설정 상태 반환 (UI에서 확인용)"""
        return {
            "common": self.merged_settings.get('common', {}),
            "tabs": self.merged_settings.get('tabs', {}),
            "fonts": list(self.fonts.keys())
        }