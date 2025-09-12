import customtkinter as ctk
from src import config
import tkinter as tk
import os
import json
import glob
from tkinter import filedialog
from src.ui.ui_utils import create_labeled_widget




class ImageTabView(ctk.CTkFrame):
    def __init__(self, parent, root=None):
        super().__init__(parent, fg_color="transparent")
        self.root = root

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1) # 텍스트 설정 탭

        # --- 3.1. 공통 설정 섹션 ---
        common_settings_frame = ctk.CTkFrame(self, fg_color=config.COLOR_THEME["widget"])
        common_settings_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self._create_common_settings_widgets(common_settings_frame)

        # --- 3.2. 텍스트 설정 ---
        self.tab_view = ctk.CTkTabview(self, anchor="nw", border_width=1, 
                                       fg_color=config.COLOR_THEME["widget"],
                                       segmented_button_fg_color=config.COLOR_THEME["background"],
                                       segmented_button_selected_color="#E67E22",
                                       segmented_button_selected_hover_color="#F39C12",
                                       segmented_button_unselected_color="#2C3E50",
                                       text_color=config.COLOR_THEME["text"])
        self.tab_view.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self._create_text_settings_tabs(self.tab_view)

        # --- 3.3 메시지 창 (JSON 뷰어) ---
        self.json_viewer = ctk.CTkTextbox(self, fg_color=config.COLOR_THEME["widget"])
        self.json_viewer.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")

        # --- 3.4. 콘트롤 버튼 섹션 ---
        control_button_frame = ctk.CTkFrame(self, fg_color=config.COLOR_THEME["widget"])
        control_button_frame.grid(row=3, column=0, padx=10, pady=10, sticky="ew")
        self._create_control_buttons(control_button_frame)

        # 프로그램 실행 시 저장 파일 자동 로드 시도
        try:
            self.after(300, self._auto_load_settings_if_available)
        except Exception:
            pass

    def _make_base_canvas(self, width: int, height: int):
        try:
            kind = (self.bg_type_var.get() or "").strip()
            value = (self.w_bg_value.get() or "").strip()
            base = None
            # 배경 타입: 이미지/동영상/색상 처리
            if kind == "이미지" and value and os.path.isfile(value):
                from PIL import Image
                img = Image.open(value).convert('RGBA')
                iw, ih = img.size
                # cover fit
                scale = max(width / max(1, iw), height / max(1, ih))
                new_w, new_h = int(iw * scale), int(ih * scale)
                img = img.resize((new_w, new_h))
                left = max(0, (new_w - width) // 2)
                top = max(0, (new_h - height) // 2)
                img = img.crop((left, top, left + width, top + height))
                base = img
            elif kind == "동영상" and value and os.path.isfile(value):
                import tempfile, subprocess
                from PIL import Image
                with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
                    tmp_path = tmp.name
                try:
                    # 첫 프레임 추출
                    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-ss', '0', '-i', value, '-frames:v', '1', tmp_path]
                    subprocess.run(cmd, check=True)
                    img = Image.open(tmp_path).convert('RGBA')
                    iw, ih = img.size
                    scale = max(width / max(1, iw), height / max(1, ih))
                    new_w, new_h = int(iw * scale), int(ih * scale)
                    img = img.resize((new_w, new_h))
                    left = max(0, (new_w - width) // 2)
                    top = max(0, (new_h - height) // 2)
                    img = img.crop((left, top, left + width, top + height))
                    base = img
                except Exception:
                    base = None
                finally:
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass
            elif kind == "색상":
                # 색상 문자열로 RGBA 배경 생성
                from PIL import Image, ImageColor
                try:
                    rgb = ImageColor.getrgb(value or "#000000")
                except Exception:
                    rgb = (0, 0, 0)
                base = Image.new('RGBA', (width, height), (rgb[0], rgb[1], rgb[2], 255))
            if base is None:
                # 기본 회색 바탕
                from PIL import Image
                base = Image.new('RGBA', (width, height), (128,128,128,255))
            return base
        except Exception:
            from PIL import Image
            return Image.new('RGBA', (width, height), (128,128,128,255))

    def _create_common_settings_widgets(self, parent):
        
        from src.ui.ui_utils import create_labeled_widget

        # 1행
        row1 = ctk.CTkFrame(parent, fg_color="transparent")
        row1.pack(fill="x", padx=10, pady=2, anchor="w")
        ctk.CTkLabel(row1, text="배경 설정:").pack(side="left", padx=(0, 10))
        self.bg_type_var = tk.StringVar(value="색상")
        ctk.CTkRadioButton(row1, text="색상", variable=self.bg_type_var, value="색상").pack(side="left", padx=5)
        ctk.CTkRadioButton(row1, text="이미지", variable=self.bg_type_var, value="이미지").pack(side="left", padx=5)
        ctk.CTkRadioButton(row1, text="동영상", variable=self.bg_type_var, value="동영상").pack(side="left", padx=5)
        _, self.w_bg_value = create_labeled_widget(row1, "배경값", 16)
        button_kwargs = {"fg_color": config.COLOR_THEME["button"], "hover_color": config.COLOR_THEME["button_hover"], "text_color": config.COLOR_THEME["text"]}
        self.btn_browse = ctk.CTkButton(row1, text="찾아보기", width=80, command=self._on_click_browse, **button_kwargs)
        self.btn_browse.pack(side="left", padx=(0,5))
        try:
            self.bg_type_var.trace_add("write", lambda *args: self._on_bg_type_change())
        except Exception:
            pass
        # 초기 상태 적용
        self._on_bg_type_change()
        
        # 2행
        row2 = ctk.CTkFrame(parent, fg_color="transparent")
        row2.pack(fill="x", padx=10, pady=2, anchor="w")
        ctk.CTkLabel(row2, text="바탕 설정:").pack(side="left", padx=(0, 10))
        self.section_checkbox_var = tk.BooleanVar(value=False)
        _, self.section_checkbox = create_labeled_widget(row2, "구간", 5, "checkbox", {"variable": self.section_checkbox_var})
        _, self.w_bg = create_labeled_widget(row2, "바탕색", 15)
        self.w_bg.insert(0, "#000000")
        _, self.w_alpha = create_labeled_widget(row2, "투명도", 10)
        self.w_alpha.insert(0, "1.0")
        _, self.w_margin = create_labeled_widget(row2, "여백", 10, "combo", {"values": ["0", "2", "5", "10"]})
        self.w_margin.set("2")

        # 3행
        row3 = ctk.CTkFrame(parent, fg_color="transparent")
        row3.pack(fill="x", padx=10, pady=2, anchor="w")
        ctk.CTkLabel(row3, text="쉐도우 설정:").pack(side="left", padx=(0, 10))
        # 블러 사용 여부 체크박스
        self.shadow_blur_enabled = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(row3, text="블러", variable=self.shadow_blur_enabled, command=lambda: [self._on_shadow_blur_toggle(), self._update_common_states()]).pack(side="left", padx=(0,8))
        _, self.w_shadow_thick = create_labeled_widget(row3, "두께", 6)
        self.w_shadow_thick.insert(0, "2")
        _, self.w_shadow_color = create_labeled_widget(row3, "쉐도우 색상", 10)
        self.w_shadow_color.insert(0, "#000000")
        _, self.w_shadow_blur = create_labeled_widget(row3, "블러", 4)
        self.w_shadow_blur.insert(0, "8")
        _, self.w_shadow_offx = create_labeled_widget(row3, "오프셋X", 4)
        self.w_shadow_offx.insert(0, "2")
        _, self.w_shadow_offy = create_labeled_widget(row3, "오프셋Y", 4)
        self.w_shadow_offy.insert(0, "2")
        _, self.w_shadow_alpha = create_labeled_widget(row3, "불투명도", 5)
        self.w_shadow_alpha.insert(0, "0.6")
        # 두께 변경 시 블러 기본값 재추천
        try:
            self.w_shadow_thick.bind("<FocusOut>", lambda e: self._maybe_apply_shadow_defaults())
        except Exception:
            pass
        
        # 4행
        row4 = ctk.CTkFrame(parent, fg_color="transparent")
        row4.pack(fill="x", padx=10, pady=2, anchor="w")
        ctk.CTkLabel(row4, text="외곽선 설정:").pack(side="left", padx=(0, 10))
        _, self.w_border_thick = create_labeled_widget(row4, "두께", 6)
        self.w_border_thick.insert(0, "2")
        _, self.w_border_color = create_labeled_widget(row4, "외곽선 색상", 10)
        self.w_border_color.insert(0, "#000000")

        # 초기 상태 반영
        self._update_common_states()

    def _update_common_states(self):
        # 공통 설정 입력은 항상 활성화
        def set_state(widget):
            try:
                widget.configure(state="normal")
            except Exception:
                pass
        set_state(self.w_bg)
        set_state(self.w_alpha)
        set_state(self.w_margin)
        set_state(self.w_shadow_thick)
        set_state(self.w_shadow_color)
        # 블러 on/off에 따라 세부 파라미터 활성화
        try:
            enabled = bool(self.shadow_blur_enabled.get())
        except Exception:
            enabled = True
        for w in [self.w_shadow_blur, self.w_shadow_offx, self.w_shadow_offy, self.w_shadow_alpha]:
            try:
                w.configure(state=("normal" if enabled else "disabled"))
            except Exception:
                pass
        set_state(self.w_border_thick)
        set_state(self.w_border_color)

    def _maybe_apply_shadow_defaults(self):
        try:
            if not bool(self.shadow_blur_enabled.get()):
                return
            # 두께/색상 기반 표준값 추천
            try:
                thick = max(0, int(float(self.w_shadow_thick.get() or 0)))
            except Exception:
                thick = 2
            try:
                color = self.w_shadow_color.get() or "#000000"
            except Exception:
                color = "#000000"
            # 추천 규칙: blur ~ max(8, thick*2), off ~ max(2, round(thick*0.8)), alpha ~ 0.6
            blur = max(8, thick * 2)
            off = max(2, int(round(thick * 0.8)))
            # 값 반영(비워져 있거나 기본값일 때만 덮어쓰기)
            def is_default_like(s, defaults):
                return (s is None) or (str(s).strip() == "") or (str(s).strip() in defaults)
            if is_default_like(self.w_shadow_blur.get(), ["8", "0"]):
                self.w_shadow_blur.delete(0, tk.END)
                self.w_shadow_blur.insert(0, str(blur))
            if is_default_like(self.w_shadow_offx.get(), ["2", "0"]):
                self.w_shadow_offx.delete(0, tk.END)
                self.w_shadow_offx.insert(0, str(off))
            if is_default_like(self.w_shadow_offy.get(), ["2", "0"]):
                self.w_shadow_offy.delete(0, tk.END)
                self.w_shadow_offy.insert(0, str(off))
            # alpha는 기본 0.6 유지
            if is_default_like(self.w_shadow_alpha.get(), ["0.6", "1", "0.0"]):
                self.w_shadow_alpha.delete(0, tk.END)
                self.w_shadow_alpha.insert(0, "0.6")
        except Exception:
            pass

    def _on_shadow_blur_toggle(self):
        try:
            if bool(self.shadow_blur_enabled.get()):
                self._maybe_apply_shadow_defaults()
        except Exception:
            pass

    def _create_text_settings_tabs(self, tab_view):
        # Default 값: 제작 사양서 기반
        defaults = {
            "회화 설정": {"행수": "4", "비율": "16:9", "해상도": "1920x1080", "rows": [
                {"행": "순번", "x": 50, "y": 50, "w": 1820, "크기(pt)": 80, "폰트(pt)": "KoPubWorldDotum", "색상": "#FFFFFF", "굵기": "Bold", "좌우 정렬": "Left", "상하 정렬": "Top"},
                {"행": "원어", "x": 50, "y": 150, "w": 1820, "크기(pt)": 100, "폰트(pt)": "KoPubWorldDotum", "색상": "#00FFFF", "굵기": "Bold", "좌우 정렬": "Left", "상하 정렬": "Top"},
                {"행": "학습어", "x": 50, "y": 450, "w": 1820, "크기(pt)": 100, "폰트(pt)": "Noto Sans KR", "색상": "#FF00FF", "굵기": "Bold", "좌우 정렬": "Left", "상하 정렬": "Top"},
                {"행": "읽기", "x": 50, "y": 750, "w": 1820, "크기(pt)": 100, "폰트(pt)": "KoPubWorldDotum", "색상": "#FFFF00", "굵기": "Bold", "좌우 정렬": "Left", "상하 정렬": "Top"},
            ]},
            "썸네일 설정": {"행수": "4", "비율": "16:9", "해상도": "1920x1080", "rows": [
                {"행": "1행", "x": 50, "y": 50, "w": 924, "크기(pt)": 100, "폰트(pt)": "KoPubWorldDotum", "색상": "#FFFFFF", "굵기": "Bold", "좌우 정렬": "Left", "상하 정렬": "Top"},
                {"행": "2행", "x": 50, "y": 200, "w": 924, "크기(pt)": 100, "폰트(pt)": "KoPubWorldDotum", "색상": "#00FFFF", "굵기": "Bold", "좌우 정렬": "Left", "상하 정렬": "Top"},
                {"행": "3행", "x": 50, "y": 350, "w": 924, "크기(pt)": 100, "폰트(pt)": "KoPubWorldDotum", "색상": "#FF00FF", "굵기": "Bold", "좌우 정렬": "Left", "상하 정렬": "Top"},
                {"행": "4행", "x": 50, "y": 500, "w": 924, "크기(pt)": 100, "폰트(pt)": "KoPubWorldDotum", "색상": "#FFFF00", "굵기": "Bold", "좌우 정렬": "Left", "상하 정렬": "Top"},
            ]},
            "인트로 설정": {"행수": "1", "비율": "16:9", "해상도": "1920x1080", "rows": [{"행": "1행", "x": 50, "y": 50, "w": 1820, "크기(pt)": 80, "폰트(pt)": "KoPubWorldDotum", "색상": "#FFFFFF", "굵기": "Bold", "좌우 정렬": "Left", "상하 정렬": "Top"}]},
            "엔딩 설정": {"행수": "1", "비율": "16:9", "해상도": "1920x1080", "rows": [{"행": "1행", "x": 50, "y": 50, "w": 1820, "크기(pt)": 100, "폰트(pt)": "KoPubWorldDotum", "색상": "#FFFFFF", "굵기": "Bold", "좌우 정렬": "Left", "상하 정렬": "Top"}]},
            "대화 설정": {"행수": "3", "비율": "16:9", "해상도": "1920x1080", "rows": [
                {"행": "원어", "x": 50, "y": 250, "w": 1820, "크기(pt)": 100, "폰트(pt)": "KoPubWorldDotum", "색상": "#FFFFFF", "굵기": "Bold", "좌우 정렬": "Left", "상하 정렬": "Top"},
                {"행": "학습어1", "x": 50, "y": 550, "w": 1820, "크기(pt)": 100, "폰트(pt)": "KoPubWorldDotum", "색상": "#FFFFFF", "굵기": "Bold", "좌우 정렬": "Left", "상하 정렬": "Top"},
                {"행": "학습어2", "x": 50, "y": 850, "w": 1820, "크기(pt)": 100, "폰트(pt)": "KoPubWorldDotum", "색상": "#FFFFFF", "굵기": "Bold", "좌우 정렬": "Left", "상하 정렬": "Top"},
            ]},
        }
        # 기본 텍스트 설정 저장 + 각 탭 위젯 인스턴스 보관
        self.default_text_configs = defaults
        self.text_tabs = {}
        for name, default_data in defaults.items():
            tab = tab_view.add(name)
            inst = TextSettingsTab(tab, default_data)
            inst.pack(expand=True, fill="both")
            self.text_tabs[name] = inst

    def _create_control_buttons(self, parent):
        button_kwargs = {"fg_color": config.COLOR_THEME["button"], "hover_color": config.COLOR_THEME["button_hover"], "text_color": config.COLOR_THEME["text"]}
        ctk.CTkButton(parent, text="미리보기", command=self._on_click_preview, **button_kwargs).pack(side="left", padx=10, pady=10)
        ctk.CTkButton(parent, text="비디오 생성", command=self._on_click_video, **button_kwargs).pack(side="left", padx=10, pady=10)
        ctk.CTkButton(parent, text="설정 읽기", command=self._on_click_load_settings, **button_kwargs).pack(side="right", padx=10, pady=10)
        ctk.CTkButton(parent, text="설정 저장", command=self._on_click_save_settings, **button_kwargs).pack(side="right", padx=10, pady=10)

    def get_all_settings(self):
        try:
            tabs_payload = {name: tab.get_settings() for name, tab in (self.text_tabs or {}).items()}
        except Exception:
            tabs_payload = {}
        return {
            "version": 1,
            "common": self._collect_common_settings(),
            "tabs": tabs_payload,
        }

    

    def apply_all_settings(self, data: dict):
        if not isinstance(data, dict):
            return
        self._apply_common_settings((data or {}).get("common", {}))
        tabs = (data or {}).get("tabs", {})
        for name, tabdata in tabs.items():
            inst = (self.text_tabs or {}).get(name)
            if inst:
                inst.apply_settings(tabdata)

    def _log_json_object(self, title: str, obj: dict):
        try:
            pretty = json.dumps(obj, ensure_ascii=False, indent=2)
            print(f"{title}:\n{pretty}")
            self._log_json(f"{title}:\n{pretty}")
        except Exception:
            try:
                print(f"{title}: {obj}")
            except Exception:
                pass

    def _collect_common_settings(self):
        return {
            "bg": {
                "enabled": True,
                "color": self.w_bg.get(),
                "alpha": self.w_alpha.get(),
                "margin": self.w_margin.get(),
                "type": self.bg_type_var.get(),
                "value": self.w_bg_value.get(),
            },
            "shadow": {
                "enabled": True,
                "thick": self.w_shadow_thick.get(),
                "color": self.w_shadow_color.get(),
                "blur": self.w_shadow_blur.get(),
                "offx": self.w_shadow_offx.get(),
                "offy": self.w_shadow_offy.get(),
                "alpha": self.w_shadow_alpha.get(),
                "useBlur": bool(self.shadow_blur_enabled.get()) if hasattr(self, 'shadow_blur_enabled') else True,
            },
            "border": {
                "enabled": True,
                "thick": self.w_border_thick.get(),
                "color": self.w_border_color.get(),
            }
        }

    def _apply_common_settings(self, data):
        try:
            bg = (data or {}).get("bg", {})
            self.bg_type_var.set(bg.get("type", "색상"))
            self.w_bg_value.delete(0, tk.END)
            self.w_bg_value.insert(0, bg.get("value", ""))
            self.w_bg.delete(0, tk.END)
            self.w_bg.insert(0, bg.get("color", "#808080"))
            self.w_alpha.delete(0, tk.END)
            self.w_alpha.insert(0, str(bg.get("alpha", "1.0")))
            try:
                self.w_margin.set(str(bg.get("margin", "2")))
            except Exception:
                pass
            sh = (data or {}).get("shadow", {})
            self.w_shadow_thick.delete(0, tk.END)
            self.w_shadow_thick.insert(0, str(sh.get("thick", "2")))
            self.w_shadow_color.delete(0, tk.END)
            self.w_shadow_color.insert(0, sh.get("color", "#000000"))
            # 추가 쉐도우 파라미터
            try:
                self.w_shadow_blur.delete(0, tk.END)
                self.w_shadow_blur.insert(0, str(sh.get("blur", "8")))
                self.w_shadow_offx.delete(0, tk.END)
                self.w_shadow_offx.insert(0, str(sh.get("offx", "2")))
                self.w_shadow_offy.delete(0, tk.END)
                self.w_shadow_offy.insert(0, str(sh.get("offy", "2")))
                self.w_shadow_alpha.delete(0, tk.END)
                self.w_shadow_alpha.insert(0, str(sh.get("alpha", "0.6")))
                if hasattr(self, 'shadow_blur_enabled'):
                    try:
                        self.shadow_blur_enabled.set(bool(sh.get("useBlur", True)))
                    except Exception:
                        pass
            except Exception:
                pass
            bd = (data or {}).get("border", {})
            self.w_border_thick.delete(0, tk.END)
            self.w_border_thick.insert(0, str(bd.get("thick", "2")))
            self.w_border_color.delete(0, tk.END)
            self.w_border_color.insert(0, bd.get("color", "#000000"))
        finally:
            self._update_common_states()

    def _on_click_save_settings(self):
        try:
            if not getattr(self, 'root', None):
                return
            project_name = self.root.data_page.project_name_var.get()
            identifier = self.root.data_page.identifier_var.get()
            out_dir = os.path.join(config.OUTPUT_PATH, project_name, identifier)
            os.makedirs(out_dir, exist_ok=True)
            payload = self.get_all_settings()
            path = os.path.join(out_dir, "_text_settings.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            self._log_json(f"[설정 저장] 완료: {path}")
            print(f"[설정 저장] {path}")
            self._log_json_object("[설정 저장 데이터]", payload)
        except Exception as e:
            self._log_json(f"[설정 저장 오류] {e}")
            print(f"[설정 저장 오류] {e}")

    def _on_click_load_settings(self):
        try:
            if not getattr(self, 'root', None):
                return
            project_name = self.root.data_page.project_name_var.get()
            identifier = self.root.data_page.identifier_var.get()
            out_dir = os.path.join(config.OUTPUT_PATH, project_name, identifier)
            path = os.path.join(out_dir, "_text_settings.json")
            if not os.path.isfile(path):
                self._log_json(f"[설정 읽기] 파일 없음: {path}")
                print(f"[설정 읽기] 파일 없음: {path}")
                return
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.apply_all_settings(data)
            self._log_json(f"[설정 읽기] 완료: {path}")
            print(f"[설정 읽기] {path}")
            self._log_json_object("[설정 읽기 데이터]", data)
        except Exception as e:
            self._log_json(f"[설정 읽기 오류] {e}")
            print(f"[설정 읽기 오류] {e}")

    def _auto_load_settings_if_available(self):
        try:
            if not getattr(self, 'root', None):
                return
            data_page = getattr(self.root, 'data_page', None)
            if not data_page:
                return
            project_name = getattr(data_page, 'project_name_var', None)
            identifier = getattr(data_page, 'identifier_var', None)
            if not project_name or not identifier:
                return
            project_name = project_name.get()
            identifier = identifier.get()
            if not project_name or not identifier:
                return
            out_dir = os.path.join(config.OUTPUT_PATH, project_name, identifier)
            path = os.path.join(out_dir, "_text_settings.json")
            if os.path.isfile(path):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.apply_all_settings(data)
                self._log_json(f"[자동 로드] {path} 적용")
                print(f"[자동 로드] {path}")
                self._log_json_object("[자동 로드 데이터]", data)
        except Exception as e:
            try:
                print(f"[자동 로드 오류] {e}")
            except Exception:
                pass
    def _on_click_preview(self):
        try:
            print("[미리보기] 버튼 클릭")
            if not getattr(self, 'root', None):
                print("[미리보기] root 미연결 - 종료")
                return
            project_name = self.root.data_page.project_name_var.get()
            identifier = self.root.data_page.identifier_var.get()
            out_dir = os.path.join(config.OUTPUT_PATH, project_name, identifier)
            print(f"[미리보기] project={project_name}, identifier={identifier}")
            print(f"[미리보기] out_dir={out_dir}")
            os.makedirs(out_dir, exist_ok=True)
            data = getattr(self.root.data_page, 'generated_data', None) or {}
            dialogue_csv = (data.get('fullVideoScript') or {}).get('dialogueCsv') or data.get('dialogueCsv')
            if not dialogue_csv:
                self._log_json('[미리보기] dialogueCsv가 없습니다. 데이터 생성/읽기를 먼저 수행하세요.')
                print('[미리보기] dialogueCsv 없음 - 종료')
                return
            from PIL import Image, ImageDraw, ImageFont, ImageColor
            lines = [row for row in dialogue_csv.splitlines() if row.strip()][1:]
            print(f"[미리보기] CSV 라인 수(헤더 제외)={len(lines)}")
            dialog_dir = os.path.join(out_dir, 'dialog')
            os.makedirs(dialog_dir, exist_ok=True)
            width, height = 1920, 1080
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", 64)
            except Exception:
                font = ImageFont.load_default()
            # 회화 설정: 현재 UI 값을 사용
            try:
                conv_cfg = (self.text_tabs.get("회화 설정").get_settings() if hasattr(self, 'text_tabs') and self.text_tabs.get("회화 설정") else (self.default_text_configs or {}).get("회화 설정", {}))
            except Exception:
                conv_cfg = (self.default_text_configs or {}).get("회화 설정", {})
            rows_cfg = conv_cfg.get("rows", [])
            row_map = {str(r.get("행", "")): r for r in rows_cfg}
            print("[미리보기] 회화 설정 로우 구성:")
            for k in ["순번","원어","학습어","읽기"]:
                cfg = row_map.get(k, {})
                print(f"  - {k}: x={cfg.get('x')} y={cfg.get('y')} w={cfg.get('w')} size={cfg.get('크기(pt)')} font={cfg.get('폰트(pt)')} color={cfg.get('색상')} align=({cfg.get('좌우 정렬')},{cfg.get('상하 정렬')})")

            use_section_background = self.section_checkbox_var.get()

            def draw_label(img, draw, label_name, text, use_section_background):
                cfg = row_map.get(label_name, {})
                # 좌표/폭/크기/색상/정렬
                try:
                    x = int(cfg.get("x", 100))
                except Exception:
                    x = 100
                try:
                    y = int(cfg.get("y", 100))
                except Exception:
                    y = 100
                try:
                    w = int(cfg.get("w", 1720))
                except Exception:
                    w = 1720
                try:
                    size = int(cfg.get("크기(pt)", 64))
                except Exception:
                    size = 64
                color_hex = cfg.get("색상", "#FFFFFF")
                align_h = cfg.get("좌우 정렬", "Left")
                align_v = cfg.get("상하 정렬", "Top")
                # 행별 효과 온오프
                def as_bool(v):
                    try:
                        return str(v).strip().lower() in ["true", "1", "yes", "y"]
                    except Exception:
                        return False
                row_bg = as_bool(cfg.get("바탕", "False"))
                row_shadow = as_bool(cfg.get("쉐도우", "False"))
                row_border = as_bool(cfg.get("외곽선", "False"))
                try:
                    fnt = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", size)
                except Exception:
                    fnt = ImageFont.load_default()
                # 색상 변환
                try:
                    col = ImageColor.getrgb(color_hex)
                except Exception:
                    col = (255,255,255)
                # 쉐도우/외곽선 (행 체크박스 기준만 사용)
                shadow_px = int(self.w_shadow_thick.get() or 0) if row_shadow else 0
                border_px = int(self.w_border_thick.get() or 0) if row_border else 0
                try:
                    shadow_col = ImageColor.getrgb(self.w_shadow_color.get()) if shadow_px else (0,0,0)
                except Exception:
                    shadow_col = (0,0,0)
                # 텍스트 크기 측정(정렬 계산용)
                tw, th = draw.textbbox((0,0), text, font=fnt)[2:]
                if align_h == "Center":
                    tx = x + max(0, (w - tw) // 2)
                elif align_h == "Right":
                    tx = x + max(0, (w - tw))
                else:
                    tx = x
                if align_v == "Middle":
                    ty = y - th // 2
                elif align_v == "Bottom":
                    ty = y - th
                else:
                    ty = y
                print(f"[draw_label] {label_name}: x={x} y={y} w={w} size={size} color={color_hex} align=({align_h},{align_v}) text='{text[:60]}'")
                # 텍스트 실제 위치 bbox 계산 (최종 좌표에서의 경계)
                bbox_l, bbox_t, bbox_r, bbox_b = draw.textbbox((tx, ty), text, font=fnt)
                bbox_w = bbox_r - bbox_l
                bbox_h = bbox_b - bbox_t
                # 텍스트 바탕 박스(여백 포함) 렌더링 - 실제 bbox 기준 (오버레이 합성으로 투명도 보존)
                if row_bg:
                    try:
                        bg_rgb = ImageColor.getrgb(self.w_bg.get())
                    except Exception:
                        bg_rgb = (128,128,128)
                    try:
                        alpha_px = max(0, min(255, int(float(self.w_alpha.get()) * 255)))
                    except Exception:
                        alpha_px = 255
                    try:
                        margin_px = int(self.w_margin.get())
                    except Exception:
                        margin_px = 0
                    
                    if use_section_background:
                        left = x
                        top = y
                        right = x + w
                        bottom = y + size
                    else:
                        left = max(0, bbox_l - margin_px)
                        top = max(0, bbox_t - margin_px)
                        right = min(width, bbox_r + margin_px)
                        bottom = min(height, bbox_b + margin_px)

                    rect = (int(left), int(top), int(right), int(bottom))
                    # RGBA 이미지 전제: 오버레이에 그리고 합성
                    overlay = Image.new('RGBA', (width, height), (0,0,0,0))
                    o_draw = ImageDraw.Draw(overlay)
                    o_draw.rectangle(rect, fill=(bg_rgb[0], bg_rgb[1], bg_rgb[2], alpha_px))
                    img.alpha_composite(overlay)
                    print(f"[bg-box] rect={rect} bbox={(bbox_l,bbox_t,bbox_r,bbox_b)} size={(bbox_w,bbox_h)} color={self.w_bg.get()} alpha={self.w_alpha.get()} margin={self.w_margin.get()}")
                # 쉐도우: 블러/오프셋/알파 적용
                if shadow_px:
                    try:
                        from PIL import ImageFilter
                        try:
                            blur = max(0, int(float(self.w_shadow_blur.get())))
                        except Exception:
                            blur = 0
                        # 블러 사용 여부 적용
                        try:
                            if hasattr(self, 'shadow_blur_enabled') and (not bool(self.shadow_blur_enabled.get())):
                                blur = 0
                        except Exception:
                            pass
                        try:
                            offx = int(float(self.w_shadow_offx.get()))
                            offy = int(float(self.w_shadow_offy.get()))
                        except Exception:
                            offx, offy = shadow_px, shadow_px
                        try:
                            s_alpha = max(0, min(255, int(float(self.w_shadow_alpha.get()) * 255)))
                        except Exception:
                            s_alpha = 153
                        # 최소 bbox 오버레이 생성
                        margin = max(shadow_px, blur) * 3
                        ox1, oy1 = max(0, tx - margin), max(0, ty - margin)
                        ox2, oy2 = min(width, tx + tw + margin), min(height, ty + th + margin)
                        overlay = Image.new('RGBA', (max(1, ox2-ox1), max(1, oy2-oy1)), (0,0,0,0))
                        o_draw = ImageDraw.Draw(overlay)
                        o_draw.text(((tx+offx)-ox1, (ty+offy)-oy1), text, fill=(shadow_col[0], shadow_col[1], shadow_col[2], s_alpha), font=fnt, stroke_width=0)
                        if blur > 0:
                            overlay = overlay.filter(ImageFilter.GaussianBlur(radius=blur))
                        img.alpha_composite(overlay, (ox1, oy1))
                    except Exception:
                        # 폴백: 단순 오프셋 그림자
                        draw.text((tx+shadow_px, ty+shadow_px), text, fill=shadow_col, font=fnt)
                # 외곽 포함 본문
                try:
                    draw.text((tx, ty), text, fill=col, font=fnt, stroke_width=border_px, stroke_fill=self.w_border_color.get())
                except Exception:
                    draw.text((tx, ty), text, fill=col, font=fnt)
            for idx, row in enumerate(lines, start=1):
                try:
                    cols = [c.strip('"') for c in row.split(',')]
                    seq = cols[0] if len(cols) > 0 else ''
                    native = cols[1] if len(cols) > 1 else ''
                    learning = cols[2] if len(cols) > 2 else ''
                    reading = cols[3] if len(cols) > 3 else ''
                except Exception:
                    continue
                print(f"[row] idx={idx} seq='{seq}' 원어='{native[:60]}' 학습어='{learning[:60]}' 읽기='{reading[:60]}'")
                print(f"[공통] bg_color={self.w_bg.get()} alpha={self.w_alpha.get()} margin={self.w_margin.get()} shadow_thick={self.w_shadow_thick.get()} shadow_color={self.w_shadow_color.get()} border_thick={self.w_border_thick.get()} border_color={self.w_border_color.get()}")
                img1 = self._make_base_canvas(width, height)
                d1 = ImageDraw.Draw(img1)
                draw_label(img1, d1, "순번", f"{seq}", use_section_background)
                draw_label(img1, d1, "원어", native, use_section_background)
                save1 = os.path.join(dialog_dir, f"{identifier}_{idx:03d}_a.png")
                img1.save(save1)
                print(f"[save] {save1}")
                img2 = self._make_base_canvas(width, height)
                d2 = ImageDraw.Draw(img2)
                draw_label(img2, d2, "순번", f"{seq}", use_section_background)
                draw_label(img2, d2, "원어", native, use_section_background)
                draw_label(img2, d2, "학습어", learning, use_section_background)
                draw_label(img2, d2, "읽기", reading, use_section_background)
                save2 = os.path.join(dialog_dir, f"{identifier}_{idx:03d}_b.png")
                img2.save(save2)
                print(f"[save] {save2}")
            # 썸네일 미리보기 생성
            try:
                self.generate_thumbnail_images()
            except Exception as e:
                print(f"[썸네일 미리보기 오류] {e}")
            # 인트로 이미지 생성
            try:
                self.generate_intro_images()
            except Exception as e:
                print(f"[인트로 미리보기 오류] {e}")
            # 엔딩 이미지 생성
            try:
                self.generate_ending_images()
            except Exception as e:
                print(f"[엔딩 미리보기 오류] {e}")
            print("[미리보기] 완료")
        except Exception as e:
            try:
                self._log_json(f"[미리보기 오류] {e}")
                print(f"[미리보기 오류] {e}")
            except Exception:
                pass

    def generate_thumbnail_images(self):
        """썸네일 설정과 AI 데이터의 thumbnailTextVersions를 사용해 썸네일 이미지를 생성합니다."""
        if not getattr(self, 'root', None):
            return
        project_name = self.root.data_page.project_name_var.get()
        identifier = self.root.data_page.identifier_var.get()
        out_dir = os.path.join(config.OUTPUT_PATH, project_name, identifier)
        thumb_dir = os.path.join(out_dir, 'thumbnail')
        os.makedirs(thumb_dir, exist_ok=True)
        data = getattr(self.root.data_page, 'generated_data', None) or {}
        versions = data.get('thumbnailTextVersions') or []
        if not versions:
            self._log_json('[썸네일] thumbnailTextVersions가 없습니다.')
            print('[썸네일] thumbnailTextVersions 없음')
            return
        # 썸네일 설정 탭 구성 사용
        try:
            thumb_cfg = (self.text_tabs.get("썸네일 설정").get_settings() if hasattr(self, 'text_tabs') and self.text_tabs.get("썸네일 설정") else (self.default_text_configs or {}).get("썸네일 설정", {}))
        except Exception:
            thumb_cfg = (self.default_text_configs or {}).get("썸네일 설정", {})
        rows_cfg = thumb_cfg.get("rows", [])
        row_map = {str(r.get("행", "")): r for r in rows_cfg}
        print("[썸네일] 설정 로우 구성:")
        for k in ["1행","2행","3행","4행"]:
            cfg = row_map.get(k, {})
            print(f"  - {k}: x={cfg.get('x')} y={cfg.get('y')} w={cfg.get('w')} size={cfg.get('크기(pt)')} font={cfg.get('폰트(pt)')} color={cfg.get('색상')} align=({cfg.get('좌우 정렬')},{cfg.get('상하 정렬')})")
        from PIL import Image, ImageDraw, ImageFont, ImageColor
        # 공통 캔버스 크기 (해상도 파싱)
        res_text = thumb_cfg.get('해상도') or '1920x1080'
        try:
            width, height = [int(v) for v in res_text.lower().split('x')[:2]]
        except Exception:
            width, height = 1920, 1080

        def as_bool(v):
            try:
                return str(v).strip().lower() in ["true","1","yes","y"]
            except Exception:
                return False

        def draw_label(img, draw, label_name, text):
            cfg = row_map.get(label_name, {})
            try:
                x = int(cfg.get("x", 100))
            except Exception:
                x = 100
            try:
                y = int(cfg.get("y", 100))
            except Exception:
                y = 100
            try:
                w = int(cfg.get("w", 1720))
            except Exception:
                w = 1720
            try:
                size = int(cfg.get("크기(pt)", 64))
            except Exception:
                size = 64
            color_hex = cfg.get("색상", "#FFFFFF")
            align_h = cfg.get("좌우 정렬", "Left")
            align_v = cfg.get("상하 정렬", "Top")
            row_bg = as_bool(cfg.get("바탕", "False"))
            row_shadow = as_bool(cfg.get("쉐도우", "False"))
            row_border = as_bool(cfg.get("외곽선", "False"))
            # 폰트 로딩 함수
            def load_font(px):
                try:
                    return ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", px)
                except Exception:
                    return ImageFont.load_default()
            fnt = load_font(size)
            try:
                col = ImageColor.getrgb(color_hex)
            except Exception:
                col = (255,255,255)
            # 쉐도우/외곽선 픽셀
            shadow_px = int(self.w_shadow_thick.get() or 0) if row_shadow else 0
            border_px = int(self.w_border_thick.get() or 0) if row_border else 0
            try:
                shadow_col = ImageColor.getrgb(self.w_shadow_color.get()) if shadow_px else (0,0,0)
            except Exception:
                shadow_col = (0,0,0)
            # 사이즈 자동 축소: 텍스트 폭이 w를 넘으면 줄어들 때까지 감소
            try:
                min_size = max(16, int(size * 0.5))
            except Exception:
                min_size = 16
            tw, th = draw.textbbox((0,0), text, font=fnt)[2:]
            while tw > w and size > min_size:
                size = max(min_size, size - 4)
                fnt = load_font(size)
                tw, th = draw.textbbox((0,0), text, font=fnt)[2:]
            # 정렬 보정 좌표
            if align_h == "Center":
                tx = x + max(0, (w - tw) // 2)
            elif align_h == "Right":
                tx = x + max(0, (w - tw))
            else:
                tx = x
            if align_v == "Middle":
                ty = y - th // 2
            elif align_v == "Bottom":
                ty = y - th
            else:
                ty = y
            # bbox
            bbox_l, bbox_t, bbox_r, bbox_b = draw.textbbox((tx, ty), text, font=fnt)
            # 바탕 박스
            if row_bg:
                try:
                    bg_rgb = ImageColor.getrgb(self.w_bg.get())
                except Exception:
                    bg_rgb = (128,128,128)
                try:
                    alpha_px = max(0, min(255, int(float(self.w_alpha.get()) * 255)))
                except Exception:
                    alpha_px = 255
                try:
                    margin_px = int(self.w_margin.get())
                except Exception:
                    margin_px = 0
                left = max(0, bbox_l - margin_px)
                top = max(0, bbox_t - margin_px)
                right = min(width, bbox_r + margin_px)
                bottom = min(height, bbox_b + margin_px)
                overlay = Image.new('RGBA', (width, height), (0,0,0,0))
                o_draw = ImageDraw.Draw(overlay)
                o_draw.rectangle((left, top, right, bottom), fill=(bg_rgb[0], bg_rgb[1], bg_rgb[2], alpha_px))
                img.alpha_composite(overlay)
            # 쉐도우(블러 지원)
            if shadow_px:
                try:
                    from PIL import ImageFilter
                    try:
                        blur = max(0, int(float(self.w_shadow_blur.get())))
                    except Exception:
                        blur = 0
                    try:
                        if hasattr(self, 'shadow_blur_enabled') and (not bool(self.shadow_blur_enabled.get())):
                            blur = 0
                    except Exception:
                        pass
                    try:
                        offx = int(float(self.w_shadow_offx.get()))
                        offy = int(float(self.w_shadow_offy.get()))
                    except Exception:
                        offx, offy = shadow_px, shadow_px
                    try:
                        s_alpha = max(0, min(255, int(float(self.w_shadow_alpha.get()) * 255)))
                    except Exception:
                        s_alpha = 153
                    margin = max(shadow_px, blur) * 3
                    ox1, oy1 = max(0, tx - margin), max(0, ty - margin)
                    ox2, oy2 = min(width, tx + tw + margin), min(height, ty + th + margin)
                    overlay = Image.new('RGBA', (max(1, ox2-ox1), max(1, oy2-oy1)), (0,0,0,0))
                    o_draw = ImageDraw.Draw(overlay)
                    o_draw.text(((tx+offx)-ox1, (ty+offy)-oy1), text, fill=(shadow_col[0], shadow_col[1], shadow_col[2], s_alpha), font=fnt)
                    if blur > 0:
                        overlay = overlay.filter(ImageFilter.GaussianBlur(radius=blur))
                    img.alpha_composite(overlay, (ox1, oy1))
                except Exception:
                    draw.text((tx+shadow_px, ty+shadow_px), text, fill=shadow_col, font=fnt)
            # 본문
            try:
                draw.text((tx, ty), text, fill=col, font=fnt, stroke_width=border_px, stroke_fill=self.w_border_color.get())
            except Exception:
                draw.text((tx, ty), text, fill=col, font=fnt)

        # 최대 3세트 생성
        for idx, ver in enumerate(versions[:3], start=1):
            text = (ver or {}).get('text') or ''
            # 4줄로 분해(부족하면 빈 문자열)
            lines = [ln.strip() for ln in (text.splitlines() if isinstance(text, str) else []) if ln.strip()]
            # 출력 로그
            print(f"[썸네일] 버전 {idx}: 줄 수={len(lines)}")
            for i, ln in enumerate(lines[:4], start=1):
                print(f"  [L{i}] {ln}")
            img = self._make_base_canvas(width, height)
            d = ImageDraw.Draw(img)
            # 1~4행 매핑하여 그리기
            for i in range(1,5):
                label = f"{i}행"
                txt = lines[i-1] if i-1 < len(lines) else ''
                if not txt:
                    continue
                draw_label(img, d, label, txt)
            savep = os.path.join(thumb_dir, f"thumbnail_{idx}.jpg")
            try:
                img.convert('RGB').save(savep, quality=92)
            except Exception:
                img.save(savep.replace('.jpg', '.png'))
            print(f"[썸네일 저장] {savep}")

    def generate_intro_images(self):
        """인트로 설정과 introScript를 사용해 인트로 이미지를 생성합니다."""
        if not getattr(self, 'root', None):
            return
        project_name = self.root.data_page.project_name_var.get()
        identifier = self.root.data_page.identifier_var.get()
        out_dir = os.path.join(config.OUTPUT_PATH, project_name, identifier)
        intro_dir = os.path.join(out_dir, 'intro')
        os.makedirs(intro_dir, exist_ok=True)
        data = getattr(self.root.data_page, 'generated_data', None) or {}
        intro_text = (data.get('introScript') or '').strip()
        if not intro_text:
            self._log_json('[인트로] introScript가 없습니다.')
            print('[인트로] introScript 없음')
            return
        # 인트로 설정 읽기
        try:
            intro_cfg = (self.text_tabs.get("인트로 설정").get_settings() if hasattr(self, 'text_tabs') and self.text_tabs.get("인트로 설정") else (self.default_text_configs or {}).get("인트로 설정", {}))
        except Exception:
            intro_cfg = (self.default_text_configs or {}).get("인트로 설정", {})
        rows_cfg = intro_cfg.get("rows", [])
        if not rows_cfg:
            print('[인트로] 설정 로우가 없습니다.')
            return
        row = rows_cfg[0]
        from PIL import Image, ImageDraw, ImageFont, ImageColor, ImageFilter
        # 해상도
        res_text = intro_cfg.get('해상도') or '1920x1080'
        try:
            width, height = [int(v) for v in res_text.lower().split('x')[:2]]
        except Exception:
            width, height = 1920, 1080

        def as_bool(v):
            try:
                return str(v).strip().lower() in ["true","1","yes","y"]
            except Exception:
                return False

        # 설정 파싱
        try:
            x = int(row.get("x", 100))
        except Exception:
            x = 100
        try:
            y = int(row.get("y", 100))
        except Exception:
            y = 100
        try:
            w = int(row.get("w", 1720))
        except Exception:
            w = 1720
        try:
            size_base = int(row.get("크기(pt)", 64))
        except Exception:
            size_base = 64
        color_hex = row.get("색상", "#FFFFFF")
        align_h = row.get("좌우 정렬", "Left")
        align_v = row.get("상하 정렬", "Top")
        row_bg = as_bool(row.get("바탕", "False"))
        row_shadow = as_bool(row.get("쉐도우", "False"))
        row_border = as_bool(row.get("외곽선", "False"))

        def load_font(px):
            try:
                return ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", px)
            except Exception:
                return ImageFont.load_default()

        # 문장 분리 (마침표/물음표/느낌표 포함 후 분리)
        import re
        sentences = [p.strip() for p in re.split(r"(?<=[\.!\?。？！])\s+", intro_text) if p.strip()]
        print(f"[인트로] 문장 수={len(sentences)}")

        def wrap_text(draw, text, font, max_w):
            # 공백 기준 우선, 없으면 문자 단위로 줄바꿈
            lines = []
            if not text:
                return lines
            tokens = text.split(' ')
            if len(tokens) == 1:
                # 공백이 거의 없는 경우(한글/중문): 문자 단위
                cur = ''
                for ch in text:
                    test = cur + ch
                    tw, _ = draw.textbbox((0,0), test, font=font)[2:]
                    if tw <= max_w:
                        cur = test
                    else:
                        if cur:
                            lines.append(cur)
                        cur = ch
                if cur:
                    lines.append(cur)
                return lines
            # 단어 단위 래핑
            cur = ''
            for t in tokens:
                test = (cur + ' ' + t).strip()
                tw, _ = draw.textbbox((0,0), test, font=font)[2:]
                if not cur or tw <= max_w:
                    cur = test
                else:
                    lines.append(cur)
                    cur = t
            if cur:
                lines.append(cur)
            return lines

        for idx, s in enumerate(sentences, start=1):
            img = self._make_base_canvas(width, height)
            d = ImageDraw.Draw(img)
            # 기본 폰트 및 색상
            fnt = load_font(size_base)
            try:
                col = ImageColor.getrgb(color_hex)
            except Exception:
                col = (255,255,255)
            # 래핑 라인 계산 (폰트 자동 축소 적용)
            size = size_base
            min_size = max(16, int(size_base * 0.5))
            lines = wrap_text(d, s, fnt, w)
            while any(d.textbbox((0,0), ln, font=fnt)[2] > w for ln in lines) and size > min_size:
                size = max(min_size, size - 4)
                fnt = load_font(size)
                lines = wrap_text(d, s, fnt, w)
            # 총 높이 계산 (라인 간격 1.25)
            line_h = d.textbbox((0,0), 'Ag', font=fnt)[3]
            spacing = max(1, int(line_h * 0.25))
            total_h = 0
            bboxes = []
            for ln in lines:
                lb = d.textbbox((0,0), ln, font=fnt)
                bboxes.append(lb)
                total_h += (lb[3] - lb[1]) + spacing
            if bboxes:
                total_h -= spacing
            # 시작 y 계산 (상하 정렬)
            if align_v == 'Middle':
                # 전체 캔버스 기준 세로 중앙 배치
                sy = max(0, (height - total_h) // 2)
            elif align_v == 'Bottom':
                sy = y - total_h
            else:
                sy = y
            # 각 라인 렌더링
            cy = sy
            for i, ln in enumerate(lines):
                tw = d.textbbox((0,0), ln, font=fnt)[2]
                if align_h == 'Center':
                    tx = x + max(0, (w - tw)//2)
                elif align_h == 'Right':
                    tx = x + max(0, (w - tw))
                else:
                    tx = x
                # 바탕 박스(라인별)
                if row_bg:
                    try:
                        bg_rgb = ImageColor.getrgb(self.w_bg.get())
                    except Exception:
                        bg_rgb = (128,128,128)
                    try:
                        alpha_px = max(0, min(255, int(float(self.w_alpha.get()) * 255)))
                    except Exception:
                        alpha_px = 255
                    try:
                        margin_px = int(self.w_margin.get())
                    except Exception:
                        margin_px = 0
                    lb = d.textbbox((tx, cy), ln, font=fnt)
                    overlay = Image.new('RGBA', (width, height), (0,0,0,0))
                    o_draw = ImageDraw.Draw(overlay)
                    o_draw.rectangle((max(0, lb[0]-margin_px), max(0, lb[1]-margin_px), min(width, lb[2]+margin_px), min(height, lb[3]+margin_px)),
                                     fill=(bg_rgb[0], bg_rgb[1], bg_rgb[2], alpha_px))
                    img.alpha_composite(overlay)
                # 쉐도우(블러)
                if row_shadow:
                    try:
                        shadow_px = int(self.w_shadow_thick.get() or 0)
                    except Exception:
                        shadow_px = 0
                    if shadow_px:
                        try:
                            blur = max(0, int(float(self.w_shadow_blur.get())))
                        except Exception:
                            blur = 0
                        try:
                            if hasattr(self, 'shadow_blur_enabled') and (not bool(self.shadow_blur_enabled.get())):
                                blur = 0
                        except Exception:
                            pass
                        try:
                            offx = int(float(self.w_shadow_offx.get()))
                            offy = int(float(self.w_shadow_offy.get()))
                        except Exception:
                            offx, offy = shadow_px, shadow_px
                        try:
                            s_alpha = max(0, min(255, int(float(self.w_shadow_alpha.get()) * 255)))
                        except Exception:
                            s_alpha = 153
                        try:
                            shadow_col = ImageColor.getrgb(self.w_shadow_color.get())
                        except Exception:
                            shadow_col = (0,0,0)
                        lb = d.textbbox((tx, cy), ln, font=fnt)
                        margin = max(shadow_px, blur) * 3
                        ox1, oy1 = max(0, lb[0] - margin), max(0, lb[1] - margin)
                        ox2, oy2 = min(width, lb[2] + margin), min(height, lb[3] + margin)
                        overlay = Image.new('RGBA', (max(1, ox2-ox1), max(1, oy2-oy1)), (0,0,0,0))
                        o_draw = ImageDraw.Draw(overlay)
                        o_draw.text(((tx+offx)-ox1, (cy+offy)-oy1), ln, fill=(shadow_col[0], shadow_col[1], shadow_col[2], s_alpha), font=fnt)
                        if blur > 0:
                            overlay = overlay.filter(ImageFilter.GaussianBlur(radius=blur))
                        img.alpha_composite(overlay, (ox1, oy1))
                # 본문
                try:
                    border_px = int(self.w_border_thick.get() or 0) if row_border else 0
                except Exception:
                    border_px = 0
                try:
                    d.text((tx, cy), ln, fill=col, font=fnt, stroke_width=border_px, stroke_fill=self.w_border_color.get())
                except Exception:
                    d.text((tx, cy), ln, fill=col, font=fnt)
                cy += (d.textbbox((0,0), ln, font=fnt)[3] - d.textbbox((0,0), ln, font=fnt)[1]) + spacing
            savep = os.path.join(intro_dir, f"intro_{idx:03d}.png")
            img.save(savep)
            print(f"[인트로 저장] {savep}")

    def generate_ending_images(self):
        """엔딩 설정과 endingScript를 사용해 엔딩 이미지를 생성합니다."""
        if not getattr(self, 'root', None):
            return
        project_name = self.root.data_page.project_name_var.get()
        identifier = self.root.data_page.identifier_var.get()
        out_dir = os.path.join(config.OUTPUT_PATH, project_name, identifier)
        ending_dir = os.path.join(out_dir, 'ending')
        os.makedirs(ending_dir, exist_ok=True)
        data = getattr(self.root.data_page, 'generated_data', None) or {}
        ending_text = (data.get('endingScript') or '').strip()
        if not ending_text:
            self._log_json('[엔딩] endingScript가 없습니다.')
            print('[엔딩] endingScript 없음')
            return
        # 엔딩 설정 읽기
        try:
            ending_cfg = (self.text_tabs.get("엔딩 설정").get_settings() if hasattr(self, 'text_tabs') and self.text_tabs.get("엔딩 설정") else (self.default_text_configs or {}).get("엔딩 설정", {}))
        except Exception:
            ending_cfg = (self.default_text_configs or {}).get("엔딩 설정", {})
        rows_cfg = ending_cfg.get("rows", [])
        if not rows_cfg:
            print('[엔딩] 설정 로우가 없습니다.')
            return
        row = rows_cfg[0]
        from PIL import Image, ImageDraw, ImageFont, ImageColor, ImageFilter
        # 해상도
        res_text = ending_cfg.get('해상도') or '1920x1080'
        try:
            width, height = [int(v) for v in res_text.lower().split('x')[:2]]
        except Exception:
            width, height = 1920, 1080

        def as_bool(v):
            try:
                return str(v).strip().lower() in ["true","1","yes","y"]
            except Exception:
                return False

        # 설정 파싱
        try:
            x = int(row.get("x", 100))
        except Exception:
            x = 100
        try:
            y = int(row.get("y", 100))
        except Exception:
            y = 100
        try:
            w = int(row.get("w", 1720))
        except Exception:
            w = 1720
        try:
            size_base = int(row.get("크기(pt)", 64))
        except Exception:
            size_base = 64
        color_hex = row.get("색상", "#FFFFFF")
        align_h = row.get("좌우 정렬", "Left")
        align_v = row.get("상하 정렬", "Top")
        row_bg = as_bool(row.get("바탕", "False"))
        row_shadow = as_bool(row.get("쉐도우", "False"))
        row_border = as_bool(row.get("외곽선", "False"))

        def load_font(px):
            try:
                return ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", px)
            except Exception:
                return ImageFont.load_default()

        # 문장 분리
        import re
        sentences = [p.strip() for p in re.split(r"(?<=[\.!\?。？！])\s+", ending_text) if p.strip()]
        print(f"[엔딩] 문장 수={len(sentences)}")

        def wrap_text(draw, text, font, max_w):
            lines = []
            if not text:
                return lines
            tokens = text.split(' ')
            if len(tokens) == 1:
                cur = ''
                for ch in text:
                    test = cur + ch
                    tw, _ = draw.textbbox((0,0), test, font=font)[2:]
                    if tw <= max_w:
                        cur = test
                    else:
                        if cur:
                            lines.append(cur)
                        cur = ch
                if cur:
                    lines.append(cur)
                return lines
            cur = ''
            for t in tokens:
                test = (cur + ' ' + t).strip()
                tw, _ = draw.textbbox((0,0), test, font=font)[2:]
                if not cur or tw <= max_w:
                    cur = test
                else:
                    lines.append(cur)
                    cur = t
            if cur:
                lines.append(cur)
            return lines

        for idx, s in enumerate(sentences, start=1):
            img = self._make_base_canvas(width, height)
            d = ImageDraw.Draw(img)
            fnt = load_font(size_base)
            try:
                col = ImageColor.getrgb(color_hex)
            except Exception:
                col = (255,255,255)
            size = size_base
            min_size = max(16, int(size_base * 0.5))
            lines = wrap_text(d, s, fnt, w)
            while any(d.textbbox((0,0), ln, font=fnt)[2] > w for ln in lines) and size > min_size:
                size = max(min_size, size - 4)
                fnt = load_font(size)
                lines = wrap_text(d, s, fnt, w)
            line_h = d.textbbox((0,0), 'Ag', font=fnt)[3]
            spacing = max(1, int(line_h * 0.25))
            total_h = 0
            for ln in lines:
                lb = d.textbbox((0,0), ln, font=fnt)
                total_h += (lb[3] - lb[1]) + spacing
            if lines:
                total_h -= spacing
            if align_v == 'Middle':
                # 전체 캔버스 기준 세로 중앙 배치
                sy = max(0, (height - total_h) // 2)
            elif align_v == 'Bottom':
                sy = y - total_h
            else:
                sy = y
            cy = sy
            for ln in lines:
                tw = d.textbbox((0,0), ln, font=fnt)[2]
                if align_h == 'Center':
                    tx = x + max(0, (w - tw)//2)
                elif align_h == 'Right':
                    tx = x + max(0, (w - tw))
                else:
                    tx = x
                # 바탕 박스
                if row_bg:
                    try:
                        bg_rgb = ImageColor.getrgb(self.w_bg.get())
                    except Exception:
                        bg_rgb = (128,128,128)
                    try:
                        alpha_px = max(0, min(255, int(float(self.w_alpha.get()) * 255)))
                    except Exception:
                        alpha_px = 255
                    try:
                        margin_px = int(self.w_margin.get())
                    except Exception:
                        margin_px = 0
                    lb = d.textbbox((tx, cy), ln, font=fnt)
                    overlay = Image.new('RGBA', (width, height), (0,0,0,0))
                    o_draw = ImageDraw.Draw(overlay)
                    o_draw.rectangle((max(0, lb[0]-margin_px), max(0, lb[1]-margin_px), min(width, lb[2]+margin_px), min(height, lb[3]+margin_px)),
                                     fill=(bg_rgb[0], bg_rgb[1], bg_rgb[2], alpha_px))
                    img.alpha_composite(overlay)
                # 쉐도우
                if row_shadow:
                    try:
                        shadow_px = int(self.w_shadow_thick.get() or 0)
                    except Exception:
                        shadow_px = 0
                    if shadow_px:
                        try:
                            blur = max(0, int(float(self.w_shadow_blur.get())))
                        except Exception:
                            blur = 0
                        try:
                            if hasattr(self, 'shadow_blur_enabled') and (not bool(self.shadow_blur_enabled.get())):
                                blur = 0
                        except Exception:
                            pass
                        try:
                            offx = int(float(self.w_shadow_offx.get()))
                            offy = int(float(self.w_shadow_offy.get()))
                        except Exception:
                            offx, offy = shadow_px, shadow_px
                        try:
                            s_alpha = max(0, min(255, int(float(self.w_shadow_alpha.get()) * 255)))
                        except Exception:
                            s_alpha = 153
                        try:
                            shadow_col = ImageColor.getrgb(self.w_shadow_color.get())
                        except Exception:
                            shadow_col = (0,0,0)
                        lb = d.textbbox((tx, cy), ln, font=fnt)
                        margin = max(shadow_px, blur) * 3
                        ox1, oy1 = max(0, lb[0] - margin), max(0, lb[1] - margin)
                        ox2, oy2 = min(width, lb[2] + margin), min(height, lb[3] + margin)
                        overlay = Image.new('RGBA', (max(1, ox2-ox1), max(1, oy2-oy1)), (0,0,0,0))
                        o_draw = ImageDraw.Draw(overlay)
                        o_draw.text(((tx+offx)-ox1, (cy+offy)-oy1), ln, fill=(shadow_col[0], shadow_col[1], shadow_col[2], s_alpha), font=fnt)
                        if blur > 0:
                            overlay = overlay.filter(ImageFilter.GaussianBlur(radius=blur))
                        img.alpha_composite(overlay, (ox1, oy1))
                # 본문
                try:
                    border_px = int(self.w_border_thick.get() or 0) if row_border else 0
                except Exception:
                    border_px = 0
                try:
                    d.text((tx, cy), ln, fill=col, font=fnt, stroke_width=border_px, stroke_fill=self.w_border_color.get())
                except Exception:
                    d.text((tx, cy), ln, fill=col, font=fnt)
                cy += (d.textbbox((0,0), ln, font=fnt)[3] - d.textbbox((0,0), ln, font=fnt)[1]) + spacing
            savep = os.path.join(ending_dir, f"ending_{idx:03d}.png")
            img.save(savep)
            print(f"[엔딩 저장] {savep}")

    def _on_click_browse(self):
        try:
            kind = (self.bg_type_var.get() or "").strip()
            if kind == "이미지":
                filetypes = [("Image files", "*.jpg *.jpeg *.png")]
            elif kind == "동영상":
                filetypes = [("Video files", "*.mp4")]
            else:
                filetypes = [("All files", "*.*")]
            path = filedialog.askopenfilename(title="파일 선택", filetypes=filetypes)
            if path:
                self.w_bg_value.delete(0, tk.END)
                self.w_bg_value.insert(0, path)
        except Exception as e:
            try:
                self._log_json(f"[찾아보기 오류] {e}")
            except Exception:
                pass

    def _on_bg_type_change(self):
        try:
            kind = (self.bg_type_var.get() or "").strip()
            # 색상 선택: 기본값 표시 및 텍스트 편집 가능, 찾아보기 비활성화
            if kind == "색상":
                try:
                    self.w_bg_value.configure(state="normal")
                    self.w_bg_value.delete(0, tk.END)
                    self.w_bg_value.insert(0, "#000000")
                except Exception:
                    pass
                try:
                    self.btn_browse.configure(state="disabled")
                except Exception:
                    pass
            else:
                # 이미지/동영상: 경로 입력은 직접 편집도 가능하지만 기본은 비워두고 찾아보기 활성화
                try:
                    self.w_bg_value.configure(state="normal")
                    if not (self.w_bg_value.get() or "").strip():
                        self.w_bg_value.delete(0, tk.END)
                except Exception:
                    pass
                try:
                    self.btn_browse.configure(state="normal")
                except Exception:
                    pass
        except Exception:
            pass

    def _on_click_video(self):
        try:
            if not getattr(self, 'root', None):
                return
            project_name = self.root.data_page.project_name_var.get()
            identifier = self.root.data_page.identifier_var.get()
            out_dir = os.path.join(config.OUTPUT_PATH, project_name, identifier)
            dialog_dir = os.path.join(out_dir, 'dialog')
            if not os.path.isdir(dialog_dir):
                self._log_json('[비디오] dialog 폴더에 PNG가 없습니다. 먼저 미리보기를 생성하세요.')
                return
            out_mp4 = os.path.join(out_dir, f'{identifier}_dialog_preview.mp4')
            import subprocess, tempfile, glob, io, wave, struct
            # 1) 대화 행 로드
            data = getattr(self.root.data_page, 'generated_data', None) or {}
            dialogue_csv = (data.get('fullVideoScript') or {}).get('dialogueCsv') or data.get('dialogueCsv')
            if not dialogue_csv:
                self._log_json('[비디오] dialogueCsv가 없습니다. 데이터 생성/읽기를 먼저 수행하세요.')
                return
            lines = [row for row in dialogue_csv.splitlines() if row.strip()][1:]
            # 2) 화자/언어 설정 확보 (DataTabView 로직 준용)
            speaker_page = getattr(self.root, 'speaker_page', None)
            if not speaker_page:
                self._log_json('[비디오] 화자 설정 탭을 먼저 구성하세요.')
                return
            native_voice_name = speaker_page.native_speaker_dropdown.get()
            learner_voice_names = [w["dropdown"].get() for w in speaker_page.learner_speaker_widgets]
            native_lang_code = speaker_page.native_lang_code
            learning_lang_code = speaker_page.learning_lang_code
            if not native_voice_name or not learner_voice_names or not native_lang_code or not learning_lang_code:
                # DataTabView를 통해 언어 설정 로드
                data_page = getattr(self.root, 'data_page', None)
                if not data_page:
                    self._log_json('[비디오] 데이터 탭을 찾을 수 없습니다.')
                    return
                n_code, l_code = data_page.get_selected_language_codes()
                speaker_page.update_language_settings(
                    native_lang_code=n_code,
                    learning_lang_code=l_code,
                    project_name=project_name,
                    identifier=identifier
                )
                native_voice_name = speaker_page.native_speaker_dropdown.get()
                learner_voice_names = [w["dropdown"].get() for w in speaker_page.learner_speaker_widgets]
                native_lang_code = speaker_page.native_lang_code
                learning_lang_code = speaker_page.learning_lang_code
            # 보정: 기본 화자 채우기
            from src import api_services
            if (not native_voice_name) and native_lang_code:
                voices = api_services.get_voices_for_language(native_lang_code)
                if voices:
                    native_voice_name = voices[0]
                    speaker_page.native_speaker_dropdown.set(native_voice_name)
            if (not learner_voice_names) and learning_lang_code:
                voices = api_services.get_voices_for_language(learning_lang_code)
                if voices:
                    if not speaker_page.learner_speaker_widgets:
                        speaker_page._update_learner_speakers_ui(1)
                    speaker_page.learner_speaker_widgets[0]["dropdown"].set(voices[0])
                    learner_voice_names = [w["dropdown"].get() for w in speaker_page.learner_speaker_widgets]
            if not native_voice_name or not learner_voice_names:
                self._log_json('[비디오] 화자 정보를 확인하세요.')
                return
            # 3) 오디오 세그먼트 생성 + 길이 측정
            def synth_wav_bytes(text: str, lang: str, voice: str) -> bytes:
                return api_services.synthesize_speech(text, lang, voice, audio_encoding="LINEAR16", sample_rate_hz=16000) or b""
            def silence_wav(duration_sec: float = 1.0, sample_rate: int = 16000) -> bytes:
                num_samples = int(sample_rate * duration_sec)
                buf = io.BytesIO()
                with wave.open(buf, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(sample_rate)
                    silence_frame = struct.pack('<h', 0)
                    for _ in range(num_samples):
                        wf.writeframes(silence_frame)
                return buf.getvalue()
            def wav_duration_seconds(wav_bytes: bytes) -> float:
                if not wav_bytes:
                    return 0.0
                with wave.open(io.BytesIO(wav_bytes), 'rb') as wf:
                    frames = wf.getnframes()
                    rate = wf.getframerate()
                    if rate <= 0:
                        return 0.0
                    return frames / float(rate)
            def concat_wav(segments: list[bytes]) -> bytes:
                import wave as _wave
                out = io.BytesIO()
                with _wave.open(out, 'wb') as wf_out:
                    wf_out.setnchannels(1)
                    wf_out.setsampwidth(2)
                    wf_out.setframerate(16000)
                    for seg in segments:
                        with _wave.open(io.BytesIO(seg), 'rb') as wf_in:
                            wf_out.writeframes(wf_in.readframes(wf_in.getnframes()))
                return out.getvalue()
            def write_wav(wav_bytes: bytes, out_wav_path: str):
                with open(out_wav_path, 'wb') as f:
                    f.write(wav_bytes)
            rows = []
            import csv, io as _io
            reader = csv.reader(_io.StringIO(dialogue_csv))
            entries = list(reader)
            if entries and [c.strip('"') for c in entries[0][:4]] == ["순번","원어","학습어","읽기"]:
                entries = entries[1:]
            for row in entries:
                cols = [c.strip('"') for c in row]
                seq = cols[0] if len(cols) > 0 else ''
                native = cols[1] if len(cols) > 1 else ''
                learning = cols[2] if len(cols) > 2 else ''
                reading = cols[3] if len(cols) > 3 else ''
                rows.append((seq, native, learning, reading))
            # 4) 프레임별 지속시간 계산 및 오디오 결합 세그먼트 준비
            a_b_frames: list[tuple[str, float]] = []
            audio_segments: list[bytes] = []
            gap = silence_wav(1.0)
            for idx, (_seq, native_text, learning_text, _reading_text) in enumerate(rows, start=1):
                # A: native
                a_png = os.path.join(dialog_dir, f"{identifier}_{idx:03d}_a.png")
                b_png = os.path.join(dialog_dir, f"{identifier}_{idx:03d}_b.png")
                nat_wav = synth_wav_bytes(native_text, native_lang_code, native_voice_name) if native_text.strip() else b""
                nat_dur = wav_duration_seconds(nat_wav)
                if nat_wav:
                    audio_segments.append(nat_wav)
                    audio_segments.append(gap)
                # A 프레임은 원어 구간 + 화자간 무음 1초까지 포함
                a_b_frames.append((a_png, max(0.1, nat_dur + 1.0)))
                # B: learners
                b_total = 0.0
                if learning_text.strip():
                    num_learners = len(learner_voice_names)
                    for i, vname in enumerate(learner_voice_names):
                        lwav = synth_wav_bytes(learning_text, learning_lang_code, vname)
                        ldur = wav_duration_seconds(lwav)
                        if lwav:
                            audio_segments.append(lwav)
                            # 화자 간 무음: 마지막 화자 뒤에는 추가하지 않음
                            if i < num_learners - 1:
                                audio_segments.append(gap)
                        b_total += ldur
                        if i < num_learners - 1:
                            b_total += 1.0  # 화자 사이 무음
                a_b_frames.append((b_png, max(0.1, b_total)))
            # 5) 오디오 MP3 저장
            if not audio_segments:
                self._log_json('[비디오] 생성된 오디오 세그먼트가 없습니다.')
                return
            combined_wav = concat_wav(audio_segments)
            out_wav = os.path.join(out_dir, f"{identifier}_dialog.wav")
            write_wav(combined_wav, out_wav)
            # 6) 배경 이미지 준비 및 비디오 생성
            # 배경 이미지/색상으로 base 비디오 생성
            bg_kind = (self.bg_type_var.get() or "").strip()
            bg_value = (self.w_bg_value.get() or "").strip()
            
            # 해상도 추출
            resolution = self._get_current_resolution()
            width, height = map(int, resolution.split('x'))
            
            # 배경 base 비디오 생성
            base_video_path = os.path.join(out_dir, f"{identifier}_base.mp4")
            if bg_kind == "색상" and bg_value:
                # 색상 배경으로 1초 비디오 생성
                cmd_base = [
                    'ffmpeg', '-y', '-loglevel', 'error',
                    '-f', 'lavfi',
                    '-i', f'color=c={bg_value}:s={width}x{height}:d=1',
                    '-pix_fmt', 'yuv420p',
                    base_video_path
                ]
            elif bg_kind == "이미지" and bg_value and os.path.isfile(bg_value):
                # 이미지 배경으로 1초 비디오 생성
                cmd_base = [
                    'ffmpeg', '-y', '-loglevel', 'error',
                    '-loop', '1',
                    '-i', bg_value,
                    '-t', '1',
                    '-vf', f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2',
                    '-pix_fmt', 'yuv420p',
                    base_video_path
                ]
            elif bg_kind == "동영상" and bg_value and os.path.isfile(bg_value):
                # 동영상 배경으로 1초 비디오 생성 (첫 프레임 사용)
                cmd_base = [
                    'ffmpeg', '-y', '-loglevel', 'error',
                    '-i', bg_value,
                    '-ss', '0',
                    '-t', '1',
                    '-vf', f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2',
                    '-pix_fmt', 'yuv420p',
                    base_video_path
                ]
            else:
                # 기본 검은색 배경
                cmd_base = [
                    'ffmpeg', '-y', '-loglevel', 'error',
                    '-f', 'lavfi',
                    '-i', f'color=c=black:s={width}x{height}:d=1',
                    '-pix_fmt', 'yuv420p',
                    base_video_path
                ]
            
            subprocess.run(cmd_base, check=True)
            
            # 7) 각 프레임을 배경 위에 overlay하여 최종 비디오 생성
            temp_videos = []
            for idx, (png_path, duration) in enumerate(a_b_frames):
                temp_video = os.path.join(out_dir, f"{identifier}_temp_{idx:03d}.mp4")
                temp_videos.append(temp_video)
                
                # PNG를 배경 위에 overlay하여 비디오 생성
                cmd_overlay = [
                    'ffmpeg', '-y', '-loglevel', 'error',
                    '-i', base_video_path,
                    '-i', png_path,
                    '-filter_complex', f'[0:v][1:v]overlay=0:0:shortest=1',
                    '-t', str(duration),
                    '-pix_fmt', 'yuv420p',
                    temp_video
                ]
                subprocess.run(cmd_overlay, check=True)
            
            # 8) concat 리스트 작성 후 최종 비디오 생성
            with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.txt') as listf:
                for temp_video in temp_videos:
                    listf.write(f"file '{temp_video}'\n")
                list_path = listf.name
            
            cmd_final = [
                'ffmpeg', '-y', '-loglevel', 'error',
                '-f', 'concat', '-safe', '0', '-i', list_path,
                '-i', out_wav,
                '-pix_fmt', 'yuv420p',
                '-shortest',
                out_mp4
            ]
            subprocess.run(cmd_final, check=True)
            
            # 임시 파일들 정리
            os.remove(list_path)
            os.remove(base_video_path)
            for temp_video in temp_videos:
                os.remove(temp_video)
            self._log_json(f'[비디오] 생성 완료: {out_mp4}')
        except Exception as e:
            self._log_json(f'[비디오 오류] {e}')

    def _log_json(self, message: str):
        try:
            self.json_viewer.insert('end', message + "\n")
            self.json_viewer.see('end')
        except Exception:
            pass

    def _get_current_resolution(self):
        """현재 선택된 해상도를 반환합니다."""
        try:
            # 현재 활성화된 텍스트 설정 탭에서 해상도 가져오기
            current_tab = self.tab_view.get()
            if current_tab in self.text_tabs:
                tab = self.text_tabs[current_tab]
                if hasattr(tab, '_controls') and "해상도" in tab._controls:
                    resolution = tab._controls["해상도"].get()
                    if resolution and 'x' in resolution:
                        return resolution
        except Exception:
            pass
        
        # 기본값 반환
        return "1920x1080"

class TextSettingsTab(ctk.CTkFrame):
    def __init__(self, parent, default_data):
        super().__init__(parent, fg_color=config.COLOR_THEME["widget"])
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._controls = {}
        self._grid_widgets = []
        
        # --- 상단 컨트롤 ---
        top_controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_controls_frame.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        
        def create_top_control(p, label, width_chars, values, default_val):
            frame = ctk.CTkFrame(p, fg_color="transparent")
            ctk.CTkLabel(frame, text=f"{label}:").pack(side="left", padx=(0, 3))
            combo = ctk.CTkComboBox(frame, values=values, width=width_chars * 9, 
                                  fg_color=config.COLOR_THEME["widget"], 
                                  text_color=config.COLOR_THEME["text"])
            combo.set(default_val)
            combo.pack(side="left")
            frame.pack(side="left", padx=(0, 20))
            return combo

        self._controls["행수"] = create_top_control(top_controls_frame, "텍스트 행수", 6, [str(i) for i in range(1, 11)], default_data["행수"])
        self._controls["비율"] = create_top_control(top_controls_frame, "화면비율", 10, ["16:9", "1:1", "9:16"], default_data["비율"])
        self._controls["해상도"] = create_top_control(top_controls_frame, "해상도", 15, ["1920x1080", "1080x1080", "1080x1920", "1024x768"], default_data["해상도"])

        # --- 설정 그리드 ---
        grid_frame = ctk.CTkScrollableFrame(self)
        grid_frame.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        
        headers = ["행", "x", "y", "w", "크기(pt)", "폰트(pt)", "색상", "굵기", "좌우 정렬", "상하 정렬", "바탕", "쉐도우", "외곽선"]
        col_widths = {"행": 5, "x": 5, "y": 5, "w": 6, "크기(pt)": 5, "폰트(pt)": 30, "색상": 10, "굵기": 8, "좌우 정렬": 8, "상하 정렬": 8, "바탕": 6, "쉐도우": 6, "외곽선": 6}

        for col, header_text in enumerate(headers):
            hdr_cell = ctk.CTkLabel(grid_frame, text=header_text, justify="center", anchor="center")
            hdr_cell.grid(row=0, column=col, padx=2, pady=5, sticky="nsew")

        font_options = ["Noto Sans KR", "KoPubWorld돋움체", "KoPubWorld바탕체"]
        weight_options = ["Light", "Medium", "Bold"]
        h_align_options = ["Left", "Center", "Right"]
        v_align_options = ["Top", "Middle", "Bottom"]

        for row_idx, row_data in enumerate(default_data["rows"], start=1):
            for col_idx, key in enumerate(headers):
                pixel_width = col_widths.get(key, 10) * 9 
                params = {"master": grid_frame, "width": pixel_width, 
                          "fg_color": config.COLOR_THEME["widget"], 
                          "text_color": config.COLOR_THEME["text"]}
                
                if key == "행":
                    widget = ctk.CTkLabel(grid_frame, text=row_data.get(key), justify="center")
                elif key in ["폰트(pt)", "굵기", "좌우 정렬", "상하 정렬"]:
                    if key == "폰트(pt)":
                        values = font_options
                    elif key == "굵기":
                        values = weight_options
                    elif key == "좌우 정렬":
                        values = h_align_options
                    else:
                        values = v_align_options
                    widget = ctk.CTkComboBox(**params, values=values)
                    widget.set(row_data.get(key))
                else:
                    if key in ["바탕", "쉐도우", "외곽선"]:
                        # 중앙정렬 컨테이너에 체크박스 배치
                        container = ctk.CTkFrame(grid_frame, fg_color="transparent", width=pixel_width)
                        try:
                            container.grid_propagate(False)
                        except Exception:
                            pass
                        val = str(row_data.get(key, "False")).lower() in ["true", "1", "yes", "y"]
                        var = tk.BooleanVar(value=val)
                        cb = ctk.CTkCheckBox(container, text="", variable=var)
                        cb.pack(expand=True)
                        # 헤더 중앙 정렬과 시각적 일치: 컨테이너도 고정 높이 적용
                        try:
                            container.configure(height=26)
                        except Exception:
                            pass
                        container.grid(row=row_idx, column=col_idx, padx=1, pady=1)
                        widget = cb
                    else:
                        widget = ctk.CTkEntry(**params, justify="center")
                        widget.insert(0, str(row_data.get(key, '')))
                    
                widget.grid(row=row_idx, column=col_idx, padx=1, pady=1) if not (key in ["바탕", "쉐도우", "외곽선"]) else None
                self._grid_widgets.append((row_idx, key, widget))

    def get_settings(self):
        try:
            result = {
                "행수": self._controls.get("행수").get() if self._controls.get("행수") else "",
                "비율": self._controls.get("비율").get() if self._controls.get("비율") else "",
                "해상도": self._controls.get("해상도").get() if self._controls.get("해상도") else "",
                "rows": []
            }
            # 행 이름 수집
            row_names = {}
            for row_idx, key, widget in self._grid_widgets:
                if key == "행":
                    row_names[row_idx] = widget.cget("text")
            # 값 수집
            row_map = {idx: {"행": name} for idx, name in row_names.items()}
            for row_idx, key, widget in self._grid_widgets:
                if key == "행":
                    continue
                if isinstance(widget, ctk.CTkCheckBox):
                    # 체크박스는 True/False 문자열로 저장
                    val = "True" if widget.get() in [True, "True", "1", 1] else "False"
                elif isinstance(widget, ctk.CTkComboBox):
                    val = widget.get()
                elif isinstance(widget, ctk.CTkEntry):
                    val = widget.get()
                else:
                    val = getattr(widget, 'get', lambda: '')()
                row_map.setdefault(row_idx, {"행": row_names.get(row_idx, str(row_idx))})
                row_map[row_idx][key] = val
            result["rows"] = [row_map[idx] for idx in sorted(row_map.keys())]
            return result
        except Exception:
            return {"행수": "", "비율": "", "해상도": "", "rows": []}

    def apply_settings(self, data):
        try:
            if self._controls.get("행수") and data.get("행수"):
                self._controls["행수"].set(str(data.get("행수")))
            if self._controls.get("비율") and data.get("비율"):
                self._controls["비율"].set(str(data.get("비율")))
            if self._controls.get("해상도") and data.get("해상도"):
                self._controls["해상도"].set(str(data.get("해상도")))
            rows = data.get("rows", [])
            # row 이름 인덱스 맵 구성
            rowidx_to_name = {}
            for row_idx, key, widget in self._grid_widgets:
                if key == "행":
                    rowidx_to_name[row_idx] = widget.cget("text")
            # 위젯에 값 반영
            for row_idx, key, widget in self._grid_widgets:
                if key == "행":
                    continue
                row_name = rowidx_to_name.get(row_idx)
                row_data = next((r for r in rows if str(r.get("행")) == str(row_name)), None)
                if not row_data:
                    continue
                val = row_data.get(key)
                if val is None:
                    continue
                if isinstance(widget, ctk.CTkCheckBox):
                    # 체크박스 복원
                    val_str = str(val)
                    if val_str in ["True", "1", "true", "YES", "Yes", "y", "Y"]:
                        widget.select()
                    else:
                        widget.deselect()
                elif isinstance(widget, ctk.CTkComboBox):
                    widget.set(str(val))
                elif isinstance(widget, ctk.CTkEntry):
                    widget.delete(0, tk.END)
                    widget.insert(0, str(val))
        except Exception:
            pass