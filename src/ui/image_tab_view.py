import customtkinter as ctk
from src import config
import tkinter as tk
import os
import json
from tkinter import filedialog
from tkinter import colorchooser # Color chooser import
from src.ui.ui_utils import create_labeled_widget
import traceback

class ImageTabView(ctk.CTkFrame):
    # 명세에 따른 새로운 기본값
    defaults = {
        "conversation": {
            "main_background": {"type": "이미지", "value": "/Users/janghwanmoon/Projects/captionGen/assets/background/shubham-dhage-1pK0lHvVaeM-unsplash.jpg"},
            "line_spacing": {"ratio": 0.8},
            "background_box": {"type": "없음", "color": "#000000", "alpha": 0.2, "margin": 2},
            "shadow": {"useBlur": True, "thick": 2, "color": "#000000", "blur": 8, "offx": 2, "offy": 2, "alpha": 0.6},
            "border": {"thick": 2, "color": "#000000"},
            "행수": "4", "비율": "16:9", "해상도": "1920x1080" ,
            "rows": [
                {"행": "순번", "x": 50, "y": 50, "w": 1820, "크기(pt)": 80, "폰트(pt)": "KoPubWorld돋움체 Bold", "색상": "#FFFFFF", "좌우 정렬": "Left", "상하 정렬": "Top", "바탕": False, "쉐도우": False, "외곽선": False},
                {"행": "원어", "x": 50, "y": 150, "w": 1820, "크기(pt)": 100, "폰트(pt)": "KoPubWorld돋움체 Bold", "색상": "#00FFFF", "좌우 정렬": "Center", "상하 정렬": "Top", "바탕": False, "쉐도우": False, "외곽선": False},
                {"행": "학습어", "x": 50, "y": 450, "w": 1820, "크기(pt)": 100, "폰트(pt)": "Noto Sans KR Bold", "색상": "#FF00FF", "좌우 정렬": "Center", "상하 정렬": "Top", "바탕": False, "쉐도우": False, "외곽선": False},
                {"행": "읽기", "x": 50, "y": 750, "w": 1820, "크기(pt)": 100, "폰트(pt)": "KoPubWorld돋움체 Bold", "색상": "#FFFF00", "좌우 정렬": "Center", "상하 정렬": "Top", "바탕": False, "쉐도우": False, "외곽선": False},
            ]
        },
        "thumbnail": {
            "main_background": {"type": "이미지", "value": ""},
            "line_spacing": {"ratio": 1.0},
            "background_box": {"type": "블록", "color": "#000000", "alpha": 0.7, "margin": 10},
            "shadow": {"useBlur": True, "thick": 5, "color": "#FFFFFF", "blur": 10, "offx": 0, "offy": 0, "alpha": 0.5},
            "border": {"thick": 0, "color": "#000000"},
            "행수": "4", "비율": "16:9", "해상도": "1920x1080" ,
            "rows": [
                {"행": "제목", "x": 50, "y": 50, "w": 924, "크기(pt)": 100, "폰트(pt)": "KoPubWorld돋움체 Bold", "색상": "#FFFFFF", "좌우 정렬": "Left", "상하 정렬": "Top", "바탕": True, "쉐도우": True, "외곽선": False},
                {"행": "부제목", "x": 50, "y": 200, "w": 924, "크기(pt)": 100, "폰트(pt)": "KoPubWorld돋움체 Bold", "색상": "#00FFFF", "좌우 정렬": "Left", "상하 정렬": "Top", "바탕": True, "쉐도우": True, "외곽선": False},
                {"행": "설명", "x": 50, "y": 350, "w": 924, "크기(pt)": 100, "폰트(pt)": "KoPubWorld돋움체 Bold", "색상": "#FF00FF", "좌우 정렬": "Left", "상하 정렬": "Top", "바탕": True, "쉐도우": True, "외곽선": False},
                {"행": "태그", "x": 50, "y": 500, "w": 924, "크기(pt)": 100, "폰트(pt)": "KoPubWorld돋움체 Bold", "색상": "#FFFF00", "좌우 정렬": "Left", "상하 정렬": "Top", "바탕": True, "쉐도우": True, "외곽선": False},
            ]
        },
        "intro": {
            "main_background": {"type": "색상", "value": "#111111"},
            "line_spacing": {"ratio": 1.2},
            "background_box": {"type": "없음", "color": "#000000", "alpha": 0.5, "margin": 5},
            "shadow": {"useBlur": False, "thick": 2, "color": "#FFFFFF", "blur": 5, "offx": 2, "offy": 2, "alpha": 0.8},
            "border": {"thick": 1, "color": "#FFFFFF"},
            "행수": "1", "비율": "16:9", "해상도": "1920x1080" ,
            "rows": [{"행": "인트로", "x": 50, "y": 50, "w": 1820, "크기(pt)": 80, "폰트(pt)": "KoPubWorld돋움체 Bold", "색상": "#FFFFFF", "좌우 정렬": "Left", "상하 정렬": "Top", "바탕": True, "쉐도우": True, "외곽선": True}]
        },
        "ending": {
            "main_background": {"type": "색상", "value": "#222222"},
            "line_spacing": {"ratio": 1.2},
            "background_box": {"type": "없음", "color": "#000000", "alpha": 0.5, "margin": 5},
            "shadow": {"useBlur": True, "thick": 3, "color": "#000000", "blur": 5, "offx": 3, "offy": 3, "alpha": 0.7},
            "border": {"thick": 0, "color": "#000000"},
            "행수": "1", "비율": "16:9", "해상도": "1920x1080" ,
            "rows": [{"행": "엔딩", "x": 50, "y": 50, "w": 1820, "크기(pt)": 100, "폰트(pt)": "KoPubWorld돋움체 Bold", "색상": "#FFFFFF", "좌우 정렬": "Left", "상하 정렬": "Top", "바탕": False, "쉐도우": True, "외곽선": False}]
        },
        "dialogue": {
            "main_background": {"type": "색상", "value": "#000000"},
            "line_spacing": {"ratio": 0.8},
            "background_box": {"type": "블록", "color": "#000000", "alpha": 0.5, "margin": 5},
            "shadow": {"useBlur": True, "thick": 2, "color": "#000000", "blur": 8, "offx": 2, "offy": 2, "alpha": 0.6},
            "border": {"thick": 2, "color": "#000000"},
            "행수": "3", "비율": "16:9", "해상도": "1920x1080" ,
            "rows": [
                {"행": "원어", "x": 50, "y": 250, "w": 1820, "크기(pt)": 100, "폰트(pt)": "KoPubWorld돋움체 Bold", "색상": "#FFFFFF", "좌우 정렬": "Left", "상하 정렬": "Top", "바탕": True, "쉐도우": False, "외곽선": False},
                {"행": "학습어1", "x": 50, "y": 550, "w": 1820, "크기(pt)": 100, "폰트(pt)": "KoPubWorld돋움체 Bold", "색상": "#FFFFFF", "좌우 정렬": "Left", "상하 정렬": "Top", "바탕": True, "쉐도우": False, "외곽선": False},
                {"행": "학습어2", "x": 50, "y": 850, "w": 1820, "크기(pt)": 100, "폰트(pt)": "KoPubWorld돋움체 Bold", "색상": "#FFFFFF", "좌우 정렬": "Left", "상하 정렬": "Top", "바탕": True, "쉐도우": False, "외곽선": False},
            ]
        },
    }

    def __init__(self, parent, root=None):
        super().__init__(parent, fg_color="transparent")
        self.root = root
        self.current_script_name = None

        try:
            config_path = os.path.join(config.BASE_DIR, 'config.json')
            with open(config_path, 'r', encoding='utf-8') as f:
                self.app_config = json.load(f)
            self.font_options = list(self.app_config.get("fonts", {}).keys())
        except (FileNotFoundError, json.JSONDecodeError):
            self.app_config = {}
            self.font_options = ["Arial"] # Fallback

        self.defaults = self._get_updated_defaults()
        
        # _text_settings.json 파일에서 설정 로드 시도
        try:
            text_settings_path = os.path.join(config.BASE_DIR, '_text_settings.json')
            if os.path.exists(text_settings_path):
                with open(text_settings_path, 'r', encoding='utf-8') as f:
                    saved_settings = json.load(f)
                print(f"✅ [UI] _text_settings.json 파일에서 설정 로드 완료")
                print(f"🔍 [UI] 로드된 설정 키들: {list(saved_settings.keys())}")
                
                # 저장된 설정으로 script_settings 초기화
                self.script_settings = {}
                for script_type, settings in saved_settings.items():
                    self.script_settings[script_type] = settings.copy()
                    print(f"🔍 [UI] {script_type} 설정 로드: {list(settings.keys())}")
            else:
                print(f"⚠️ [UI] _text_settings.json 파일이 없어서 기본 설정을 사용합니다.")
                self.script_settings = {key: value.copy() for key, value in self.defaults.items()}
        except Exception as e:
            print(f"⚠️ [UI] _text_settings.json 로드 실패: {e}")
            print(f"🔍 [UI] 기본 설정을 사용합니다.")
            self.script_settings = {key: value.copy() for key, value in self.defaults.items()}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        selector_frame = ctk.CTkFrame(self, fg_color=config.COLOR_THEME["widget"])
        selector_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        self._create_script_selector(selector_frame)

        settings_grid_frame = ctk.CTkFrame(self, fg_color="transparent")
        settings_grid_frame.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        
        initial_script = self.script_selector.get()
        self.settings_grid = TextSettingsTab(settings_grid_frame, self.defaults[initial_script], self.font_options, self._open_color_picker)
        self.settings_grid.pack(expand=True, fill="both")

        self.json_viewer = tk.Text(self, height=20, bg="black", fg="white", insertbackground="white", relief="flat", borderwidth=0)
        self.json_viewer.grid(row=2, column=0, padx=10, pady=5, sticky="nsew")

        control_button_frame = ctk.CTkFrame(self, fg_color=config.COLOR_THEME["widget"])
        control_button_frame.grid(row=3, column=0, padx=10, pady=10, sticky="ew")
        self._create_control_buttons(control_button_frame)

        self.current_script_name = self.script_selector.get()
        self.after(100, self._on_click_load_settings)

    def _get_updated_defaults(self):
        return {
            "conversation": {
                "main_background": {"type": "이미지", "value": "/Users/janghwanmoon/Projects/captionGen/assets/background/shubham-dhage-1pK0lHvVaeM-unsplash.jpg"},
                "line_spacing": {"ratio": 0.8},
                "background_box": {"type": "없음", "color": "#000000", "alpha": 0.2, "margin": 2},
                "shadow": {"useBlur": True, "thick": 2, "color": "#000000", "blur": 8, "offx": 2, "offy": 2, "alpha": 0.6},
                "border": {"thick": 2, "color": "#000000"},
                "행수": "4", "비율": "16:9", "해상도": "1920x1080" ,
                "rows": [
                    {"행": "순번", "x": 50, "y": 50, "w": 1820, "크기(pt)": 80, "폰트(pt)": "KoPubWorld돋움체 Bold", "색상": "#FFFFFF", "좌우 정렬": "Left", "상하 정렬": "Top", "바탕": False, "쉐도우": False, "외곽선": False},
                    {"행": "원어", "x": 50, "y": 150, "w": 1820, "크기(pt)": 100, "폰트(pt)": "KoPubWorld돋움체 Bold", "색상": "#00FFFF", "좌우 정렬": "Center", "상하 정렬": "Top", "바탕": False, "쉐도우": False, "외곽선": False},
                    {"행": "학습어", "x": 50, "y": 450, "w": 1820, "크기(pt)": 100, "폰트(pt)": "Noto Sans KR Bold", "색상": "#FF00FF", "좌우 정렬": "Center", "상하 정렬": "Top", "바탕": False, "쉐도우": False, "외곽선": False},
                    {"행": "읽기", "x": 50, "y": 750, "w": 1820, "크기(pt)": 100, "폰트(pt)": "KoPubWorld돋움체 Bold", "색상": "#FFFF00", "좌우 정렬": "Center", "상하 정렬": "Top", "바탕": False, "쉐도우": False, "외곽선": False},
                ]
            },
            "thumbnail": {
                "main_background": {"type": "이미지", "value": ""},
                "line_spacing": {"ratio": 1.0},
                "background_box": {"type": "블록", "color": "#000000", "alpha": 0.7, "margin": 10},
                "shadow": {"useBlur": True, "thick": 5, "color": "#FFFFFF", "blur": 10, "offx": 0, "offy": 0, "alpha": 0.5},
                "border": {"thick": 0, "color": "#000000"},
                "행수": "4", "비율": "16:9", "해상도": "1920x1080" ,
                "rows": [
                    {"행": "제목", "x": 50, "y": 50, "w": 924, "크기(pt)": 100, "폰트(pt)": "KoPubWorld돋움체 Bold", "색상": "#FFFFFF", "좌우 정렬": "Left", "상하 정렬": "Top", "바탕": True, "쉐도우": True, "외곽선": False},
                    {"행": "부제목", "x": 50, "y": 200, "w": 924, "크기(pt)": 100, "폰트(pt)": "KoPubWorld돋움체 Bold", "색상": "#00FFFF", "좌우 정렬": "Left", "상하 정렬": "Top", "바탕": True, "쉐도우": True, "외곽선": False},
                    {"행": "설명", "x": 50, "y": 350, "w": 924, "크기(pt)": 100, "폰트(pt)": "KoPubWorld돋움체 Bold", "색상": "#FF00FF", "좌우 정렬": "Left", "상하 정렬": "Top", "바탕": True, "쉐도우": True, "외곽선": False},
                    {"행": "태그", "x": 50, "y": 500, "w": 924, "크기(pt)": 100, "폰트(pt)": "KoPubWorld돋움체 Bold", "색상": "#FFFF00", "좌우 정렬": "Left", "상하 정렬": "Top", "바탕": True, "쉐도우": True, "외곽선": False},
                ]
            },
            "intro": {
                "main_background": {"type": "색상", "value": "#111111"},
                "line_spacing": {"ratio": 1.2},
                "background_box": {"type": "없음", "color": "#000000", "alpha": 0.5, "margin": 5},
                "shadow": {"useBlur": False, "thick": 2, "color": "#FFFFFF", "blur": 5, "offx": 2, "offy": 2, "alpha": 0.8},
                "border": {"thick": 1, "color": "#FFFFFF"},
                "행수": "1", "비율": "16:9", "해상도": "1920x1080" ,
                "rows": [{"행": "인트로", "x": 50, "y": 50, "w": 1820, "크기(pt)": 80, "폰트(pt)": "KoPubWorld돋움체 Bold", "색상": "#FFFFFF", "좌우 정렬": "Left", "상하 정렬": "Top", "바탕": True, "쉐도우": True, "외곽선": True}]
            },
            "ending": {
                "main_background": {"type": "색상", "value": "#222222"},
                "line_spacing": {"ratio": 1.2},
                "background_box": {"type": "없음", "color": "#000000", "alpha": 0.5, "margin": 5},
                "shadow": {"useBlur": True, "thick": 3, "color": "#000000", "blur": 5, "offx": 3, "offy": 3, "alpha": 0.7},
                "border": {"thick": 0, "color": "#000000"},
                "행수": "1", "비율": "16:9", "해상도": "1920x1080" ,
                "rows": [{"행": "엔딩", "x": 50, "y": 50, "w": 1820, "크기(pt)": 100, "폰트(pt)": "KoPubWorld돋움체 Bold", "색상": "#FFFFFF", "좌우 정렬": "Left", "상하 정렬": "Top", "바탕": False, "쉐도우": True, "외곽선": False}]
            },
            "dialogue": {
                "main_background": {"type": "색상", "value": "#000000"},
                "line_spacing": {"ratio": 0.8},
                "background_box": {"type": "블록", "color": "#000000", "alpha": 0.5, "margin": 5},
                "shadow": {"useBlur": True, "thick": 2, "color": "#000000", "blur": 8, "offx": 2, "offy": 2, "alpha": 0.6},
                "border": {"thick": 2, "color": "#000000"},
                "행수": "3", "비율": "16:9", "해상도": "1920x1080" ,
                "rows": [
                    {"행": "원어", "x": 50, "y": 250, "w": 1820, "크기(pt)": 100, "폰트(pt)": "KoPubWorld돋움체 Bold", "색상": "#FFFFFF", "좌우 정렬": "Left", "상하 정렬": "Top", "바탕": True, "쉐도우": False, "외곽선": False},
                    {"행": "학습어1", "x": 50, "y": 550, "w": 1820, "크기(pt)": 100, "폰트(pt)": "KoPubWorld돋움체 Bold", "색상": "#FFFFFF", "좌우 정렬": "Left", "상하 정렬": "Top", "바탕": True, "쉐도우": False, "외곽선": False},
                    {"행": "학습어2", "x": 50, "y": 850, "w": 1820, "크기(pt)": 100, "폰트(pt)": "KoPubWorld돋움체 Bold", "색상": "#FFFFFF", "좌우 정렬": "Left", "상하 정렬": "Top", "바탕": True, "쉐도우": False, "외곽선": False},
                ]
            },
        }

    def _create_script_selector(self, parent):
        parent.grid_columnconfigure(1, weight=0)
        ctk.CTkLabel(parent, text="스크립트 선택:").pack(side="left", padx=(10, 10), pady=10)
        
        script_names = list(self.defaults.keys())
        self.script_selector = ctk.CTkComboBox(parent, values=script_names, width=200, command=self._on_script_selected)
        self.script_selector.set(script_names[0])
        self.script_selector.pack(side="left", padx=(0, 10), pady=10)

    def _on_script_selected(self, selected_script_name: str):
        if self.current_script_name == selected_script_name:
            return

        # 1. Save the current UI state (which belongs to the old script) under the OLD script name.
        if self.current_script_name:
            self.script_settings[self.current_script_name] = self.settings_grid.get_settings()
            print(f"💾 [메모리 저장] '{self.current_script_name}' 스크립트의 UI 상태를 메모리에 저장했습니다.")

        # 2. Apply the settings for the NEW script name to the UI.
        self._apply_settings_from_memory_to_ui(selected_script_name)
        
        # 3. Finally, update the current script name to the NEW one.
        self.current_script_name = selected_script_name

    def _initialize_settings(self):
        self.script_settings = {key: value.copy() for key, value in self.defaults.items()}
        print("[초기화] 인메모리 설정이 기본값으로 초기화되었습니다.")

    def _save_ui_to_memory(self):
        if not self.current_script_name: return
        self.script_settings[self.current_script_name] = self.settings_grid.get_settings()
        print(f"💾 [메모리 저장] '{self.current_script_name}' 스크립트의 UI 상태를 메모리에 저장했습니다.")
        self._update_json_viewer()

    def _apply_settings_from_memory_to_ui(self, script_name):
        if script_name not in self.script_settings:
            print(f"❌ [UI 적용 실패] '{script_name}'에 대한 설정이 메모리에 없습니다.")
            return
        
        settings = self.script_settings[script_name]
        self.settings_grid.apply_settings(settings)
        print(f"🎨 [UI 적용] '{script_name}' 스크립트의 설정을 화면에 표시합니다.")
        self._update_json_viewer()

    def _on_click_save_settings(self):
        try:
            self._save_ui_to_memory()
            path = os.path.join(config.BASE_DIR, "_text_settings.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.script_settings, f, ensure_ascii=False, indent=2)
            self._update_json_viewer(f"✅ 모든 설정이 {os.path.basename(path)} 에 저장되었습니다.")
        except Exception as e:
            self._update_json_viewer(f"❌ 설정 저장 중 오류 발생:\n{e}")
            traceback.print_exc()

    def _on_click_load_settings(self):
        try:
            path = os.path.join(config.BASE_DIR, "_text_settings.json")
            if not os.path.isfile(path):
                self._initialize_settings()
            else:
                with open(path, "r", encoding="utf-8") as f:
                    self.script_settings = json.load(f)
            
            self._apply_settings_from_memory_to_ui(self.script_selector.get())
            self._update_json_viewer(f"✅ 설정을 불러왔습니다.")
        except Exception as e:
            self._update_json_viewer(f"❌ 설정 파일 로드 중 오류 발생:\n{e}")
            self._initialize_settings()
            self._apply_settings_from_memory_to_ui(self.script_selector.get())

    def _update_json_viewer(self, message=None):
        try:
            current_script = self.script_selector.get()
            display_data = self.script_settings.get(current_script, {})
            header = f"🔄 '{current_script}' 스크립트 실시간 설정 상태"
            if message: header = message
            display_text = f"{header}\n{'=' * 50}\n\n{json.dumps(display_data, indent=2, ensure_ascii=False)}"
            self.json_viewer.delete("1.0", tk.END)
            self.json_viewer.insert("1.0", display_text)
        except Exception as e:
            print(f"❌ JSON 뷰어 업데이트 중 오류: {e}")

    def _create_control_buttons(self, parent):
        button_kwargs = {"fg_color": config.COLOR_THEME["button"], "hover_color": config.COLOR_THEME["button_hover"], "text_color": config.COLOR_THEME["text"]}
        ctk.CTkButton(parent, text="설정 저장", command=self._on_click_save_settings, **button_kwargs).pack(side="left", padx=(10, 5), pady=10)
        ctk.CTkButton(parent, text="설정 읽기", command=self._on_click_load_settings, **button_kwargs).pack(side="left", padx=5, pady=10)

    def activate(self):
        print("🖼️ 이미지 설정 탭 활성화")
        self._apply_settings_from_memory_to_ui(self.script_selector.get())

    def _open_color_picker(self, entry_widget):
        color_code = colorchooser.askcolor(title="색상 선택")
        if color_code[1]: # color_code[1] is the hex string
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, color_code[1].upper())

