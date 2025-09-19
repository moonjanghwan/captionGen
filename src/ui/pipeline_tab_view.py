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
from src.ui.ui_utils import create_labeled_widget

# 파이프라인 모듈 import
# SubtitleGenerator는 삭제됨 - PNGRenderer 사용
PIPELINE_AVAILABLE = True

from src.pipeline.ffmpeg.pipeline_manager import PipelineManager

class PipelineTabView(ctk.CTkFrame):
    """파이프라인 실행 탭 뷰"""
    
    def __init__(self, parent, root=None):
        super().__init__(parent, fg_color="transparent")
        self.root = root
        self.pipeline_manager = PipelineManager(root)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)
        
        self.grid_rowconfigure(1, minsize=300)
        self.grid_rowconfigure(2, minsize=300)
        
        self._create_project_settings_section()
        self._create_script_section()
        self._create_output_section()
        self._create_pipeline_controls_section()
        self._create_context_menu()
        self._setup_csv_editing() # Call the new method
        
        self._update_ui_state()
        self.after(100, self._refresh_script)

    def _create_context_menu(self):
        """컨텍스트 메뉴 생성"""
        # Textbox context menu - 기본 기능 사용
        self.text_context_menu = tk.Menu(self, tearoff=0)
        self.text_context_menu.add_command(label="Copy", command=lambda: self.focus_get().event_generate("<<Copy>>"))
        self.text_context_menu.add_command(label="Cut", command=lambda: self.focus_get().event_generate("<<Cut>>"))
        self.text_context_menu.add_command(label="Paste", command=lambda: self.focus_get().event_generate("<<Paste>>"))
        self.text_context_menu.add_command(label="Select All", command=lambda: self.focus_get().tag_add("sel", "1.0", "end"))

        # Treeview context menu
        self.csv_context_menu = tk.Menu(self, tearoff=0)
        self.csv_context_menu.add_command(label="Copy Cell", command=self._copy_csv_cell)
        self.csv_context_menu.add_command(label="Paste Cell", command=self._paste_csv_cell)
        self.csv_context_menu.add_command(label="Delete Row(s)", command=self._delete_csv_rows)

    def _show_context_menu(self, event):
        """컨텍스트 메뉴 표시"""
        if event.widget == self.script_text:
            self.text_context_menu.post(event.x_root, event.y_root)
        elif event.widget == self.output_text:
            self.text_context_menu.post(event.x_root, event.y_root)
        elif event.widget == self.csv_tree:
            self.csv_context_menu.post(event.x_root, event.y_root)

    def _copy_to_clipboard(self):
        try:
            widget = self.focus_get()
            if hasattr(widget, 'get'):
                # CustomTkinter Textbox의 경우
                if hasattr(widget, 'get'):
                    selected_text = widget.get("sel.first", "sel.last")
                    if selected_text:
                        self.clipboard_clear()
                        self.clipboard_append(selected_text)
                else:
                    widget.event_generate("<<Copy>>")
        except Exception as e:
            print(f"복사 실패: {e}")

    def _cut_to_clipboard(self):
        try:
            widget = self.focus_get()
            if hasattr(widget, 'get'):
                # CustomTkinter Textbox의 경우
                if hasattr(widget, 'get'):
                    selected_text = widget.get("sel.first", "sel.last")
                    if selected_text:
                        self.clipboard_clear()
                        self.clipboard_append(selected_text)
                        widget.delete("sel.first", "sel.last")
                else:
                    widget.event_generate("<<Cut>>")
        except Exception as e:
            print(f"잘라내기 실패: {e}")

    def _paste_from_clipboard(self):
        try:
            widget = self.focus_get()
            if hasattr(widget, 'insert'):
                # CustomTkinter Textbox의 경우
                clipboard_content = self.clipboard_get()
                if clipboard_content:
                    widget.insert("insert", clipboard_content)
            else:
                widget.event_generate("<<Paste>>")
        except Exception as e:
            print(f"붙여넣기 실패: {e}")
    
    def _select_all(self):
        try:
            widget = self.focus_get()
            if hasattr(widget, 'tag_add'):
                widget.tag_add("sel", "1.0", "end")
            elif hasattr(widget, 'select_range'):
                widget.select_range(0, tk.END)
        except Exception as e:
            print(f"전체 선택 실패: {e}")
    
    # CustomTkinter Textbox 전용 메서드들
    def _copy_text(self, text_widget):
        """CustomTkinter Textbox에서 텍스트 복사"""
        try:
            selected_text = text_widget.get("sel.first", "sel.last")
            if selected_text:
                self.clipboard_clear()
                self.clipboard_append(selected_text)
                print(f"복사됨: {selected_text[:50]}...")
        except Exception as e:
            print(f"복사 실패: {e}")
    
    def _paste_text(self, text_widget):
        """CustomTkinter Textbox에 텍스트 붙여넣기"""
        try:
            clipboard_content = self.clipboard_get()
            if clipboard_content:
                text_widget.insert("insert", clipboard_content)
                print(f"붙여넣기됨: {clipboard_content[:50]}...")
        except Exception as e:
            print(f"붙여넣기 실패: {e}")
    
    def _cut_text(self, text_widget):
        """CustomTkinter Textbox에서 텍스트 잘라내기"""
        try:
            selected_text = text_widget.get("sel.first", "sel.last")
            if selected_text:
                self.clipboard_clear()
                self.clipboard_append(selected_text)
                text_widget.delete("sel.first", "sel.last")
                print(f"잘라내기됨: {selected_text[:50]}...")
        except Exception as e:
            print(f"잘라내기 실패: {e}")
    
    def _select_all_text(self, text_widget):
        """CustomTkinter Textbox에서 전체 텍스트 선택"""
        try:
            text_widget.tag_add("sel", "1.0", "end")
            print("전체 텍스트 선택됨")
        except Exception as e:
            print(f"전체 선택 실패: {e}")
    
    # 컨텍스트 메뉴용 메서드들
    def _context_copy(self):
        """컨텍스트 메뉴에서 복사"""
        widget = self.focus_get()
        if widget == self.script_text:
            self._copy_text(self.script_text)
        elif widget == self.output_text:
            self._copy_text(self.output_text)
    
    def _context_cut(self):
        """컨텍스트 메뉴에서 잘라내기"""
        widget = self.focus_get()
        if widget == self.script_text:
            self._cut_text(self.script_text)
        elif widget == self.output_text:
            self._cut_text(self.output_text)
    
    def _context_paste(self):
        """컨텍스트 메뉴에서 붙여넣기"""
        widget = self.focus_get()
        if widget == self.script_text:
            self._paste_text(self.script_text)
        elif widget == self.output_text:
            self._paste_text(self.output_text)
    
    def _context_select_all(self):
        """컨텍스트 메뉴에서 전체 선택"""
        widget = self.focus_get()
        if widget == self.script_text:
            self._select_all_text(self.script_text)
        elif widget == self.output_text:
            self._select_all_text(self.output_text)
    
    # 키보드 이벤트 핸들러들
    def _on_copy_key(self, event):
        """Ctrl+C 키 이벤트 핸들러"""
        print("🔍 Ctrl+C 키 감지됨!")
        widget = event.widget
        if widget == self.script_text:
            self._copy_text(self.script_text)
        elif widget == self.output_text:
            self._copy_text(self.output_text)
        return "break"  # 기본 이벤트 방지
    
    def _on_paste_key(self, event):
        """Ctrl+V 키 이벤트 핸들러"""
        print("🔍 Ctrl+V 키 감지됨!")
        widget = event.widget
        if widget == self.script_text:
            self._paste_text(self.script_text)
        elif widget == self.output_text:
            self._paste_text(self.output_text)
        return "break"  # 기본 이벤트 방지
    
    def _on_cut_key(self, event):
        """Ctrl+X 키 이벤트 핸들러"""
        print("🔍 Ctrl+X 키 감지됨!")
        widget = event.widget
        if widget == self.script_text:
            self._cut_text(self.script_text)
        elif widget == self.output_text:
            self._cut_text(self.output_text)
        return "break"  # 기본 이벤트 방지
    
    def _on_select_all_key(self, event):
        """Ctrl+A 키 이벤트 핸들러"""
        print("🔍 Ctrl+A 키 감지됨!")
        widget = event.widget
        if widget == self.script_text:
            self._select_all_text(self.script_text)
        elif widget == self.output_text:
            self._select_all_text(self.output_text)
        return "break"  # 기본 이벤트 방지
    
    def _copy_csv_cell(self):
        """CSV Treeview에서 선택된 셀의 내용을 클립보드에 복사"""
        item_id = self.csv_tree.focus()
        if not item_id:
            return
        
        column_id = self.csv_tree.identify_column(self.csv_tree.winfo_pointerx() - self.csv_tree.winfo_rootx())
        if not column_id:
            return
        
        column_index = int(column_id[1:]) - 1
        current_values = list(self.csv_tree.item(item_id, 'values'))
        
        if 0 <= column_index < len(current_values):
            cell_content = current_values[column_index]
            self.clipboard_clear()
            self.clipboard_append(cell_content)
            self._add_output_message(f"클립보드에 '{cell_content}' 복사됨", "INFO")

    def _paste_csv_cell(self):
        """클립보드 내용을 CSV Treeview의 선택된 셀에 붙여넣기"""
        item_id = self.csv_tree.focus()
        if not item_id:
            return
        
        column_id = self.csv_tree.identify_column(self.csv_tree.winfo_pointerx() - self.csv_tree.winfo_rootx())
        if not column_id:
            return
        
        column_index = int(column_id[1:]) - 1
        
        # '순번' 컬럼은 편집 불가
        if column_index == 0:
            self._add_output_message("순번 컬럼은 편집할 수 없습니다.", "WARNING")
            return

        try:
            clipboard_content = self.clipboard_get()
            current_values = list(self.csv_tree.item(item_id, 'values'))
            
            if 0 <= column_index < len(current_values):
                current_values[column_index] = clipboard_content
                self.csv_tree.item(item_id, values=current_values)
                self._add_output_message(f"셀에 '{clipboard_content}' 붙여넣기 완료", "INFO")
        except tk.TclError:
            self._add_output_message("클립보드에 내용이 없습니다.", "WARNING")
        except Exception as e:
            self._add_output_message(f"셀 붙여넣기 실패: {e}", "ERROR")

    def _delete_csv_rows(self):
        """CSV Treeview에서 선택된 행 삭제"""
        selected_items = self.csv_tree.selection()
        if not selected_items:
            self._add_output_message("삭제할 행을 선택해주세요.", "WARNING")
            return
        
        if messagebox.askyesno("행 삭제", f"{len(selected_items)}개의 행을 삭제하시겠습니까?"):
            for item_id in selected_items:
                self.csv_tree.delete(item_id)
            self._add_output_message(f"{len(selected_items)}개의 행 삭제 완료", "INFO")
    
    def _setup_csv_editing(self):
        """CSV Treeview의 인라인 편집 기능 설정"""
        def set_cell_value(event):
            item_id = self.csv_tree.focus()
            if not item_id:
                return

            column_id = self.csv_tree.identify_column(event.x)
            if not column_id:
                return

            # Get column index (e.g., #1, #2, #3, #4)
            column_index = int(column_id[1:]) - 1 
            
            # Only allow editing for '원어', '학습어', '읽기' (columns 1, 2, 3)
            if column_index == 0: # '순번' column
                return

            # Get current value
            current_values = list(self.csv_tree.item(item_id, 'values'))
            current_text = current_values[column_index]

            # Get dimensions for the entry widget
            x, y, width, height = self.csv_tree.bbox(item_id, column_id)

            # Create a temporary Entry widget with width and height
            entry_editor = ctk.CTkEntry(self.csv_tree, width=width, height=height)
            entry_editor.insert(0, current_text)
            entry_editor.focus_force()

            def on_edit_end(event=None):
                new_text = entry_editor.get()
                current_values[column_index] = new_text
                self.csv_tree.item(item_id, values=current_values)
                entry_editor.destroy()

            entry_editor.bind("<Return>", on_edit_end) # Enter key
            entry_editor.bind("<FocusOut>", on_edit_end) # Click outside

            # Position the entry widget
            x, y, width, height = self.csv_tree.bbox(item_id, column_id)
            entry_editor.place(x=x, y=y)

        self.csv_tree.bind("<Double-1>", set_cell_value)
    
    def _create_project_settings_section(self):
        """프로젝트 설정 섹션 생성"""
        settings_frame = ctk.CTkFrame(self, fg_color=config.COLOR_THEME["widget"])
        settings_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        
        script_tab_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        script_tab_frame.pack(fill="x", padx=20, pady=5)
        
        self.script_var = tk.StringVar(value="회화")
        
        widget_params = {
            "values": ["회화", "인트로", "엔딩", "대화"],
            "variable": self.script_var,
            "command": self._on_script_change,
            "fg_color": config.COLOR_THEME["button"],
            "button_color": config.COLOR_THEME["button_hover"],
            "text_color": config.COLOR_THEME["text"],
        }
        
        frame, self.script_combo = create_labeled_widget(
            script_tab_frame, 
            "생성할 스크립트", 
            12, # 글자 수 기반 너비
            "combo", 
            widget_params
        )
        frame.pack(side="left", padx=(0, 10))

        # 데이터 저장/읽기 버튼 추가
        save_button = ctk.CTkButton(
            script_tab_frame,
            text="데이터 저장",
            command=self._save_script_data,
            fg_color=config.COLOR_THEME["button"],
            hover_color=config.COLOR_THEME["button_hover"],
            width=100, height=30
        )
        save_button.pack(side="left", padx=(0, 10))

        load_button = ctk.CTkButton(
            script_tab_frame,
            text="데이터 읽기",
            command=self._load_script_data,
            fg_color=config.COLOR_THEME["button"],
            hover_color=config.COLOR_THEME["button_hover"],
            width=100, height=30
        )
        load_button.pack(side="left", padx=(0, 10))
    
    def _create_pipeline_controls_section(self):
        """파이프라인 제어 섹션 생성"""
        controls_frame = ctk.CTkFrame(self, fg_color=config.COLOR_THEME["widget"])
        controls_frame.grid(row=4, column=0, padx=10, pady=5, sticky="ew")
        
        button_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        button_frame.pack(pady=15)
        
        buttons = {
            "📋 Manifest 생성": (self._create_manifest, "#3498DB", "#2980B9"),
            "🎵 오디오 생성": (self._create_audio, "#3498DB", "#2980B9"),
            "📝 자막 이미지 생성": (self._create_subtitles, "#3498DB", "#2980B9"),
            "⏰ 타임라인 생성": (self._create_timeline, "#3498DB", "#2980B9"),
            "🎬 비디오 렌더링": (self._render_video, "#3498DB", "#2980B9"),
            "⚡ 타이밍 기반 렌더링": (self._timing_based_render, "#E74C3C", "#C0392B"),
            "🔗 최종 병합": (self._merge_final_video, "#3498DB", "#2980B9"),
            "🚀 자동 생성": (self._auto_generation, "#3498DB", "#2980B9")
        }

        for text, (command, fg_color, hover_color) in buttons.items():
            button = ctk.CTkButton(
                button_frame, text=text, command=command,
                fg_color=fg_color, hover_color=hover_color,
                width=150, height=40
            )
            button.pack(side="left", padx=(0, 10))
            if text == "📋 Manifest 생성": self.manifest_button = button

    def _create_script_section(self):
        """스크립트 섹션 생성"""
        script_frame = ctk.CTkFrame(self, fg_color=config.COLOR_THEME["widget"])
        script_frame.grid(row=1, column=0, padx=10, pady=(5, 2), sticky="nsew")
        script_frame.grid_rowconfigure(0, weight=1)
        
        self.script_display_frame = ctk.CTkFrame(script_frame, fg_color="transparent")
        self.script_display_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.script_display_frame.grid_columnconfigure(0, weight=1)
        self.script_display_frame.grid_rowconfigure(0, weight=1)

        self.script_text = ctk.CTkTextbox(self.script_display_frame, font=ctk.CTkFont(size=11))
        self.script_text.grid(row=0, column=0, sticky="nsew")
        self.script_text.bind("<Button-3>", self._show_context_menu)
        
        # CustomTkinter Textbox는 기본적으로 복사/붙여넣기가 작동해야 함
        # 추가 바인딩 없이 기본 기능 사용
        
        self.csv_tree = ttk.Treeview(self.script_display_frame, columns=("순번", "원어", "학습어", "읽기"), show="headings")
        for col in ("순번", "원어", "학습어", "읽기"): self.csv_tree.heading(col, text=col)
        self.csv_tree.column("순번", width=50, minwidth=50, stretch=False, anchor="center")
        for col in ("원어", "학습어", "읽기"): self.csv_tree.column(col, width=200, stretch=True, anchor="w")
        
        self.csv_scroll_y = ttk.Scrollbar(self.script_display_frame, orient="vertical", command=self.csv_tree.yview)
        self.csv_tree.configure(yscrollcommand=self.csv_scroll_y.set)
        
        self.csv_tree.grid_remove()
        self.csv_scroll_y.grid_remove()

    def _create_output_section(self):
        """출력 섹션 생성"""
        output_frame = ctk.CTkFrame(self, fg_color=config.COLOR_THEME["widget"])
        output_frame.grid(row=2, column=0, padx=10, pady=(2, 2), sticky="nsew")
        output_frame.grid_rowconfigure(0, weight=1)
        
        self.output_text = ctk.CTkTextbox(output_frame, font=ctk.CTkFont(size=11))
        self.output_text.pack(fill="both", expand=True, padx=10, pady=10)
        self.output_text.bind("<Button-3>", self._show_context_menu)
        
        # 테스트용 텍스트 추가
        self.output_text.insert("1.0", "테스트 텍스트입니다. 이 텍스트를 선택하고 Ctrl+C를 눌러보세요.\n")
        self.output_text.insert("end", "또는 Ctrl+A로 전체 선택해보세요.\n")
        self.output_text.insert("end", "우클릭 메뉴도 테스트해보세요.\n")
        
        # CustomTkinter Textbox는 기본적으로 복사/붙여넣기가 작동해야 함
        # 추가 바인딩 없이 기본 기능 사용
        
        # Context menu setup can be added here if needed

    def _update_ui_state(self):
        """UI 상태 업데이트"""
        if not PIPELINE_AVAILABLE:
            self.manifest_button.configure(state="disabled", text="⚠️ 파이프라인 모듈 없음")
            self._add_output_message("❌ 파이프라인 모듈을 찾을 수 없습니다.", "ERROR")
            return
        
        state = "normal" if self.script_var.get() else "disabled"
        text = "📋 Manifest 생성" if state == "normal" else "스크립트를 선택하세요"
        self.manifest_button.configure(state=state, text=text)
    
    def _get_current_script_data_from_ui(self, script_type: str) -> Optional[Any]:
        """현재 UI에 표시된 스크립트 데이터를 추출합니다."""
        print(f"🔍 UI 데이터 추출 시작 - script_type: {script_type}")
        
        # 프로젝트명과 식별자 가져오기
        project_name = "kor-chn"  # 기본값
        identifier = "kor-chn"    # 기본값
        
        print(f"🔍 self.root 존재 여부: {hasattr(self, 'root')}")
        if hasattr(self, 'root'):
            print(f"🔍 self.root.data_page 존재 여부: {hasattr(self.root, 'data_page')}")
            if hasattr(self.root, 'data_page'):
                project_name = self.root.data_page.project_name_var.get() or "kor-chn"
                identifier = self.root.data_page.identifier_var.get() or project_name
                print(f"✅ 프로젝트명: {project_name}, 식별자: {identifier}")
            else:
                print(f"❌ self.root.data_page가 없습니다.")
        else:
            print(f"❌ self.root가 없습니다.")
        
        if script_type in ["회화", "대화"]:
            scenes = []
            print(f"🔍 회화 데이터 추출 시작...")
            
            if hasattr(self, 'root') and hasattr(self.root, 'data_page'):
                print(f"✅ UI 데이터 페이지 접근 성공")
                csv_tree = self.root.data_page.csv_tree
                children = csv_tree.get_children()
                print(f"🔍 CSV 트리 자식 개수: {len(children)}")
                
                for i, item_id in enumerate(children):
                    values = csv_tree.item(item_id, 'values')
                    print(f"  - item {i}: {values}")
                    # Ensure values has enough elements, pad with empty strings if necessary
                    padded_values = (list(values) + [''] * 4)[:4] 
                    scenes.append({
                        "order": padded_values[0],
                        "native_script": padded_values[1],
                        "learning_script": padded_values[2],
                        "reading_script": padded_values[3]
                    })
                    print(f"    ✅ 회화 데이터 추가: {padded_values[1]}")
                
                print(f"🔍 최종 추출된 scenes 개수: {len(scenes)}")
                
                # CSV 트리에 데이터가 없으면 테스트용 샘플 데이터 추가
                if len(scenes) == 0:
                    print(f"⚠️ CSV 트리에 데이터가 없습니다. 테스트용 샘플 데이터를 추가합니다.")
                    scenes = [
                        {
                            "order": "1",
                            "native_script": "안녕하세요!",
                            "learning_script": "你好！",
                            "reading_script": "니 하오!"
                        },
                        {
                            "order": "2",
                            "native_script": "감사합니다.",
                            "learning_script": "谢谢。",
                            "reading_script": "씨에 씨에"
                        },
                        {
                            "order": "3",
                            "native_script": "이거 얼마예요?",
                            "learning_script": "这个多少钱？",
                            "reading_script": "쩌거 뚜오샤오 치엔?"
                        },
                        {
                            "order": "4",
                            "native_script": "죄송합니다 / 실례합니다.",
                            "learning_script": "对不起 / 不好意思。",
                            "reading_script": "뙤이부치 / 뿌 하오 이쓰"
                        },
                        {
                            "order": "5",
                            "native_script": "안녕히 계세요.",
                            "learning_script": "再见。",
                            "reading_script": "짜이찌엔"
                        }
                    ]
                    print(f"✅ 테스트용 샘플 데이터 {len(scenes)}개 추가 완료")
            else:
                print(f"❌ UI 데이터 페이지에 접근할 수 없습니다.")
            
            return {
                "project_name": project_name,
                "identifier": identifier,
                "scenes": scenes
            }
        elif script_type in ["인트로", "엔딩"]:
            script_text = self.script_text.get("1.0", tk.END).strip()
            return {
                "project_name": project_name,
                "identifier": identifier,
                "script_text": script_text
            }
        return None

    def _create_manifest(self):
        """timeline_manifest.json 생성"""
        try:
            script_type = self.script_var.get()
            current_script_data = self._get_current_script_data_from_ui(script_type)

            if current_script_data is None:
                self._add_output_message(f"'{script_type}' 스크립트 데이터를 UI에서 가져올 수 없습니다.", "ERROR")
                messagebox.showerror("오류", f"'{script_type}' 스크립트 데이터를 가져올 수 없습니다.")
                return

            manifest_data, filepath = self.pipeline_manager.create_manifest(script_type, current_script_data)
            
            # 출력 창에 상세 정보 표시
            self.output_text.delete("1.0", tk.END)
            self.output_text.insert("end", f"📋 Manifest 생성 완료!\n\n")
            self.output_text.insert("end", "=== 저장 정보 ===\n")
            self.output_text.insert("end", f"📁 저장 디렉토리: {os.path.dirname(filepath)}\n")
            self.output_text.insert("end", f"📄 파일명: {os.path.basename(filepath)}\n")
            self.output_text.insert("end", f"💾 전체 경로: {filepath}\n")
            self.output_text.insert("end", f"🏷️ 프로젝트명: {manifest_data.get('project_name', 'N/A')}\n")
            self.output_text.insert("end", f"📝 스크립트 타입: {script_type}\n\n")
            
            self.output_text.insert("end", "=== Manifest JSON 내용 ===\n")
            self.output_text.insert("end", json.dumps(manifest_data, ensure_ascii=False, indent=2))
            
            self._add_output_message(f"✅ {os.path.basename(filepath)} 생성 완료", "INFO")
        except Exception as e:
            error_msg = f"Manifest 생성 실패: {e}"
            self._add_output_message(error_msg, "ERROR")
            messagebox.showerror("오류", error_msg)

    def _create_audio(self):
        """오디오 생성"""
        if not PIPELINE_AVAILABLE:
            messagebox.showerror("오류", "파이프라인 모듈을 사용할 수 없습니다.")
            return
        
        script_type = self.script_var.get()
        current_script_data = self._get_current_script_data_from_ui(script_type)

        if current_script_data is None:
            self._add_output_message(f"'{script_type}' 스크립트 데이터를 UI에서 가져올 수 없습니다.", "ERROR")
            messagebox.showerror("오류", f"'{script_type}' 스크립트 데이터를 가져올 수 없습니다.")
            return

        thread = threading.Thread(target=self.pipeline_manager.create_audio, args=(script_type, current_script_data, self.output_text,)) 
        thread.start()

    def _create_subtitles(self):
        """자막 이미지 생성"""
        if not PIPELINE_AVAILABLE:
            messagebox.showerror("오류", "파이프라인 모듈을 사용할 수 없습니다.")
            return
        
        script_type = self.script_var.get()
        thread = threading.Thread(target=self.pipeline_manager.create_subtitles, args=(script_type, self.output_text,)) 
        thread.start()

    def _create_timeline(self):
        """타임라인 생성"""
        if not PIPELINE_AVAILABLE:
            messagebox.showerror("오류", "파이프라인 모듈을 사용할 수 없습니다.")
            return
        
        script_type = self.script_var.get()
        thread = threading.Thread(target=self.pipeline_manager.create_timeline, args=(script_type, self.output_text,)) 
        thread.start()

    def _render_video(self):
        """비디오 렌더링 - 제작 사양서에 따른 회화/인트로/엔딩 비디오 생성"""
        # 프로젝트 설정 검증
        project_name = self.root.data_page.project_name_var.get() if self.root and hasattr(self.root, 'data_page') else ""
        identifier = self.root.data_page.identifier_var.get() if self.root and hasattr(self.root, 'data_page') else ""
        
        if not project_name or not identifier:
            self._add_output_message("❌ 프로젝트명과 식별자를 먼저 설정해주세요.", "ERROR")
            return
        
        self._add_output_message("🎬 비디오 렌더링 시작...", "INFO")
        
        def run_render():
            try:
                # UI 데이터 수집
                ui_data = self._collect_ui_data()
                
                # 파이프라인 실행
                result = self.pipeline_manager.run_pipeline_from_ui_data(ui_data)
                
                if result.get('success', False):
                    self._add_output_message("✅ 비디오 렌더링 완료!", "SUCCESS")
                    
                    # 생성된 비디오 파일들 표시
                    generated_files = result.get('generated_files', {})
                    if generated_files.get("video"):
                        self._add_output_message(f"📁 최종 비디오: {generated_files['video']}", "INFO")
                    if generated_files.get("intro_video"):
                        self._add_output_message(f"📁 인트로 비디오: {generated_files['intro_video']}", "INFO")
                    if generated_files.get("conversation_video"):
                        self._add_output_message(f"📁 회화 비디오: {generated_files['conversation_video']}", "INFO")
                    if generated_files.get("ending_video"):
                        self._add_output_message(f"📁 엔딩 비디오: {generated_files['ending_video']}", "INFO")
                else:
                    self._add_output_message("❌ 비디오 렌더링 실패", "ERROR")
                    for error in result.get('errors', []):
                        self._add_output_message(f"  - {error}", "ERROR")
                
            except Exception as e:
                self._add_output_message(f"❌ 비디오 렌더링 중 오류 발생: {e}", "ERROR")
        
        # 백그라운드에서 실행
        threading.Thread(target=run_render, daemon=True).start()

    def _collect_ui_data(self):
        """UI에서 데이터를 수집하여 파이프라인에 전달"""
        try:
            project_name = self.root.data_page.project_name_var.get() if self.root and hasattr(self.root, 'data_page') else ""
            identifier = self.root.data_page.identifier_var.get() if self.root and hasattr(self.root, 'data_page') else ""
            
            return {
                'project_name': project_name,
                'identifier': identifier,
                'script_type': self.script_var.get(),
                'enable_audio_generation': True,
                'enable_subtitle_generation': True,
                'enable_video_rendering': True,
                'enable_quality_optimization': False,
                'enable_preview_generation': False
            }
        except Exception as e:
            self._add_output_message(f"❌ UI 데이터 수집 실패: {e}", "ERROR")
            return {}

    def _auto_generation(self):
        """자동 생성 - A~G 단계를 순차적으로 자동 실행"""
        # 프로젝트 설정 검증
        project_name = self.root.data_page.project_name_var.get() if self.root and hasattr(self.root, 'data_page') else ""
        identifier = self.root.data_page.identifier_var.get() if self.root and hasattr(self.root, 'data_page') else ""
        
        if not project_name or not identifier:
            self._add_output_message("❌ 프로젝트명과 식별자를 먼저 설정해주세요.", "ERROR")
            return
        
        self._add_output_message("🚀 자동 생성 시작 - 전체 파이프라인 실행...", "INFO")
        
        def run_auto_generation():
            try:
                # UI 데이터 수집
                ui_data = self._collect_ui_data()
                
                # 1. 매니페스트 생성
                self._add_output_message("📋 1단계: 매니페스트 생성...", "INFO")
                manifest_result = self.pipeline_manager.run_manifest_creation(ui_data)
                if not manifest_result.get('success', False):
                    self._add_output_message("❌ 매니페스트 생성 실패", "ERROR")
                    return
                
                # 2. 오디오 생성
                self._add_output_message("🎵 2단계: 오디오 생성...", "INFO")
                audio_result = self.pipeline_manager.run_audio_generation(ui_data)
                if not audio_result.get('success', False):
                    self._add_output_message("❌ 오디오 생성 실패", "ERROR")
                    return
                
                # 3. 자막 이미지 생성
                self._add_output_message("📝 3단계: 자막 이미지 생성...", "INFO")
                subtitle_result = self.pipeline_manager.run_subtitle_creation(ui_data)
                if not subtitle_result.get('success', False):
                    self._add_output_message("❌ 자막 이미지 생성 실패", "ERROR")
                    return
                
                # 4. 타임라인 생성
                self._add_output_message("⏰ 4단계: 타임라인 생성...", "INFO")
                timeline_result = self.pipeline_manager.run_timeline_creation(ui_data)
                if not timeline_result.get('success', False):
                    self._add_output_message("❌ 타임라인 생성 실패", "ERROR")
                    return
                
                # 5. 비디오 렌더링
                self._add_output_message("🎬 5단계: 비디오 렌더링...", "INFO")
                video_result = self.pipeline_manager.run_video_rendering(ui_data)
                if not video_result.get('success', False):
                    self._add_output_message("❌ 비디오 렌더링 실패", "ERROR")
                    return
                
                # 6. 최종 병합
                self._add_output_message("🔗 6단계: 최종 병합...", "INFO")
                merge_result = self.pipeline_manager.create_final_merged_video(project_name, identifier, f"output/{project_name}/{identifier}")
                if not merge_result:
                    self._add_output_message("❌ 최종 병합 실패", "ERROR")
                    return
                
                self._add_output_message("✅ 자동 생성 완료! 모든 단계가 성공적으로 완료되었습니다.", "SUCCESS")
                self._add_output_message(f"📁 최종 비디오: {merge_result}", "INFO")
                
            except Exception as e:
                self._add_output_message(f"❌ 자동 생성 중 오류 발생: {e}", "ERROR")
        
        # 백그라운드에서 실행
        threading.Thread(target=run_auto_generation, daemon=True).start()
    
    def _timing_based_render(self):
        """타이밍 기반 비디오 렌더링 - 타임라인 생성 생략"""
        project_name = self.root.data_page.project_name_var.get() if self.root and hasattr(self.root, 'data_page') else ""
        identifier = self.root.data_page.identifier_var.get() if self.root and hasattr(self.root, 'data_page') else ""
        
        if not project_name or not identifier:
            self._add_output_message("❌ 프로젝트명과 식별자를 먼저 설정해주세요.", "ERROR")
            return
        
        self._add_output_message("⚡ 타이밍 기반 비디오 렌더링 시작...", "INFO")
        
        def run_timing_based_render():
            try:
                ui_data = self._collect_ui_data()
                result = self.pipeline_manager.run_timing_based_video_rendering(ui_data)
                
                if result.get('success', False):
                    self._add_output_message("✅ 타이밍 기반 비디오 렌더링 완료!", "SUCCESS")
                    self._add_output_message(f"📁 비디오 파일: {result.get('video_path', '')}", "INFO")
                else:
                    self._add_output_message(f"❌ 타이밍 기반 비디오 렌더링 실패: {result.get('message', '')}", "ERROR")
                    
            except Exception as e:
                self._add_output_message(f"❌ 타이밍 기반 렌더링 중 오류 발생: {e}", "ERROR")
        
        threading.Thread(target=run_timing_based_render, daemon=True).start()

    def _on_script_change(self, choice=None):
        self.after(50, self._refresh_script)

    def _refresh_script(self):
        """스크립트 종류에 따라 UI를 새로고침합니다."""
        script_type = self.script_var.get()
        
        self.script_text.grid_remove()
        self.csv_tree.grid_remove()
        self.csv_scroll_y.grid_remove()
        for item in self.csv_tree.get_children(): self.csv_tree.delete(item)
        self.script_text.delete("1.0", tk.END)

        try:
            project_name = self.root.data_page.project_name_var.get()
            identifier = self.root.data_page.identifier_var.get()

            ai_data = None
            if project_name and identifier:
                ai_json_path = os.path.join("output", project_name, identifier, f"{identifier}_ai.json")
                if os.path.exists(ai_json_path):
                    with open(ai_json_path, 'r', encoding='utf-8') as f:
                        ai_data = json.load(f)
                else:
                    self._add_output_message(f"AI JSON 파일을 찾을 수 없습니다: {ai_json_path}", "WARNING")

            script_data = None
            if ai_data:
                # Extract data from ai_data based on script_type
                if script_type == "회화" or script_type == "대화":
                    # Assuming conversation/dialog data is under a key like 'conversation_script' or 'dialog_script'
                    # Or it might be directly in the 'scenes' array if the AI output is structured that way
                    # For now, let's assume it's in 'fullVideoScript' -> 'dialogueCsv' as seen in pipeline_manager
                    dialogue_csv_content = ai_data.get("fullVideoScript", {}).get("dialogueCsv") or ai_data.get("dialogueCsv", "")
                    if dialogue_csv_content and dialogue_csv_content.strip(): # Add strip() and check for emptiness
                        # Parse CSV content
                        reader = csv.reader(io.StringIO(dialogue_csv_content))
                        rows = list(reader)
                        if rows and [c.strip('"') for c in rows[0][:4]] == ["순번", "원어", "학습어", "읽기"]:
                            rows = rows[1:] # Skip header if present
                        
                        scenes = []
                        for row in rows:
                            normalized = [c.strip('"') for c in row]
                            padded = (normalized + [""] * 4)[:4]
                            scenes.append({
                                "order": padded[0], "native_script": padded[1],
                                "learning_script": padded[2], "reading_script": padded[3]
                            })
                        script_data = {"scenes": scenes}
                    else:
                        self._add_output_message(f"AI JSON에 '회화' 또는 '대화' 스크립트 데이터가 비어 있습니다.", "WARNING")
                elif script_type == "인트로":
                    script_data = ai_data.get("introScript", "")
                elif script_type == "엔딩":
                    script_data = ai_data.get("endingScript", "")
            
            # Fallback to pipeline_manager's data collection if AI data is not available or not relevant
            if script_data is None:
                script_data = self.pipeline_manager._collect_script_data(script_type)

            if script_type in ["회화", "대화"] and isinstance(script_data, dict) and "scenes" in script_data:
                self._show_csv_grid(script_data["scenes"])
            elif isinstance(script_data, str):
                self._show_text_content(script_data)
            else:
                self._show_text_content(f"표시할 데이터가 없습니다: {script_type}")
        except Exception as e:
            self._show_text_content(f"스크립트 로딩 중 오류 발생: {e}")
            self._add_output_message(f"스크립트 로딩 중 오류 발생: {e}", "ERROR")

    def _show_text_content(self, content: str):
        self.csv_tree.grid_remove()
        self.csv_scroll_y.grid_remove()
        self.script_text.grid(row=0, column=0, sticky="nsew")
        self.script_text.delete("1.0", tk.END)
        self.script_text.insert("1.0", content)

    def _show_csv_grid(self, scenes):
        self.script_text.grid_remove()
        self.csv_tree.grid(row=0, column=0, sticky="nsew")
        self.csv_scroll_y.grid(row=0, column=1, sticky="ns")
        
        for iid in self.csv_tree.get_children(): self.csv_tree.delete(iid)
        
        for scene in scenes:
            values = [scene.get(k, '') for k in ['order', 'native_script', 'learning_script', 'reading_script']]
            self.csv_tree.insert("", tk.END, values=values)

    def _add_output_message(self, message: str, level: str = "INFO"):
        """출력 메시지 추가"""
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_message = f"[{timestamp}] {level}: {message}"
            self.output_text.insert("end", f"{log_message}\n")
            self.output_text.see("end")
            print(log_message)
        except Exception as e:
            print(f"Error adding output message: {e}")

    def _save_script_data(self):
        """데이터 저장 버튼 클릭 시 호출"""
        script_type = self.script_var.get()
        project_name = self.root.data_page.project_name_var.get()
        identifier = self.root.data_page.identifier_var.get()

        if not project_name or not identifier:
            self._add_output_message("프로젝트 이름 또는 식별자를 설정해주세요.", "ERROR")
            messagebox.showerror("오류", "프로젝트 이름 또는 식별자를 설정해주세요.")
            return

        output_dir = os.path.join("output", project_name, identifier)
        os.makedirs(output_dir, exist_ok=True)

        filename_map = {
            "회화": f"{identifier}_conversation.csv",
            "인트로": f"{identifier}_intro.txt",
            "엔딩": f"{identifier}_ending.txt",
            "대화": f"{identifier}_dialog.csv" # Assuming dialog also uses CSV
        }
        filename = filename_map.get(script_type)

        if not filename:
            self._add_output_message(f"알 수 없는 스크립트 타입: {script_type}", "ERROR")
            messagebox.showerror("오류", f"알 수 없는 스크립트 타입: {script_type}")
            return

        filepath = os.path.join(output_dir, filename)

        try:
            if script_type in ["회화", "대화"]:
                # Save CSV data from Treeview
                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    # Write header
                    writer.writerow(["순번", "원어", "학습어", "읽기"])
                    for item_id in self.csv_tree.get_children():
                        values = self.csv_tree.item(item_id, 'values')
                        writer.writerow(values)
            else:
                # Save text data from Textbox
                content = self.script_text.get("1.0", tk.END).strip()
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)

            self._add_output_message(f"✅ '{script_type}' 데이터 저장 완료: {filepath}", "INFO")
        except Exception as e:
            error_msg = f"'{script_type}' 데이터 저장 실패: {e}"
            self._add_output_message(error_msg, "ERROR")
            messagebox.showerror("오류", error_msg)

    def _load_script_data(self):
        """데이터 읽기 버튼 클릭 시 호출"""
        script_type = self.script_var.get()
        project_name = self.root.data_page.project_name_var.get()
        identifier = self.root.data_page.identifier_var.get()

        if not project_name or not identifier:
            self._add_output_message("프로젝트 이름 또는 식별자를 설정해주세요.", "ERROR")
            messagebox.showerror("오류", "프로젝트 이름 또는 식별자를 설정해주세요.")
            return

        output_dir = os.path.join("output", project_name, identifier)
        
        filename_map = {
            "회화": f"{identifier}_conversation.csv",
            "인트로": f"{identifier}_intro.txt",
            "엔딩": f"{identifier}_ending.txt",
            "대화": f"{identifier}_dialog.csv"
        }
        filename = filename_map.get(script_type)

        if not filename:
            self._add_output_message(f"알 수 없는 스크립트 타입: {script_type}", "ERROR")
            messagebox.showerror("오류", f"알 수 없는 스크립트 타입: {script_type}")
            return

        filepath = os.path.join(output_dir, filename)

        if not os.path.exists(filepath):
            self._add_output_message(f"파일을 찾을 수 없습니다: {filepath}", "WARNING")
            messagebox.showinfo("정보", "저장된 스크립트 파일이 없습니다.")
            return

        try:
            if script_type in ["회화", "대화"]:
                # Load CSV data to Treeview
                self.csv_tree.delete(*self.csv_tree.get_children()) # Clear existing
                
                content = ""
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read() # Read entire content as string
                except Exception as file_e:
                    self._add_output_message(f"CSV 파일 읽기 오류: {file_e}", "ERROR")
                    messagebox.showerror("오류", f"CSV 파일 읽기 오류: {file_e}")
                    return

                if not content.strip(): # Check if file is empty or only whitespace
                    self._add_output_message(f"경고: CSV 파일이 비어 있습니다: {filepath}", "WARNING")
                    return

                try:
                    reader = csv.reader(io.StringIO(content))
                    all_rows = list(reader) # Read all rows into a list
                except Exception as csv_e:
                    self._add_output_message(f"CSV 파싱 오류: {csv_e}", "ERROR")
                    messagebox.showerror("오류", f"CSV 파싱 오류: {csv_e}")
                    return
                
                if not all_rows: # Should not happen if content.strip() is true, but for safety
                    self._add_output_message(f"경고: CSV 파일에 내용이 없습니다: {filepath}", "WARNING")
                    return

                header = all_rows[0]
                data_rows = all_rows[1:] # Data rows start from the second row

                if header != ["순번", "원어", "학습어", "읽기"]:
                    self._add_output_message(f"경고: CSV 헤더가 예상과 다릅니다. {filepath}", "WARNING")
                
                rows_to_display = []
                if data_rows is not None: # Explicit check, though data_rows should always be a list
                    for row in data_rows:
                        rows_to_display.append(row)
                
                if not rows_to_display and not data_rows: # Only header or no data rows
                    self._add_output_message(f"경고: CSV 파일에 데이터 행이 없습니다 (헤더만 존재): {filepath}", "WARNING")
                
                # Populate Treeview
                for row_values in rows_to_display:
                    self.csv_tree.insert("", tk.END, values=row_values)

                # Ensure the grid is visible if it was hidden
                self.script_text.grid_remove()
                self.csv_tree.grid(row=0, column=0, sticky="nsew")
                self.csv_scroll_y.grid(row=0, column=1, sticky="ns")
            else:
                # Load text data to Textbox
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                self._show_text_content(content) # Refresh display

            self._add_output_message(f"✅ '{script_type}' 데이터 로드 완료: {filepath}", "INFO")
        except Exception as e:
            error_msg = f"'{script_type}' 데이터 로드 실패: {e}"
            self._add_output_message(error_msg, "ERROR")
            messagebox.showerror("오류", error_msg)

    def _merge_final_video(self):
        """최종 비디오 병합"""
        # 프로젝트 설정 검증
        project_name = self.root.data_page.project_name_var.get() if self.root and hasattr(self.root, 'data_page') else ""
        identifier = self.root.data_page.identifier_var.get() if self.root and hasattr(self.root, 'data_page') else ""
        
        if not project_name or not identifier:
            self._add_output_message("❌ 프로젝트명과 식별자를 먼저 설정해주세요.", "ERROR")
            return
        
        self._add_output_message("🔗 최종 비디오 병합 시작...", "INFO")
        
        def run_merge():
            try:
                output_dir = os.path.join("output", project_name, identifier)
                result = self.pipeline_manager.create_final_merged_video(project_name, identifier, output_dir)
                if result:
                    self._add_output_message("✅ 최종 비디오 병합 완료!", "SUCCESS")
                    self._add_output_message(f"📁 최종 비디오: {result}", "INFO")
                else:
                    self._add_output_message("❌ 최종 비디오 병합 실패", "ERROR")
            except Exception as e:
                self._add_output_message(f"❌ 최종 비디오 병합 중 오류: {e}", "ERROR")
        
        thread = threading.Thread(target=run_merge)
        thread.start()
