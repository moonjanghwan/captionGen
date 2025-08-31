import customtkinter as ctk
from src import config
from src.ui.data_tab_view import DataTabView
from src.ui.speaker_tab_view import SpeakerTabView
from src.ui.image_tab_view import ImageTabView
from src import api_services
import threading
import json
import os

class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- 윈도우 설정 ---
        self.title("AI 영상 콘텐츠 자동화 프로그램")
        self._set_window_geometry()
        
        # --- 테마 및 외관 설정 ---
        ctk.set_appearance_mode(config.UI_APPEARANCE_MODE)
        ctk.set_default_color_theme(config.UI_THEME)
        
        # --- 레이아웃 설정 (메뉴 영역 + 메인 영역) ---
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.current_play_obj = None # 현재 재생 중인 오디오 객체
        self.cancel_event = threading.Event() # 모든 작업 취소 이벤트
        self.active_processes = [] # 서브프로세스 목록

        # --- 메뉴 프레임 생성 ---
        self.menu_frame = ctk.CTkFrame(self, height=50, corner_radius=0, fg_color=config.COLOR_THEME["background"])
        self.menu_frame.grid(row=0, column=0, sticky="ew")

        button_kwargs = {
            "fg_color": config.COLOR_THEME["button"],
            "hover_color": config.COLOR_THEME["button_hover"],
            "text_color": config.COLOR_THEME["text"]
        }

        self.data_button = ctk.CTkButton(self.menu_frame, text="데이터 생성", command=lambda: self._show_page("data"), **button_kwargs)
        self.data_button.pack(side="left", padx=10, pady=10)
        
        self.speaker_button = ctk.CTkButton(self.menu_frame, text="화자 선택", command=lambda: self._show_page("speaker"), **button_kwargs)
        self.speaker_button.pack(side="left", padx=10, pady=10)

        self.image_button = ctk.CTkButton(self.menu_frame, text="이미지 설정", command=lambda: self._show_page("image"), **button_kwargs)
        self.image_button.pack(side="left", padx=10, pady=10)

        # 텍스트 설정 버튼 제거 (이미지 설정 탭에 통합)

        # 텍스트 설정 탭은 사용하지 않음 (요청에 따라 제거)

        # --- 메인 프레임 생성 ---
        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color=config.COLOR_THEME["background"])
        self.main_frame.grid(row=1, column=0, sticky="nsew")
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # --- 페이지 생성 및 설정 ---
        self.pages = {}
        # MainWindow 인스턴스(self)를 root로 전달
        self.data_page = DataTabView(self.main_frame, on_language_change=self._update_speaker_tab, root=self)
        self.speaker_page = SpeakerTabView(self.main_frame, root=self)
        self.image_page = ImageTabView(self.main_frame)
        # MainWindow 참조를 런타임 주입 (구버전 시그니처 호환)
        try:
            self.image_page.root = self
        except Exception:
            pass
        

        self.pages["data"] = self.data_page
        self.pages["speaker"] = self.speaker_page
        self.pages["image"] = self.image_page
        
        
        
        # 각 페이지를 그리드에 배치하지만, pack_forget으로 숨김
        for page in self.pages.values():
            page.grid(row=0, column=0, sticky='nsew')
            page.grid_remove()

        self._show_page("data")
        # 초기 렌더 후 실제 창 크기를 기준으로 중앙 정렬 보정
        self.after(50, self._center_on_screen)
        
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

        self._initialize_apis()

    def _set_window_geometry(self):
        """윈도우를 화면 중앙에 위치시키는 함수"""
        width = 1600
        height = 900
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _center_on_screen(self):
        try:
            self.update_idletasks()
            width = self.winfo_width() or 1600
            height = self.winfo_height() or 900
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            x = (screen_width - width) // 2
            y = (screen_height - height) // 2
            # 최소 0 보정
            x = max(0, x)
            y = max(0, y)
            self.geometry(f"{width}x{height}+{x}+{y}")
        except Exception:
            pass

    def _setup_pages(self):
        supported_languages = api_services.get_tts_supported_languages()

        self.pages["data"] = DataTabView(self.main_frame, supported_languages, self._on_project_info_updated, root=self)
        self.pages["data"].grid(row=0, column=0, sticky="nsew")
        self.pages["speaker"] = SpeakerTabView(self.main_frame, root=self)
        self.pages["speaker"].grid(row=0, column=0, sticky="nsew")
        self.pages["image"] = ImageTabView(self.main_frame)
        self.pages["image"].grid(row=0, column=0, sticky="nsew")

    def _show_page(self, page_name):
        if page_name == "speaker":
            self._update_speaker_tab()
        
        for name, page in self.pages.items():
            if name == page_name:
                page.grid() # grid()를 사용하여 보이게 함
            else:
                page.grid_remove() # grid_remove()를 사용하여 숨김
        # 메뉴 버튼 선택 상태 스타일 업데이트
        self._update_menu_buttons_style(page_name)

    def _update_menu_buttons_style(self, selected: str):
        normal_fg = config.COLOR_THEME["button"]
        normal_hover = config.COLOR_THEME["button_hover"]
        selected_fg = config.COLOR_THEME["button_hover"]
        selected_hover = config.COLOR_THEME["button_hover"]
        buttons = {
            "data": self.data_button,
            "speaker": self.speaker_button,
            "image": self.image_button,
        }
        for key, btn in buttons.items():
            if not btn:
                continue
            if key == selected:
                btn.configure(fg_color=selected_fg, hover_color=selected_hover)
            else:
                btn.configure(fg_color=normal_fg, hover_color=normal_hover)

    def _on_project_info_updated(self, native_lang, learning_lang, project_name, identifier):
        """DataTabView에서 프로젝트 정보가 변경되었을 때 호출되는 콜백입니다."""
        speaker_tab = self.pages.get("speaker")
        if speaker_tab:
            speaker_tab.update_language_settings(native_lang, learning_lang, project_name, identifier)

    def stop_all_sounds(self):
        """현재 수행 중인 재생/생성 작업을 모두 중지합니다."""
        try:
            # 취소 신호
            self.cancel_event.set()
            # 재생 프로세스 종료
            if self.current_play_obj:
                try:
                    self.current_play_obj.terminate()
                except Exception:
                    pass
                self.current_play_obj = None
            # 활성 프로세스 일괄 종료 (ffmpeg 등)
            for proc in list(self.active_processes):
                try:
                    proc.terminate()
                except Exception:
                    pass
            self.active_processes.clear()
            print("모든 작업을 중지했습니다.")
        except Exception as e:
            print(f"작업 중지 중 오류: {e}")

    def register_process(self, proc):
        try:
            self.active_processes.append(proc)
        except Exception:
            pass

    def unregister_process(self, proc):
        try:
            if proc in self.active_processes:
                self.active_processes.remove(proc)
        except Exception:
            pass

    def _initialize_apis(self):
        """API 서비스들을 초기화하고 결과를 메시지 창에 표시합니다."""
        data_tab = self.pages.get("data")
        if data_tab:
            # Gemini 초기화
            gemini_status = api_services.initialize_gemini()
            data_tab.log_message(f"[초기화] {gemini_status}")
            
            # Google TTS 초기화
            tts_status = api_services.initialize_google_tts()
            data_tab.log_message(f"[초기화] {tts_status}")

    def _update_speaker_tab(self):
        # 1. 데이터 탭에서 현재 선택된 언어 코드 가져오기
        native_lang, learning_lang = self.data_page.get_selected_language_codes()
        
        # 2. 데이터 탭에서 프로젝트명과 식별자 가져오기 (가상)
        # 실제 구현에서는 data_page에서 이 값들을 가져오는 메서드가 필요합니다.
        project_name = self.data_page.project_name_var.get()
        identifier = project_name 
        
        # 3. 화자 탭의 언어 설정 업데이트
        if native_lang and learning_lang:
            self.speaker_page.update_language_settings(
                native_lang_code=native_lang,
                learning_lang_code=learning_lang,
                project_name=project_name,
                identifier=identifier
            )

    def _on_closing(self):
        self.stop_all_sounds() # 종료 전 오디오 정지
        try:
            config_path = os.path.join(config.BASE_DIR, 'config.json')
            
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
            else:
                config_data = {}

            data_tab = self.pages.get("data")
            if data_tab:
                native_lang = data_tab.native_lang_var.get()
                learning_lang = data_tab.learning_lang_var.get()
                
                if native_lang and learning_lang:
                    config_data['last_native_lang'] = native_lang
                    config_data['last_learning_lang'] = learning_lang

            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4, ensure_ascii=False)

        except Exception as e:
            print(f"Error saving config on closing: {e}")
        
        self.destroy()
