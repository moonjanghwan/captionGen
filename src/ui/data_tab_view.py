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
    def __init__(self, parent, root=None):
        super().__init__(parent, fg_color=config.COLOR_THEME["background"])
        self.root = root
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=3)
        self.grid_rowconfigure(2, weight=1)

        self.languages = api_services.get_tts_supported_languages()
        self._save_job = None

        self.lang_codes_3_letter = {
            "한국어": "kor", "영어": "eng", "일본어": "jpn", "중국어": "chn",
            "베트남어": "vnm", "인도네시아어": "idn", "이탈리아어": "ita",
            "스페인어": "spa", "프랑스어": "fra", "독일어": "deu"
        }

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="black", foreground="white", fieldbackground="black", borderwidth=0)
        style.map('Treeview', background=[('selected', '#22559B')])
        style.configure("Treeview.Heading", background="#333333", foreground="white", relief="flat")
        style.map("Treeview.Heading", background=[('active', '#4A4A4A')])

        self._init_state_variables()
        self._create_widgets()
        self._load_settings()
        self._setup_csv_editing()

    def _init_state_variables(self):
        self.native_lang_var = tk.StringVar()
        self.learning_lang_var = tk.StringVar()
        self.project_name_var = tk.StringVar()
        self.identifier_var = tk.StringVar()
        self.topic_var = tk.StringVar()
        self.custom_topic_var = tk.StringVar()
        self.level_var = tk.StringVar()
        self.count_var = tk.StringVar()
        self.ai_service_var = tk.StringVar()

        self.native_lang_var.trace_add("write", self._on_project_related_change)
        self.learning_lang_var.trace_add("write", self._on_project_related_change)
        self.topic_var.trace_add("write", self._schedule_save)
        self.custom_topic_var.trace_add("write", self._schedule_save)
        self.level_var.trace_add("write", self._schedule_save)
        self.count_var.trace_add("write", self._schedule_save)
        self.ai_service_var.trace_add("write", self._schedule_save)

    def _on_project_related_change(self, *args):
        self._update_project_info()
        self._schedule_save()
        if hasattr(self.root, '_update_speaker_tab') and callable(self.root._update_speaker_tab):
            self.root.after(10, self.root._update_speaker_tab)

    def _create_widgets(self):
        from src.ui.ui_utils import create_labeled_widget
        button_kwargs = {"fg_color": config.COLOR_THEME["button"], "hover_color": config.COLOR_THEME["button_hover"], "text_color": config.COLOR_THEME["text"]}
        
        data_section_frame = ctk.CTkFrame(self, fg_color=config.COLOR_THEME["widget"])
        data_section_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        row1 = ctk.CTkFrame(data_section_frame, fg_color="transparent")
        row1.pack(fill="x", padx=5, pady=2, anchor="w")
        
        lang_names = list(self.languages.keys())
        _, self.native_lang_combo = create_labeled_widget(row1, "원어", 10, "combo", {"values": lang_names, "variable": self.native_lang_var})
        self.native_lang_combo.master.pack(side="left", padx=(0,15))
        _, self.learning_lang_combo = create_labeled_widget(row1, "학습어", 10, "combo", {"values": lang_names, "variable": self.learning_lang_var})
        self.learning_lang_combo.master.pack(side="left", padx=(0,15))
        
        _, project_name_entry = create_labeled_widget(row1, "프로젝트명", 20, "entry", {"textvariable": self.project_name_var, "state": "readonly"})
        project_name_entry.master.pack(side="left", padx=(0,15))
        _, identifier_entry = create_labeled_widget(row1, "식별자", 20, "entry", {"textvariable": self.identifier_var, "state": "readonly"})
        identifier_entry.master.pack(side="left", padx=(0,15))
        
        row2 = ctk.CTkFrame(data_section_frame, fg_color="transparent")
        row2.pack(fill="x", padx=5, pady=2, anchor="w")
        
        topic_values = ["일상", "비즈니스", "여행", "음식", "쇼핑", "교통", "학교", "병원"]
        _, self.topic_combo = create_labeled_widget(row2, "학습 주제", 20, "combo", {"values": topic_values, "variable": self.topic_var})
        self.topic_combo.master.pack(side="left", padx=(0,15))
        self.custom_topic_entry = ctk.CTkEntry(row2, placeholder_text="직접 주제를 입력하세요", width=40*9, textvariable=self.custom_topic_var)
        self.custom_topic_entry.pack(side="left", padx=(0, 15), pady=5)
        _, self.level_combo = create_labeled_widget(row2, "등급", 15, "combo", {"values": ["초급", "중급", "고급"], "variable": self.level_var})
        self.level_combo.master.pack(side="left", padx=(0,15))
        _, self.count_combo = create_labeled_widget(row2, "데이터 개수", 3, "combo", {"values": [str(i) for i in range(5, 21, 5)], "variable": self.count_var})
        self.count_combo.master.pack(side="left", padx=(0,15))

        row3 = ctk.CTkFrame(data_section_frame, fg_color="transparent")
        row3.pack(fill="x", padx=5, pady=2, anchor="w")

        _, self.ai_service_combo = create_labeled_widget(row3, "AI 서비스", 20, "combo", {"values": ["gemini-1.5-flash", "gemini-1.5-pro"], "variable": self.ai_service_var})
        self.ai_service_combo.master.pack(side="left", padx=(0,15))

        script_types = ["conversation", "dialogue", "title", "thumbnail", "intro", "ending", "keywords"]
        script_dropdown_colors = {"fg_color": "black", "button_color": "#555555", "text_color": "white"}
        _, self.script_selector_combo = create_labeled_widget(row3, "스크립트", 20, "combo", {"values": script_types, **script_dropdown_colors})
        self.script_selector_combo.master.pack(side="left", padx=(10,0))
        self.script_selector_combo.set("conversation")
        self.script_selector_combo.configure(command=lambda _: self._render_selected_script())

        ctk.CTkButton(row3, text="AI 데이터 생성", command=self._on_click_generate_ai_data, **button_kwargs).pack(side="left", padx=(10,0), pady=5)
        ctk.CTkButton(row3, text="AI 데이터 읽기", command=self._on_click_read_ai_data, **button_kwargs).pack(side="left", padx=(10,0), pady=5)
        ctk.CTkButton(row3, text="AI 데이터 저장", command=self._on_click_save_ai_data, **button_kwargs).pack(side="left", padx=(10,0), pady=5)
        ctk.CTkButton(row3, text="대화 데이터 읽기", command=self._on_click_read_dialogue_data, **button_kwargs).pack(side="left", padx=(10,0), pady=5)
        ctk.CTkButton(row3, text="대화 데이터 저장", command=self._on_click_save_dialogue_data, **button_kwargs).pack(side="left", padx=(10,0), pady=5)

        script_section_frame = ctk.CTkFrame(self, fg_color="black")
        script_section_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        script_section_frame.grid_columnconfigure(0, weight=1)
        script_section_frame.grid_rowconfigure(0, weight=1)
        
        self.script_textbox = ctk.CTkTextbox(script_section_frame, fg_color="black", text_color="white")
        self.script_textbox.grid(row=0, column=0, sticky="nsew")

        self.csv_tree = ttk.Treeview(script_section_frame, show="headings", style="Treeview")
        self.csv_scroll_y = ttk.Scrollbar(script_section_frame, orient="vertical", command=self.csv_tree.yview)
        self.csv_tree.configure(yscrollcommand=self.csv_scroll_y.set)
        self.csv_tree.grid(row=0, column=0, sticky="nsew")
        self.csv_scroll_y.grid(row=0, column=1, sticky="ns")
        self.csv_tree.grid_remove()
        self.csv_scroll_y.grid_remove()
        
        self.message_textbox = tk.Text(self, height=15, bg="black", fg="white", insertbackground="white", relief="flat", borderwidth=0)
        self.message_textbox.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")


        control_button_frame = ctk.CTkFrame(self, fg_color=config.COLOR_THEME["widget"])
        control_button_frame.grid(row=3, column=0, padx=10, pady=10, sticky="ew")

        # self.btn_thumb_generate = ctk.CTkButton(control_button_frame, text="썸네일 생성", command=self._on_click_thumb_generate, **button_kwargs)
        # self.btn_thumb_generate.pack(side="left", padx=5, pady=5, expand=True, fill="x")
        self.btn_exit = ctk.CTkButton(control_button_frame, text="종료", command=(self.root._on_closing if self.root else None), **button_kwargs)
        self.btn_exit.pack(side="left", padx=5, pady=5, expand=True, fill="x")

    def _schedule_save(self, *args):
        if self._save_job:
            self.after_cancel(self._save_job)
        self._save_job = self.after(500, self._save_settings)

    def _save_settings(self):
        try:
            settings = {
                "native_lang": self.native_lang_var.get(),
                "learning_lang": self.learning_lang_var.get(),
                "topic": self.topic_var.get(),
                "custom_topic": self.custom_topic_var.get(),
                "level": self.level_var.get(),
                "count": self.count_var.get(),
                "ai_service": self.ai_service_var.get(),
            }
            settings_path = os.path.join(config.BASE_DIR, "project_settings.json")
            with open(settings_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=4)
            self.log_message(f"[자동 저장] 설정이 project_settings.json에 저장되었습니다.")
        except Exception as e:
            self.log_message(f"[저장 오류] 설정 저장에 실패했습니다: {e}")

    def _load_settings(self):
        try:
            settings_path = os.path.join(config.BASE_DIR, "project_settings.json")
            if os.path.exists(settings_path):
                with open(settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                self.log_message(f"[불러오기] 저장된 설정을 불러옵니다: {settings_path}")
            else:
                self.log_message("[불러오기] 저장된 설정 파일이 없어 기본값을 사용합니다.")
                settings = {}

            self.native_lang_var.set(settings.get("native_lang", "한국어"))
            self.learning_lang_var.set(settings.get("learning_lang", "영어"))
            self.topic_var.set(settings.get("topic", "일상"))
            self.custom_topic_var.set(settings.get("custom_topic", ""))
            self.level_var.set(settings.get("level", "초급"))
            self.count_var.set(settings.get("count", "5"))
            self.ai_service_var.set(settings.get("ai_service", "gemini-1.5-flash"))
                
        except Exception as e:
            self.log_message(f"[불러오기 오류] 설정 불러오기 실패: {e}")
            self.native_lang_var.set("한국어")
            self.learning_lang_var.set("영어")
            self.topic_var.set("일상")
            self.level_var.set("초급")
            self.count_var.set("5")
            self.ai_service_var.set("gemini-1.5-flash")

    def log_message(self, message):
        self.message_textbox.insert(tk.END, message + "\n")
        self.message_textbox.see(tk.END)

    def _update_project_info(self, *args):
        native_lang_name = self.native_lang_var.get()
        learning_lang_name = self.learning_lang_var.get()
        if native_lang_name in self.lang_codes_3_letter and learning_lang_name in self.lang_codes_3_letter:
            native_code_short = self.lang_codes_3_letter[native_lang_name]
            learning_code_short = self.lang_codes_3_letter[learning_lang_name]
            project_name = f"{native_code_short}-{learning_code_short}"
            self.project_name_var.set(project_name)
            self.identifier_var.set(project_name)

    def get_selected_language_codes(self):
        native_lang_name = self.native_lang_var.get()
        learning_lang_name = self.learning_lang_var.get()
        native_lang_code = self.languages.get(native_lang_name)
        learning_lang_code = self.languages.get(learning_lang_name)
        return native_lang_code, learning_lang_code

    def _on_click_read_ai_data(self):
        try:
            project_name = self.project_name_var.get()
            identifier = self.identifier_var.get()
            json_path = os.path.join(config.OUTPUT_PATH, project_name, identifier, f"{identifier}_ai.json")
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    self.generated_data = json.load(f)
                self.log_message(f"[AI 데이터 읽기] 성공: {json_path}")
                self._render_selected_script()
                self._update_audio_buttons_state()
                if self.root and hasattr(self.root, 'pipeline_page'):
                    self.root.pipeline_page.activate()
            else:
                self.log_message(f"[AI 데이터 읽기] 실패: 파일을 찾을 수 없습니다: {json_path}")
        except Exception as e:
            self.log_message(f"[오류] AI 데이터 읽기 실패: {e}")

    def _update_generated_data_from_ui(self):
        """현재 UI(CSV 그리드 또는 텍스트박스)의 내용을 self.generated_data에 반영합니다."""
        if not hasattr(self, 'generated_data') or not self.generated_data:
            return

        selected = self.script_selector_combo.get()

        # CSV 그리드가 활성화된 경우
        if self.csv_tree.winfo_ismapped():
            output = io.StringIO()
            writer = csv.writer(output)
            
            columns = self.csv_tree["columns"]
            writer.writerow(columns)
            
            for item_id in self.csv_tree.get_children():
                writer.writerow(self.csv_tree.item(item_id, 'values'))
            
            csv_data = output.getvalue()
            
            if "fullVideoScript" not in self.generated_data:
                self.generated_data["fullVideoScript"] = {}
            self.generated_data["fullVideoScript"]["dialogueCsv"] = csv_data
            self.log_message(f"[{selected}] 스크립트가 CSV 그리드로부터 업데이트되었습니다.")

        # 텍스트 박스가 활성화된 경우
        elif self.script_textbox.winfo_ismapped():
            content = self.script_textbox.get("1.0", tk.END).strip()
            
            script_map = {
                "title": "videoTitleSuggestions",
                "keywords": "videoKeywords",
                "intro": "introScript",
                "ending": "endingScript",
                "thumbnail": "thumbnailTextVersions"
            }
            data_key = script_map.get(selected)

            if not data_key:
                return

            if selected == "thumbnail":
                # 썸네일은 파싱이 복잡하므로, 여기서는 단순 텍스트로 저장하지 않고 건너뜁니다.
                # 추후 필요시 파싱 로직을 정교하게 구현해야 합니다.
                self.log_message("[저장] 썸네일 스크립트는 현재 UI에서 JSON으로 역변환하는 기능을 지원하지 않습니다.")
                pass
            elif isinstance(self.generated_data.get(data_key), list):
                self.generated_data[data_key] = content.splitlines()
            else:
                self.generated_data[data_key] = content
            
            self.log_message(f"[{selected}] 스크립트가 텍스트 박스로부터 업데이트되었습니다.")

    def _on_click_save_ai_data(self):
        try:
            if not hasattr(self, 'generated_data') or not self.generated_data:
                self.log_message("[AI 데이터 저장] 실패: 저장할 AI 데이터가 없습니다.")
                return

            # UI의 현재 내용을 self.generated_data에 업데이트
            self._update_generated_data_from_ui()

            project_name = self.project_name_var.get()
            identifier = self.identifier_var.get()
            json_path = os.path.join(config.OUTPUT_PATH, project_name, identifier, f"{identifier}_ai.json")
            os.makedirs(os.path.dirname(json_path), exist_ok=True)
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(self.generated_data, f, ensure_ascii=False, indent=4)
            self.log_message(f"[AI 데이터 저장] 성공: {json_path}")
            
        except Exception as e:
            self.log_message(f"[오류] AI 데이터 저장 실패: {e}")

    def _on_click_read_dialogue_data(self):
        try:
            project_name = self.project_name_var.get()
            identifier = self.identifier_var.get()
            csv_path = os.path.join(config.OUTPUT_PATH, project_name, identifier, "dialogue", f"{identifier}_dialogue.csv")
            if os.path.exists(csv_path):
                with open(csv_path, 'r', encoding='utf-8') as f:
                    csv_content = f.read()
                self._setup_and_show_csv_grid("dialogue", csv_content)
                self.script_selector_combo.set("dialogue")
                self.log_message(f"[대화 데이터 읽기] 성공: {csv_path}")
            else:
                self.log_message(f"[대화 데이터 읽기] 실패: 파일을 찾을 수 없습니다: {csv_path}")
        except Exception as e:
            self.log_message(f"[오류] 대화 데이터 읽기 실패: {e}")

    def _on_click_save_dialogue_data(self):
        try:
            project_name = self.project_name_var.get()
            identifier = self.identifier_var.get()
            output_dir = os.path.join(config.OUTPUT_PATH, project_name, identifier, "dialogue")
            os.makedirs(output_dir, exist_ok=True)
            filepath = os.path.join(output_dir, f"{identifier}_dialogue.csv")

            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                columns = self.csv_tree["columns"]
                writer.writerow(columns)
                for item_id in self.csv_tree.get_children():
                    writer.writerow(self.csv_tree.item(item_id, 'values'))
            self.log_message(f"[대화 데이터 저장] 성공: {filepath}")
        except Exception as e:
            self.log_message(f"[오류] 대화 데이터 저장 실패: {e}")

    def load_generated_data(self):
        try:
            project_name = self.project_name_var.get()
            identifier = self.identifier_var.get()
            json_path = os.path.join(config.OUTPUT_PATH, project_name, identifier, f"{identifier}_ai.json")
            if not os.path.exists(json_path):
                return False
            with open(json_path, 'r', encoding='utf-8') as f:
                self.generated_data = json.load(f)
            return True
        except Exception:
            return False

    def _on_click_generate_ai_data(self):
        try:
            dialogue_script_content = ""
            if self.script_textbox.winfo_ismapped():
                dialogue_script_content = self.script_textbox.get("1.0", tk.END).strip()

            params = {
                "native_lang": self.native_lang_var.get(),
                "learning_lang": self.learning_lang_var.get(),
                "topic": self.topic_var.get(),
                "custom_topic": self.custom_topic_var.get(),
                "level": self.level_var.get(),
                "count": int(self.count_var.get()),
                "dialogue_script": dialogue_script_content,
                "additional_requests": ""
            }
            model_name = self.ai_service_var.get()
            project_name = self.project_name_var.get()
            identifier = self.identifier_var.get()

            if not project_name or not identifier:
                self.log_message("[오류] 프로젝트명과 식별자를 먼저 설정해야 합니다.")
                return

            def target():
                try:
                    self.log_message(f"[{model_name}] 모델을 사용하여 AI 데이터 생성을 시작합니다...")
                    
                    result = api_services.generate_ai_data(params, model_name, project_name, identifier)
                    
                    self.generated_data = result['data']
                    
                    self.log_message("--- [AI 응답 데이터] ---")
                    self.log_message(json.dumps(self.generated_data, indent=2, ensure_ascii=False))
                    self.log_message("--------------------------")

                    self.log_message(f"[성공] AI 데이터 생성이 완료되었습니다.")
                    self.log_message(f"  - 프롬프트: {result['prompt_path']}")
                    self.log_message(f"  - 결과 JSON: {result['json_path']}")

                    # Save other script files
                    # saved_files = api_services.save_outputs_from_ai_data(self.generated_data, project_name, identifier)
                    # self.log_message(f"[성공] AI 데이터로부터 다음 스크립트 파일들을 저장했습니다:")
                    # for name, path in saved_files.items():
                    #     self.log_message(f"  - {name}: {path}")

                    # UI 업데이트는 메인 스레드에서 실행
                    self.after(0, self._render_selected_script)
                    self.after(0, self._update_audio_buttons_state)
                    if self.root and hasattr(self.root, 'pipeline_page'):
                        self.after(0, self.root.pipeline_page.activate)

                except Exception as e:
                    import traceback
                    error_message = f"[오류] AI 데이터 생성 중 예외가 발생했습니다: {e}\n{traceback.format_exc()}"
                    self.log_message(error_message)

            threading.Thread(target=target, daemon=True).start()

        except Exception as e:
            self.log_message(f"[오류] AI 데이터 생성 작업을 시작하지 못했습니다: {e}")

    def _render_selected_script(self):
        data = getattr(self, "generated_data", None)
        if not data:
            self.log_message("먼저 AI 데이터를 생성하거나 읽어오세요.")
            return
        
        selected = self.script_selector_combo.get()
        
        if selected in ["conversation", "dialogue"]:
            csv_data = data.get("dialogueCsv") or data.get("fullVideoScript", {}).get("dialogueCsv", "")
            if csv_data and csv_data.strip():
                self._setup_and_show_csv_grid(selected, csv_data)
            else:
                # 데이터가 없어도 컬럼만 정해진 크기로 표시
                self._setup_and_show_csv_grid(selected, "")
        else:
            script_map = {
                "title": "videoTitleSuggestions",
                "keywords": "videoKeywords",
                "intro": "introScript",
                "ending": "endingScript",
                "thumbnail": "thumbnailTextVersions"
            }
            content = ""
            data_key = script_map.get(selected)
            if data_key:
                if selected == "thumbnail":
                    versions = data.get(data_key, [])
                    lines = []
                    for i, v in enumerate(versions, 1):
                        text = v.get("text", "")
                        concept = v.get("imageConcept", "")
                        lines.append(f"[버전 {i}]\n{text}\n- 콘셉트: {concept}\n")
                    content = "\n".join(lines)
                elif isinstance(data.get(data_key), list):
                    content = "\n".join(data.get(data_key, []))
                else:
                    content = self._sentences_multiline(data.get(data_key, ""))
            self._show_text_content(content)

    def _show_text_content(self, content: str):
        self.csv_tree.grid_remove()
        self.csv_scroll_y.grid_remove()
        self.script_textbox.grid(row=0, column=0, sticky="nsew")
        self.script_textbox.delete("1.0", tk.END)
        self.script_textbox.insert("1.0", content)

    def _setup_and_show_csv_grid(self, script_type, csv_data):
        self.script_textbox.grid_remove()
        self.csv_tree.grid(row=0, column=0, sticky="nsew")
        self.csv_scroll_y.grid(row=0, column=1, sticky="ns")

        for item in self.csv_tree.get_children():
            self.csv_tree.delete(item)

        if script_type == "dialogue":
            columns = ("순번", "역할", "화자", "원어", "학습어")
        else: # conversation
            columns = ("순번", "원어", "학습어", "읽기")

        self.csv_tree["columns"] = columns
        for col in columns:
            self.csv_tree.heading(col, text=col)
            self.csv_tree.column(col, anchor="w")

        def _distribute_columns():
            width = self.csv_tree.winfo_width()
            if width <= 1: return 

            if script_type == "dialogue":
                fixed_width = 50 + 100 + 100 
                remaining_width = width - fixed_width
                stretch_col_width = remaining_width // 2
                self.csv_tree.column("순번", width=50, stretch=False)
                self.csv_tree.column("역할", width=100, stretch=False)
                self.csv_tree.column("화자", width=100, stretch=False)
                self.csv_tree.column("원어", width=stretch_col_width)
                self.csv_tree.column("학습어", width=stretch_col_width)
            else: # conversation
                fixed_width = 50
                remaining_width = width - fixed_width
                stretch_col_width = remaining_width // 3
                self.csv_tree.column("순번", width=50, stretch=False)
                self.csv_tree.column("원어", width=stretch_col_width)
                self.csv_tree.column("학습어", width=stretch_col_width)
                self.csv_tree.column("읽기", width=stretch_col_width)

        self.csv_tree.column("순번", width=50, stretch=False, anchor="center")
        
        reader = csv.reader(io.StringIO(csv_data))
        try:
            header = next(reader)
        except StopIteration:
            header = []
        
        for row in reader:
            self.csv_tree.insert("", tk.END, values=row)
            
        self.csv_tree.after(20, _distribute_columns)

    def _setup_csv_editing(self):
        def on_double_click(event):
            region = self.csv_tree.identify("region", event.x, event.y)
            if region != "cell": return

            column_id = self.csv_tree.identify_column(event.x)
            item_id = self.csv_tree.identify_row(event.y)
            column_index = int(column_id.replace('#', '')) - 1

            x, y, width, height = self.csv_tree.bbox(item_id, column_id)

            entry_editor = ctk.CTkEntry(self.csv_tree, width=width, height=height, fg_color="#333333", text_color="white")
            current_text = self.csv_tree.item(item_id, "values")[column_index]
            entry_editor.insert(0, current_text)
            entry_editor.focus_force()

            def on_edit_end(event=None):
                new_text = entry_editor.get()
                current_values = list(self.csv_tree.item(item_id, "values"))
                current_values[column_index] = new_text
                self.csv_tree.item(item_id, values=current_values)
                entry_editor.destroy()

            entry_editor.bind("<Return>", on_edit_end)
            entry_editor.bind("<FocusOut>", on_edit_end)
            entry_editor.place(x=x, y=y)

        self.csv_tree.bind("<Double-1>", on_double_click)

    def _sentences_multiline(self, text: str) -> str:
        if not text: return ""
        parts = [p.strip() for p in re.split(r"(?<=[\.!\?。？！])\s+", text.strip()) if p.strip()]
        return "\n".join(parts)

    def _update_audio_buttons_state(self):
        try:
            has_text = bool(self.script_textbox.winfo_ismapped() and self.script_textbox.get("1.0", tk.END).strip())
            has_rows = bool(self.csv_tree.winfo_ismapped() and len(self.csv_tree.get_children()) > 0)
            has_content = has_text or has_rows
            new_state = "normal" if has_content else "disabled"
        except Exception: pass

    def _on_click_audio_generate(self):
            pass

    def _on_click_thumb_generate(self):
        pass

    def _on_click_audio_play(self):
        pass

    def _setup_csv_context_menu(self):
        pass