class TextSettingsTab(ctk.CTkFrame):
    def __init__(self, parent, default_data, font_options, open_color_picker_callback):
        super().__init__(parent, fg_color="transparent")
        self.font_options = font_options
        self.open_color_picker_callback = open_color_picker_callback
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.recreate_widgets(default_data)

    def recreate_widgets(self, data):
        for widget in self.winfo_children():
            widget.destroy()
        self._controls = {}
        self._grid_widgets = []
        
        self.bg_type_var = tk.StringVar(value=data.get("main_background", {}).get("type", "색상"))
        self.shadow_blur_enabled = tk.BooleanVar(value=data.get("shadow", {}).get("useBlur", True))
        self.bg_box_type_var = tk.StringVar(value=data.get("background_box", {}).get("type", "없음"))

        scrollable_frame = ctk.CTkScrollableFrame(self, fg_color="black")
        scrollable_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        self._create_common_settings_widgets(scrollable_frame, data)
        self._create_grid_settings_widgets(scrollable_frame, data)

    def _on_row_count_changed(self, new_row_count_str: str):
        try:
            new_row_count = int(new_row_count_str)
        except (ValueError, TypeError):
            return

        current_settings = self.get_settings()
        current_rows = current_settings.get("rows", [])
        
        default_row_structure = {"행": "N행", "x": 50, "y": 50, "w": 1820, "크기(pt)": 100, "폰트(pt)": self.font_options[0] if self.font_options else "Arial", "색상": "#FFFFFF", "좌우 정렬": "Left", "상하 정렬": "Top", "바탕": False, "쉐도우": False, "외곽선": False}

        while len(current_rows) < new_row_count:
            new_row = default_row_structure.copy()
            new_row['행'] = f'{len(current_rows) + 1}행'
            new_row['y'] = 50 + (len(current_rows) * 100)
            current_rows.append(new_row)
        
        if len(current_rows) > new_row_count:
            current_rows = current_rows[:new_row_count]
        
        current_settings["rows"] = current_rows
        current_settings["행수"] = new_row_count_str
        self.recreate_widgets(current_settings)

    def _create_common_settings_widgets(self, parent, data):
        common_frame = ctk.CTkFrame(parent, fg_color="transparent")
        common_frame.pack(fill="x", padx=10, pady=5, expand=True)
        button_kwargs = {"fg_color": config.COLOR_THEME["button"], "hover_color": config.COLOR_THEME["button_hover"], "text_color": config.COLOR_THEME["text"]}

        row1 = ctk.CTkFrame(common_frame, fg_color="transparent"); row1.pack(fill="x", pady=2, anchor="w")
        ctk.CTkLabel(row1, text="배경 설정:").pack(side="left", padx=(0, 5))
        bg_type_combo = ctk.CTkComboBox(row1, width=120, variable=self.bg_type_var, values=["색상", "이미지", "동영상"], command=self._on_bg_type_change)
        bg_type_combo.pack(side="left", padx=5)
        _, self.w_bg_value = create_labeled_widget(row1, "배경값:", 80); self.w_bg_value.insert(0, data.get("main_background", {}).get("value", "#000000"))
        self.btn_browse = ctk.CTkButton(row1, text="찾아보기", width=80, command=self._on_click_browse, **button_kwargs); self.btn_browse.pack(side="left", padx=(5,0))
        self.btn_bg_color_picker = ctk.CTkButton(row1, text="🎨", width=30, command=lambda: self.open_color_picker_callback(self.w_bg_value), **button_kwargs)
        self.btn_bg_color_picker.pack(side="left", padx=(5,0))
        self._on_bg_type_change()

        row2 = ctk.CTkFrame(common_frame, fg_color="transparent"); row2.pack(fill="x", pady=2, anchor="w")
        _, self.w_line_spacing = create_labeled_widget(row2, "텍스트 행간 비율:", 10, "entry", {"justify": "center"}); self.w_line_spacing.insert(0, str(data.get("line_spacing", {}).get("ratio", "0.8")))

        row3 = ctk.CTkFrame(common_frame, fg_color="transparent"); row3.pack(fill="x", pady=2, anchor="w")
        ctk.CTkLabel(row3, text="바탕 설정:").pack(side="left", padx=(0, 10))
        _, self.w_bg_box_type = create_labeled_widget(row3, "바탕 형태:", 10, "combo", {"values": ["없음", "텍스트", "블록", "전체"], "variable": self.bg_box_type_var})
        _, self.w_bg_box_color = create_labeled_widget(row3, "바탕색:", 15); self.w_bg_box_color.insert(0, data.get("background_box", {}).get("color", "#000000"))
        self.btn_bg_box_color_picker = ctk.CTkButton(row3, text="🎨", width=30, command=lambda: self.open_color_picker_callback(self.w_bg_box_color), **button_kwargs)
        self.btn_bg_box_color_picker.pack(side="left", padx=(5,0))
        _, self.w_bg_box_alpha = create_labeled_widget(row3, "투명도:", 10); self.w_bg_box_alpha.insert(0, str(data.get("background_box", {}).get("alpha", "0.2")))
        _, self.w_bg_box_margin = create_labeled_widget(row3, "여백:", 6); self.w_bg_box_margin.insert(0, str(data.get("background_box", {}).get("margin", "2")))

        row4 = ctk.CTkFrame(common_frame, fg_color="transparent"); row4.pack(fill="x", pady=2, anchor="w")
        ctk.CTkLabel(row4, text="쉐도우 설정:").pack(side="left", padx=(0, 10))
        ctk.CTkCheckBox(row4, text="블러", variable=self.shadow_blur_enabled, command=self._update_common_states).pack(side="left", padx=(0,8))
        _, self.w_shadow_thick = create_labeled_widget(row4, "두께", 6); self.w_shadow_thick.insert(0, str(data.get("shadow", {}).get("thick", "2")))
        _, self.w_shadow_color = create_labeled_widget(row4, "쉐도우 색상", 10); self.w_shadow_color.insert(0, data.get("shadow", {}).get("color", "#000000"))
        self.btn_shadow_color_picker = ctk.CTkButton(row4, text="🎨", width=30, command=lambda: self.open_color_picker_callback(self.w_shadow_color), **button_kwargs)
        self.btn_shadow_color_picker.pack(side="left", padx=(5,0))
        
        row5 = ctk.CTkFrame(common_frame, fg_color="transparent"); row5.pack(fill="x", pady=2, anchor="w")
        ctk.CTkLabel(row5, text="외곽선 설정:").pack(side="left", padx=(0, 10))
        _, self.w_border_thick = create_labeled_widget(row5, "두께", 6); self.w_border_thick.insert(0, str(data.get("border", {}).get("thick", "2")))
        _, self.w_border_color = create_labeled_widget(row5, "외곽선 색상", 10); self.w_border_color.insert(0, data.get("border", {}).get("color", "#000000"))
        self.btn_border_color_picker = ctk.CTkButton(row5, text="🎨", width=30, command=lambda: self.open_color_picker_callback(self.w_border_color), **button_kwargs)
        self.btn_border_color_picker.pack(side="left", padx=(5,0))
        
        self._update_common_states()

    def _create_grid_settings_widgets(self, parent, data):
        grid_frame = ctk.CTkFrame(parent, fg_color="transparent")
        grid_frame.pack(fill="x", pady=5, expand=True)
        
        top_controls_frame = ctk.CTkFrame(grid_frame, fg_color="transparent"); top_controls_frame.pack(fill="x", pady=5)
        combo_params = {"fg_color": config.COLOR_THEME["widget"], "text_color": config.COLOR_THEME["text"]}
        button_kwargs = {"fg_color": config.COLOR_THEME["button"], "hover_color": config.COLOR_THEME["button_hover"], "text_color": config.COLOR_THEME["text"]}
        
        # 텍스트 행수
        frame, self._controls["행수"] = create_labeled_widget(top_controls_frame, "텍스트 행수", 8, "combo", {**combo_params, "values": [str(i) for i in range(1, 11)], "command": self._on_row_count_changed})
        self._controls["행수"].set(data.get("행수", "1")); frame.pack(side="left", padx=(0, 10))
        
        # 화면비율 (복구)
        frame, self._controls["비율"] = create_labeled_widget(top_controls_frame, "화면비율", 16, "combo", {**combo_params, "values": ["16:9", "1:1", "9:16"]})
        self._controls["비율"].set(data.get("비율", "16:9")); frame.pack(side="left", padx=(0, 10))
        
        # 해상도 (복구)
        frame, self._controls["해상도"] = create_labeled_widget(top_controls_frame, "해상도", 16, "combo", {**combo_params, "values": ["1920x1080", "1024x768", "1080x1080", "768x1024", "1080x1920"]})
        self._controls["해상도"].set(data.get("해상도", "1920x1080")); frame.pack(side="left", padx=(0, 20))

        settings_grid = ctk.CTkFrame(grid_frame, fg_color="transparent")
        settings_grid.pack(fill="both", expand=True, pady=5)
        
        headers = ["행", "x", "y", "w", "크기(pt)", "폰트(pt)", "색상", "좌우 정렬", "상하 정렬", "바탕", "쉐도우", "외곽선"]
        col_widths = {"행": 6, "x": 6, "y": 6, "w": 10, "크기(pt)": 8, "폰트(pt)": 30, "색상": 16, "좌우 정렬": 16, "상하 정렬": 16, "바탕": 6, "쉐도우": 6, "외곽선": 6}

        for col, header_text in enumerate(headers):
            ctk.CTkLabel(settings_grid, text=header_text, justify="center", anchor="center").grid(row=0, column=col, padx=2, pady=5, sticky="nsew")

        h_align_options = ["Left", "Center", "Right"]
        v_align_options = ["Top", "Center", "Bottom"]

        rows_data = data.get("rows", [])
        
        for row_idx, row_data in enumerate(rows_data, start=1):
            row_widgets = {}
            for col_idx, key in enumerate(headers):
                pixel_width = col_widths.get(key, 10) * 9
                params = {"master": settings_grid, "width": pixel_width, "fg_color": config.COLOR_THEME["widget"], "text_color": config.COLOR_THEME["text"]}
                
                widget = None
                if key == "행":
                    # 행 라벨을 디폴트 값으로 설정
                    default_labels = ["순번", "원어", "학습어", "읽기"]
                    default_label = default_labels[row_idx - 1] if row_idx <= len(default_labels) else f"{row_idx}행"
                    widget = ctk.CTkEntry(**params, justify="center"); widget.insert(0, default_label)
                elif key in ["폰트(pt)", "좌우 정렬", "상하 정렬"]:
                    values = {"폰트(pt)": self.font_options, "좌우 정렬": h_align_options, "상하 정렬": v_align_options}[key]
                    widget = ctk.CTkComboBox(**params, values=values); widget.set(row_data.get(key))
                elif key == "색상":
                    color_frame = ctk.CTkFrame(settings_grid, fg_color="transparent")
                    color_frame.grid(row=row_idx, column=col_idx, padx=1, pady=1, sticky="nsew")
                    color_entry = ctk.CTkEntry(color_frame, width=pixel_width - 40, justify="center")
                    color_entry.insert(0, str(row_data.get(key, '')))
                    color_entry.pack(side="left", fill="x", expand=True)
                    btn_color_picker = ctk.CTkButton(color_frame, text="🎨", width=30, command=lambda entry=color_entry: self.open_color_picker_callback(entry), **button_kwargs)
                    btn_color_picker.pack(side="left", padx=(5,0))
                    row_widgets[key] = color_entry
                    row_widgets[f"{key}_picker"] = btn_color_picker
                    widget = color_frame # The widget to grid is the frame
                elif key in ["바탕", "쉐도우", "외곽선"]:
                    container = ctk.CTkFrame(settings_grid, fg_color="transparent"); container.grid(row=row_idx, column=col_idx, padx=1, pady=1, sticky="nsew")
                    container.grid_rowconfigure(0, weight=1); container.grid_columnconfigure(0, weight=1)
                    val = str(row_data.get(key, "False")).lower() in ["true", "1"]; var = tk.BooleanVar(value=val)
                    widget = ctk.CTkCheckBox(container, text="", variable=var); widget.grid(row=0, column=0, sticky="")
                    row_widgets[key] = var
                    continue
                else:
                    widget = ctk.CTkEntry(**params, justify="center"); widget.insert(0, str(row_data.get(key, '')))
                
                if key != "색상": # Color frame is already gridded
                    widget.grid(row=row_idx, column=col_idx, padx=1, pady=1)
                if key not in ["바탕", "쉐도우", "외곽선", "색상"]: # Checkboxes and color frame are handled differently
                    row_widgets[key] = widget
            self._grid_widgets.append(row_widgets)

    def get_settings(self):
        """현재 UI 위젯들의 상태를 읽어 하나의 설정 딕셔너리로 반환합니다."""
        try:
            # 공통 컨트롤에서 설정값 가져오기
            bg_type = self.bg_type_var.get()
            bg_value = self.w_bg_value.get()
            if bg_type in ["이미지", "동영상"] and hasattr(self, 'w_bg_value_absolute_path'):
                bg_value = self.w_bg_value_absolute_path

            settings = {
                "main_background": {"type": bg_type, "value": bg_value},
                "line_spacing": {"ratio": self.w_line_spacing.get()},
                "background_box": {"type": self.bg_box_type_var.get(), "color": self.w_bg_box_color.get(), "alpha": self.w_bg_box_alpha.get(), "margin": self.w_bg_box_margin.get()},
                "shadow": {"useBlur": self.shadow_blur_enabled.get(), "thick": self.w_shadow_thick.get(), "color": self.w_shadow_color.get()},
                "border": {"thick": self.w_border_thick.get(), "color": self.w_border_color.get()},
                "행수": self._controls["행수"].get(),
                "비율": self._controls["비율"].get(),
                "해상도": self._controls["해상도"].get()
            }

            # 그리드에서 행 데이터 가져오기
            rows = []
            for row_widgets in self._grid_widgets:
                row_data = {}
                for key, widget in row_widgets.items():
                    if key == "행":
                        # 행 라벨을 그대로 유지
                        text_value = widget.get()
                        row_data["행"] = text_value
                    elif isinstance(widget, tk.BooleanVar): 
                        row_data[key] = widget.get()
                    elif key.endswith("_picker"): 
                        continue
                    elif isinstance(widget, ctk.CTkFrame): # Handle color frame
                        # Get value from the entry inside the frame
                        entry_widget = widget.winfo_children()[0] # Assuming entry is the first child
                        row_data[key] = entry_widget.get()
                    else: 
                        row_data[key] = widget.get()
                rows.append(row_data)
            settings["rows"] = rows
            return settings
            
        except Exception as e:
            traceback.print_exc()
            return {}

    def apply_settings(self, data):
        self.recreate_widgets(data)

    def _on_click_browse(self):
        try:
            kind = self.bg_type_var.get()
            if kind == "이미지": filetypes = [("Image files", "*.jpg *.jpeg *.png")]
            elif kind == "동영상": filetypes = [("Video files", "*.mp4")]
            else: return
            path = filedialog.askopenfilename(title="파일 선택", filetypes=filetypes)
            if path:
                self.w_bg_value_absolute_path = path
                self.w_bg_value.configure(state="normal")
                self.w_bg_value.delete(0, tk.END)
                self.w_bg_value.insert(0, path)
                if self.bg_type_var.get() in ["이미지", "동영상"]:
                    self.w_bg_value.configure(state="disabled")
        except Exception as e: 
            print(f"[찾아보기 오류] {e}")

    def _on_bg_type_change(self, *_):
        try:
            selected_type = self.bg_type_var.get()
            if selected_type == "색상":
                self.btn_browse.configure(state="disabled")
                if hasattr(self, 'w_bg_value'): self.w_bg_value.configure(state="normal")
                if hasattr(self, 'btn_bg_color_picker'): self.btn_bg_color_picker.configure(state="normal")
            else: # 이미지 or 동영상
                self.btn_browse.configure(state="normal")
                if hasattr(self, 'w_bg_value'): self.w_bg_value.configure(state="disabled")
                if hasattr(self, 'btn_bg_color_picker'): self.btn_bg_color_picker.configure(state="disabled")
        except Exception: pass

    def _update_common_states(self, event=None):
        try:
            state = "normal" if self.shadow_blur_enabled.get() else "disabled"
            for w in [self.w_shadow_blur, self.w_shadow_offx, self.w_shadow_offy, self.w_shadow_alpha]:
                if w: w.configure(state=state)
        except Exception: pass