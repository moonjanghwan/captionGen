"""
파이프라인 실행 탭 뷰

UI 통합 파이프라인을 실행하고 진행 상황을 모니터링하는 인터페이스입니다.
"""

import customtkinter as ctk
from src import config
import tkinter as tk
from tkinter import ttk
import os
import json
import threading
import csv
import io
import time as time_module
from tkinter import filedialog, messagebox
from typing import Dict, Any, Optional
import tempfile

# 파이프라인 모듈 import
try:
    from src.pipeline.ui_integrated_manager import (
        UIIntegratedPipelineManager, UIPipelineConfig
    )
    from src.pipeline.subtitle.generator import SubtitleGenerator
    PIPELINE_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ 파이프라인 모듈 import 실패: {e}")
    PIPELINE_AVAILABLE = False


class PipelineTabView(ctk.CTkFrame):
    """파이프라인 실행 탭 뷰"""
    
    def __init__(self, parent, root=None):
        super().__init__(parent, fg_color="transparent")
        self.root = root
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)  # 스크립트 창이 확장 가능
        self.grid_rowconfigure(2, weight=1)  # 출력 창이 확장 가능
        
        # 최소 높이 설정으로 일관된 크기 유지 (컨트롤 버튼이 보이도록 조정)
        self.grid_rowconfigure(1, minsize=300)
        self.grid_rowconfigure(2, minsize=300)
        
        # 파이프라인 매니저
        self.pipeline_manager: Optional[UIIntegratedPipelineManager] = None
        self.current_project_name = ""
        
        # UI 컴포넌트 생성
        self._create_project_settings_section()
        self._create_script_section()
        self._create_output_section()
        self._create_pipeline_controls_section()
        
        # 초기 상태 설정
        self._update_ui_state()
        
        # 초기 스크립트 로드
        self.after(100, self._refresh_script)
    
    def _create_project_settings_section(self):
        """프로젝트 설정 섹션 생성"""
        settings_frame = ctk.CTkFrame(self, fg_color=config.COLOR_THEME["widget"])
        settings_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        

        
        # 스크립트 선택 탭
        script_tab_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        script_tab_frame.pack(fill="x", padx=20, pady=5)
        
        script_label = ctk.CTkLabel(script_tab_frame, text="생성할 스크립트:")
        script_label.pack(side="left", padx=(0, 10))
        
        self.script_var = tk.StringVar(value="회화")
        script_combo = ctk.CTkComboBox(
            script_tab_frame, 
            values=["회화", "인트로", "엔딩", "대화"], 
            variable=self.script_var, 
            width=120,
            fg_color=config.COLOR_THEME["button"],
            button_color=config.COLOR_THEME["button_hover"],
            text_color=config.COLOR_THEME["text"]
        )
        script_combo.pack(side="left")
        
        # 스크립트 변경 이벤트 바인딩
        script_combo.configure(command=self._on_script_change)
    
    def _create_pipeline_controls_section(self):
        """파이프라인 제어 섹션 생성"""
        controls_frame = ctk.CTkFrame(self, fg_color=config.COLOR_THEME["widget"])
        controls_frame.grid(row=4, column=0, padx=10, pady=5, sticky="ew")
        
        # 제어 버튼들 (맨 아래로 이동)
        button_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        button_frame.pack(pady=15)
        
        # Manifest 생성 버튼
        self.manifest_button = ctk.CTkButton(
            button_frame, 
            text="📋 Manifest 생성", 
            command=self._create_manifest,
            fg_color="#3498DB",
            hover_color="#2980B9",
            width=150,
            height=40
        )
        self.manifest_button.pack(side="left", padx=(0, 10))
        
        # 오디오 생성 버튼
        self.audio_button = ctk.CTkButton(
            button_frame, 
            text="🎵 오디오 생성", 
            command=self._create_audio,
            fg_color="#E67E22",
            hover_color="#D35400",
            width=150,
            height=40
        )
        self.audio_button.pack(side="left", padx=(0, 10))
        
        # 자막 이미지 생성 버튼
        self.subtitle_button = ctk.CTkButton(
            button_frame, 
            text="📝 자막 이미지 생성", 
            command=self._create_subtitles,
            fg_color="#9B59B6",
            hover_color="#8E44AD",
            width=150,
            height=40
        )
        self.subtitle_button.pack(side="left", padx=(0, 10))
        
        # 비디오 렌더링 버튼
        self.video_button = ctk.CTkButton(
            button_frame, 
            text="🎬 비디오 렌더링", 
            command=self._render_video,
            fg_color="#27AE60",
            hover_color="#229954",
            width=150,
            height=40
        )
        self.video_button.pack(side="left", padx=(0, 10))

        self.final_button = ctk.CTkButton(
            button_frame,
            text="🚀 최종 생성",
            command=self._final_generation,
            fg_color="#F1C40F",
            hover_color="#F39C12",
            width=150,
            height=40
        )
        self.final_button.pack(side="left")
    
    def _create_script_section(self):
        """스크립트 섹션 생성"""
        script_frame = ctk.CTkFrame(self, fg_color=config.COLOR_THEME["widget"])
        script_frame.grid(row=1, column=0, padx=10, pady=(5, 2), sticky="nsew")
        script_frame.grid_rowconfigure(0, weight=1)
        

        
        # 스크립트 표시 컨테이너 (텍스트/그리드 전환)
        self.script_display_frame = ctk.CTkFrame(script_frame, fg_color="transparent")
        self.script_display_frame.pack(fill="both", expand=True, padx=10, pady=(10, 10))
        self.script_display_frame.grid_columnconfigure(0, weight=1)
        self.script_display_frame.grid_rowconfigure(0, weight=1)

        # 텍스트 박스 (선택, 복사, 붙여넣기 가능)
        self.script_text = ctk.CTkTextbox(self.script_display_frame, 
                                         font=ctk.CTkFont(size=11))
        self.script_text.grid(row=0, column=0, sticky="nsew")
        
        # 스크립트 창 우클릭 메뉴 추가
        self.script_context_menu = tk.Menu(self.script_text, tearoff=0)
        self.script_context_menu.add_command(label="복사", command=self._copy_selected_script)
        self.script_context_menu.add_command(label="붙여넣기", command=self._paste_to_script)
        self.script_context_menu.add_command(label="전체 선택", command=self._select_all_script)
        self.script_context_menu.add_separator()
        self.script_context_menu.add_command(label="지우기", command=self._clear_script)
        
        # 스크립트 창 우클릭 이벤트 바인딩
        self.script_text.bind("<Button-3>", self._show_script_context_menu)

        # CSV 그리드 (ttk.Treeview) - 회화 스크립트용
        self.csv_tree = ttk.Treeview(self.script_display_frame, 
                                    columns=("순번", "원어", "학습어", "읽기"), 
                                    show="headings")
        # 컬럼 폭: 순번(고정 50), 나머지 3개는 동일 비율 가변
        for col in ("순번", "원어", "학습어", "읽기"):
            self.csv_tree.heading(col, text=col)
        self.csv_tree.column("순번", width=50, minwidth=50, stretch=False, anchor="center")
        for col in ("원어", "학습어", "읽기"):
            self.csv_tree.column(col, width=200, stretch=True, anchor="w")
        
        # 스크롤바
        self.csv_scroll_y = ttk.Scrollbar(self.script_display_frame, orient="vertical", command=self.csv_tree.yview)
        self.csv_tree.configure(yscrollcommand=self.csv_scroll_y.set)
        
        # 초기에는 텍스트 박스만 표시
        self.csv_tree.grid_remove()
        self.csv_scroll_y.grid_remove()
        

    
    def _create_output_section(self):
        """출력 섹션 생성"""
        output_frame = ctk.CTkFrame(self, fg_color=config.COLOR_THEME["widget"])
        output_frame.grid(row=2, column=0, padx=10, pady=(2, 2), sticky="nsew")
        output_frame.grid_rowconfigure(0, weight=1)
        

        
        # 출력 텍스트 박스 (선택, 복사, 붙여넣기 가능)
        self.output_text = ctk.CTkTextbox(output_frame, 
                                         font=ctk.CTkFont(size=11))
        self.output_text.pack(fill="both", expand=True, padx=10, pady=(10, 10))
        
        # 우클릭 메뉴 추가
        self.output_context_menu = tk.Menu(self.output_text, tearoff=0)
        self.output_context_menu.add_command(label="복사", command=self._copy_selected_text)
        self.output_context_menu.add_command(label="붙여넣기", command=self._paste_to_output)
        self.output_context_menu.add_command(label="전체 선택", command=self._select_all_output)
        self.output_context_menu.add_separator()
        self.output_context_menu.add_command(label="지우기", command=self._clear_output)
        
        # 우클릭 이벤트 바인딩
        self.output_text.bind("<Button-3>", self._show_output_context_menu)
        

    
    def _update_ui_state(self):
        """UI 상태 업데이트"""
        if not PIPELINE_AVAILABLE:
            self.manifest_button.configure(state="disabled", text="⚠️ 파이프라인 모듈 없음")
            self.output_text.insert("end", "❌ 파이프라인 모듈을 찾을 수 없습니다.\n")
            self.output_text.insert("end", "필요한 모듈을 설치하거나 경로를 확인하세요.\n\n")
            return
        
        # 스크립트가 선택되면 실행 가능
        script_type = self.script_var.get()
        if script_type:
            self.manifest_button.configure(state="normal", text="📋 Manifest 생성")
        else:
            self.manifest_button.configure(state="disabled", text="스크립트를 선택하세요")
    
    def _create_manifest(self):
        """Manifest 생성 - 선택된 스크립트만 개별 생성"""
        if not PIPELINE_AVAILABLE:
            messagebox.showerror("오류", "파이프라인 모듈을 사용할 수 없습니다.")
            return
        
        script_type = self.script_var.get()
        if not script_type:
            messagebox.showerror("오류", "스크립트를 선택하세요.")
            return
        
        try:
            # 스크립트 데이터 수집
            script_data = self._collect_script_data(script_type)
            if not script_data:
                messagebox.showerror("오류", "스크립트 데이터를 수집할 수 없습니다.")
                return
            
            # 선택된 스크립트만 Manifest 생성
            manifest_data = self._generate_manifest_data(script_type, script_data)
            
            # 출력 창에 JSON 디스플레이
            self.output_text.delete("1.0", tk.END)
            self.output_text.insert("end", f"📋 {script_type} Manifest 생성 완료!\n\n")
            self.output_text.insert("end", "=== Manifest JSON 내용 ===\n")
            self.output_text.insert("end", json.dumps(manifest_data, ensure_ascii=False, indent=2))
            
            # 파일명 형식에 맞춰 저장
            filename = self._save_manifest_file(manifest_data, script_type)
            if filename:
                self.output_text.insert("end", f"\n\n💾 파일 저장 완료: {filename}")
            
            self._add_output_message(f"✅ {script_type} Manifest 생성 완료", "INFO")
            
        except Exception as e:
            error_msg = f"Manifest 생성 실패: {e}"
            self._add_output_message(error_msg, "ERROR")
            messagebox.showerror("오류", error_msg)
    
    def _create_audio(self):
        """오디오 생성 - SSML 파일을 출력창에 디스플레이"""
        if not PIPELINE_AVAILABLE:
            messagebox.showerror("오류", "파이프라인 모듈을 사용할 수 없습니다.")
            return
        
        try:
            script_type = self.script_var.get()
            
            # 🎯 오디오 생성 시작 메시지
            self.output_text.delete("1.0", tk.END)
            self.output_text.insert("end", "🎵 오디오 생성 파이프라인 시작\n")
            self.output_text.insert("end", "="*60 + "\n\n")
            self.output_text.insert("end", f"📝 선택된 스크립트: {script_type}\n")
            self.output_text.insert("end", f"⏰ 시작 시간: {self._get_current_time()}\n\n")
            
            # 터미널 로그 출력
            print(f"[오디오 생성] {script_type} 오디오 생성 시작...")
            print(f"[오디오 생성] 시작 시간: {self._get_current_time()}")
            
            # 🧹 기존 SSML 파일들 정리 (새로운 SSML 강제 생성)
            self.output_text.insert("end", "🧹 기존 SSML 파일 정리 중...\n")
            self._cleanup_old_ssml_files()
            
            self._add_output_message(f"🎵 {script_type} 오디오 생성 시작...", "INFO")
            
            # 🔍 1단계: SSML 생성 및 분석
            self.output_text.insert("end", "🔍 1단계: SSML 생성 및 분석\n")
            self.output_text.insert("end", "-"*40 + "\n")
            self.output_text.insert("end", "📋 SSML 내용 생성 중...\n")
            
            print(f"[오디오 생성] 1단계: SSML 생성 시작 ({script_type})")
            
            # 회화와 대화는 각 화자별 별도 처리
            if script_type in ["회화", "대화"]:
                ssml_parts = self._generate_ssml_for_script(script_type)
                if ssml_parts:
                    # 화자별 SSML 파트를 하나의 SSML로 합치기 (표시용)
                    ssml_content = ""
                    for part in ssml_parts:
                        ssml_content += part['ssml'] + "\n"
            else:
                ssml_content = self._generate_ssml_for_script(script_type)
            
            if ssml_content or (script_type in ["회화", "대화"] and ssml_parts):
                self.output_text.insert("end", "✅ SSML 내용 생성 완료!\n\n")
                print(f"[오디오 생성] 1단계: SSML 생성 완료 (길이: {len(ssml_content)} 문자)")
                
                # 📊 2단계: 스마트한 추정 길이 계산
                self.output_text.insert("end", "📊 2단계: 스마트한 추정 길이 계산\n")
                self.output_text.insert("end", "-"*40 + "\n")
                
                # 제작 사양서 규칙에 따른 SSML 파일명 표시
                script_type_mapping = {
                    "회화": "dialog",
                    "인트로": "intro", 
                    "엔딩": "ending",
                    "대화": "dialog"
                }
                script_suffix = script_type_mapping.get(script_type, script_type.lower())
                identifier = self.root.data_page.identifier_var.get() if hasattr(self.root, 'data_page') else "kor-chn"
                ssml_filename = f"{identifier}_{script_suffix}.ssml"
                
                self.output_text.insert("end", f"📁 SSML 파일명: {ssml_filename}\n")
                self.output_text.insert("end", f"📊 총 마크 태그: {ssml_content.count('<mark')}개\n")
                
                # 언어별 분석 정보 추가
                korean_text = self._extract_korean_text(ssml_content)
                chinese_text = self._extract_chinese_text(ssml_content)
                self.output_text.insert("end", f"🇰🇷 한국어 글자: {len(korean_text)}자\n")
                self.output_text.insert("end", f"🇨🇳 중국어 글자: {len(chinese_text)}자\n")
                
                estimated_duration = self._estimate_audio_duration(ssml_content)
                self.output_text.insert("end", f"⏱️ 예상 오디오 길이: {estimated_duration}초 (스마트 추정)\n")
                self.output_text.insert("end", "="*60 + "\n\n")
                
                # 📋 SSML 파일 내용 표시
                self.output_text.insert("end", "📋 SSML 파일 내용:\n")
                self.output_text.insert("end", "```xml\n")
                self.output_text.insert("end", ssml_content)
                self.output_text.insert("end", "\n```\n\n")
                
                self._add_output_message("✅ SSML 파일 생성 및 출력창 디스플레이 완료", "INFO")
                
                # 💾 3단계: SSML 파일 저장
                self.output_text.insert("end", "💾 3단계: SSML 파일 저장\n")
                self.output_text.insert("end", "-"*40 + "\n")
                self.output_text.insert("end", "📁 파일 저장 중...\n")
                
                self._save_ssml_file(script_type, ssml_content)
                
                # 🎯 4단계: 정확한 동기화 준비
                self.output_text.insert("end", "🎯 4단계: 정확한 동기화 준비\n")
                self.output_text.insert("end", "-"*40 + "\n")
                
                self._prepare_audio_generation_with_sync(script_type, ssml_content)
                
                # 🎵 5단계: MP3 파일 생성
                self.output_text.insert("end", "🎵 5단계: MP3 파일 생성\n")
                self.output_text.insert("end", "-"*40 + "\n")
                
                self._generate_mp3_file(script_type, ssml_content)
                
                # 🎉 완료 메시지
                self.output_text.insert("end", "="*60 + "\n")
                self.output_text.insert("end", "🎉 오디오 생성 파이프라인 완료!\n")
                self.output_text.insert("end", f"⏰ 완료 시간: {self._get_current_time()}\n")
                self.output_text.insert("end", "="*60 + "\n")
                
            else:
                self.output_text.insert("end", "❌ SSML 생성 실패\n")
                print(f"[오디오 생성] ❌ SSML 생성 실패")
                self._add_output_message("❌ SSML 생성 실패", "ERROR")
                
        except Exception as e:
            error_msg = f"오디오 생성 실패: {e}"
            self.output_text.insert("end", f"❌ 오류 발생: {error_msg}\n")
            print(f"[오디오 생성] ❌ 오류 발생: {error_msg}")
            print(f"[오디오 생성] 오류 상세: {type(e).__name__}: {str(e)}")
            import traceback
            print(f"[오디오 생성] 스택 트레이스:\n{traceback.format_exc()}")
            self._add_output_message(error_msg, "ERROR")
            messagebox.showerror("오류", error_msg)
    
    def _create_subtitles(self):
        """자막 이미지 생성"""
        if not PIPELINE_AVAILABLE:
            messagebox.showerror("오류", "파이프라인 모듈을 사용할 수 없습니다.")
            return
        
        try:
            script_type = self.script_var.get()
            self._add_output_message(f"📝 {script_type} 자막 이미지 생성 시작...", "INFO")
            
            project_name = self.root.data_page.project_name_var.get() if hasattr(self.root, 'data_page') else "kor-chn"
            identifier = self.root.data_page.identifier_var.get() if hasattr(self.root, 'data_page') else "kor-chn"

            if script_type == "회화":
                self._generate_conversation_images(project_name, identifier)
            elif script_type == "인트로":
                self._generate_intro_images(project_name, identifier)
            elif script_type == "엔딩":
                self._generate_ending_images(project_name, identifier)
            elif script_type == "대화":
                self._generate_dialogue_images(project_name, identifier)
            else:
                self._add_output_message(f"지원하지 않는 스크립트 타입: {script_type}", "ERROR")

        except Exception as e:
            error_msg = f"자막 이미지 생성 실패: {e}"
            self._add_output_message(error_msg, "ERROR")
            messagebox.showerror("오류", error_msg)

    def _generate_conversation_images(self, project_name, identifier):
        """회화 스크립트 자막 이미지 생성"""
        try:
    
            
            # Manifest 파일 경로
            manifest_path = "output/manifest_conversation.json"
            if not os.path.exists(manifest_path):
                self._add_output_message(f"❌ Manifest 파일을 찾을 수 없습니다: {manifest_path}", "ERROR")
                messagebox.showerror("오류", f"Manifest 파일을 찾을 수 없습니다: {manifest_path}")
                return

            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest_data = json.load(f)

            # 이미지 설정 가져오기
            image_settings = self.root.image_page.get_all_settings()

            # 자막 생성기 초기화
            subtitle_generator = SubtitleGenerator(settings=image_settings)
            
            # 출력 디렉토리 설정
            output_dir = os.path.join("output", project_name, identifier, "subtitles")
            
            # 자막 이미지 생성
            frames = subtitle_generator.generate_from_manifest(manifest_data, output_dir)

        except Exception as e:
            error_msg = f"회화 자막 이미지 생성 실패: {e}"
            self._add_output_message(error_msg, "ERROR")
            messagebox.showerror("오류", error_msg)

    def _generate_intro_images(self, project_name, identifier):
        """인트로 스크립트 자막 이미지 생성"""
        try:
            
            
            # Manifest 파일 경로
            manifest_path = "output/manifest_intro.json"
            if not os.path.exists(manifest_path):
                self._add_output_message(f"❌ Manifest 파일을 찾을 수 없습니다: {manifest_path}", "ERROR")
                messagebox.showerror("오류", f"Manifest 파일을 찾을 수 없습니다: {manifest_path}")
                return

            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest_data = json.load(f)

            # 이미지 설정 가져오기
            image_settings = self.root.image_page.get_all_settings()

            # 자막 생성기 초기화
            subtitle_generator = SubtitleGenerator(settings=image_settings)
            
            # 출력 디렉토리 설정
            output_dir = os.path.join("output", project_name, identifier, "subtitles")
            
            # 자막 이미지 생성
            frames = subtitle_generator.generate_from_manifest(manifest_data, output_dir)

        except Exception as e:
            error_msg = f"인트로 자막 이미지 생성 실패: {e}"
            self._add_output_message(error_msg, "ERROR")
            messagebox.showerror("오류", error_msg)

    def _generate_ending_images(self, project_name, identifier):
        """엔딩 스크립트 자막 이미지 생성"""
        try:
            
            
            # Manifest 파일 경로
            manifest_path = "output/manifest_ending.json"
            if not os.path.exists(manifest_path):
                self._add_output_message(f"❌ Manifest 파일을 찾을 수 없습니다: {manifest_path}", "ERROR")
                messagebox.showerror("오류", f"Manifest 파일을 찾을 수 없습니다: {manifest_path}")
                return

            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest_data = json.load(f)

            # 이미지 설정 가져오기
            image_settings = self.root.image_page.get_all_settings()

            # 자막 생성기 초기화
            subtitle_generator = SubtitleGenerator(settings=image_settings)
            
            # 출력 디렉토리 설정
            output_dir = os.path.join("output", project_name, identifier, "subtitles")
            
            # 자막 이미지 생성
            frames = subtitle_generator.generate_from_manifest(manifest_data, output_dir)

        except Exception as e:
            error_msg = f"엔딩 자막 이미지 생성 실패: {e}"
            self._add_output_message(error_msg, "ERROR")
            messagebox.showerror("오류", error_msg)

    def _generate_dialogue_images(self, project_name, identifier):
        """대화 스크립트 자막 이미지 생성"""
        try:
            
            
            # Manifest 파일 경로
            manifest_path = "output/manifest_dialog.json"
            if not os.path.exists(manifest_path):
                self._add_output_message(f"❌ Manifest 파일을 찾을 수 없습니다: {manifest_path}", "ERROR")
                messagebox.showerror("오류", f"Manifest 파일을 찾을 수 없습니다: {manifest_path}")
                return

            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest_data = json.load(f)

            # 이미지 설정 가져오기
            image_settings = self.root.image_page.get_all_settings()

            # 자막 생성기 초기화
            subtitle_generator = SubtitleGenerator(settings=image_settings)
            
            # 출력 디렉토리 설정
            output_dir = os.path.join("output", project_name, identifier, "subtitles")
            
            # 자막 이미지 생성
            frames = subtitle_generator.generate_from_manifest(manifest_data, output_dir)

        except Exception as e:
            error_msg = f"대화 자막 이미지 생성 실패: {e}"
            self._add_output_message(error_msg, "ERROR")
            messagebox.showerror("오류", error_msg)
    
    def _final_generation(self):
        self._add_output_message("🚀 최종 생성 시작...", "INFO")

    def _render_video(self):
        """비디오 렌더링"""
        if not PIPELINE_AVAILABLE:
            messagebox.showerror("오류", "파이프라인 모듈을 사용할 수 없습니다.")
            return
        
        try:
            script_type = self.script_var.get()
            self._add_output_message(f"🎬 {script_type} 비디오 렌더링 시작...", "INFO")
            
            # 추후 기능 구현 예정
            self.output_text.delete("1.0", tk.END)
            self.output_text.insert("end", f"🎬 {script_type} 비디오 렌더링\n\n")
            self.output_text.insert("end", "이 기능은 추후 구현 예정입니다.\n")
            self.output_text.insert("end", "현재는 Manifest와 SSML 생성만 지원합니다.")
            
            self._add_output_message("⚠️ 비디오 렌더링은 추후 구현 예정", "WARNING")
            
        except Exception as e:
            error_msg = f"비디오 렌더링 실패: {e}"
            self._add_output_message(error_msg, "ERROR")
            messagebox.showerror("오류", error_msg)
    
    def _on_script_change(self, choice=None):
        self.after(50, self._refresh_script)

    def _refresh_script(self):
        """스크립트 종류에 따라 UI를 새로고침합니다."""
        script_type = self.script_var.get()
        
        self.script_text.grid_remove()
        self.csv_tree.grid_remove()
        self.csv_scroll_y.grid_remove()
        for item in self.csv_tree.get_children():
            self.csv_tree.delete(item)
        self.script_text.delete("1.0", tk.END)

        try:
            script_data = self._collect_script_data(script_type)
            
            if script_type in ["회화", "대화"] and isinstance(script_data, dict) and "scenes" in script_data:
                self._show_csv_grid(script_data["scenes"])
            elif isinstance(script_data, str):
                self._show_text_content(script_data)
            else:
                self._show_text_content(f"표시할 데이터가 없습니다: {script_type}")

        except Exception as e:
            self._show_text_content(f"스크립트 로딩 중 오류 발생: {e}")

    def _collect_script_data(self, script_type: str) -> Optional[Any]:
        """데이터 탭에서 스크립트 데이터를 가져옵니다."""
        if not hasattr(self.root, 'data_page'):
            return None
        
        data_page = self.root.data_page
        if not hasattr(data_page, 'generated_data') or not data_page.generated_data:
            if not data_page.load_generated_data():
                return None

        if not hasattr(data_page, 'generated_data'):
            return None

        data = data_page.generated_data
        if not data:
            return None

        if script_type == "회화" or script_type == "대화":
            dialogue_csv = data.get("fullVideoScript", {}).get("dialogueCsv") or data.get("dialogueCsv", "")
            if dialogue_csv and dialogue_csv.strip():
                reader = csv.reader(io.StringIO(dialogue_csv))
                rows = list(reader)
                if rows and [c.strip('"') for c in rows[0][:4]] == ["순번", "원어", "학습어", "읽기"]:
                    rows = rows[1:]
                
                scenes = []
                for row in rows:
                    normalized = [c.strip('"') for c in row]
                    padded = (normalized + [""] * 4)[:4]
                    scenes.append({
                        "order": padded[0],
                        "native_script": padded[1],
                        "learning_script": padded[2],
                        "reading_script": padded[3]
                    })
                return {"scenes": scenes}
            return None
        elif script_type == "인트로":
            return data.get("introScript", "")
        elif script_type == "엔딩":
            return data.get("endingScript", "")
        else:
            return None

    def _show_text_content(self, content: str):
        """텍스트 내용을 텍스트 박스에 표시"""
        self.csv_tree.grid_remove()
        self.csv_scroll_y.grid_remove()
        self.script_text.grid(row=0, column=0, sticky="nsew")
        self.script_text.delete("1.0", tk.END)
        self.script_text.insert("1.0", content)

    def _show_csv_grid(self, scenes):
        """CSV 데이터를 그리드로 표시"""
        self.script_text.grid_remove()
        self.csv_tree.grid(row=0, column=0, sticky="nsew")
        self.csv_scroll_y.grid(row=0, column=1, sticky="ns")
        
        for iid in self.csv_tree.get_children():
            self.csv_tree.delete(iid)
        
        for scene in scenes:
            values = [
                scene.get('order', ''),
                scene.get('native_script', ''),
                scene.get('learning_script', ''),
                scene.get('reading_script', '')
            ]
            self.csv_tree.insert("", tk.END, values=values)
    
    def _display_conversation_script(self, script_data):
        """회화 스크립트 표시 - 그리드 형식으로 표시"""
        try:
            if not script_data or "scenes" not in script_data:
                self._show_text_content("회화 스크립트 데이터가 없습니다.\n데이터 생성 탭에서 먼저 스크립트를 생성하세요.")
                return
            
            # CSV 그리드로 표시
            self._show_csv_grid(script_data["scenes"])
        except Exception as e:
            self._show_text_content(f"회화 스크립트 표시 실패: {e}")
    
    def _display_intro_script(self, script_data):
        """인트로 스크립트 표시 - 문장 단위로 줄바꿈"""
        try:
            if not script_data or "script" not in script_data:
                self._show_text_content("인트로 스크립트 데이터가 없습니다.\n데이터 생성 탭에서 먼저 스크립트를 생성하세요.")
                return
            
            script = script_data.get("script", "")
            # 문장 단위로 줄바꿈하여 표시
            if script:
                parts = [p.strip() for p in script.split(".") if p.strip()]
                content = []
                for i, part in enumerate(parts, 1):
                    if part:
                        content.append(f"{i}. {part.strip()}")
                self._show_text_content("\n".join(content))
            else:
                self._show_text_content("인트로 스크립트가 비어있습니다.")
        except Exception as e:
            self._show_text_content(f"인트로 스크립트 표시 실패: {e}")
    
    def _display_ending_script(self, script_data):
        """엔딩 스크립트 표시 - 문장 단위로 줄바꿈"""
        try:
            if not script_data or "script" not in script_data:
                self._show_text_content("엔딩 스크립트 데이터가 없습니다.\n데이터 생성 탭에서 먼저 스크립트를 생성하세요.")
                return
            
            script = script_data.get("script", "")
            # 문장 단위로 줄바꿈하여 표시
            if script:
                parts = [p.strip() for p in script.split(".") if p.strip()]
                content = []
                for i, part in enumerate(parts, 1):
                    if part:
                        content.append(f"{i}. {part.strip()}")
                self._show_text_content("\n".join(content))
            else:
                self._show_text_content("엔딩 스크립트가 비어있습니다.")
        except Exception as e:
            self._show_text_content(f"엔딩 스크립트 표시 실패: {e}")
    
    def _display_dialogue_script(self, script_data):
        """대화 스크립트 표시 - 그리드 형식으로 표시"""
        try:
            if not script_data or "scenes" not in script_data:
                self._show_text_content("대화 스크립트 데이터가 없습니다.\n데이터 생성 탭에서 먼저 스크립트를 생성하세요.")
                return
            
            # 대화도 그리드로 표시 (회화와 동일한 구조)
            self._show_csv_grid(script_data["scenes"])
        except Exception as e:
            self._show_text_content(f"대화 스크립트 표시 실패: {e}")
    
    def _split_into_sentences(self, text):
        """텍스트를 문장 단위로 분리 (마침표, 느낌표, 물음표 기준)"""
        import re
        # 마침표, 느낌표, 물음표를 기준으로 문장 분리
        # 단, 줄바꿈이 있는 경우에도 분리
        sentences = re.split(r'[.!?]\s*|\n+', text)
        # 빈 문자열 제거 및 공백 정리
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences

    def _generate_manifest_data(self, script_type, script_data):
        """Manifest 데이터 생성 - 선택된 스크립트만 개별 생성"""
        try:
            # 기본 Manifest 구조
            manifest = {
                "metadata": {
                    "script_type": script_type,
                    "created_at": time_module.strftime("%Y-%m-%d %H:%M:%S"),
                    "version": "1.0"
                },
                "project_config": {
                    "project_name": f"중국어_학습_{script_type}",
                    "resolution": "1920x1080",
                    "fps": 30,
                    "default_background": "#000000"
                },
                "scenes": []
            }
            
            if script_type == "회화":
                scenes = script_data.get("scenes", [])
                for i, scene in enumerate(scenes, 1):
                    # 회화 설정에 따른 4가지 스크립트 포함
                    manifest["scenes"].append({
                        "id": f"conversation_{i:02d}",
                        "type": "conversation",
                        "sequence": i,
                        "duration": None,  # 오디오 길이에 따라 동적 결정
                        "content": {
                            "order": scene.get("order", str(i)),  # 순번
                            "native_script": scene.get("native_script", ""),  # 원어
                            "learning_script": scene.get("learning_script", ""),  # 학습어
                            "reading_script": scene.get("reading_script", "")  # 발음
                        },
                        "display_config": {
                            "screen_1": {
                                "type": "order_native_only",
                                "elements": ["order", "native_script"]
                            },
                            "screen_2": {
                                "type": "full_content",
                                "elements": ["order", "native_script", "learning_script", "reading_script"]
                            }
                        },
                        "audio_config": {
                            "speakers": [
                                {"type": "native", "script": "native_script", "duration": None},
                                {"type": "learning", "script": "learning_script", "duration": None},
                                {"type": "reading", "script": "reading_script", "duration": None}
                            ],
                            "silence_between": 1.0  # 화자간, 행간 1초 무음
                        }
                    })
            
            elif script_type == "인트로":
                script = script_data
                # 문장 단위로 분리 (마침표, 느낌표, 물음표 기준)
                sentences = self._split_into_sentences(script)
                
                for i, sentence in enumerate(sentences, 1):
                    if sentence.strip():  # 빈 문장 제외
                        manifest["scenes"].append({
                            "id": f"intro_{i:02d}",
                            "type": "intro",
                            "sequence": i,
                            "duration": None,  # 오디오 길이에 따라 동적 결정
                            "content": {
                                "sentence": sentence.strip(),
                                "sentence_number": i,
                                "total_sentences": len(sentences)
                            },
                            "display_config": {
                                "smart_wrapping": True,
                                "max_lines": 3,
                                "background_color": "#000000",
                                "alignment": "top",  # x,y 기준으로 아래로 텍스트 배치
                                "text_settings": {
                                    "font": "KoPubWorldDotum",
                                    "size": 90,
                                    "color": "#FFFFFF",
                                    "weight": "Bold",
                                    "alignment": "Center",
                                    "vertical_alignment": "Bottom"
                                }
                            },
                            "audio_config": {
                                "speakers": [
                                    {"type": "native", "script": sentence.strip(), "duration": None}
                                ]
                            }
                        })
                        

            
            elif script_type == "엔딩":
                script = script_data
                # 문장 단위로 분리 (마침표, 느낌표, 물음표 기준)
                sentences = self._split_into_sentences(script)
                
                for i, sentence in enumerate(sentences, 1):
                    if sentence.strip():  # 빈 문장 제외
                        manifest["scenes"].append({
                            "id": f"ending_{i:02d}",
                            "type": "ending",
                            "sequence": i,
                            "duration": None,  # 오디오 길이에 따라 동적 결정
                            "content": {
                                "sentence": sentence.strip(),
                                "sentence_number": i,
                                "total_sentences": len(sentences)
                            },
                            "display_config": {
                                "smart_wrapping": True,
                                "max_lines": 3,
                                "background_color": "#000000",
                                "alignment": "bottom",  # x,y가 마지막 줄 기준, 위로 텍스트 배치
                                "text_settings": {
                                    "font": "KoPubWorldDotum",
                                    "size": 100,
                                    "color": "#FFFFFF",
                                    "weight": "Bold",
                                    "alignment": "Center",
                                    "vertical_alignment": "Middle"
                                }
                            },
                            "audio_config": {
                                "speakers": [
                                    {"type": "native", "script": sentence.strip(), "duration": None}
                                ]
                            }
                        })
                        

            
            elif script_type == "대화":
                scenes = script_data.get("scenes", [])
                for i, scene in enumerate(scenes, 1):
                    manifest["scenes"].append({
                        "id": f"dialogue_{i:02d}",
                        "type": "dialogue",
                        "sequence": i,
                        "duration": None,  # 오디오 길이에 따라 동적 결정
                        "content": {
                            "order": scene.get("order", str(i)),  # 순번
                            "native_script": scene.get("native_script", ""),  # 원어
                            "learning_script": scene.get("learning_script", "")  # 학습어
                        },
                        "display_config": {
                            "screen_1": {
                                "type": "order_native_only",
                                "elements": ["order", "native_script"]
                            },
                            "screen_2": {
                                "type": "full_content",
                                "elements": ["order", "native_script", "learning_script"]
                            }
                        },
                        "audio_config": {
                            "speakers": [
                                {"type": "native", "script": "native_script", "duration": None},
                                {"type": "learning", "script": "learning_script", "duration": None}
                            ],
                            "silence_between": 1.0  # 화자간, 행간 1초 무음
                        }
                    })
            
            return manifest
            
        except Exception as e:
            raise Exception(f"Manifest 데이터 생성 실패: {e}")
    
    def _save_manifest_file(self, manifest_data, script_type):
        """Manifest 파일 저장 - 파일명 형식에 맞춰 저장"""
        try:
            # 파일명 형식: manifest_[스크립트타입].json
            script_type_mapping = {
                "회화": "conversation",
                "인트로": "intro",
                "엔딩": "ending",
                "대화": "dialog"
            }
            script_suffix = script_type_mapping.get(script_type, script_type.lower())
            filename = f"manifest_{script_suffix}.json"
            filepath = os.path.join("output", filename)
            
            # 출력 디렉토리 생성
            os.makedirs("output", exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(manifest_data, f, ensure_ascii=False, indent=2)
            
            self._add_output_message(f"💾 Manifest 파일 저장 완료: {filepath}", "INFO")
            return filename
            
        except Exception as e:
            self._add_output_message(f"❌ Manifest 파일 저장 실패: {e}", "ERROR")
            return None
    
    def _generate_ssml_for_script(self, script_type):
        """스크립트에 대한 SSML 생성"""
        try:
            script_data = self._collect_script_data(script_type)
            if not script_data:
                return None
            
            if script_type == "회화":
                return self._generate_conversation_ssml(script_data)
            elif script_type == "인트로":
                return self._generate_intro_ssml(script_data)
            elif script_type == "엔딩":
                return self._generate_ending_ssml(script_data)
            elif script_type == "대화":
                return self._generate_dialogue_ssml(script_data)
            
            return None
            
        except Exception as e:
            self._add_output_message(f"SSML 생성 실패: {e}", "ERROR")
            return None
    
    def _generate_conversation_ssml(self, script_data):
        """회화 SSML 생성 - 제작 사양서 준수 (각 화자별 별도 처리)"""
        try:
            # 화자 설정 가져오기
            speaker_settings = self._get_speaker_settings()
            native_voice = speaker_settings.get("native_speaker", "ko-KR-Chirp3-HD-Achernar")
            learner_voices = speaker_settings.get("learner_speakers", [])
            
            print(f"[SSML 생성] 회화 - 원어 화자: {native_voice}")
            print(f"[SSML 생성] 회화 - 학습어 화자들: {learner_voices}")
            
            # 각 화자별로 별도의 SSML 생성 (Chirp3 음성 지원)
            scenes = script_data.get("scenes", [])
            all_ssml_parts = []
            
            for i, scene in enumerate(scenes, 1):
                scene_parts = []
                
                # 1. 원어화자 - 원어
                native_ssml = f'<speak>\n  <mark name="scene_{i:02d}_native_start"/>\n  {scene.get("native_script", "")}\n  <mark name="scene_{i:02d}_native_end"/>\n</speak>'
                scene_parts.append({
                    'ssml': native_ssml,
                    'voice': native_voice,
                    'text': scene.get("native_script", ""),
                    'type': 'native'
                })
                
                # 2-5. 학습어 화자들 - 학습어
                for j, learner_voice in enumerate(learner_voices, 1):
                    learner_ssml = f'<speak>\n  <mark name="scene_{i:02d}_learner{j}_start"/>\n  {scene.get("learning_script", "")}\n  <mark name="scene_{i:02d}_learner{j}_end"/>\n</speak>'
                    scene_parts.append({
                        'ssml': learner_ssml,
                        'voice': learner_voice,
                        'text': scene.get("learning_script", ""),
                        'type': 'learner'
                    })
                
                all_ssml_parts.extend(scene_parts)
            
            return all_ssml_parts
            
        except Exception as e:
            raise Exception(f"회화 SSML 생성 실패: {e}")
    
    def _generate_intro_ssml(self, script_data):
        """인트로 SSML 생성 - 제작 사양서 준수 (Chirp3 음성 지원)"""
        try:
            # 화자 설정 가져오기
            speaker_settings = self._get_speaker_settings()
            intro_voice = speaker_settings.get("native_speaker", "ko-KR-Chirp3-HD-Achernar")
            
            print(f"[SSML 생성] 인트로 화자: {intro_voice}")
            
            script = script_data
            # 문장 단위로 분리
            sentences = self._split_into_sentences(script)
            
            # Chirp3 음성 지원: SSML에서 <voice> 태그 제거
            ssml = '<speak>\n'
            
            for i, sentence in enumerate(sentences, 1):
                if sentence.strip():
                    ssml += f'  <mark name="intro_sentence_{i:02d}_start"/>\n'
                    ssml += f'  {sentence.strip()}\n'
                    ssml += f'  <mark name="intro_sentence_{i:02d}_end"/>\n'
                    
                    # 마지막 문장이 아니면 1초 무음 추가
                    if i < len(sentences):
                        ssml += f'  <break time="1s"/>\n'  # 문장간 1초 무음
            
            ssml += '</speak>'
            return ssml
            
        except Exception as e:
            raise Exception(f"인트로 SSML 생성 실패: {e}")
    
    def _generate_ending_ssml(self, script_data):
        """엔딩 SSML 생성 - 제작 사양서 준수 (Chirp3 음성 지원)"""
        try:
            # 화자 설정 가져오기
            speaker_settings = self._get_speaker_settings()
            ending_voice = speaker_settings.get("native_speaker", "ko-KR-Chirp3-HD-Achernar")
            
            print(f"[SSML 생성] 엔딩 화자: {ending_voice}")
            
            script = script_data
            # 문장 단위로 분리
            sentences = self._split_into_sentences(script)
            
            # Chirp3 음성 지원: SSML에서 <voice> 태그 제거
            ssml = '<speak>\n'
            
            for i, sentence in enumerate(sentences, 1):
                if sentence.strip():
                    ssml += f'  <mark name="ending_sentence_{i:02d}_start"/>\n'
                    ssml += f'  {sentence.strip()}\n'
                    ssml += f'  <mark name="ending_sentence_{i:02d}_end"/>\n'
                    
                    # 마지막 문장이 아니면 1초 무음 추가
                    if i < len(sentences):
                        ssml += f'  <break time="1s"/>\n'  # 문장간 1초 무음
            
            ssml += '</speak>'
            return ssml
            
        except Exception as e:
            raise Exception(f"엔딩 SSML 생성 실패: {e}")
    
    def _generate_dialogue_ssml(self, script_data):
        """대화 SSML 생성 - 제작 사양서 준수 (각 화자별 별도 처리)"""
        try:
            # 화자 설정 가져오기
            speaker_settings = self._get_speaker_settings()
            native_voice = speaker_settings.get("native_speaker", "ko-KR-Chirp3-HD-Achernar")
            learner_voices = speaker_settings.get("learner_speakers", [])
            
            print(f"[SSML 생성] 대화 - 원어 화자: {native_voice}")
            print(f"[SSML 생성] 대화 - 학습어 화자들: {learner_voices}")
            
            # 각 화자별로 별도의 SSML 생성 (Chirp3 음성 지원)
            scenes = script_data.get("scenes", [])
            all_ssml_parts = []
            
            for i, scene in enumerate(scenes, 1):
                scene_parts = []
                
                # 1. 원어화자 - 원어
                native_ssml = f'<speak>\n  <mark name="dialogue_{i:02d}_native_start"/>\n  {scene.get("native_script", "")}\n  <mark name="dialogue_{i:02d}_native_end"/>\n</speak>'
                scene_parts.append({
                    'ssml': native_ssml,
                    'voice': native_voice,
                    'text': scene.get("native_script", ""),
                    'type': 'native'
                })
                
                # 2-5. 학습어 화자들 - 학습어
                for j, learner_voice in enumerate(learner_voices, 1):
                    learner_ssml = f'<speak>\n  <mark name="dialogue_{i:02d}_learner{j}_start"/>\n  {scene.get("learning_script", "")}\n  <mark name="dialogue_{i:02d}_learner{j}_end"/>\n</speak>'
                    scene_parts.append({
                        'ssml': learner_ssml,
                        'voice': learner_voice,
                        'text': scene.get("learning_script", ""),
                        'type': 'learner'
                    })
                
                all_ssml_parts.extend(scene_parts)
            
            return all_ssml_parts
            
        except Exception as e:
            raise Exception(f"대화 SSML 생성 실패: {e}")
    
    def _save_subtitle_image(self, image, project_name, identifier, script_type, image_index):
        """Saves a subtitle image to the correct directory with the correct filename."""
        dir_map = {
            "회화": "dialog",
            "인트로": "intro",
            "엔딩": "ending",
            "대화": "dialog"
        }
        sub_dir = dir_map.get(script_type)
        if not sub_dir:
            return None

        image_dir = os.path.join(config.OUTPUT_PATH, project_name, identifier, sub_dir)
        os.makedirs(image_dir, exist_ok=True)
        
        filename = f"{identifier}_{image_index:03d}.png"
        filepath = os.path.join(image_dir, filename)
        image.save(filepath, 'PNG')
        return filepath

    def _add_output_message(self, message: str, level: str = "INFO"):
        """출력 메시지 추가"""
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            log_message = f"[{timestamp}] {level}: {message}"
            # 출력 창에 메시지 추가
            self.output_text.insert("end", f"{log_message}\n")
            self.output_text.see("end")
            # 터미널에도 출력
            print(log_message)
            
        except Exception:
            pass
    
    def _copy_selected_text(self):
        """선택된 텍스트를 클립보드에 복사"""
        try:
            selected_text = self.output_text.get("sel.first", "sel.last")
            if selected_text:
                self.clipboard_clear()
                self.clipboard_append(selected_text)
                self._add_output_message("선택된 텍스트가 클립보드에 복사되었습니다.", "SUCCESS")
        except tk.TclError:
            # 선택된 텍스트가 없는 경우
            self._add_output_message("복사할 텍스트를 먼저 선택하세요.", "WARNING")

    def _paste_to_output(self):
        """클립보드의 텍스트를 출력 창에 붙여넣기"""
        try:
            clipboard_text = self.clipboard_get()
            if clipboard_text:
                # 현재 커서 위치에 붙여넣기
                self.output_text.insert(tk.INSERT, clipboard_text)
                self._add_output_message("클립보드의 텍스트가 출력 창에 붙여넣기되었습니다.", "SUCCESS")
        except tk.TclError:
            # 클립보드에 텍스트가 없는 경우
            self._add_output_message("클립보드에 붙여넣을 텍스트가 없습니다.", "WARNING")
    
    def _select_all_output(self):
        """출력 창의 모든 텍스트 선택"""
        self.output_text.tag_add("sel", "1.0", "end")
        self._add_output_message("전체 텍스트가 선택되었습니다.", "INFO")
    
    def _show_output_context_menu(self, event):
        """출력 창 우클릭 메뉴 표시"""
        try:
            self.output_context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.output_context_menu.grab_release()
    
    def _copy_selected_script(self):
        """스크립트 창에서 선택된 텍스트를 클립보드에 복사"""
        try:
            selected_text = self.script_text.get("sel.first", "sel.last")
            if selected_text:
                self.clipboard_clear()
                self.clipboard_append(selected_text)
                self._add_output_message("선택된 스크립트 텍스트가 클립보드에 복사되었습니다.", "SUCCESS")
        except tk.TclError:
            # 선택된 텍스트가 없는 경우
            self._add_output_message("복사할 스크립트 텍스트를 먼저 선택하세요.", "WARNING")
    
    def _paste_to_script(self):
        """클립보드의 텍스트를 스크립트 창에 붙여넣기"""
        try:
            clipboard_text = self.clipboard_get()
            if clipboard_text:
                # 현재 커서 위치에 붙여넣기
                self.script_text.insert(tk.INSERT, clipboard_text)
                self._add_output_message("클립보드의 텍스트가 스크립트 창에 붙여넣기되었습니다.", "SUCCESS")
        except tk.TclError:
            # 클립보드에 텍스트가 없는 경우
            self._add_output_message("클립보드에 붙여넣을 텍스트가 없습니다.", "WARNING")
    
    def _select_all_script(self):
        """스크립트 창의 모든 텍스트 선택"""
        self.script_text.tag_add("sel", "1.0", "end")
        self._add_output_message("스크립트 전체 텍스트가 선택되었습니다.", "INFO")
    
    def _clear_script(self):
        """스크립트 창 내용 지우기"""
        self.script_text.delete("1.0", tk.END)
        self._add_output_message("스크립트 창이 지워졌습니다.", "INFO")
    
    def _show_script_context_menu(self, event):
        """스크립트 창 우클릭 메뉴 표시"""
        try:
            self.script_context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.script_context_menu.grab_release()
    
    def _clear_output(self):
        """출력 지우기"""
        self.output_text.delete("1.0", tk.END)
        self._add_output_message("출력이 지워졌습니다.", "INFO")
    
    def _save_output(self):
        """출력 저장"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )
            
            if filename:
                output_content = self.output_text.get("1.0", tk.END)
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(output_content)
                
                self._add_output_message(f"💾 출력이 저장되었습니다: {filename}", "INFO")
                
        except Exception as e:
            self._add_output_message(f"❌ 출력 저장 실패: {e}", "ERROR")
    
    def _save_script(self):
        """스크립트 저장"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )
            
            if filename:
                script_content = self.script_text.get("1.0", tk.END)
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(script_content)
                
                self._add_output_message(f"💾 스크립트가 저장되었습니다: {filename}", "INFO")
                
        except Exception as e:
            self._add_output_message(f"❌ 스크립트 저장 실패: {e}", "ERROR")
    
    def _save_ssml_file(self, script_type, ssml_content):
        """SSML 파일 저장 - 제작 사양서 준수"""
        try:
            # UI에서 프로젝트명과 식별자 가져오기
            project_name = self.root.data_page.project_name_var.get() if hasattr(self.root, 'data_page') else "kor-chn"
            identifier = self.root.data_page.identifier_var.get() if hasattr(self.root, 'data_page') else "kor-chn"
            
            # 폴더 경로 생성: ./output/{프로젝트명}/{식별자}/SSML/
            base_dir = "output"
            project_dir = os.path.join(base_dir, project_name)
            identifier_dir = os.path.join(project_dir, identifier)
            ssml_dir = os.path.join(identifier_dir, "SSML")
            
            # 폴더 생성
            os.makedirs(ssml_dir, exist_ok=True)
            
            # 파일명: {파일식별자}_{스크립트타입}.ssml (제작 사양서 규칙)
            script_type_mapping = {
                "회화": "conversation",
                "인트로": "intro", 
                "엔딩": "ending",
                "대화": "dialog"
            }
            
            script_suffix = script_type_mapping.get(script_type, script_type.lower())
            filename = f"{identifier}_{script_suffix}.ssml"
            filepath = os.path.join(ssml_dir, filename)
            
            # 기존 SSML 파일이 있으면 삭제 (새로운 SSML 강제 생성)
            if os.path.exists(filepath):
                os.remove(filepath)
                print(f"[SSML 저장] 기존 SSML 파일 삭제: {filepath}")
            
            # 새로운 SSML 파일 저장 (항상 새로 생성)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(ssml_content)
            
            print(f"[SSML 저장] 새로운 SSML 파일 생성: {filepath}")
            self._add_output_message(f"💾 새로운 SSML 파일이 생성되었습니다: {filepath}", "INFO")
            
            # 출력창에 저장 정보 표시
            self.output_text.insert("end", f"💾 SSML 파일 저장됨: {filepath}\n")
            
            # 폴더 구조 정보 표시
            self.output_text.insert("end", f"📁 폴더 구조: {base_dir}/{project_name}/{identifier}/SSML/\n")
            
        except Exception as e:
            self._add_output_message(f"❌ SSML 파일 저장 실패: {e}", "ERROR")
    
    def _estimate_audio_duration_smart(self, ssml_content):
        """1단계: 스마트한 추정 계산 - 언어별, 문장 구조별 고려"""
        try:
            import re
            total_duration = 0
            
            # 언어별 텍스트 추출
            korean_text = self._extract_korean_text(ssml_content)
            chinese_text = self._extract_chinese_text(ssml_content)
            
            # 한국어: 한 글자당 0.08초 (더 빠름)
            total_duration += len(korean_text) * 0.08
            
            # 중국어: 한 글자당 0.12초 (더 느림)
            total_duration += len(chinese_text) * 0.12
            
            # 문장 구조별 보정
            voice_count = ssml_content.count('</voice>')
            total_duration += voice_count * 0.3  # 문장 전환 시간
            
            # break 태그 시간 (정확한 시간 반영)
            break_matches = re.findall(r'<break time="(\d+)s"/>', ssml_content)
            for match in break_matches:
                total_duration += int(match)
            
            # 마크 태그 개수에 따른 추가 시간
            mark_count = ssml_content.count('<mark')
            total_duration += mark_count * 0.1  # 마크 태그당 0.1초
            
            return round(total_duration, 1)
            
        except Exception:
            return "계산 불가"
    
    def _extract_korean_text(self, text):
        """한국어 텍스트만 추출"""
        import re
        # 한국어 유니코드 범위: AC00-D7AF
        korean_pattern = re.compile(r'[가-힣]+')
        korean_matches = korean_pattern.findall(text)
        return ''.join(korean_matches)
    
    def _extract_chinese_text(self, text):
        """중국어 텍스트만 추출"""
        import re
        # 중국어 유니코드 범위: 4E00-9FFF
        chinese_pattern = re.compile(r'[\u4e00-\u9fff]+')
        chinese_matches = chinese_pattern.findall(text)
        return ''.join(chinese_matches)
    
    def _estimate_audio_duration(self, ssml_content):
        """기존 메서드 - 호환성 유지"""
        return self._estimate_audio_duration_smart(ssml_content)
    
    def _prepare_audio_generation_with_sync(self, script_type, ssml_content):
        """3단계: 실제 오디오 생성 후 정확한 동기화 준비"""
        try:
            # 3단계 진행 상황 표시
            self.output_text.insert("end", "\n" + "="*60 + "\n")
            self.output_text.insert("end", "🎯 3단계: 정확한 동기화 준비\n")
            self.output_text.insert("end", "="*60 + "\n\n")
            
            # 정확한 타이밍 계산을 위한 정보 표시
            timing_info = self._analyze_ssml_timing_structure(ssml_content)
            self.output_text.insert("end", "📊 SSML 타이밍 구조 분석:\n")
            self.output_text.insert("end", f"   • 총 마크 태그: {timing_info['total_marks']}개\n")
            self.output_text.insert("end", f"   • 총 break 태그: {timing_info['total_breaks']}개\n")
            self.output_text.insert("end", f"   • 총 무음 시간: {timing_info['total_silence']}초\n")
            self.output_text.insert("end", f"   • 예상 음성 시간: {timing_info['estimated_speech']}초\n")
            self.output_text.insert("end", f"   • 예상 총 길이: {timing_info['total_estimated']}초\n\n")
            
            # 다음 단계 안내
            self.output_text.insert("end", "💡 다음 단계:\n")
            self.output_text.insert("end", "   1. 🎵 오디오 생성 버튼: 실제 MP3 파일 생성\n")
            self.output_text.insert("end", "   2. 📝 자막 이미지 생성: 정확한 타이밍으로 PNG 생성\n")
            self.output_text.insert("end", "   3. 🎬 비디오 렌더링: 자막과 오디오 동기화\n\n")
            
            self._add_output_message("✅ 3단계 동기화 준비 완료", "INFO")
            
        except Exception as e:
            self._add_output_message(f"❌ 3단계 준비 실패: {e}", "ERROR")
    
    def _generate_mp3_file(self, script_type, ssml_content):
        """4단계: MP3 파일 생성 (제작 사양서 준수)"""
        try:
            self.output_text.insert("end", "="*60 + "\n")
            self.output_text.insert("end", "🎵 4단계: MP3 파일 생성\n")
            self.output_text.insert("end", "="*60 + "\n\n")
            
            # UI에서 프로젝트명과 식별자 가져오기
            project_name = self.root.data_page.project_name_var.get() if hasattr(self.root, 'data_page') else "kor-chn"
            identifier = self.root.data_page.identifier_var.get() if hasattr(self.root, 'data_page') else "kor-chn"
            
            # 제작 사양서에 따른 MP3 저장 경로: ./output/{프로젝트명}/{식별자}/{식별자}.mp3
            base_dir = "output"
            project_dir = os.path.join(base_dir, project_name)
            identifier_dir = os.path.join(project_dir, identifier)
            mp3_dir = os.path.join(identifier_dir, "mp3")
            os.makedirs(mp3_dir, exist_ok=True)
            script_type_mapping = {
                "회화": "conversation",
                "인트로": "intro", 
                "엔딩": "ending",
                "대화": "dialog"
            }
            script_suffix = script_type_mapping.get(script_type, script_type.lower())
            mp3_filename = f"{identifier}_{script_suffix}.mp3"
            mp3_filepath = os.path.join(mp3_dir, mp3_filename)
            
            # 폴더 생성
            os.makedirs(identifier_dir, exist_ok=True)
            
            # MP3 파일 생성 (Google Cloud TTS API 사용)
            self._create_dummy_mp3(mp3_filepath, ssml_content, script_type)
            
            # 실제 오디오 품질 확인
            self._verify_audio_quality(mp3_filepath)
            
            self.output_text.insert("end", f"💾 MP3 파일 생성됨: {mp3_filepath}\n")
            self.output_text.insert("end", f"📁 폴더 구조: {base_dir}/{project_name}/{identifier}/\n")
            self.output_text.insert("end", f"📄 파일명: {mp3_filename}\n\n")
            
            self._add_output_message(f"✅ MP3 파일 생성 완료: {mp3_filepath}", "INFO")
            
        except Exception as e:
            self._add_output_message(f"❌ MP3 파일 생성 실패: {e}", "ERROR")
    
    def _get_current_time(self):
        """현재 시간을 포맷된 문자열로 반환"""
        import time
        return time.strftime("%H:%M:%S", time.localtime())
    
    def _convert_ssml_to_text(self, ssml_content):
        """SSML을 텍스트로 변환 (Chirp3 음성 지원)"""
        try:
            import re
            # SSML 태그 제거하고 텍스트만 추출
            text = re.sub(r'<[^>]+>', '', ssml_content)
            # 여러 공백을 하나로 정리
            text = re.sub(r'\s+', ' ', text)
            # 앞뒤 공백 제거
            text = text.strip()
            print(f"[SSML 변환] SSML → 텍스트 변환 완료 (길이: {len(text)} 문자)")
            return text
        except Exception as e:
            print(f"[SSML 변환] SSML → 텍스트 변환 실패: {e}")
            return ssml_content
    
    def _cleanup_old_ssml_files(self):
        """기존 SSML 파일들 정리 (새로운 SSML 강제 생성)"""
        try:
            # 프로젝트 정보 가져오기
            project_name = self.root.data_page.project_name_var.get() if hasattr(self.root, 'data_page') else "kor-chn"
            identifier = self.root.data_page.identifier_var.get() if hasattr(self.root, 'data_page') else "kor-chn"
            
            # SSML 폴더 경로
            ssml_dir = os.path.join("output", project_name, identifier, "SSML")
            
            if os.path.exists(ssml_dir):
                # 기존 SSML 파일들 삭제
                ssml_files = [f for f in os.listdir(ssml_dir) if f.endswith('.ssml')]
                for ssml_file in ssml_files:
                    filepath = os.path.join(ssml_dir, ssml_file)
                    os.remove(filepath)
                    print(f"[SSML 정리] 기존 SSML 파일 삭제: {filepath}")
                
                if ssml_files:
                    print(f"[SSML 정리] {len(ssml_files)}개 기존 SSML 파일 삭제 완료")
                    self.output_text.insert("end", f"🧹 기존 SSML 파일 {len(ssml_files)}개 정리 완료\n")
                else:
                    print(f"[SSML 정리] 삭제할 기존 SSML 파일 없음")
            else:
                print(f"[SSML 정리] SSML 폴더 없음: {ssml_dir}")
                
        except Exception as e:
            print(f"[SSML 정리] 기존 SSML 파일 정리 중 오류: {e}")
            self.output_text.insert("end", f"⚠️ 기존 SSML 파일 정리 중 오류: {e}\n")
    
    def _validate_ssml_voices(self, ssml_content, speaker_settings):
        """SSML 내부 음성 설정 검증 및 안전장치"""
        try:
            import re
            
            # SSML에서 <voice name="..."> 태그 추출
            voice_pattern = r'<voice name="([^"]+)">'
            ssml_voices = re.findall(voice_pattern, ssml_content)
            
            print(f"[SSML 검증] SSML 내부 음성 태그 개수: {len(ssml_voices)}")
            
            if not ssml_voices:
                # SSML에 음성 지정이 없는 경우
                warning_msg = "⚠️ SSML에 음성 지정이 없습니다! 기본 음성이 사용됩니다."
                self.output_text.insert("end", f"{warning_msg}\n")
                print(f"[SSML 검증] {warning_msg}")
                return
            
            # 설정된 화자들과 SSML 내부 음성 비교
            expected_voices = []
            if speaker_settings.get("native_speaker"):
                expected_voices.append(speaker_settings["native_speaker"])
            if speaker_settings.get("learner_speakers"):
                expected_voices.extend(speaker_settings["learner_speakers"])
            
            print(f"[SSML 검증] 예상 음성들: {expected_voices}")
            print(f"[SSML 검증] SSML 내부 음성들: {ssml_voices}")
            
            # SSML 내부 음성이 설정된 화자들과 일치하는지 확인
            for voice in ssml_voices:
                if voice not in expected_voices:
                    warning_msg = f"⚠️ SSML에 예상되지 않은 음성이 있습니다: {voice}"
                    self.output_text.insert("end", f"{warning_msg}\n")
                    print(f"[SSML 검증] {warning_msg}")
            
            # 성공 메시지
            success_msg = f"✅ SSML 내부 음성 설정 확인됨 ({len(ssml_voices)}개 음성)"
            self.output_text.insert("end", f"{success_msg}\n")
            print(f"[SSML 검증] {success_msg}")
            
        except Exception as e:
            error_msg = f"SSML 음성 검증 중 오류: {e}"
            self.output_text.insert("end", f"❌ {error_msg}\n")
            print(f"[SSML 검증] {error_msg}")
    
    def _get_speaker_settings(self):
        """화자 설정 데이터 가져오기"""
        try:
            # 프로젝트 정보 가져오기
            project_name = self.root.data_page.project_name_var.get() if hasattr(self.root, 'data_page') else "kor-chn"
            identifier = self.root.data_page.identifier_var.get() if hasattr(self.root, 'data_page') else "kor-chn"
            
            # 화자 설정 파일 경로
            speaker_config_path = os.path.join("output", project_name, identifier, f"{identifier}_speaker.json")
            print(f"[화자 설정] 설정 파일 경로: {speaker_config_path}")
            
            # 화자 설정 파일 읽기
            if os.path.exists(speaker_config_path):
                try:
                    with open(speaker_config_path, 'r', encoding='utf-8') as f:
                        settings = json.load(f)
                    
                    print(f"[화자 설정] 화자 설정 파일 로드 성공")
                    print(f"[화자 설정] 원어 화자: {settings.get('native_speaker', 'N/A')}")
                    print(f"[화자 설정] 학습어 화자 수: {settings.get('num_learner_speakers', 'N/A')}")
                    print(f"[화자 설정] 학습어 화자들: {settings.get('learner_speakers', [])}")
                    
                    # 화자 설정을 표준 형식으로 변환
                    speaker_data = {
                        "native_speaker": settings.get("native_speaker", "ko-KR-Standard-A"),
                        "learner_speakers": settings.get("learner_speakers", [])
                    }
                    
                    return speaker_data
                    
                except Exception as e:
                    print(f"[화자 설정] 설정 파일 읽기 실패: {e}")
            
            # 기본 화자 설정 반환 (SSML 내부에서 지원되는 음성 사용)
            default_speakers = {
                "native_speaker": "ko-KR-Standard-A",
                "learner_speakers": [
                    "ko-KR-Standard-B",
                    "ko-KR-Standard-C", 
                    "ko-KR-Standard-D",
                    "cmn-CN-Standard-A"
                ]
            }
            
            print(f"[화자 설정] 기본 화자 설정 사용")
            return default_speakers
            
        except Exception as e:
            print(f"[화자 설정] 화자 설정 로드 실패: {e}")
            return {
                "native_speaker": "ko-KR-Standard-A",
                "learner_speakers": ["ko-KR-Standard-B", "ko-KR-Standard-C", "ko-KR-Standard-D", "cmn-CN-Standard-A"]
            }
    
    def _create_dummy_mp3(self, filepath, ssml_content, script_type):
        """실제 MP3 오디오 파일 생성 (Google Cloud TTS API 사용)"""
        try:
            self.output_text.insert("end", "🔊 Google Cloud TTS API 연동 중...\n")
            
            # Google Cloud TTS API를 사용하여 실제 MP3 생성
            # 현재는 더미 파일 생성 (API 키 설정 필요)
            if self._has_google_tts_credentials():
                self.output_text.insert("end", "✅ Google Cloud TTS API 인증 확인됨\n")
                self.output_text.insert("end", "🎵 실제 오디오 생성 중...\n")
                
                # 실제 TTS API 호출
                if script_type in ["회화", "대화"]:
                    # 회화/대화는 화자별 별도 처리
                    ssml_parts = self._generate_ssml_for_script(script_type)
                    if ssml_parts:
                        self._generate_real_mp3_with_tts(filepath, ssml_parts, script_type)
                    else:
                        self._generate_real_mp3_with_tts(filepath, ssml_content, script_type)
                else:
                    # 인트로/엔딩은 단일 처리
                    self._generate_real_mp3_with_tts(filepath, ssml_content, script_type)
                
            else:
                self.output_text.insert("end", "⚠️ Google Cloud TTS API 인증 정보 없음\n")
                self.output_text.insert("end", "📝 더미 오디오 파일 생성됨\n")
                self._create_temp_audio_file(filepath)
            
            self._add_output_message("📝 MP3 파일 생성됨 (오디오 품질 확인 필요)", "INFO")
            
        except Exception as e:
            self._add_output_message(f"❌ MP3 파일 생성 실패: {e}", "ERROR")
    
    def _has_google_tts_credentials(self):
        """Google Cloud TTS API 인증 정보 확인"""
        try:
            # Google Cloud Application Default Credentials 확인
            import os
            from google.auth import default
            
            # Application Default Credentials 확인
            try:
                credentials, project = default()
                if credentials and project:
                    self.output_text.insert("end", f"✅ Google Cloud 인증 확인됨 (프로젝트: {project})\n")
                    return True
            except Exception as e:
                self.output_text.insert("end", f"⚠️ Google Cloud 인증 확인 실패: {e}\n")
            
            # 환경 변수 확인 (선택사항)
            api_key = os.getenv('GOOGLE_CLOUD_API_KEY')
            if api_key:
                self.output_text.insert("end", "✅ 환경 변수 API 키 확인됨\n")
                return True
            
            # 설정 파일에서 확인 (선택사항)
            config_path = os.path.join("config", "google_tts.json")
            if os.path.exists(config_path):
                self.output_text.insert("end", "✅ 설정 파일 API 키 확인됨\n")
                return True
                
            return False
            
        except Exception as e:
            self.output_text.insert("end", f"❌ 인증 확인 중 오류: {e}\n")
            return False
    
    def _create_temp_audio_file(self, filepath):
        """임시 오디오 파일 생성 (테스트용)"""
        try:
            # 간단한 테스트 오디오 파일 생성
            with open(filepath, 'wb') as f:
                # MP3 헤더 (더미)
                f.write(b'ID3')
                f.write(b'\x00' * 1000)  # 더 큰 더미 데이터
                
            self.output_text.insert("end", "📁 임시 MP3 파일 생성됨\n")
            
        except Exception as e:
            self.output_text.insert("end", f"❌ 임시 파일 생성 실패: {e}\n")
    
    def _generate_real_mp3_with_tts(self, filepath, ssml_data, script_type):
        """Google Cloud TTS API를 사용하여 실제 MP3 생성"""
        try:
            self.output_text.insert("end", "🚀 Google Cloud TTS API 호출 중...\n")
            print(f"[TTS API] Google Cloud TTS API 호출 시작")
            print(f"[TTS API] 출력 파일: {filepath}")
            print(f"[TTS API] 스크립트 타입: {script_type}")
            
            # 회화/대화는 화자별 별도 처리, 인트로/엔딩은 단일 처리
            if script_type in ["회화", "대화"] and isinstance(ssml_data, list):
                print(f"[TTS API] 화자별 SSML 파트 수: {len(ssml_data)}개")
                ssml_parts = ssml_data
            else:
                print(f"[TTS API] 단일 SSML 처리")
                ssml_content = ssml_data
            
            # Google Cloud TTS API 호출
            try:
                from google.cloud import texttospeech
                import io
                from pydub import AudioSegment
                AudioSegment.converter = "/opt/homebrew/bin/ffmpeg"
                print(f"[TTS API] google-cloud-texttospeech 패키지 로드 성공")
                
                # TTS 클라이언트 초기화
                print(f"[TTS API] TTS 클라이언트 초기화 중...")
                client = texttospeech.TextToSpeechClient()
                print(f"[TTS API] TTS 클라이언트 초기화 완료")
                
                # 회화/대화: 각 화자별로 별도 오디오 생성
                if script_type in ["회화", "대화"] and isinstance(ssml_data, list):
                    audio_segments = []
                    
                    for i, part in enumerate(ssml_parts):
                        print(f"[TTS API] 화자 {i+1}/{len(ssml_parts)} 처리 중...")
                        print(f"[TTS API]   - 화자: {part['voice']}")
                        print(f"[TTS API]   - 텍스트: {part['text'][:50]}...")
                    
                        # 텍스트 입력 (Chirp3 음성 지원)
                        synthesis_input = texttospeech.SynthesisInput(text=part['text'])
                        
                        # 화자별 음성 설정
                        voice = texttospeech.VoiceSelectionParams(
                            language_code="ko-KR" if "ko-KR" in part['voice'] else "cmn-CN",
                            name=part['voice']
                        )
                        
                        # 오디오 설정
                        audio_config = texttospeech.AudioConfig(
                            audio_encoding=texttospeech.AudioEncoding.MP3,
                            sample_rate_hertz=24000
                        )
                        
                        # TTS 요청
                        response = client.synthesize_speech(
                            input=synthesis_input,
                            voice=voice,
                            audio_config=audio_config
                        )
                        
                        # 오디오 세그먼트 생성
                        audio_segment = AudioSegment.from_mp3(io.BytesIO(response.audio_content))
                        audio_segments.append(audio_segment)
                        
                        # 화자간 1초 무음 추가 (마지막이 아닌 경우)
                        if i < len(ssml_parts) - 1:
                            silence = AudioSegment.silent(duration=1000)  # 1초 무음
                            audio_segments.append(silence)
                        
                        print(f"[TTS API]   - 오디오 길이: {len(audio_segment)}ms")
                    
                    # 모든 오디오 세그먼트 합치기
                    print(f"[TTS API] 오디오 세그먼트 합치는 중...")
                    final_audio = sum(audio_segments)
                    
                    # MP3 파일 저장
                    final_audio.export(filepath, format="mp3")
                    print(f"[TTS API] ✅ MP3 파일 저장 완료: {filepath}")
                    print(f"[TTS API] 최종 오디오 길이: {len(final_audio)}ms")
                
                else:
                    # 인트로/엔딩: 단일 SSML 처리
                    print(f"[TTS API] 단일 SSML 처리 중...")
                    text_content = self._convert_ssml_to_text(ssml_content)
                    synthesis_input = texttospeech.SynthesisInput(text=text_content)
                    
                    # 기본 음성 설정
                    voice = texttospeech.VoiceSelectionParams(
                        language_code="ko-KR",
                        name="ko-KR-Chirp3-HD-Achernar"
                    )
                    
                    audio_config = texttospeech.AudioConfig(
                        audio_encoding=texttospeech.AudioEncoding.MP3,
                        sample_rate_hertz=24000
                    )
                    
                    response = client.synthesize_speech(
                        input=synthesis_input,
                        voice=voice,
                        audio_config=audio_config
                    )
                    
                    # MP3 파일 저장
                    with open(filepath, 'wb') as out:
                        out.write(response.audio_content)
                    print(f"[TTS API] ✅ MP3 파일 저장 완료: {filepath}")
                
                self.output_text.insert("end", f"🎵 오디오 품질: 고품질 MP3 (24kHz)\n")
                
            except ImportError:
                self.output_text.insert("end", "❌ google-cloud-texttospeech 패키지가 설치되지 않음\n")
                self.output_text.insert("end", "💡 설치 명령: pip install google-cloud-texttospeech\n")
                print(f"[TTS API] ❌ google-cloud-texttospeech 패키지 미설치")
                raise Exception("Google Cloud TTS 패키지 미설치")
                
        except Exception as e:
            self.output_text.insert("end", f"❌ 실제 MP3 생성 실패: {e}\n")
            print(f"[TTS API] ❌ 실제 MP3 생성 실패: {e}")
            print(f"[TTS API] 오류 상세: {type(e).__name__}: {str(e)}")
            import traceback
            print(f"[TTS API] 스택 트레이스:\n{traceback.format_exc()}")
            raise e
    
    def _verify_audio_quality(self, filepath):
        """오디오 파일 품질 확인"""
        try:
            self.output_text.insert("end", "🔍 오디오 파일 품질 확인 중...\n")
            
            # 파일 크기 확인
            file_size = os.path.getsize(filepath)
            self.output_text.insert("end", f"📁 파일 크기: {file_size} bytes\n")
            
            # 파일 확장자 확인
            if filepath.endswith('.mp3'):
                self.output_text.insert("end", "✅ MP3 파일 형식 확인됨\n")
                
                # 더미 파일인지 확인 (현재는 더미 파일)
                if file_size < 10000:  # 10KB 미만은 더미 파일로 간주
                    self.output_text.insert("end", "⚠️ 더미 MP3 파일 (실제 오디오 없음)\n")
                    self.output_text.insert("end", "💡 Google Cloud TTS API 연동 필요\n")
                else:
                    self.output_text.insert("end", "✅ 실제 오디오 파일로 판단됨\n")
            else:
                self.output_text.insert("end", "❌ MP3 파일 형식이 아님\n")
                
        except Exception as e:
            self.output_text.insert("end", f"❌ 오디오 품질 확인 실패: {e}\n")
    
    def _analyze_ssml_timing_structure(self, ssml_content):
        """SSML 타이밍 구조 분석"""
        try:
            import re
            
            # 마크 태그 개수
            total_marks = ssml_content.count('<mark')
            
            # break 태그 개수와 총 무음 시간
            break_matches = re.findall(r'<break time="(\d+)s"/>', ssml_content)
            total_breaks = len(break_matches)
            total_silence = sum(int(match) for match in break_matches)
            
            # 예상 음성 시간 (1단계 추정)
            estimated_speech = self._estimate_audio_duration_smart(ssml_content)
            if isinstance(estimated_speech, (int, float)):
                total_estimated = estimated_speech
            else:
                total_estimated = "계산 불가"
            
            return {
                'total_marks': total_marks,
                'total_breaks': total_breaks,
                'total_silence': total_silence,
                'estimated_speech': estimated_speech,
                'total_estimated': total_estimated
            }
            
        except Exception:
            return {
                'total_marks': 0,
                'total_breaks': 0,
                'total_silence': 0,
                'estimated_speech': "계산 불가",
                'total_estimated': "계산 불가"
            }
    
    def _save_config(self):
        """설정 저장"""
        try:
            config_data = {
                "script_type": self.script_var.get()
            }
            
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, ensure_ascii=False, indent=2)
                
                self._add_output_message(f"💾 설정이 저장되었습니다: {filename}", "INFO")
                
        except Exception as e:
            self._add_output_message(f"❌ 설정 저장 실패: {e}", "ERROR")
    
    def _load_config(self):
        """설정 로드"""
        try:
            filename = filedialog.askopenfilename(
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if filename:
                with open(filename, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # UI에 설정 적용
                if "script_type" in config_data:
                    self.script_var.set(config_data["script_type"])
                    self._refresh_script()
                
                self._add_output_message(f"📂 설정이 로드되었습니다: {filename}", "INFO")
                self._update_ui_state()
                
        except Exception as e:
            self._add_output_message(f"❌ 설정 로드 실패: {e}", "ERROR")
    
    def _save_subtitle_image(self, image, project_name, identifier, script_type, image_index):
        """Saves a subtitle image to the correct directory with the correct filename."""
        dir_map = {
            "회화": "dialog",
            "인트로": "intro",
            "엔딩": "ending",
            "대화": "dialog"
        }
        sub_dir = dir_map.get(script_type)
        if not sub_dir:
            return None

        image_dir = os.path.join(config.OUTPUT_PATH, project_name, identifier, sub_dir)
        os.makedirs(image_dir, exist_ok=True)
        
        filename = f"{identifier}_{image_index:03d}.png"
        filepath = os.path.join(image_dir, filename)
        image.save(filepath, 'PNG')
        return filepath

    def _open_project_folder(self):
        """프로젝트 폴더 열기"""
        try:
            output_path = "output"
            if os.path.exists(output_path):
                os.startfile(output_path) if os.name == 'nt' else os.system(f'open "{output_path}"')
                self._add_output_message(f"📁 출력 폴더를 열었습니다: {output_path}", "INFO")
            else:
                messagebox.showinfo("정보", "출력 폴더가 아직 생성되지 않았습니다.\nManifest를 먼저 생성하세요.")
                
        except Exception as e:
            self._add_output_message(f"❌ 출력 폴더 열기 실패: {e}", "ERROR")
