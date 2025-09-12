import customtkinter as ctk
from src import config
import tkinter as tk
from tkinter import ttk
import os
import json
import csv
import io
import re
import tempfile
import subprocess
import threading
import time
from src import api_services
from src.ui.ui_utils import create_labeled_widget

class DataTabView(ctk.CTkFrame):
    def __init__(self, parent, on_language_change=None, root=None):
        super().__init__(parent, fg_color=config.COLOR_THEME["background"])
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1) # 메시지 창
        self.root = root # MainWindow instance

        self.on_language_change = on_language_change
        self.languages = api_services.get_tts_supported_languages()
        lang_names = list(self.languages.keys())

        self.lang_codes_3_letter = {
            "한국어": "kor", "영어": "eng", "일본어": "jpn", "중국어": "chn",
            "베트남어": "vnm", "인도네시아어": "idn", "이탈리아어": "ita",
            "스페인어": "spa", "프랑스어": "fra", "독일어": "deu"
        }

        self.native_lang_var = tk.StringVar()
        self.learning_lang_var = tk.StringVar()
        self.project_name_var = tk.StringVar()
        self.identifier_var = tk.StringVar()

        self.native_lang_var.trace_add("write", self._update_project_info)
        self.learning_lang_var.trace_add("write", self._update_project_info)

        self._create_widgets()
        self._load_last_settings()

    def _create_widgets(self):
        # --- 위젯 생성 헬퍼 ---
        from src.ui.ui_utils import create_labeled_widget
        
        # --- 1.1. 데이터 섹션 ---
        data_section_frame = ctk.CTkFrame(self, fg_color=config.COLOR_THEME["widget"])
        data_section_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        # 1행
        row1 = ctk.CTkFrame(data_section_frame, fg_color="transparent")
        row1.pack(fill="x", padx=5, pady=2, anchor="w")
        
        self.languages = api_services.get_tts_supported_languages()
        lang_names = list(self.languages.keys())

        # `create_labeled_widget`를 사용하여 위젯 생성하고 인스턴스 변수로 저장
        _, self.native_lang_combo = create_labeled_widget(row1, "원어", 10, "combo", {"values": lang_names})
        self.native_lang_combo.master.pack(side="left", padx=(0,15))
        self.native_lang_combo.set("한국어")
        
        _, self.learning_lang_combo = create_labeled_widget(row1, "학습어", 10, "combo", {"values": lang_names})
        self.learning_lang_combo.master.pack(side="left", padx=(0,15))
        self.learning_lang_combo.set("중국어")

        # 언어 변경 시 콜백 함수 호출
        self.native_lang_combo.configure(command=self._language_changed)
        self.learning_lang_combo.configure(command=self._language_changed)
        
        _, project_name_entry = create_labeled_widget(row1, "프로젝트명", 20, "entry", {"textvariable": self.project_name_var, "state": "readonly"})
        project_name_entry.master.pack(side="left", padx=(0,15))
        
        _, identifier_entry = create_labeled_widget(row1, "식별자", 20, "entry", {"textvariable": self.identifier_var, "state": "readonly"})
        identifier_entry.master.pack(side="left", padx=(0,15))

        # 2행
        row2 = ctk.CTkFrame(data_section_frame, fg_color="transparent")
        row2.pack(fill="x", padx=5, pady=2, anchor="w")
        
        _, self.topic_combo = create_labeled_widget(row2, "학습 주제", 20, "combo", {"values": ["일상", "비즈니스", "여행"]})
        self.topic_combo.master.pack(side="left", padx=(0,15))
        self.topic_combo.set("일상")

        self.custom_topic_entry = ctk.CTkEntry(row2, placeholder_text="직접 주제를 입력하세요", width=50*9)
        self.custom_topic_entry.pack(side="left", padx=(0, 15), pady=5)

        _, self.level_combo = create_labeled_widget(row2, "등급", 15, "combo", {"values": ["초급", "중급", "고급"]})
        self.level_combo.master.pack(side="left", padx=(0,15))
        self.level_combo.set("초급")

        _, self.count_combo = create_labeled_widget(row2, "데이터 개수", 3, "combo", {"values": [str(i) for i in range(5, 21, 5)]})
        self.count_combo.master.pack(side="left", padx=(0,15))
        self.count_combo.set("5")

        # 3행
        row3 = ctk.CTkFrame(data_section_frame, fg_color="transparent")
        row3.pack(fill="x", padx=5, pady=2, anchor="w")

        _, self.ai_service_combo = create_labeled_widget(row3, "AI 서비스", 20, "combo", {"values": ["gemini-2.5-flash", "gemini-2.5-pro"]})
        self.ai_service_combo.master.pack(side="left", padx=(0,15))
        self.ai_service_combo.set("gemini-2.5-flash")
        
        button_kwargs = {
            "fg_color": config.COLOR_THEME["button"],
            "hover_color": config.COLOR_THEME["button_hover"],
            "text_color": config.COLOR_THEME["text"]
        }
        ctk.CTkButton(row3, text="AI 데이터 생성", command=self._on_click_generate_ai_data, **button_kwargs).pack(side="left", pady=5)
        ctk.CTkButton(row3, text="데이터 읽기", command=self._on_click_read_data, **button_kwargs).pack(side="left", padx=(10,0), pady=5)

        # --- 1.2. 스크립트 섹션 ---
        script_section_frame = ctk.CTkFrame(self, fg_color=config.COLOR_THEME["widget"])
        script_section_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        script_section_frame.grid_columnconfigure(0, weight=1)
        script_section_frame.grid_rowconfigure(1, weight=1)

        script_selector_frame = ctk.CTkFrame(script_section_frame, fg_color="transparent")
        script_selector_frame.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        _, self.script_selector_combo = create_labeled_widget(
            script_selector_frame, "스크립트 선택", 30, "combo",
            {"values": ["회화 스크립트", "타이틀 스크립트", "썸네일 스크립트", "인트로 스크립트", "엔딩 스크립트", "키워드 스크립트"],
             "fg_color": config.COLOR_THEME["widget"]}
        )
        self.script_selector_combo.master.pack(side="left")
        self.script_selector_combo.set("회화 스크립트")
        self.script_selector_combo.configure(command=lambda _: self._render_selected_script())
        
        # 스크립트 표시 컨테이너 (텍스트/그리드 전환)
        self.script_display_frame = ctk.CTkFrame(script_section_frame, fg_color=config.COLOR_THEME["widget"])
        self.script_display_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.script_display_frame.grid_columnconfigure(0, weight=1)
        self.script_display_frame.grid_rowconfigure(0, weight=1)

        # 텍스트 박스
        self.script_textbox = ctk.CTkTextbox(self.script_display_frame, fg_color=config.COLOR_THEME["widget"])
        self.script_textbox.grid(row=0, column=0, sticky="nsew")

        # CSV 그리드 (ttk.Treeview)
        self.csv_tree = ttk.Treeview(self.script_display_frame, columns=("순번", "원어", "학습어", "읽기"), show="headings")
        # 컬럼 폭: 순번(고정 50), 나머지 3개는 동일 비율 가변
        for col in ("순번", "원어", "학습어", "읽기"):
            self.csv_tree.heading(col, text=col)
        self.csv_tree.column("순번", width=50, minwidth=50, stretch=False, anchor="center")
        for col in ("원어", "학습어", "읽기"):
            self.csv_tree.column(col, width=200, stretch=True, anchor="w")
        self.csv_scroll_y = ttk.Scrollbar(self.script_display_frame, orient="vertical", command=self.csv_tree.yview)
        self.csv_tree.configure(yscrollcommand=self.csv_scroll_y.set)
        self.csv_tree.grid(row=0, column=0, sticky="nsew")
        self.csv_scroll_y.grid(row=0, column=1, sticky="ns")
        # 초기에는 숨김
        self.csv_tree.grid_remove()
        self.csv_scroll_y.grid_remove()

        # --- 1.3. 메시지 윈도우 ---
        self.message_textbox = ctk.CTkTextbox(self, fg_color=config.COLOR_THEME["widget"])
        self.message_textbox.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")

        # --- 1.4. 콘트롤 버튼 섹션 ---
        control_button_frame = ctk.CTkFrame(self, fg_color=config.COLOR_THEME["widget"])
        control_button_frame.grid(row=3, column=0, padx=10, pady=10, sticky="ew")

        # 주요 버튼들을 속성으로 보관하여 활성/비활성 제어
        self.btn_audio_generate = ctk.CTkButton(control_button_frame, text="오디오 생성", state="disabled", command=self._on_click_audio_generate, **button_kwargs)
        self.btn_audio_generate.pack(side="left", padx=5, pady=5, expand=True, fill="x")

        self.btn_audio_play = ctk.CTkButton(control_button_frame, text="오디오 듣기", state="disabled", command=self._on_click_audio_play, **button_kwargs)
        self.btn_audio_play.pack(side="left", padx=5, pady=5, expand=True, fill="x")

        self.btn_thumb_generate = ctk.CTkButton(control_button_frame, text="썸네일 생성", command=self._on_click_thumb_generate, **button_kwargs)
        self.btn_thumb_generate.pack(side="left", padx=5, pady=5, expand=True, fill="x")

        self.btn_video_dialogue = ctk.CTkButton(control_button_frame, text="회화 비디오", **button_kwargs)
        self.btn_video_dialogue.pack(side="left", padx=5, pady=5, expand=True, fill="x")

        self.btn_video_intro = ctk.CTkButton(control_button_frame, text="인트로 비디오", **button_kwargs)
        self.btn_video_intro.pack(side="left", padx=5, pady=5, expand=True, fill="x")

        self.btn_video_ending = ctk.CTkButton(control_button_frame, text="엔딩 비디오", **button_kwargs)
        self.btn_video_ending.pack(side="left", padx=5, pady=5, expand=True, fill="x")

        self.btn_video_conversation = ctk.CTkButton(control_button_frame, text="대화 비디오", **button_kwargs)
        self.btn_video_conversation.pack(side="left", padx=5, pady=5, expand=True, fill="x")

        self.btn_stop = ctk.CTkButton(control_button_frame, text="정지", command=(self.root.stop_all_sounds if self.root else None), **button_kwargs)
        self.btn_stop.pack(side="left", padx=5, pady=5, expand=True, fill="x")

        self.btn_exit = ctk.CTkButton(control_button_frame, text="종료", command=(self.root._on_closing if self.root else None), **button_kwargs)
        self.btn_exit.pack(side="left", padx=5, pady=5, expand=True, fill="x")

        # 초기 프로젝트명/식별자 설정 동기화
        self._language_changed()

    def log_message(self, message):
        """메시지 텍스트박스에 메시지를 추가합니다."""
        self.message_textbox.insert(tk.END, message + "\n")
        self.message_textbox.see(tk.END) # 자동 스크롤

    def _load_last_settings(self):
        try:
            config_path = os.path.join(config.BASE_DIR, 'config.json')
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                last_native = config_data.get("last_native_lang")
                last_learning = config_data.get("last_learning_lang")

                if last_native and last_native in self.languages:
                    self.native_lang_var.set(last_native)
                
                if last_learning and last_learning in self.languages:
                    self.learning_lang_var.set(last_learning)
        except Exception as e:
            # 파일이 없거나 JSON 형식이 잘못된 경우 등 오류 발생 시 무시하고 넘어감
            print(f"Error loading config: {e}")

    def _update_project_info(self, *args):
        native_lang_name = self.native_lang_var.get()
        learning_lang_name = self.learning_lang_var.get()

        if native_lang_name in self.lang_codes_3_letter and learning_lang_name in self.lang_codes_3_letter:
            native_code_short = self.lang_codes_3_letter[native_lang_name]
            learning_code_short = self.lang_codes_3_letter[learning_lang_name]
            
            project_name = f"{native_code_short}-{learning_code_short}"
            self.project_name_var.set(project_name)
            self.identifier_var.set(project_name)

            # 콜백 이름 변경에 따른 수정
            if hasattr(self, 'on_language_change') and self.on_language_change:
                # 이 콜백은 언어 변경 시에만 호출되므로, 
                # 프로젝트 정보 업데이트 시 호출하는 것이 맞는지 확인 필요.
                # 현재 로직에서는 언어 정보가 아닌 프로젝트명만 업데이트하므로
                # 직접적인 언어 변경 콜백 호출은 부적절할 수 있음.
                # 여기서는 MainWindow의 다른 메서드를 호출하는 것이 더 적절할 수 있음.
                # 예: self.root._on_project_info_updated(...)
                pass

    def _language_changed(self, *args):
        # 콤보 값 -> 내부 StringVar 동기화 및 프로젝트명/식별자 갱신
        try:
            self.native_lang_var.set(self.native_lang_combo.get())
            self.learning_lang_var.set(self.learning_lang_combo.get())
            self._update_project_info()
        except Exception:
            pass
        # MainWindow 초기화 중엔 data_page 속성이 없을 수 있으므로 안전 가드
        try:
            if self.on_language_change and getattr(self.root, 'data_page', None):
                self.on_language_change()
        except Exception:
            pass

    def get_selected_language_codes(self):
        native_lang_name = self.native_lang_combo.get()
        learning_lang_name = self.learning_lang_combo.get()
        
        native_lang_code = self.languages.get(native_lang_name)
        learning_lang_code = self.languages.get(learning_lang_name)
        
        return native_lang_code, learning_lang_code

    def _on_click_read_data(self):
        try:
            if self.load_generated_data():
                project_name = self.project_name_var.get() or "project"
                identifier = self.identifier_var.get() or project_name
                json_path = os.path.join(config.OUTPUT_PATH, project_name, identifier, f"{identifier}_ai.json")
                self.log_message(f"[데이터 읽기] 불러옴: {json_path}")
                api_services.save_outputs_from_ai_data(self.generated_data, project_name, identifier)
                self._render_selected_script()
                self._update_audio_buttons_state()
            else:
                project_name = self.project_name_var.get() or "project"
                identifier = self.identifier_var.get() or project_name
                json_path = os.path.join(config.OUTPUT_PATH, project_name, identifier, f"{identifier}_ai.json")
                self.log_message(f"[데이터 읽기] 파일이 없습니다: {json_path}")
        except Exception as e:
            self.log_message(f"[오류] 데이터 읽기 실패: {e}")

    def load_generated_data(self):
        """Loads the generated AI data from the JSON file without logging to the UI."""
        try:
            project_name = self.project_name_var.get() or "project"
            identifier = self.identifier_var.get() or project_name
            out_dir = os.path.join(config.OUTPUT_PATH, project_name, identifier)
            json_path = os.path.join(out_dir, f"{identifier}_ai.json")
            if not os.path.exists(json_path):
                return False
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.generated_data = data
            return True
        except Exception:
            return False

    # --- AI 데이터 생성 핸들러 ---
    def _on_click_generate_ai_data(self):
        try:
            project_name = self.project_name_var.get() or "project"
            identifier = self.identifier_var.get() or project_name

            native_code, learning_code = self.get_selected_language_codes()
            learner_level = self.level_combo.get()
            topic = self.custom_topic_entry.get().strip() or self.topic_combo.get()
            try:
                count = int(self.count_combo.get())
            except Exception:
                count = 5
            model_name = self.ai_service_combo.get() or "gemini-2.5-flash"

            dialogue_script_text = self.script_textbox.get("1.0", tk.END).strip()
            params = {
                "nativeLanguage": native_code,
                "learningLanguage": learning_code,
                "learnerLevel": learner_level,
                "topic": topic,
                "count": count,
            }
            if dialogue_script_text:
                params["dialogueScript"] = dialogue_script_text

            self.log_message("[AI] 데이터 생성 요청 중...")
            result = api_services.generate_ai_data(
                params=params,
                model_name=model_name,
                project_name=project_name,
                identifier=identifier,
            )

            self.generated_data = result.get("data", {})
            self.log_message(f"[AI] 프롬프트 저장: {result.get('prompt_path')}")
            self.log_message(f"[AI] 결과 저장: {result.get('json_path')}")
            # 스크립트별 텍스트 저장
            saved = api_services.save_outputs_from_ai_data(self.generated_data, project_name, identifier)
            if saved:
                self.log_message("[저장] 스크립트 파일 저장 완료")
            self._render_selected_script()
            self.log_message("[AI] 데이터 생성 완료")
            self._update_audio_buttons_state()

        except Exception as e:
            self.log_message(f"[오류] AI 데이터 생성 실패: {e}")

    def _render_selected_script(self):
        data = getattr(self, "generated_data", None)
        if not data:
            return
        try:
            selected = self.script_selector_combo.get()
            if selected == "회화 스크립트":
                # nested 또는 top-level 모두 지원
                dialogue_csv = data.get("fullVideoScript", {}).get("dialogueCsv") or data.get("dialogueCsv", "")
                if dialogue_csv and dialogue_csv.strip():
                    self._show_csv_grid(dialogue_csv)
                else:
                    self.log_message("[데이터] dialogueCsv가 없어 표시할 수 없습니다.")
                    self._show_text_content("")
            else:
                if selected == "타이틀 스크립트":
                    titles = data.get("videoTitleSuggestions", [])
                    content = "\n".join(titles)
                elif selected == "키워드 스크립트":
                    keywords = data.get("videoKeywords", [])
                    content = ", ".join(keywords)
                elif selected == "인트로 스크립트":
                    content = self._sentences_multiline(data.get("introScript", ""))
                elif selected == "엔딩 스크립트":
                    content = self._sentences_multiline(data.get("endingScript", ""))
                elif selected == "썸네일 스크립트":
                    versions = data.get("thumbnailTextVersions", [])
                    lines = []
                    for i, v in enumerate(versions, 1):
                        text = v.get("text", "")
                        concept = v.get("imageConcept", "")
                        lines.append(f"[버전 {i}]\n{text}\n- 콘셉트: {concept}\n")
                    content = "\n".join(lines)
                else:
                    content = ""
                self._show_text_content(content)

            self._update_audio_buttons_state()
        except Exception as e:
            self.log_message(f"[오류] 스크립트 렌더링 실패: {e}")

    def _show_text_content(self, content: str):
        # Treeview 숨기고 텍스트 표시
        try:
            self.csv_tree.grid_remove()
            self.csv_scroll_y.grid_remove()
        except Exception:
            pass
        self.script_textbox.grid(row=0, column=0, sticky="nsew")
        self.script_textbox.delete("1.0", tk.END)
        self.script_textbox.insert(tk.END, content)

    def _show_csv_grid(self, dialogue_csv: str):
        # 텍스트 숨기고 그리드 표시
        self.script_textbox.grid_remove()
        self.csv_tree.grid(row=0, column=0, sticky="nsew")
        self.csv_scroll_y.grid(row=0, column=1, sticky="ns")
        # 기존 행 제거
        for iid in self.csv_tree.get_children():
            self.csv_tree.delete(iid)
        if not dialogue_csv:
            return
        # CSV 파싱
        # RFC4180 호환: 큰따옴표로 감싸진 필드 처리
        reader = csv.reader(io.StringIO(dialogue_csv))
        rows = list(reader)
        # 헤더 제거
        if rows and [c.strip('"') for c in rows[0][:4]] == ["순번", "원어", "학습어", "읽기"]:
            rows = rows[1:]
        for row in rows:
            normalized = [c.strip('"') for c in row]
            padded = (normalized + [""] * 4)[:4]
            self.csv_tree.insert("", tk.END, values=padded)

    def _sentences_multiline(self, text: str) -> str:
        if not text:
            return ""
        parts = [p.strip() for p in re.split(r"(?<=[\.!\?。？！])\s+", text.strip()) if p.strip()]
        return "\n".join(parts)

    def _update_audio_buttons_state(self):
        try:
            has_text = bool(self.script_textbox.winfo_ismapped() and self.script_textbox.get("1.0", tk.END).strip())
            has_rows = bool(self.csv_tree.winfo_ismapped() and len(self.csv_tree.get_children()) > 0)
            has_content = has_text or has_rows
            new_state = "normal" if has_content else "disabled"
            self.btn_audio_generate.configure(state=new_state)
            self.btn_audio_play.configure(state=new_state)
        except Exception:
            pass

    def _on_click_thumb_generate(self):
        try:
            # Image 탭의 썸네일 생성 함수를 호출
            image_page = getattr(self.root, 'image_page', None)
            if not image_page:
                self.log_message('[썸네일] 이미지 설정 탭을 찾지 못했습니다.')
                return
            # 프로젝트/식별자는 image_page 내부에서 root.data_page를 참조하여 사용
            image_page.generate_thumbnail_images()
            self.log_message('[썸네일] 생성 완료')
        except Exception as e:
            self.log_message(f'[썸네일 오류] {e}')

    # --- 오디오 재생 ---
    def _get_dialogue_rows(self):
        data = getattr(self, "generated_data", None) or {}
        csv_text = (data.get("fullVideoScript") or {}).get("dialogueCsv") or ""
        if not csv_text.strip():
            return []
        reader = csv.reader(io.StringIO(csv_text))
        rows = list(reader)
        if rows and [c.strip('"') for c in rows[0][:4]] == ["순번", "원어", "학습어", "읽기"]:
            rows = rows[1:]
        normalized = []
        for row in rows:
            fields = [c.strip('"') for c in row]
            seq, native_text, learning_text, reading_text = (fields + [""] * 4)[:4]
            normalized.append((seq, native_text, learning_text, reading_text))
        return normalized

    def _on_click_audio_play(self):
        playback_thread = threading.Thread(target=self._play_dialogue_audio_thread)
        playback_thread.daemon = True
        playback_thread.start()

    def _play_dialogue_audio_thread(self):
        try:
            # 스피커 설정 가져오기
            speaker_page = getattr(self.root, 'speaker_page', None)
            if not speaker_page:
                self.log_message("[오디오] 화자 설정 탭을 먼저 구성하세요.")
                return
            native_voice_name = speaker_page.native_speaker_dropdown.get()
            learner_voice_names = [w["dropdown"].get() for w in speaker_page.learner_speaker_widgets]
            native_lang_code = speaker_page.native_lang_code
            learning_lang_code = speaker_page.learning_lang_code
            if not native_voice_name or not learner_voice_names or not native_lang_code or not learning_lang_code:
                project_name = self.project_name_var.get() or "project"
                identifier = self.identifier_var.get() or project_name
                n_code, l_code = self.get_selected_language_codes()
                speaker_page.update_language_settings(
                    native_lang_code=n_code,
                    learning_lang_code=l_code,
                    project_name=project_name,
                    identifier=identifier
                )
                # 로드 이후 값 다시 읽기
                native_voice_name = speaker_page.native_speaker_dropdown.get()
                learner_voice_names = [w["dropdown"].get() for w in speaker_page.learner_speaker_widgets]
                native_lang_code = speaker_page.native_lang_code
                learning_lang_code = speaker_page.learning_lang_code
                # 기본값 보정
                if (not native_voice_name) and native_lang_code:
                    native_voices = api_services.get_voices_for_language(native_lang_code)
                    if native_voices:
                        native_voice_name = native_voices[0]
                        speaker_page.native_speaker_dropdown.set(native_voice_name)
                if (not learner_voice_names) and learning_lang_code:
                    learner_voices = api_services.get_voices_for_language(learning_lang_code)
                    if learner_voices:
                        if not speaker_page.learner_speaker_widgets:
                            speaker_page._update_learner_speakers_ui(1)
                        speaker_page.learner_speaker_widgets[0]["dropdown"].set(learner_voices[0])
                        learner_voice_names = [w["dropdown"].get() for w in speaker_page.learner_speaker_widgets]
            # 최종 검증 실패 시 중단
            if not native_voice_name or not learner_voice_names or not native_lang_code or not learning_lang_code:
                self.log_message("[오디오] 저장된 화자 설정을 찾지 못했습니다.")
                return

            rows = self._get_dialogue_rows()
            if not rows:
                self.log_message("[오디오] 재생할 회화 데이터가 없습니다.")
                return

            # 취소 이벤트 초기화
            if self.root:
                self.root.cancel_event.clear()

            self.log_message("[오디오] 재생 시작")
            for seq, native_text, learning_text, _reading in rows:
                if self.root and self.root.cancel_event.is_set():
                    break
                # 원어 화자
                if native_text.strip():
                    self._speak_once(native_text, native_lang_code, native_voice_name)
                    if self.root and self.root.cancel_event.is_set():
                        break
                    # 1초 대기 중에도 취소 가능
                    if self.root and self.root.cancel_event.wait(1.0):
                        break
                # 학습어 화자들
                for voice_name in learner_voice_names:
                    if self.root and self.root.cancel_event.is_set():
                        break
                    if learning_text.strip():
                        self._speak_once(learning_text, learning_lang_code, voice_name)
                        if self.root and self.root.cancel_event.is_set():
                            break
                        if self.root and self.root.cancel_event.wait(1.0):
                            break
            self.log_message("[오디오] 재생 완료")
        except Exception as e:
            self.log_message(f"[오디오 오류] {e}")

    def _on_click_audio_generate(self):
        # 전체 행을 MP3로 생성 및 저장
        try:
            speaker_page = getattr(self.root, 'speaker_page', None)
            if not speaker_page:
                self.log_message("[오디오 생성] 화자 설정 탭을 먼저 구성하세요.")
                return
            native_voice_name = speaker_page.native_speaker_dropdown.get()
            learner_voice_names = [w["dropdown"].get() for w in speaker_page.learner_speaker_widgets]
            native_lang_code = speaker_page.native_lang_code
            learning_lang_code = speaker_page.learning_lang_code
            # 화자/언어 정보가 비어있으면 저장된 설정을 자동 로드하여 세팅
            if not native_voice_name or not learner_voice_names or not native_lang_code or not learning_lang_code:
                project_name = self.project_name_var.get() or "project"
                identifier = self.identifier_var.get() or project_name
                n_code, l_code = self.get_selected_language_codes()
                # Speaker 탭에 언어/프로젝트 정보를 반영하면서 저장된 설정 로드
                speaker_page.update_language_settings(
                    native_lang_code=n_code,
                    learning_lang_code=l_code,
                    project_name=project_name,
                    identifier=identifier
                )
                # 로드 이후 값 다시 읽기
                native_voice_name = speaker_page.native_speaker_dropdown.get()
                learner_voice_names = [w["dropdown"].get() for w in speaker_page.learner_speaker_widgets]
                native_lang_code = speaker_page.native_lang_code
                learning_lang_code = speaker_page.learning_lang_code
                # 여전히 비어있다면 가능한 첫 번째 화자로 기본 세팅
                if (not native_voice_name) and native_lang_code:
                    native_voices = api_services.get_voices_for_language(native_lang_code)
                    if native_voices:
                        native_voice_name = native_voices[0]
                        speaker_page.native_speaker_dropdown.set(native_voice_name)
                if (not learner_voice_names) and learning_lang_code:
                    learner_voices = api_services.get_voices_for_language(learning_lang_code)
                    if learner_voices:
                        # 최소 1명 보장
                        if not speaker_page.learner_speaker_widgets:
                            speaker_page._update_learner_speakers_ui(1)
                        speaker_page.learner_speaker_widgets[0]["dropdown"].set(learner_voices[0])
                        learner_voice_names = [w["dropdown"].get() for w in speaker_page.learner_speaker_widgets]
            # 최종 검증
            if not native_voice_name or not learner_voice_names or not native_lang_code or not learning_lang_code:
                self.log_message("[오디오 생성] 저장된 화자 설정을 찾지 못했습니다.")
                return

            rows = self._get_dialogue_rows()
            if not rows:
                self.log_message("[오디오 생성] 생성할 회화 데이터가 없습니다.")
                return

            # 각 세그먼트를 순서대로 합쳐 MP3로 저장
            segments = []
            silence_wav = self._generate_silence_wav(duration_sec=1.0)
            for seq, native_text, learning_text, _reading in rows:
                if native_text.strip():
                    wav = self._synthesize_linear16(native_text, native_lang_code, native_voice_name)
                    if wav:
                        segments.append(wav)
                        segments.append(silence_wav)
                for voice_name in learner_voice_names:
                    if learning_text.strip():
                        wav = self._synthesize_linear16(learning_text, learning_lang_code, voice_name)
                        if wav:
                            segments.append(wav)
                            segments.append(silence_wav)

            if not segments:
                self.log_message("[오디오 생성] 생성된 오디오 세그먼트가 없습니다.")
                return

            # WAV 결합 후 ffmpeg로 MP3 인코딩
            combined_wav = self._concat_wav_segments(segments)
            project_name = self.project_name_var.get() or "project"
            identifier = self.identifier_var.get() or project_name
            out_dir = os.path.join(config.OUTPUT_PATH, project_name, identifier)
            os.makedirs(out_dir, exist_ok=True)
            mp3_dir = os.path.join(out_dir, "mp3")
            os.makedirs(mp3_dir, exist_ok=True)
            out_mp3 = os.path.join(mp3_dir, f"{identifier}.mp3")
            self._encode_wav_to_mp3(combined_wav, out_mp3)
            self.log_message(f"[오디오 생성] 저장 완료: {out_mp3}")
        except Exception as e:
            self.log_message(f"[오디오 생성 오류] {e}")

    def _synthesize_linear16(self, text: str, lang: str, voice: str) -> bytes:
        # SSML <mark>를 사용한 타이밍 정보 활성화 (가능한 경우)
        ssml = f"<speak><mark name='start'/>{self._escape_ssml(text)}<mark name='end'/></speak>"
        return api_services.synthesize_speech(ssml, lang, voice, audio_encoding="LINEAR16", sample_rate_hz=16000, enable_timepoints=True) or b""

    def _escape_ssml(self, text: str) -> str:
        return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def _generate_silence_wav(self, duration_sec: float = 1.0, sample_rate: int = 16000) -> bytes:
        import wave, struct
        num_samples = int(sample_rate * duration_sec)
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit PCM
            wf.setframerate(sample_rate)
            silence_frame = struct.pack('<h', 0)
            for _ in range(num_samples):
                wf.writeframes(silence_frame)
        return buf.getvalue()

    def _concat_wav_segments(self, segments: list[bytes]) -> bytes:
        import wave
        import struct
        # 가정: 모두 동일한 포맷(16kHz, mono, 16-bit)
        sample_rate = 16000
        out = io.BytesIO()
        with wave.open(out, 'wb') as wf_out:
            wf_out.setnchannels(1)
            wf_out.setsampwidth(2)
            wf_out.setframerate(sample_rate)
            for seg in segments:
                with wave.open(io.BytesIO(seg), 'rb') as wf_in:
                    wf_out.writeframes(wf_in.readframes(wf_in.getnframes()))
        return out.getvalue()

    def _encode_wav_to_mp3(self, wav_bytes: bytes, out_mp3_path: str):
        # ffmpeg를 사용하여 바이트 입력을 mp3로 저장
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp:
                tmp.write(wav_bytes)
                tmp_path = tmp.name
            cmd = [
                'ffmpeg', '-y', '-loglevel', 'error',
                '-i', tmp_path,
                '-codec:a', 'libmp3lame', '-b:a', '192k',
                out_mp3_path
            ]
            proc = subprocess.Popen(cmd)
            if self.root:
                self.root.register_process(proc)
            # 취소 가능 대기
            while True:
                ret = proc.poll()
                if ret is not None:
                    break
                if self.root and self.root.cancel_event.is_set():
                    try:
                        proc.terminate()
                    except Exception:
                        pass
                    break
                time.sleep(0.1)
        finally:
            try:
                if 'tmp_path' in locals() and os.path.exists(tmp_path):
                    os.remove(tmp_path)
                if self.root and 'proc' in locals():
                    self.root.unregister_process(proc)
            except Exception:
                pass

    def _speak_once(self, text: str, lang_code: str, voice_name: str):
        try:
            audio_content = api_services.synthesize_speech(text, lang_code, voice_name, audio_encoding="LINEAR16", sample_rate_hz=16000)
            if not audio_content:
                return
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                tmp_file.write(audio_content)
                tmp_path = tmp_file.name
            process = subprocess.Popen(["afplay", tmp_path])
            # MainWindow에 현재 재생 프로세스 등록
            if self.root:
                self.root.current_play_obj = process
                self.root.register_process(process)
            # 취소 가능 대기
            while True:
                ret = process.poll()
                if ret is not None:
                    break
                if self.root and self.root.cancel_event.is_set():
                    try:
                        process.terminate()
                    except Exception:
                        pass
                    break
                time.sleep(0.05)
        except Exception:
            pass
        finally:
            try:
                if 'tmp_path' in locals() and os.path.exists(tmp_path):
                    os.remove(tmp_path)
                if self.root and 'process' in locals():
                    self.root.unregister_process(process)
            except Exception:
                pass
