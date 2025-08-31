import customtkinter as ctk
from src import config, api_services
import tkinter as tk
import os
import json
import tempfile
import subprocess
import threading

PREVIEW_TEXTS = {
    "ko-KR": "안녕하세요. 만나서 반갑습니다.",
    "en-US": "Hello, nice to meet you.",
    "ja-JP": "こんにちは。はじめまして。",
    "cmn-CN": "你好，很高兴认识你。",
    "vi-VN": "Xin chào, rất vui được gặp bạn.",
    "id-ID": "Halo, senang bertemu dengan Anda.",
    "it-IT": "Ciao, piacere di conoscerti.",
    "es-US": "Hola, mucho gusto.",
    "fr-FR": "Bonjour, enchanté de vous rencontrer.",
    "de-DE": "Hallo, schön Sie kennenzulernen."
}

class SpeakerTabView(ctk.CTkFrame):
    def __init__(self, parent, root=None):
        super().__init__(parent, fg_color=config.COLOR_THEME["background"])
        self.root = root
        self.grid_columnconfigure(0, weight=1)

        self.project_name = ""
        self.identifier = None
        self.native_lang_code = None
        self.learning_lang_code = None
        
        self.learner_speaker_widgets = []

        self._create_widgets()

    def _create_widgets(self):
        button_kwargs = {
            "fg_color": config.COLOR_THEME["button"],
            "hover_color": config.COLOR_THEME["button_hover"],
            "text_color": config.COLOR_THEME["text"]
        }
        # --- 원어 화자 섹션 ---
        self.native_speaker_frame = ctk.CTkFrame(self, fg_color=config.COLOR_THEME["widget"])
        self.native_speaker_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        
        self.native_speaker_label = ctk.CTkLabel(self.native_speaker_frame, text="원어 화자:")
        self.native_speaker_label.pack(side="left", padx=10, pady=10)
        
        self.native_speaker_dropdown = ctk.CTkComboBox(self.native_speaker_frame, width=50*9, values=[], 
                                                     fg_color=config.COLOR_THEME["widget"], 
                                                     text_color=config.COLOR_THEME["text"])
        self.native_speaker_dropdown.pack(side="left", padx=10, pady=10)
        
        ctk.CTkButton(self.native_speaker_frame, text="미리듣기", command=lambda: self._preview_voice(
            self.native_speaker_dropdown.get(), self.native_lang_code
        ), **button_kwargs).pack(side="left", padx=10, pady=10)

        # --- 학습어 화자 섹션 ---
        learner_speaker_frame = ctk.CTkFrame(self, fg_color=config.COLOR_THEME["widget"])
        learner_speaker_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

        num_speaker_frame = ctk.CTkFrame(learner_speaker_frame, fg_color="transparent")
        num_speaker_frame.pack(fill="x", padx=5, pady=5, anchor="w")

        self.num_speakers_var = tk.StringVar(value="4")
        _, self.num_speakers_dropdown = self.create_labeled_widget(num_speaker_frame, "화자 수", 6, "combo", 
            {"values": [str(i) for i in range(1, 6)], "variable": self.num_speakers_var, "command": self._on_num_speakers_changed})
        self.num_speakers_dropdown.master.pack(side="left")

        self.learner_speakers_container = ctk.CTkFrame(learner_speaker_frame, fg_color="transparent")
        self.learner_speakers_container.pack(fill="x", expand=True, padx=5, pady=5)
        
        # --- 설정 저장 버튼 ---
        save_button_frame = ctk.CTkFrame(self, fg_color=config.COLOR_THEME["widget"])
        save_button_frame.grid(row=2, column=0, padx=10, pady=20, sticky="ew")
        ctk.CTkButton(save_button_frame, text="화자 설정 저장", command=self._save_speaker_settings, 
                      **button_kwargs).pack(anchor="w", padx=10, pady=10)

    def update_language_settings(self, native_lang_code, learning_lang_code, project_name, identifier):
        self.project_name = project_name
        self.identifier = identifier
        self.native_lang_code = native_lang_code
        self.learning_lang_code = learning_lang_code

        # --- 원어 화자 목록 업데이트 ---
        native_voices = api_services.get_voices_for_language(self.native_lang_code)
        self.native_speaker_dropdown.configure(values=native_voices)
        if native_voices:
            self.native_speaker_dropdown.set(native_voices[0])

        # --- 학습어 화자 목록 업데이트 ---
        # 이전에 동적으로 생성된 학습어 화자 프레임들 제거
        for widget in self.learner_speakers_container.winfo_children():
            widget.destroy()
        
        # num_speakers_entry의 현재 값 또는 기본값으로 화자 수 결정
        try:
            num_speakers = int(self.num_speakers_var.get())
        except (ValueError, AttributeError):
            num_speakers = 1 # 기본값
            if hasattr(self, 'num_speakers_var'):
                self.num_speakers_var.set("1")

        self.learner_speaker_widgets = []
        self._update_learner_speakers_ui(num_speakers)

        # 저장된 설정 불러오기
        self._load_speaker_settings()


    def _on_num_speakers_changed(self, *args):
        try:
            num = int(self.num_speakers_var.get())
            if num > 0:
                self._update_learner_speakers_ui(num)
        except ValueError:
            pass # 숫자가 아닌 값이 입력된 경우 무시

    def _update_learner_speakers_ui(self, num_speakers):
        # 기존 위젯 삭제
        for widgets in self.learner_speaker_widgets:
            widgets["frame"].destroy()
        self.learner_speaker_widgets.clear()
        
        learner_voices = api_services.get_voices_for_language(self.learning_lang_code)

        for i in range(num_speakers):
            frame = ctk.CTkFrame(self.learner_speakers_container)
            frame.pack(pady=2, padx=10, fill="x")

            label = ctk.CTkLabel(frame, text=f"학습어 화자 {i+1}:")
            label.pack(side="left", padx=10, pady=5)
            
            dropdown = ctk.CTkComboBox(frame, width=50*9, values=learner_voices, 
                                       fg_color=config.COLOR_THEME["widget"], 
                                       text_color=config.COLOR_THEME["text"])
            if learner_voices:
                dropdown.set(learner_voices[i % len(learner_voices)])
            dropdown.pack(side="left", padx=10, pady=10)
            
            button_kwargs = {
                "fg_color": config.COLOR_THEME["button"],
                "hover_color": config.COLOR_THEME["button_hover"],
                "text_color": config.COLOR_THEME["text"]
            }
            button = ctk.CTkButton(frame, text="미리 듣기", command=lambda dd=dropdown: self._preview_voice(
                dd.get(), self.learning_lang_code
            ), **button_kwargs)
            button.pack(side="left", padx=10, pady=10)

            self.learner_speaker_widgets.append({"frame": frame, "dropdown": dropdown})

    def _preview_voice(self, voice_name, lang_code):
        if not voice_name or not lang_code:
            print("미리듣기를 위한 화자 또는 언어 코드가 선택되지 않았습니다.")
            return

        # 다른 오디오가 재생 중이면 중지
        self.root.stop_all_sounds()

        text_to_speak = PREVIEW_TEXTS.get(lang_code, "No sample text available for this language.")
        
        def play_audio():
            audio_content = api_services.synthesize_speech(text_to_speak, lang_code, voice_name)
            if audio_content:
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                        tmp_file.write(audio_content)
                        tmp_file_path = tmp_file.name
                    
                    # afplay를 사용하여 오디오 재생 (subprocess.Popen)
                    process = subprocess.Popen(["afplay", tmp_file_path])
                    self.root.current_play_obj = process
                    process.wait() # 재생이 끝날 때까지 기다림
                
                except Exception as e:
                    print(f"오디오 재생 중 오류 발생: {e}")
                finally:
                    # 임시 파일 정리
                    if 'tmp_file_path' in locals() and os.path.exists(tmp_file_path):
                        os.remove(tmp_file_path)
                    # 재생이 끝나면 MainWindow의 객체도 정리
                    self.root.current_play_obj = None


        # UI가 멈추지 않도록 별도 스레드에서 오디오 재생
        playback_thread = threading.Thread(target=play_audio)
        playback_thread.daemon = True
        playback_thread.start()

    def _get_speaker_config_path(self):
        if self.project_name and self.identifier:
            return os.path.join(config.OUTPUT_PATH, self.project_name, self.identifier, f"{self.identifier}_speaker.json")
        return None

    def _save_speaker_settings(self):
        config_path = self._get_speaker_config_path()
        if not config_path:
            print("프로젝트 정보가 없어 화자 설정을 저장할 수 없습니다.")
            return

        settings = {
            "native_speaker": self.native_speaker_dropdown.get(),
            "num_learner_speakers": self.num_speakers_var.get(),
            "learner_speakers": [w["dropdown"].get() for w in self.learner_speaker_widgets]
        }
        
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
        print(f"화자 설정이 저장되었습니다: {config_path}")

    def _load_speaker_settings(self):
        config_path = self._get_speaker_config_path()
        if not config_path or not os.path.exists(config_path):
            return

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)

            if "native_speaker" in settings:
                self.native_speaker_dropdown.set(settings["native_speaker"])
            
            if "num_learner_speakers" in settings:
                self.num_speakers_var.set(settings["num_learner_speakers"])
                self._update_learner_speakers_ui(int(settings["num_learner_speakers"]))
            
            if "learner_speakers" in settings:
                for i, speaker in enumerate(settings["learner_speakers"]):
                    if i < len(self.learner_speaker_widgets):
                        self.learner_speaker_widgets[i]["dropdown"].set(speaker)
            print(f"화자 설정을 불러왔습니다: {config_path}")
        except Exception as e:
            print(f"화자 설정 파일 로드 중 오류 발생: {e}")

    def create_labeled_widget(self, p, label_text, char_width, widget_type="combo", widget_params=None):
        frame = ctk.CTkFrame(p, fg_color="transparent")
        ctk.CTkLabel(frame, text=f"{label_text}:").pack(side="left", padx=10, pady=10)
        pixel_width = char_width * 9
        
        widget_params = widget_params or {}
        if 'fg_color' not in widget_params:
            widget_params['fg_color'] = config.COLOR_THEME["widget"]
        if 'text_color' not in widget_params:
            widget_params['text_color'] = config.COLOR_THEME["text"]
            
        widget = ctk.CTkComboBox(frame, width=pixel_width, **widget_params)
        widget.pack(side="left", padx=10, pady=10)
        return frame, widget
