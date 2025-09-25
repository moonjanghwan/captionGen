import customtkinter as ctk
from src import config
import tkinter as tk
from tkinter import ttk
import os
import json
import threading
import csv
import io
import re
from tkinter import messagebox
from src.ui.ui_utils import create_labeled_widget
from src.pipeline.ffmpeg.pipeline_manager import PipelineManager

class PipelineTabView(ctk.CTkFrame):
    def __init__(self, parent, root=None):
        super().__init__(parent, fg_color="transparent")
        self.root = root
        self.pipeline_manager = PipelineManager(root=root, log_callback=self.log_message)
        self.generated_data = None
        
        # 데이터 생성 탭과 동일한 그리드 스타일 설정
        self._setup_treeview_style()
        
        self._create_widgets()
        self._setup_layout()
        # self._bind_events() # Removed to enable native copy-paste
    
    def _setup_treeview_style(self):
        """데이터 생성 탭과 동일한 그리드 스타일을 설정합니다."""
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="black", foreground="white", fieldbackground="black", borderwidth=0)
        style.map('Treeview', background=[('selected', '#22559B')])
        style.configure("Treeview.Heading", background="#333333", foreground="white", relief="flat")
        style.map("Treeview.Heading", background=[('active', '#4A4A4A')])
        
    def _create_widgets(self):
        # 1섹션: 스크립트 선택 및 데이터 관리
        self.script_section = ctk.CTkFrame(self)
        
        # 스크립트 선택
        self.script_var = tk.StringVar(value="conversation")
        self.script_selector_combo = ctk.CTkComboBox(
            self.script_section,
            values=["conversation", "dialogue", "title", "keywords", "intro", "ending", "thumbnail"],
            variable=self.script_var,
            width=200,
            command=lambda _: self._render_selected_script()
        )
        
        # 데이터 관리 버튼들
        self.read_ai_data_btn = ctk.CTkButton(
            self.script_section,
            text="AI 데이터 읽기",
            command=self._read_ai_data,
            width=120,
            height=30
        )
        
        self.save_ai_data_btn = ctk.CTkButton(
            self.script_section,
            text="AI 데이터 저장",
            command=self._save_ai_data,
            width=120,
            height=30
        )
        
        self.read_dialogue_data_btn = ctk.CTkButton(
            self.script_section,
            text="대화 데이터 읽기",
            command=self._read_dialogue_data,
            width=120,
            height=30
        )
        
        self.save_dialogue_data_btn = ctk.CTkButton(
            self.script_section,
            text="대화 데이터 저장",
            command=self._save_dialogue_data,
            width=120,
            height=30
        )
        
        # 2섹션: 데이터 편집창 (데이터 생성 탭과 동일한 배경색)
        self.edit_section = ctk.CTkFrame(self, fg_color="black")
        
        # CSV 트리뷰 (데이터 생성 탭과 동일한 스타일 적용)
        self.csv_tree = ttk.Treeview(self.edit_section, show="headings", style="Treeview")
        self.csv_scroll_y = ttk.Scrollbar(self.edit_section, orient="vertical", command=self.csv_tree.yview)
        self.csv_tree.configure(yscrollcommand=self.csv_scroll_y.set)
        
        # 텍스트 박스
        self.script_textbox = ctk.CTkTextbox(self.edit_section)
        
        # 3섹션: 메시지 출력창
        self.message_section = ctk.CTkFrame(self)
        self.log_textbox = tk.Text(self.message_section, height=20, bg="black", fg="white", insertbackground="white", relief="flat", borderwidth=0)
        
        # 4섹션: 컨트롤 버튼 섹션
        self.control_section = ctk.CTkFrame(self)
        
        # 컨트롤 버튼들
        self.create_thumbnail_btn = ctk.CTkButton(
            self.control_section,
            text="썸네일 생성",
            command=self._create_thumbnail,
            width=120,
            height=40
        )
        
        self.create_manifest_btn = ctk.CTkButton(
            self.control_section,
            text="Manifest 생성",
            command=self._create_manifest,
            width=120,
            height=40
        )
        
        self.create_audio_btn = ctk.CTkButton(
            self.control_section,
            text="오디오 생성",
            command=self._create_audio,
            width=120,
            height=40
        )
        
        self.create_subtitle_btn = ctk.CTkButton(
            self.control_section,
            text="자막 이미지 생성",
            command=self._create_subtitle,
            width=120,
            height=40
        )
        
        self.render_video_btn = ctk.CTkButton(
            self.control_section,
            text="비디오 렌더링",
            command=self._render_video,
            width=120,
            height=40
        )
        
        self.create_final_btn = ctk.CTkButton(
            self.control_section,
            text="최종 생성",
            command=self._create_final_video,
            width=120,
            height=40
        )

        self.auto_generate_btn = ctk.CTkButton(
            self.control_section,
            text="자동 생성",
            command=self._run_auto_generation,
            width=120,
            height=40,
            fg_color="#2D6A4F",
            hover_color="#40916C"
        )
        
        self.copy_log_btn = ctk.CTkButton(
            self.control_section,
            text="메시지 복사",
            command=self._copy_log_to_clipboard,
            width=120,
            height=40
        )

        self.exit_btn = ctk.CTkButton(
            self.control_section,
            text="프로그램 종료",
            command=self._exit_app,
            width=120,
            height=40,
            fg_color="red",
            hover_color="darkred"
        )
        
    def _setup_layout(self):
        # 1섹션: 스크립트 선택 및 데이터 관리
        self.script_section.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        # 스크립트 드롭다운 다음에 버튼들이 바로 오도록 컬럼 설정
        self.script_section.grid_columnconfigure(1, weight=0)  # 스크립트 드롭다운은 고정 크기
        self.script_section.grid_columnconfigure(2, weight=0)  # 버튼들도 고정 크기
        
        # 스크립트 선택
        ctk.CTkLabel(self.script_section, text="스크립트:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.script_selector_combo.grid(row=0, column=1, padx=10, pady=10, sticky="w")
        
        # 데이터 관리 버튼들을 스크립트 드롭다운 바로 다음에 배치
        self.read_ai_data_btn.grid(row=0, column=2, padx=5, pady=10)
        self.save_ai_data_btn.grid(row=0, column=3, padx=5, pady=10)
        self.read_dialogue_data_btn.grid(row=0, column=4, padx=5, pady=10)
        self.save_dialogue_data_btn.grid(row=0, column=5, padx=5, pady=10)
        
        # 2섹션: 데이터 편집창 (전체 창 사용)
        self.edit_section.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        self.edit_section.grid_rowconfigure(0, weight=1)
        self.edit_section.grid_columnconfigure(0, weight=1)
        
        # 3섹션: 메시지 출력창
        self.message_section.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        self.message_section.grid_rowconfigure(0, weight=1)
        self.message_section.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(self.message_section, text="메시지 출력창:").grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        self.log_textbox.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        
        # 4섹션: 컨트롤 버튼 섹션
        self.control_section.grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        self.control_section.grid_columnconfigure(0, weight=1)

        left_button_frame = ctk.CTkFrame(self.control_section, fg_color="transparent")
        left_button_frame.pack(side="left", padx=(0, 10))

        right_button_frame = ctk.CTkFrame(self.control_section, fg_color="transparent")
        right_button_frame.pack(side="right", padx=(10, 0))

        # 제작 관련 버튼들을 왼쪽에 배치
        self.create_manifest_btn.pack(side="left", padx=5, pady=10)
        self.create_thumbnail_btn.pack(side="left", padx=5, pady=10)
        self.create_audio_btn.pack(side="left", padx=5, pady=10)
        self.create_subtitle_btn.pack(side="left", padx=5, pady=10)
        self.render_video_btn.pack(side="left", padx=5, pady=10)
        self.create_final_btn.pack(side="left", padx=5, pady=10)
        self.auto_generate_btn.pack(side="left", padx=5, pady=10)

        # 유틸리티 버튼들을 오른쪽에 배치
        self.copy_log_btn.pack(side="left", padx=5, pady=10)
        self.exit_btn.pack(side="left", padx=5, pady=10)
        
        
        # 그리드 가중치 설정 - 편집창이 가장 큰 공간 차지
        self.grid_rowconfigure(1, weight=1)  # 편집창
        self.grid_rowconfigure(2, weight=0)  # 메시지창 (고정 크기)
        self.grid_rowconfigure(3, weight=0)  # 컨트롤창 (고정 크기)
        self.grid_columnconfigure(0, weight=1)
        

        
    def log_message(self, message):
        """로그 메시지를 추가합니다."""
        if hasattr(self, 'log_textbox'):
            self.log_textbox.configure(state="normal")
            self.log_textbox.insert(tk.END, f"{message}\n")
            self.log_textbox.see(tk.END)
        else:
            print(message)
    
    def _get_ui_data(self):
        """UI에서 현재 데이터를 가져옵니다."""
        ui_data = {}
        
        # 데이터 탭에서 기본 정보 가져오기
        if self.root and hasattr(self.root, 'data_page'):
            data_page = self.root.data_page
            ui_data.update({
                'project_name': data_page.project_name_var.get(),
                'identifier': data_page.identifier_var.get(),
                'native_lang': data_page.native_lang_var.get(),
                'learning_lang': data_page.learning_lang_var.get(),
                'learner_level': data_page.level_var.get(),
                'topic': data_page.topic_var.get(),
                'count': data_page.count_var.get(),
                'ai_service': data_page.ai_service_var.get()
            })
            
            # 언어 코드 가져오기
            native_lang_code, learning_lang_code = data_page.get_selected_language_codes()
            ui_data.update({
                'native_lang_code': native_lang_code,
                'learning_lang_code': learning_lang_code
            })
        
        # 현재 스크립트 타입 가져오기 (드롭다운 박스에서)
        # PipelineTabView의 스크립트 선택기를 우선 사용
        ui_data['script_type'] = self.script_var.get()
        
        # DataTabView에도 스크립트 선택기가 있다면 그것도 확인
        if self.root and hasattr(self.root, 'data_page') and hasattr(self.root.data_page, 'script_selector_combo'):
            data_script_type = self.root.data_page.script_selector_combo.get()
            # DataTabView의 선택이 더 구체적이면 그것을 사용
            if data_script_type and data_script_type != "conversation":
                ui_data['script_type'] = data_script_type
        
        # 현재 스크립트 데이터 가져오기
        script_data = self._get_current_script_data_from_ui()
        if script_data:
            ui_data['script_data'] = script_data
        
        # 스크립트별 설정 가져오기
        script_specific_settings = {}
        if hasattr(self, 'generated_data') and self.generated_data:
            if 'fullVideoScript' in self.generated_data:
                script_specific_settings = self.generated_data['fullVideoScript']
                if '비율' in script_specific_settings:
                    ui_data['aspect_ratio'] = script_specific_settings.get('비율')

        return ui_data

    def _get_script_data_for_type(self, script_type: str):
        """UI 상태와 독립적으로, self.generated_data에서 특정 타입의 스크립트 데이터를 가져옵니다."""
        if not hasattr(self, 'generated_data') or not self.generated_data:
            self.log_message(f"[{script_type} 데이터 조회] AI 생성 데이터(generated_data)가 없습니다.")
            return None

        if script_type in ["conversation", "dialogue"]:
            csv_data = self.generated_data.get("dialogueCsv") or self.generated_data.get("fullVideoScript", {}).get("dialogueCsv", "")
            if csv_data and csv_data.strip():
                try:
                    # Skip header row if it exists
                    if csv_data.strip().startswith("순번,"):
                        csv_data = '\n'.join(csv_data.split('\n')[1:])
                    
                    reader = csv.reader(io.StringIO(csv_data))
                    rows = list(reader)
                    if rows:
                        self.log_message(f"[{script_type} 데이터 조회] generated_data에서 {len(rows)}행의 CSV 데이터를 찾았습니다.")
                        return self._parse_csv_to_scenes(rows, script_type)
                except Exception as e:
                    self.log_message(f"[{script_type} 데이터 조회] generated_data에서 CSV 파싱 실패: {e}")
            self.log_message(f"[{script_type} 데이터 조회] generated_data에서 CSV 데이터를 찾지 못했습니다.")
            return None
        else:
            if script_type == "thumbnail":
                versions = self.generated_data.get('thumbnailTextVersions', [])
                if versions:
                    self.log_message(f"[{script_type} 데이터 조회] generated_data에서 {len(versions)}개의 썸네일 버전을 찾았습니다.")
                    # Each version's 'text' field contains the lines for one thumbnail
                    scenes = [{'text': v.get('text','')} for v in versions if v.get('text')]
                    return scenes
            else:
                script_map = {
                    "title": "videoTitleSuggestions",
                    "keywords": "videoKeywords",
                    "intro": "introScript",
                    "ending": "endingScript",
                }
                data_key = script_map.get(script_type)
                if not data_key:
                    self.log_message(f"[{script_type} 데이터 조회] 유효하지 않은 스크립트 타입입니다.")
                    return None
                
                content = self.generated_data.get(data_key, "")
                if isinstance(content, list):
                    content = "\n".join(content)

                if content and content.strip():
                    lines = [line.strip() for line in content.splitlines() if line.strip()]
                    if lines:
                        self.log_message(f"[{script_type} 데이터 조회] generated_data에서 {len(lines)}행의 텍스트 데이터를 찾았습니다.")
                        scenes = [{'text': line} for line in lines]
                        return scenes
        
        self.log_message(f"[{script_type} 데이터 조회] generated_data에서 해당 스크립트 데이터를 찾지 못했습니다.")
        return None

    def _get_current_script_data_from_ui(self):
        """현재 UI에 표시된 스크립트 데이터를 가져옵니다. (수동 단계 실행용)"""
        selected_script_type = self.script_var.get()

        if selected_script_type in ["conversation", "dialogue"]:
            if hasattr(self, 'csv_tree') and self.csv_tree.winfo_ismapped():
                try:
                    rows = []
                    for item_id in self.csv_tree.get_children():
                        values = self.csv_tree.item(item_id, 'values')
                        if values:
                            rows.append(list(values))
                    if rows:
                        self.log_message(f"[스크립트 데이터] CSV 트리에서 {len(rows)}행을 읽었습니다.")
                        return self._parse_csv_to_scenes(rows, selected_script_type)
                except Exception as e:
                    self.log_message(f"[오류] CSV 트리에서 데이터 읽기 실패: {e}")
        else: # Textbox-based scripts
            if hasattr(self, 'script_textbox') and self.script_textbox.winfo_ismapped():
                content = self.script_textbox.get("1.0", tk.END).strip()
                if content:
                    lines = [line.strip() for line in content.splitlines() if line.strip()]
                    if lines:
                        self.log_message(f"[스크립트 데이터] 텍스트 박스에서 {len(lines)}행을 읽었습니다.")
                        return [{'text': line} for line in lines]

        self.log_message("[스크립트 데이터] UI에서 사용 가능한 스크립트 데이터를 찾을 수 없습니다.")
        return None
    
    def _parse_csv_to_scenes(self, rows, script_type: str):
        """CSV 행을 장면 데이터로 변환합니다."""
        if not rows:
            return []
        
        scenes = []
        
        if script_type == "dialogue":
            # 대화 스크립트: 순번, 역할, 화자, 원어, 학습어
            for row in rows:
                if len(row) >= 5:
                    scenes.append({
                        'id': f"dialogue_{row[0]}",
                        'sequence': int(row[0]) if row[0].isdigit() else len(scenes) + 1,
                        'role': row[1],
                        'speaker': row[2],
                        'native_script': row[3],
                        'learning_script': row[4]
                    })
        else:
            # 회화 스크립트: 순번, 원어, 학습어, 읽기
            for row in rows:
                if not row or row[0] == '순번': continue
                if len(row) >= 4:
                    scenes.append({
                        'id': f"conversation_{row[0]}",
                        'type': 'conversation',
                        'sequence': int(row[0]) if row[0].isdigit() else len(scenes) + 1,
                        'native_script': row[1],
                        'learning_script': row[2],
                        'reading_script': row[3]
                    })
        
        return scenes

    def _run_pipeline_step(self, step_func, step_name):
        def target():
            try:
                print(f"🚀 [UI Pipeline] {step_name} 작업 시작")
                self.log_message(f"[{step_name}] 작업을 시작합니다...")
                ui_data = self._get_ui_data()
                print(f"🔍 [UI Pipeline] ui_data: {list(ui_data.keys()) if ui_data else 'None'}")

                # [리팩토링] 파이프라인 실행 직전, 이미지 탭의 최신 설정을 가져와 주입
                if self.root and hasattr(self.root, 'image_page'):
                    print("🔍 [UI Pipeline] 이미지 탭 설정 가져오기 시작...")
                    image_page = self.root.image_page
                    image_page._save_ui_to_memory() # UI의 현재 상태를 내부 메모리로 업데이트
                    ui_data['script_settings'] = image_page.script_settings
                    print(f"✅ [UI Pipeline] 이미지 탭 설정 가져오기 완료: {list(image_page.script_settings.keys())}")
                    self.log_message("[INFO] 이미지 탭의 최신 설정값을 파이프라인에 적용합니다.")
                    
                    # 배경 설정 값 바로 로그 출력
                    print("🔍 [UI Pipeline] === 배경 설정 값 확인 ===")
                    for script_type, settings in image_page.script_settings.items():
                        print(f"🔍 [UI Pipeline] {script_type} 스크립트 설정:")
                        if 'main_background' in settings:
                            bg_settings = settings['main_background']
                            print(f"  - main_background: {bg_settings}")
                            print(f"  - type: {bg_settings.get('type', 'NOT_FOUND')}")
                            print(f"  - value: {bg_settings.get('value', 'NOT_FOUND')}")
                        else:
                            print(f"  - main_background: NOT_FOUND")
                        print(f"  - 전체 설정 키들: {list(settings.keys())}")
                    print("🔍 [UI Pipeline] === 배경 설정 값 확인 완료 ===")
                else:
                    print("❌ [UI Pipeline] 이미지 탭을 찾을 수 없습니다.")

                print(f"🔄 [UI Pipeline] {step_name} 함수 호출 시작...")
                result = step_func(ui_data)
                print(f"✅ [UI Pipeline] {step_name} 함수 호출 완료: {result}")
                if result.get('success'):
                    self.log_message(f"[{step_name}] 작업 성공!")
                    if 'generated_files' in result:
                        for file_type, path in result.get('generated_files', {}).items():
                            self.log_message(f"  - 생성된 파일 ({file_type}): {path}")
                            if file_type == 'manifest' and os.path.exists(path):
                                try:
                                    with open(path, 'r', encoding='utf-8') as f:
                                        content = json.load(f)
                                    pretty_content = json.dumps(content, indent=2, ensure_ascii=False)
                                    self.log_message(f"--- Manifest Content ---\n{pretty_content}\n------------------------")
                                except Exception as e:
                                    self.log_message(f"  - 매니페스트 파일 내용을 읽는 중 오류: {e}")
                    if 'generated_videos' in result:
                        for file_type, path in result.get('generated_videos', {}).items():
                            self.log_message(f"  - 생성된 비디오 ({file_type}): {path}")
                else:
                    errors = result.get('errors', result.get('message', '알 수 없는 오류'))
                    self.log_message(f"[{step_name}] 작업 실패: {errors}")
            except Exception as e:
                import traceback
                self.log_message(f"[{step_name}] 작업 중 예외 발생: {e}\n{traceback.format_exc()}")

        threading.Thread(target=target, daemon=True).start()

    def _create_manifest(self):
        """모든 스크립트 타입의 데이터를 취합하여 마스터 Manifest 생성을 요청합니다."""
        self.log_message("[Manifest 생성] 모든 스크립트 데이터 취합 시작...")
        
        def target():
            try:
                # Get common UI data (project name, etc.)
                ui_data = self._get_ui_data()
                
                # Overwrite script_type and script_data for this special case
                ui_data['script_type'] = 'all' 
                
                all_script_data = {}
                all_script_types = ["intro", "conversation", "ending", "thumbnail", "title", "keywords", "dialogue"]
                for script_type in all_script_types:
                    data = self._get_script_data_for_type(script_type)
                    if data:
                        all_script_data[script_type] = data
                
                if not all_script_data:
                    self.log_message("[Manifest 생성] 취합할 데이터가 없습니다. AI 데이터 읽기를 먼저 실행하세요.")
                    return
                    
                ui_data['script_data'] = all_script_data
                
                # Get image settings
                if self.root and hasattr(self.root, 'image_page'):
                    image_page = self.root.image_page
                    image_page._save_ui_to_memory()
                    ui_data['script_settings'] = image_page.script_settings

                # Call the pipeline manager
                result = self.pipeline_manager.run_manifest_creation(ui_data)
                
                # Log result
                if result.get('success'):
                    self.log_message("[Manifest 생성] 작업 성공!")
                    if 'generated_files' in result:
                        for file_type, path in result.get('generated_files', {}).items():
                            self.log_message(f"  - 생성된 파일 ({file_type}): {path}")
                else:
                    self.log_message(f"[Manifest 생성] 작업 실패: {result.get('errors')}")

            except Exception as e:
                import traceback
                self.log_message(f"--- 🚨 Manifest 생성 중 심각한 오류 발생: {e} ---")
                self.log_message(traceback.format_exc())

        threading.Thread(target=target, daemon=True).start()

    def _create_audio(self):
        self._run_pipeline_step(self.pipeline_manager.run_audio_generation, "오디오 생성")

    def _create_subtitle(self):
        print("🚀 [UI] 자막 이미지 생성 버튼 클릭됨")
        self._run_pipeline_step(self.pipeline_manager.run_subtitle_creation, "자막 이미지 생성")

    def _render_video(self):
        self._run_pipeline_step(self.pipeline_manager.run_timing_based_video_rendering, "비디오 렌더링")

    def _create_final_video(self):
        def target():
            step_name = "최종 비디오 생성"
            try:
                self.log_message(f"[{step_name}] 작업을 시작합니다...")
                ui_data = self._get_ui_data()
                project_name = ui_data.get('project_name')
                identifier = ui_data.get('identifier')
        
                if not project_name or not identifier:
                    self.log_message(f"[{step_name}] 작업 실패: 프로젝트명과 식별자가 필요합니다.")
                    return
        
                output_dir = f"output/{project_name}/{identifier}"
                smooth = ui_data.get('smooth_transition', True)
                
                final_path = self.pipeline_manager.create_final_merged_video(project_name, identifier, output_dir, smooth)
                
                if final_path:
                    self.log_message(f"[{step_name}] 작업 성공! 최종 비디오: {final_path}")
                else:
                    self.log_message(f"[{step_name}] 작업 실패.")
            except Exception as e:
                import traceback
                self.log_message(f"[{step_name}] 작업 중 예외 발생: {e}\n{traceback.format_exc()}")
                
        threading.Thread(target=target, daemon=True).start()

    def _read_ai_data(self):
        """AI 데이터 읽기 기능 - 기존 activate 메서드의 로직 활용"""
        try:
            if self.root and hasattr(self.root, 'data_page'):
                project_name = self.root.data_page.project_name_var.get()
                identifier = self.root.data_page.identifier_var.get()
                
                if project_name and identifier:
                    json_path = os.path.join(config.OUTPUT_PATH, project_name, identifier, f"{identifier}_ai.json")
                    if os.path.exists(json_path):
                        with open(json_path, 'r', encoding='utf-8') as f:
                            self.generated_data = json.load(f)
                        self.log_message(f"[AI 데이터 읽기] 성공: {json_path}")
                        self._render_selected_script()
                    else:
                        self.log_message(f"[AI 데이터 읽기] 실패: 파일을 찾을 수 없습니다: {json_path}")
                else:
                    self.log_message("[AI 데이터 읽기] 실패: 프로젝트명과 식별자를 먼저 설정하세요.")
        except Exception as e:
            self.log_message(f"[오류] AI 데이터 읽기 실패: {e}")
    
    def _save_ai_data(self):
        """AI 데이터 저장 기능 - 기존 _update_generated_data_from_ui 로직 활용"""
        try:
            if not hasattr(self, 'generated_data') or not self.generated_data:
                self.log_message("[AI 데이터 저장] 저장할 데이터가 없습니다.")
                return
            
            # UI에서 데이터 업데이트
            self._update_generated_data_from_ui()
            
            if self.root and hasattr(self.root, 'data_page'):
                project_name = self.root.data_page.project_name_var.get()
                identifier = self.root.data_page.identifier_var.get()
                
                if project_name and identifier:
                    json_path = os.path.join(config.OUTPUT_PATH, project_name, identifier, f"{identifier}_ai.json")
                    os.makedirs(os.path.dirname(json_path), exist_ok=True)
                    
                    with open(json_path, 'w', encoding='utf-8') as f:
                        json.dump(self.generated_data, f, indent=2, ensure_ascii=False)
                    
                    self.log_message(f"[AI 데이터 저장] 성공: {json_path}")
                else:
                    self.log_message("[AI 데이터 저장] 실패: 프로젝트명과 식별자를 먼저 설정하세요.")
        except Exception as e:
            self.log_message(f"[오류] AI 데이터 저장 실패: {e}")
    
    def _read_dialogue_data(self):
        """대화 데이터 읽기 기능 - 기존 _get_current_script_data_from_ui 로직 활용"""
        try:
            script_data = self._get_current_script_data_from_ui()
            if script_data:
                self.log_message(f"[대화 데이터 읽기] 성공: {len(script_data)}개 장면을 읽었습니다.")
                self._render_selected_script()
            else:
                self.log_message("[대화 데이터 읽기] 읽을 수 있는 대화 데이터가 없습니다.")
        except Exception as e:
            self.log_message(f"[오류] 대화 데이터 읽기 실패: {e}")
    
    def _save_dialogue_data(self):
        """대화 데이터 저장 기능 - 기존 _update_generated_data_from_ui 로직 활용"""
        try:
            self._update_generated_data_from_ui()
            self.log_message("[대화 데이터 저장] 현재 편집창의 데이터를 저장했습니다.")
        except Exception as e:
            self.log_message(f"[오류] 대화 데이터 저장 실패: {e}")
    
    def _create_thumbnail(self):
        """썸네일 생성 파이프라인을 실행합니다."""
        self.log_message("[썸네일 생성] 작업을 시작합니다...")
        
        def target():
            try:
                # 썸네일 생성에 필요한 데이터만 선택적으로 구성
                ui_data = self._get_ui_data()
                ui_data['script_type'] = 'thumbnail'
                ui_data['script_data'] = self._get_script_data_for_type('thumbnail')

                if not ui_data['script_data']:
                    self.log_message("[썸네일 생성] 썸네일 스크립트 데이터가 없습니다. AI 데이터 읽기를 먼저 실행하세요.")
                    return

                # 이미지 탭 설정 가져오기
                if self.root and hasattr(self.root, 'image_page'):
                    image_page = self.root.image_page
                    image_page._save_ui_to_memory()
                    ui_data['script_settings'] = image_page.script_settings
                
                # Manifest 생성부터 시작
                self.log_message("  - (thumbnail) Manifest 생성 중...")
                manifest_result = self.pipeline_manager.run_manifest_creation(ui_data)
                if not manifest_result.get('success'):
                    self.log_message(f"--- ❌ (thumbnail) Manifest 생성 실패: {manifest_result.get('errors')}. ---")
                    return

                self.log_message("  - (thumbnail) 자막 이미지 생성 중...")
                subtitle_result = self.pipeline_manager.run_subtitle_creation(ui_data)
                if not subtitle_result.get('success'):
                    self.log_message(f"--- ❌ (thumbnail) 자막 이미지 생성 실패: {subtitle_result.get('errors')}. ---")
                    return
                
                self.log_message("--- ✅ 썸네일 생성 완료 ---")

            except Exception as e:
                import traceback
                self.log_message(f"--- 🚨 썸네일 생성 중 심각한 오류 발생: {e} ---")
                self.log_message(traceback.format_exc())

        threading.Thread(target=target, daemon=True).start()

    def _exit_app(self):
        if self.root:
            self.root._on_closing()

    def activate(self):
        """탭이 활성화될 때 호출됩니다. _ai.json을 읽고 UI를 업데이트합니다."""
        try:
            # 데이터 동기화: data_page에 데이터가 있으면 가져온다.
            if self.root and hasattr(self.root, 'data_page') and hasattr(self.root.data_page, 'generated_data'):
                self.generated_data = self.root.data_page.generated_data
                if self.generated_data:
                    self.log_message("[데이터 동기화] 데이터 생성 탭의 정보를 가져왔습니다.")
                else:
                    self.generated_data = None
                # 파이프라인 탭을 선택하게 되면 선택된 스크립트를 편집 창에 디스플레이
                self._render_selected_script()
                return

            # data_page에 데이터가 없으면 파일에서 직접 로드 시도
            if self.root and hasattr(self.root, 'data_page'):
                project_name = self.root.data_page.project_name_var.get()
                identifier = self.root.data_page.identifier_var.get()

                if project_name and identifier:
                    json_path = os.path.join(config.OUTPUT_PATH, project_name, identifier, f"{identifier}_ai.json")
                    if os.path.exists(json_path):
                        with open(json_path, 'r', encoding='utf-8') as f:
                            self.generated_data = json.load(f)
                        self.log_message(f"[자동 로드] {json_path}의 데이터를 읽었습니다.")
                    else:
                        self.generated_data = None
                        self.log_message(f"[자동 로드] AI 데이터 파일을 찾을 수 없습니다: {json_path}")
                else:
                    self.generated_data = None
                    self.log_message("[자동 로드] 프로젝트명과 식별자를 먼저 설정하세요.")
            
            # 파이프라인 탭을 선택하게 되면 선택된 스크립트를 편집 창에 디스플레이
            self._render_selected_script()
        except Exception as e:
            self.log_message(f"[오류] 파이프라인 탭 활성화 중 오류: {e}")
            # 오류가 발생해도 기본 스크립트 표시
            self._render_selected_script()

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
                self.log_message("[저장] 썸네일 스크립트는 현재 UI에서 JSON으로 역변환하는 기능을 지원하지 않습니다.")
                pass
            elif isinstance(self.generated_data.get(data_key), list):
                self.generated_data[data_key] = content.splitlines()
            else:
                self.generated_data[data_key] = content
            
            self.log_message(f"[{selected}] 스크립트가 텍스트 박스로부터 업데이트되었습니다.")

    def _render_selected_script(self):
        """데이터 생성 탭과 동일한 방식으로 스크립트를 표시합니다."""
        data = getattr(self, "generated_data", None)
        selected = self.script_selector_combo.get()
        
        self.log_message(f"[스크립트 선택] '{selected}' 스크립트를 표시합니다.")
        
        if not data:
            self.log_message("먼저 AI 데이터를 생성하거나 읽어오세요.")
            # 데이터가 없어도 스크립트 타입에 따라 적절한 화면 표시
            if selected in ["conversation", "dialogue"]:
                # 데이터가 없을시에는 컬럼만 표시
                self._setup_and_show_csv_grid(selected, "")
            else:
                self._show_text_content("")
            return
        
        # 데이터 생성 탭과 동일한 방식으로 데이터를 읽어서 디스플레이
        if selected in ["conversation", "dialogue"]:
            csv_data = data.get("dialogueCsv") or data.get("fullVideoScript", {}).get("dialogueCsv", "")
            # 데이터가 있든 없든 항상 CSV 그리드 표시 (데이터 생성 탭과 동일)
            self._setup_and_show_csv_grid(selected, csv_data)
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
        # CSV 트리뷰 숨기기
        self.csv_tree.grid_remove()
        self.csv_scroll_y.grid_remove()
        
        # 텍스트박스 표시
        self.script_textbox.grid(row=0, column=0, sticky="nsew")
        self.script_textbox.delete("1.0", tk.END)
        self.script_textbox.insert("1.0", content)

    def _setup_and_show_csv_grid(self, script_type, csv_data):
        # 텍스트박스 숨기기
        self.script_textbox.grid_remove()
        
        # CSV 트리뷰 표시
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

    def _sentences_multiline(self, text: str) -> str:
        if not text: return ""
        parts = [p.strip() for p in re.split(r"(?<=[\.!\?。？！])\s+", text.strip()) if p.strip()]
        return "\n".join(parts)

    def _copy_log_to_clipboard(self):
        try:
            all_text = self.log_textbox.get("1.0", tk.END)
            self.clipboard_clear()
            self.clipboard_append(all_text)
            self.log_message("[INFO] 메시지 내용이 클립보드에 복사되었습니다.")
        except Exception as e:
            self.log_message(f"[ERROR] 메시지 복사 중 오류가 발생했습니다: {e}")

    def _run_auto_generation(self):
        """자동 생성 파이프라인을 별도 스레드에서 시작합니다."""
        threading.Thread(target=self._auto_generation_thread, daemon=True).start()

    def _auto_generation_thread(self):
        """자동 생성 파이프라인의 전체 시퀀스를 순차적으로 실행합니다."""
        try:
            self.log_message("--- 🚀 자동 생성 파이프라인 시작 ---")
            
            # Get base project/id info from the data_page, which is the source of truth
            if not (self.root and hasattr(self.root, 'data_page')):
                self.log_message("--- ❌ 데이터 탭을 찾을 수 없습니다. 자동 생성을 중단합니다. ---")
                return

            project_name = self.root.data_page.project_name_var.get()
            identifier = self.root.data_page.identifier_var.get()

            if not project_name or not identifier:
                self.log_message("--- ❌ 프로젝트명과 식별자가 필요합니다. 자동 생성을 중단합니다. ---")
                return

            # Get the full script settings from the image tab once
            if self.root and hasattr(self.root, 'image_page'):
                image_page = self.root.image_page
                image_page._save_ui_to_memory()
                script_settings = image_page.script_settings
            else:
                script_settings = {}
                self.log_message("--- ⚠️ 이미지 탭 설정을 찾을 수 없습니다. ---")

            # --- Run generation for each script type ---
            for script_type in ["intro", "conversation", "ending"]:
                self.log_message(f"--- ⏳ ({script_type}) 처리 시작 ---")
                
                script_data = self._get_script_data_for_type(script_type)
                if not script_data:
                    self.log_message(f"--- ⚠️ ({script_type}) 스크립트 데이터를 찾을 수 없어 건너뜁니다. ---")
                    continue

                # Prepare ui_data for this specific step
                step_ui_data = self._get_ui_data()
                step_ui_data['script_type'] = script_type
                step_ui_data['script_data'] = script_data # Inject the correct data
                step_ui_data['script_settings'] = script_settings
                
                self.log_message(f"  - ({script_type}) Manifest 생성 중...")
                result = self.pipeline_manager.run_manifest_creation(step_ui_data)
                if not result.get('success'):
                    self.log_message(f"--- ❌ ({script_type}) Manifest 생성 실패: {result.get('errors')}. 자동 생성을 중단합니다. ---")
                    return

                self.log_message(f"  - ({script_type}) 오디오 생성 중...")
                result = self.pipeline_manager.run_audio_generation(step_ui_data)
                if not result.get('success'):
                    self.log_message(f"--- ❌ ({script_type}) 오디오 생성 실패: {result.get('errors')}. 자동 생성을 중단합니다. ---")
                    return

                self.log_message(f"  - ({script_type}) 자막 이미지 생성 중...")
                result = self.pipeline_manager.run_subtitle_creation(step_ui_data)
                if not result.get('success'):
                    self.log_message(f"--- ❌ ({script_type}) 자막 이미지 생성 실패: {result.get('errors')}. 자동 생성을 중단합니다. ---")
                    return

                self.log_message(f"  - ({script_type}) 비디오 렌더링 중...")
                result = self.pipeline_manager.run_timing_based_video_rendering(step_ui_data)
                if not result.get('success'):
                    self.log_message(f"--- ❌ ({script_type}) 비디오 렌더링 실패: {result.get('errors', result.get('message'))}. 자동 생성을 중단합니다. ---")
                    return
                
                self.log_message(f"--- ✅ ({script_type}) 처리 완료 ---")

            self.log_message("--- ⏳ 최종 비디오 병합 시작 ---")
            output_dir = f"output/{project_name}/{identifier}"
            final_path = self.pipeline_manager.create_final_merged_video(project_name, identifier, output_dir, True)
            if not final_path:
                 self.log_message(f"--- ❌ 최종 비디오 병합 실패. ---")
                 return
            
            self.log_message(f"--- 🎉 모든 자동 생성 작업 완료! 최종 파일: {final_path} ---")

        except Exception as e:
            import traceback
            self.log_message(f"--- 🚨 자동 생성 중 심각한 오류 발생: {e} ---")
            self.log_message(traceback.format_exc())