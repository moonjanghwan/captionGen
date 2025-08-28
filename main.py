import customtkinter
import tkinter
import json
import os
import pygame
from tkinter import filedialog
from tkinter.colorchooser import askcolor
import google.generativeai as genai
from google.cloud import texttospeech
from google.api_core import exceptions
from dotenv import load_dotenv, set_key
import signal, atexit, time
import re
import threading

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        # .env 경로 및 로드
        self.env_path = os.path.join(os.path.dirname(__file__), ".env")
        try:
            load_dotenv(self.env_path)
        except Exception:
            pass

        # 단일 인스턴스 보장 (이전 프로세스 종료)
        self.pid_file = "/tmp/captiongen_ui.pid"
        self._ensure_single_instance()

        # AI 설정 기본값(.env 반영)
        self.ai_settings = {
            "Gemini": {
                "api_key": os.getenv("GEMINI_API_KEY", ""),
                "model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
                "locale": os.getenv("GEMINI_LOCALE", "en-US"),
            }
        }

        self.title("Caption Generator")
        self.geometry("1600x800")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        pygame.mixer.init()

        # --- App State ---
        self.generated_scripts = {}
        
        # --- Real-time Audio State ---
        self.is_playing_realtime = False
        self.current_script_index = 0
        self.audio_queue = []
        self.playing_thread = None

        # --- Theme and Colors ---
        customtkinter.set_appearance_mode("dark")
        self.BG_COLOR = "#1B1B1B"
        self.WIDGET_COLOR = "#404040"
        self.BUTTON_COLOR = "#007ACC"
        self.BUTTON_HOVER_COLOR = "#0095FF"
        self.TEXT_COLOR = "#EAEAEA"
        self.BUTTON_TEXT_COLOR = "#EAEAEA"
        self.configure(fg_color=self.BG_COLOR)

        # --- Language Data ---
        self.language_map = {
            "한국어 (ko-KR)": ("kor", "ko-KR"),
            "영어 (en-US)": ("eng", "en-US"),
            "일본어 (ja-JP)": ("jpn", "ja-JP"),
            "중국어 (cmn-CN)": ("chn", "cmn-CN"),
            "베트남어 (vi-VN)": ("vnm", "vi-VN"),
            "인도네시아어 (id-ID)": ("idn", "id-ID"),
            "이탈리아어 (it-IT)": ("ita", "it-IT"),
            "스페인어 (es-US)": ("esp", "es-US"),
            "프랑스어 (fr-FR)": ("fra", "fr-FR"),
            "독일어 (de-DE)": ("deu", "de-DE")
        }
        self.languages = list(self.language_map.keys())
        self.tts_voices = []
        self.learner_speaker_widgets = []
        self.learning_voices = []
        self.speaker_config_to_load = None

        self.center_window()

        # --- Main UI Structure ---
        self.tab_view = customtkinter.CTkTabview(self, 
                                               command=self.on_tab_change,
                                               fg_color="transparent",
                                               segmented_button_fg_color=self.WIDGET_COLOR,
                                               segmented_button_selected_color=self.BUTTON_COLOR,
                                               segmented_button_unselected_color=self.WIDGET_COLOR,
                                               segmented_button_selected_hover_color=self.BUTTON_HOVER_COLOR,
                                               text_color=self.TEXT_COLOR)
        self.tab_view.pack(expand=True, fill="both", padx=10, pady=10)

        self.tab_view.add("데이터 생성")
        self.tab_view.add("화자 선택")
        self.tab_view.add("이미지 설정")

        # 1. Create UI Tabs
        self.create_data_generation_tab(self.tab_view.tab("데이터 생성"))
        self.create_speaker_selection_tab(self.tab_view.tab("화자 선택"))
        self.create_image_settings_tab(self.tab_view.tab("이미지 설정"))
        
        # 2. Initialize Backend Clients
        self.initialize_google_clients()

        # 3. Load Configuration
        self.load_config()

    # 단일 인스턴스 유틸
    def _ensure_single_instance(self):
        try:
            if os.path.exists(self.pid_file):
                try:
                    with open(self.pid_file, "r") as f:
                        old_pid_str = f.read().strip()
                    old_pid = int(old_pid_str) if old_pid_str.isdigit() else None
                except Exception:
                    old_pid = None
                if old_pid:
                    if self._is_process_running(old_pid):
                        try:
                            os.kill(old_pid, signal.SIGTERM)
                            for _ in range(50):
                                if not self._is_process_running(old_pid):
                                    break
                                time.sleep(0.1)
                            if self._is_process_running(old_pid):
                                os.kill(old_pid, signal.SIGKILL)
                        except Exception:
                            pass
                try:
                    os.remove(self.pid_file)
                except Exception:
                    pass
            with open(self.pid_file, "w") as f:
                f.write(str(os.getpid()))
            atexit.register(self._cleanup_pid)
        except Exception:
            pass

    def _is_process_running(self, pid: int) -> bool:
        try:
            os.kill(pid, 0)
            return True
        except Exception:
            return False

    def _cleanup_pid(self):
        try:
            if os.path.exists(self.pid_file):
                with open(self.pid_file, "r") as f:
                    content = f.read().strip()
                if content == str(os.getpid()):
                    os.remove(self.pid_file)
        except Exception:
            pass

    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

    def on_closing(self):
        self.save_config()
        self.destroy()

    def save_config(self):
        # 프로젝트별 speaker.json만 저장
        learner_speakers = [row['dropdown'].get() for row in self.learner_speaker_widgets]
        project_name = self.project_name_entry.get()
        identifier = self.identifier_entry.get()
        if not project_name or not identifier:
            self.message_window.insert("end", "[ERROR] 프로젝트명과 식별자를 먼저 설정해주세요.\n")
            print("[ERROR] 프로젝트명과 식별자를 먼저 설정해주세요.")
            return

        speaker_config_path = os.path.join("output", project_name, identifier, "speaker.json")
        os.makedirs(os.path.dirname(speaker_config_path), exist_ok=True)

        speaker_config = {
            "native_speaker": self.native_speaker_dropdown.get(),
            "learner_count": self.learner_count_dropdown.get(),
            "learner_speakers": learner_speakers,
        }
        try:
            with open(speaker_config_path, "w", encoding="utf-8") as f:
                json.dump(speaker_config, f, ensure_ascii=False, indent=4)
            msg = f"[SUCCESS] 화자 설정이 저장되었습니다: {speaker_config_path}"
            self.message_window.insert("end", msg + "\n")
            print(msg)
        except Exception as e:
            err = f"[ERROR] 화자 설정 저장 실패: {e}"
            self.message_window.insert("end", err + "\n")
            print(err)

    def load_config(self):
        # 기본 언어/프로젝트 식별자만 config.json에서 로드하고, 화자설정은 speaker.json에서만 로드
        try:
            if os.path.exists("config.json"):
                with open("config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
                self.native_lang_dropdown.set(config.get("native_lang", self.languages[0]))
                self.learning_lang_dropdown.set(config.get("learning_lang", self.languages[1]))
                self.project_name_entry.delete(0, "end")
                self.project_name_entry.insert(0, config.get("project_name", ""))
                self.identifier_entry.delete(0, "end")
                self.identifier_entry.insert(0, config.get("identifier", ""))
            else:
                self.update_project_fields()
            # 프로젝트별 speaker.json 로드
            self.load_speaker_config()
        except (FileNotFoundError, json.JSONDecodeError):
            self.update_project_fields()
            self.load_speaker_config()

    def load_speaker_config(self):
        """프로젝트별 speaker.json만을 사용하여 화자 설정을 로드한다."""
        try:
            project_name = self.project_name_entry.get()
            identifier = self.identifier_entry.get()
            if not project_name or not identifier:
                return
            speaker_config_path = os.path.join("output", project_name, identifier, "speaker.json")
            if not os.path.exists(speaker_config_path):
                self.message_window.insert("end", f"[DEBUG] 프로젝트별 화자 설정 파일이 없습니다: {speaker_config_path}\n")
                return
            with open(speaker_config_path, "r", encoding="utf-8") as f:
                speaker_config = json.load(f)
            # 탭 전환 시 적용되도록 대기 적용 변수에 넣고 리스트 갱신
            self.speaker_config_to_load = speaker_config
            self.message_window.insert("end", f"[SUCCESS] 프로젝트별 화자 설정을 로드했습니다: {speaker_config_path}\n")
            # 즉시 드롭다운에 반영
            try:
                self.native_speaker_dropdown.set(speaker_config.get("native_speaker", ""))
                self.learner_count_dropdown.set(speaker_config.get("learner_count", "4"))
                self.redraw_learner_speakers()
                saved = speaker_config.get("learner_speakers", [])
                for i, widget_row in enumerate(self.learner_speaker_widgets):
                    if i < len(saved):
                        widget_row['dropdown'].set(saved[i])
            except Exception:
                pass
        except Exception as e:
            self.message_window.insert("end", f"[ERROR] speaker.json 로드 실패: {e}\n")
    
    def load_google_cloud_config(self):
        """config.json에서 Google Cloud 설정을 로드합니다."""
        try:
            if os.path.exists("config.json"):
                with open("config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
                return config.get("google_cloud", {})
            else:
                return {}
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def update_project_fields(self, _=None):
        native_lang_key = self.native_lang_dropdown.get()
        learning_lang_key = self.learning_lang_dropdown.get()
        
        native_code, _ = self.language_map.get(native_lang_key, ("xxx", ""))
        learning_code, _ = self.language_map.get(learning_lang_key, ("yyy", ""))
        
        project_string = f"{native_code}-{learning_code}"
        
        self.project_name_entry.delete(0, "end")
        self.project_name_entry.insert(0, project_string)
        self.identifier_entry.delete(0, "end")
        self.identifier_entry.insert(0, project_string)

    def initialize_google_clients(self):
        self.tts_client = None
        self.gemini_model = None
        
        # config.json에서 Google Cloud 설정 로드
        google_cloud_config = self.load_google_cloud_config()
        
        try:
            # Google Cloud 인증 설정
            if google_cloud_config and google_cloud_config.get("credentials_path"):
                credentials_path = google_cloud_config["credentials_path"]
                self.message_window.insert("end", f"[DEBUG] Credentials path from config: {credentials_path}\n")
                print(f"[DEBUG] Credentials path from config: {credentials_path}")
                
                if os.path.exists(credentials_path):
                    abs_path = os.path.abspath(credentials_path)
                    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = abs_path
                    self.message_window.insert("end", f"[SUCCESS] Google Cloud credentials loaded from: {abs_path}\n")
                    print(f"[SUCCESS] Google Cloud credentials loaded from: {abs_path}")
                    
                    # credentials 파일 내용 확인
                    try:
                        with open(credentials_path, 'r') as f:
                            cred_data = json.load(f)
                        project_id = cred_data.get('project_id', 'Not found')
                        client_email = cred_data.get('client_email', 'Not found')
                        self.message_window.insert("end", f"[DEBUG] Credentials file - Project ID: {project_id}\n")
                        self.message_window.insert("end", f"[DEBUG] Credentials file - Client Email: {client_email}\n")
                        print(f"[DEBUG] Credentials file - Project ID: {project_id}")
                        print(f"[DEBUG] Credentials file - Client Email: {client_email}")
                    except Exception as cred_e:
                        self.message_window.insert("end", f"[WARNING] Failed to read credentials file: {cred_e}\n")
                        print(f"[WARNING] Failed to read credentials file: {cred_e}")
                else:
                    self.message_window.insert("end", f"[ERROR] Credentials file not found: {credentials_path}\n")
                    print(f"[ERROR] Credentials file not found: {credentials_path}")
                    return
            else:
                self.message_window.insert("end", "[WARNING] No credentials_path found in config.json\n")
                print("[WARNING] No credentials_path found in config.json")
            
            # TTS 클라이언트 초기화
            self.message_window.insert("end", "[INFO] Initializing Google TTS client...\n")
            print("[INFO] Initializing Google TTS client...")
            
            self.tts_client = texttospeech.TextToSpeechClient()
            self.message_window.insert("end", "[SUCCESS] Google TTS client initialized.\n")
            print("[SUCCESS] Google TTS client initialized.")
            
            # TTS 화자 목록 로드
            self.message_window.insert("end", "[INFO] Loading TTS voices...\n")
            print("[INFO] Loading TTS voices...")
            
            self.tts_voices = self.tts_client.list_voices().voices
            self.message_window.insert("end", f"[SUCCESS] {len(self.tts_voices)}개의 TTS 화자를 로드했습니다.\n")
            print(f"[SUCCESS] {len(self.tts_voices)}개의 TTS 화자를 로드했습니다.")
            
            # 지원 언어 확인
            supported_languages = set()
            for voice in self.tts_voices:
                for lang_code in voice.language_codes:
                    supported_languages.add(lang_code)
            
            self.message_window.insert("end", f"[DEBUG] Supported languages: {sorted(list(supported_languages))}\n")
            print(f"[DEBUG] Supported languages: {sorted(list(supported_languages))}")
            
        except Exception as e:
            error_msg = f"[ERROR] TTS/Voice list initialization failed: {e}"
            self.message_window.insert("end", error_msg + "\n")
            print(error_msg)
            
            # 상세한 에러 정보
            import traceback
            traceback_msg = f"[ERROR] Full traceback:\n{traceback.format_exc()}"
            print(traceback_msg)
            
            self.message_window.insert("end", "[INFO] Google Cloud TTS API 키가 설정되지 않았거나 인증에 문제가 있습니다.\n")
            self.message_window.insert("end", "[INFO] config.json에서 credentials_path를 확인하고 유효한 서비스 계정 키 파일을 지정해주세요.\n")
            self.message_window.insert("end", "[INFO] Google Cloud Console에서 TTS API가 활성화되었는지 확인해주세요.\n")

        # Gemini는 요청 시점에 설정합니다(.env 또는 설정값 사용)
        try:
            api_key = self.ai_settings.get("Gemini", {}).get("api_key") or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
            model_name = self.ai_settings.get("Gemini", {}).get("model", "gemini-2.5-flash")
            if api_key:
                genai.configure(api_key=api_key)
                self.gemini_model = genai.GenerativeModel(model_name)
                self.message_window.insert("end", f"[SUCCESS] Gemini client ready ({model_name}).\n")
            else:
                self.message_window.insert("end", "[INFO] Gemini API 키가 설정되지 않았습니다. 데이터 생성 전 '설정…'에서 키를 저장하세요.\n")
        except Exception as e:
            self.message_window.insert("end", f"[ERROR] Gemini initialization note: {e}\n")

    def generate_ai_data(self):
        # 최신 설정으로 Gemini 재구성
        try:
            api_key = self.ai_settings.get("Gemini", {}).get("api_key") or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
            model_name = self.ai_settings.get("Gemini", {}).get("model", "gemini-2.5-flash")
            if not api_key:
                self.message_window.insert("end", "[ERROR] Gemini API 키가 없습니다. 데이터 생성 전 '설정…'에서 키를 저장하세요.\n")
                return
            genai.configure(api_key=api_key)
            self.gemini_model = genai.GenerativeModel(model_name)
        except Exception as e:
            self.message_window.insert("end", f"[ERROR] Gemini 설정 실패: {e}\n")
            return

        if not self.gemini_model:
            self.message_window.insert("end", "[ERROR] Gemini client is not initialized. Please check your API key.\n")
            return
        try:
            project_name = self.project_name_entry.get()
            identifier = self.identifier_entry.get()

            if not project_name or not identifier:
                self.message_window.insert("end", "[ERROR] 프로젝트명과 식별자를 입력해야 합니다.\n")
                return

            # 1) 템플릿 로드 및 렌더링
            template = self._read_ai_prompt_template()
            vars_map = self._collect_prompt_vars()
            if not template:
                # 기본 프롬프트 폴백
                template = (
                    "Please generate scripts for the topic '{{topic}}' at a '{{level}}' level "
                    "for {{count}} items. Return JSON with keys: '회화 스크립트','타이틀 스크립트','썸네일 스크립트',"
                    "'인트로 스크립트','엔딩 스크립트','키워드 스크립트','배경 스크립트','대화 스크립트'."
                )
            prompt_text = self._render_template(template, vars_map)

            output_dir = os.path.join("output", project_name, identifier)
            os.makedirs(output_dir, exist_ok=True)

            # 프롬프트 저장 (txt + json)
            prompt_txt_path = os.path.join(output_dir, f"{identifier}_prompt.txt")
            with open(prompt_txt_path, "w", encoding="utf-8") as f:
                f.write(prompt_text)

            prompt_json_path = os.path.join(output_dir, f"{identifier}_prompt.json")
            with open(prompt_json_path, "w", encoding="utf-8") as f:
                json.dump({"prompt": prompt_text, "variables": vars_map}, f, ensure_ascii=False, indent=4)
            self.message_window.insert("end", f"[INFO] Prompt saved to {prompt_txt_path} and {prompt_json_path}\n")

            # 2) 호출
            self.message_window.insert("end", f"[INFO] Generating content with Gemini...\n")
            response = self.gemini_model.generate_content(prompt_text)
            raw_text = getattr(response, "text", "").strip()

            # 원문 저장
            raw_path = os.path.join(output_dir, f"{identifier}_ai_raw.txt")
            with open(raw_path, "w", encoding="utf-8") as f:
                f.write(raw_text)

            # 3) JSON 저장 (정상/실패 분기)
            ai_output_path = os.path.join(output_dir, f"{identifier}_ai.json")
            try:
                cleaned_text = raw_text.replace("```json", "").replace("```", "").strip()
                self.generated_scripts = json.loads(cleaned_text)
                # 후처리: 대화 CSV 교정/생성
                self.generated_scripts = self._maybe_fix_dialogue_csv(self.generated_scripts, vars_map)
                with open(ai_output_path, "w", encoding="utf-8") as f:
                    json.dump(self.generated_scripts, f, ensure_ascii=False, indent=4)
                # 정규화 후 파일 저장 (표준 키만 저장)
                canonical = self._normalize_ai_keys(self.generated_scripts)
                self._save_script_files(canonical, output_dir)
                self.message_window.insert("end", f"[SUCCESS] AI Response saved to {ai_output_path}\n")
                # 기본 선택 및 표시 갱신
                try:
                    self.script_type_dropdown.set("회화 스크립트")
                except Exception:
                    pass
                self.update_script_display()
            except Exception as e:
                self.generated_scripts = {}
                self.message_window.insert("end", f"[ERROR] JSON 파싱 실패: {e}. 원문은 {raw_path}에 저장되었습니다.\n")

            self.audio_gen_button.configure(state="normal")
            self.audio_listen_button.configure(state="normal")

        except Exception as e:
            self.message_window.insert("end", f"[ERROR] 데이터 생성 중 오류 발생: {e}\n")

    def _save_script_files(self, scripts: dict, output_dir: str) -> None:
        """AI가 반환한 스크립트를 키별로 파일에 저장합니다."""
        key_to_filename = self._script_filename_map()
        for key, value in scripts.items():
            try:
                filename = key_to_filename.get(key)
                if not filename:
                    # 매핑 외 키도 안전하게 저장
                    safe = "".join(ch if ch.isalnum() else "_" for ch in str(key)).strip("_")
                    if not safe:
                        safe = "unnamed"
                    filename = f"{safe}.txt"
                path = os.path.join(output_dir, filename)
                # 문자열이면 그대로, 리스트/딕셔너리는 JSON으로 저장
                if isinstance(value, str):
                    content = value
                else:
                    content = json.dumps(value, ensure_ascii=False, indent=2)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.message_window.insert("end", f"[INFO] Saved script: {key} -> {path}\n")
            except Exception as e:
                self.message_window.insert("end", f"[WARN] Failed saving script '{key}': {e}\n")

    def _script_filename_map(self) -> dict:
        return {
            "회화 스크립트": "conversation.txt",
            "타이틀 스크립트": "title.txt",
            "썸네일 스크립트": "thumbnail.txt",
            "인트로 스크립트": "intro.txt",
            "엔딩 스크립트": "ending.txt",
            "키워드 스크립트": "keywords.txt",
            "배경 스크립트": "background.txt",
            "대화 스크립트": "dialogue.txt",
        }

    def _get_output_dir(self) -> str:
        project_name = self.project_name_entry.get()
        identifier = self.identifier_entry.get()
        return os.path.join("output", project_name, identifier)

    def on_read_ai_data(self) -> None:
        try:
            output_dir = self._get_output_dir()
            ai_json = os.path.join(output_dir, f"{self.identifier_entry.get()}_ai.json")
            if not os.path.exists(ai_json):
                self.message_window.insert("end", f"[INFO] 저장된 AI JSON이 없습니다: {ai_json}\n")
                return
            with open(ai_json, "r", encoding="utf-8") as f:
                self.generated_scripts = json.load(f)
            # 후처리: 대화 CSV 교정/생성
            self.generated_scripts = self._maybe_fix_dialogue_csv(self.generated_scripts, self._collect_prompt_vars())
            self.message_window.insert("end", f"[SUCCESS] Loaded saved AI JSON: {ai_json}\n")
            # 정규화 후 파일 저장 (표준 키만 저장)
            canonical = self._normalize_ai_keys(self.generated_scripts)
            self._save_script_files(canonical, output_dir)
            # 기본 선택 및 표시 갱신
            try:
                self.script_type_dropdown.set("회화 스크립트")
            except Exception:
                pass
            self.update_script_display()
            self.audio_gen_button.configure(state="normal")
            self.audio_listen_button.configure(state="normal")
        except Exception as e:
            self.message_window.insert("end", f"[ERROR] 저장된 AI 데이터 읽기 실패: {e}\n")

    def _read_script_from_file(self, script_key: str) -> str | None:
        try:
            filename = self._script_filename_map().get(script_key)
            if not filename:
                return None
            path = os.path.join(self._get_output_dir(), filename)
            if not os.path.exists(path):
                try:
                    self.message_window.insert("end", f"[INFO] Script not found: {script_key} -> {path}\n")
                except Exception:
                    pass
                return None
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            try:
                self.message_window.insert("end", f"[SUCCESS] Script loaded: {script_key} -> {path}\n")
                self.message_window.see("end")
            except Exception:
                pass
            return content
        except Exception as e:
            try:
                self.message_window.insert("end", f"[ERROR] Script read failed ({script_key}): {e}\n")
            except Exception:
                pass
            return None

    def _show_text_view(self, text: str) -> None:
        try:
            self.script_grid.grid_remove()
        except Exception:
            pass
        self.script_textbox.grid()
        self.script_textbox.delete("1.0", "end")
        self.script_textbox.insert("1.0", text)

    def _clear_script_grid(self) -> None:
        for w in self.script_grid.winfo_children():
            w.destroy()

    def _show_conversation_grid(self, csv_text: str) -> None:
        # csv_text: "순번,원어,학습어,읽기" 헤더 포함 가정
        self.script_textbox.grid_remove()
        self.script_grid.grid()
        self._clear_script_grid()
        # 파싱
        lines = [ln for ln in (csv_text or "").splitlines() if ln.strip()]
        if not lines:
            customtkinter.CTkLabel(self.script_grid, text="표시할 데이터가 없습니다.").grid(row=0, column=0, padx=6, pady=6, sticky="w")
            return
        header = [h.strip() for h in lines[0].split(',')]
        rows = [[c.strip() for c in ln.split(',')] for ln in lines[1:]]
        # 헤더
        for c, h in enumerate(header):
            lbl = customtkinter.CTkLabel(self.script_grid, text=h, fg_color="#2c2c2c")
            lbl.grid(row=0, column=c, padx=4, pady=4, sticky="nsew")
            self.script_grid.grid_columnconfigure(c, weight=1)
        # 바디
        for r, row in enumerate(rows, start=1):
            for c, val in enumerate(row):
                cell = customtkinter.CTkLabel(self.script_grid, text=val, anchor="w")
                cell.grid(row=r, column=c, padx=4, pady=2, sticky="nsew")

    def update_script_display(self, _=None):
        selected_script_type = self.script_type_dropdown.get()
        # 1) 파일이 있으면 파일을 우선 표시
        file_text = self._read_script_from_file(selected_script_type)
        if selected_script_type == "회화 스크립트":
            # 파일 또는 메모리/자동 로드
            if file_text is None and not self.generated_scripts:
                try:
                    output_dir = self._get_output_dir()
                    ai_json = os.path.join(output_dir, f"{self.identifier_entry.get()}_ai.json")
                    if os.path.exists(ai_json):
                        with open(ai_json, "r", encoding="utf-8") as f:
                            self.generated_scripts = json.load(f)
                        self.generated_scripts = self._maybe_fix_dialogue_csv(self.generated_scripts, self._collect_prompt_vars())
                        self._save_script_files(self._normalize_ai_keys(self.generated_scripts), output_dir)
                        file_text = self._read_script_from_file(selected_script_type)
                except Exception:
                    pass
            # 파일이 최우선, 없으면 메모리 표시
            csv_text = file_text
            if csv_text is None and self.generated_scripts:
                val = self.generated_scripts.get("회화 스크립트")
                csv_text = val if isinstance(val, str) else None
            if csv_text:
                self._show_conversation_grid(csv_text)
                return
            # 그리드 표시할 데이터가 없으면 안내
            self._show_text_view("회화 스크립트 CSV 데이터가 없습니다.")
            return
        # 회화 외 스크립트는 텍스트 표시
        if file_text is not None:
            self._show_text_view(file_text)
            return
        # 1-보강) 파일이 없고 메모리도 비어 있으면 즉시 ai.json을 로드해 분리 저장 시도
        if not self.generated_scripts:
            try:
                output_dir = self._get_output_dir()
                ai_json = os.path.join(output_dir, f"{self.identifier_entry.get()}_ai.json")
                if os.path.exists(ai_json):
                    with open(ai_json, "r", encoding="utf-8") as f:
                        self.generated_scripts = json.load(f)
                    # 후처리 및 분리 저장
                    self.generated_scripts = self._maybe_fix_dialogue_csv(self.generated_scripts, self._collect_prompt_vars())
                    self._save_script_files(self._normalize_ai_keys(self.generated_scripts), output_dir)
                    # 재시도
                    file_text = self._read_script_from_file(selected_script_type)
                    if file_text is not None:
                        self._show_text_view(file_text)
                        return
            except Exception as e:
                try:
                    self.message_window.insert("end", f"[WARN] 자동 로드 실패: {e}\n")
                except Exception:
                    pass
        # 2) 메모리에 파싱된 결과가 있으면 그걸 표시
        if self.generated_scripts:
            display_text = self.generated_scripts.get(selected_script_type, "선택된 스크립트 종류에 대한 데이터가 없습니다.")
            if not isinstance(display_text, str):
                display_text = json.dumps(display_text, ensure_ascii=False, indent=2)
            self._show_text_view(display_text)
            return
        # 3) 둘 다 없으면 안내
        self._show_text_view("해당 스크립트 파일 또는 데이터가 없습니다. 먼저 AI 데이터를 생성하거나 읽기 버튼을 사용하세요.")

    def create_data_generation_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=2) 
        tab.grid_rowconfigure(2, weight=2)

        data_section = customtkinter.CTkFrame(tab, fg_color="transparent")
        data_section.grid(row=0, column=0, padx=10, pady=10, sticky="new")

        customtkinter.CTkLabel(data_section, text="원어:").grid(row=0, column=0, padx=(0, 5), pady=5, sticky="w")
        self.native_lang_dropdown = customtkinter.CTkOptionMenu(data_section, width=180, values=self.languages, command=self.update_project_fields, fg_color=self.WIDGET_COLOR, text_color=self.TEXT_COLOR, dropdown_fg_color=self.WIDGET_COLOR)
        self.native_lang_dropdown.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        customtkinter.CTkLabel(data_section, text="학습어:").grid(row=0, column=2, padx=(20, 5), pady=5, sticky="w")
        self.learning_lang_dropdown = customtkinter.CTkOptionMenu(data_section, width=180, values=self.languages, command=self.update_project_fields, fg_color=self.WIDGET_COLOR, text_color=self.TEXT_COLOR, dropdown_fg_color=self.WIDGET_COLOR)
        self.learning_lang_dropdown.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        customtkinter.CTkLabel(data_section, text="프로젝트명:").grid(row=0, column=4, padx=(20, 5), pady=5, sticky="w")
        self.project_name_entry = customtkinter.CTkEntry(data_section, width=150, fg_color=self.WIDGET_COLOR, text_color=self.TEXT_COLOR, border_color=self.BG_COLOR)
        self.project_name_entry.grid(row=0, column=5, padx=5, pady=5, sticky="w")

        customtkinter.CTkLabel(data_section, text="식별자:").grid(row=0, column=6, padx=(20, 5), pady=5, sticky="w")
        self.identifier_entry = customtkinter.CTkEntry(data_section, width=150, fg_color=self.WIDGET_COLOR, text_color=self.TEXT_COLOR, border_color=self.BG_COLOR)
        self.identifier_entry.grid(row=0, column=7, padx=5, pady=5, sticky="w")

        customtkinter.CTkLabel(data_section, text="학습 주제:").grid(row=1, column=0, padx=(0, 5), pady=5, sticky="w")
        self.topic_dropdown = customtkinter.CTkOptionMenu(data_section, width=180, values=["일상", "비즈니스"], fg_color=self.WIDGET_COLOR, text_color=self.TEXT_COLOR, dropdown_fg_color=self.WIDGET_COLOR)
        self.topic_dropdown.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        customtkinter.CTkLabel(data_section, text="직접 주제를 입력하세요:").grid(row=1, column=2, padx=(20, 5), pady=5, sticky="w")
        self.topic_entry = customtkinter.CTkEntry(data_section, width=180, fg_color=self.WIDGET_COLOR, text_color=self.TEXT_COLOR, border_color=self.BG_COLOR)
        self.topic_entry.grid(row=1, column=3, padx=5, pady=5, sticky="w")

        customtkinter.CTkLabel(data_section, text="등급:").grid(row=1, column=4, padx=(20, 5), pady=5, sticky="w")
        self.level_dropdown = customtkinter.CTkOptionMenu(data_section, width=150, values=["초급", "중급", "고급"], fg_color=self.WIDGET_COLOR, text_color=self.TEXT_COLOR, dropdown_fg_color=self.WIDGET_COLOR)
        self.level_dropdown.grid(row=1, column=5, padx=5, pady=5, sticky="w")

        customtkinter.CTkLabel(data_section, text="데이터 개수:").grid(row=1, column=6, padx=(20, 5), pady=5, sticky="w")
        self.count_dropdown = customtkinter.CTkOptionMenu(data_section, width=150, values=["10", "20", "30"], fg_color=self.WIDGET_COLOR, text_color=self.TEXT_COLOR, dropdown_fg_color=self.WIDGET_COLOR)
        self.count_dropdown.grid(row=1, column=7, padx=5, pady=5, sticky="w")

        customtkinter.CTkLabel(data_section, text="AI 서비스:").grid(row=2, column=0, padx=(0, 5), pady=5, sticky="w")
        self.ai_service_dropdown = customtkinter.CTkOptionMenu(data_section, width=180, values=["Gemini", "GPT-4"], fg_color=self.WIDGET_COLOR, text_color=self.TEXT_COLOR, dropdown_fg_color=self.WIDGET_COLOR)
        self.ai_service_dropdown.grid(row=2, column=1, padx=5, pady=5, sticky="w")

        customtkinter.CTkButton(data_section, text="AI 데이터 생성", command=self.generate_ai_data, fg_color=self.BUTTON_COLOR, hover_color=self.BUTTON_HOVER_COLOR, text_color=self.BUTTON_TEXT_COLOR).grid(row=2, column=2, padx=(20,5), pady=10, sticky="w")

        customtkinter.CTkButton(data_section, text="AI 데이터 읽기", command=self.on_read_ai_data, fg_color=self.BUTTON_COLOR, hover_color=self.BUTTON_HOVER_COLOR, text_color=self.BUTTON_TEXT_COLOR).grid(row=2, column=3, padx=(5,5), pady=10, sticky="w")

        customtkinter.CTkButton(data_section, text="설정...", command=self.open_ai_settings_dialog, fg_color=self.BUTTON_COLOR, hover_color=self.BUTTON_HOVER_COLOR, text_color=self.BUTTON_TEXT_COLOR).grid(row=2, column=4, padx=(5,5), pady=10, sticky="w")

        script_section = customtkinter.CTkFrame(tab, fg_color="transparent")
        script_section.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        script_section.grid_columnconfigure(1, weight=1)
        script_section.grid_rowconfigure(1, weight=1)

        customtkinter.CTkLabel(script_section, text="스크립트 선택:").grid(row=0, column=0, padx=(0, 5), pady=5, sticky="w")
        script_options = ["회화 스크립트", "타이틀 스크립트", "썸네일 스크립트", "인트로 스크립트", "엔딩 스크립트", "키워드 스크립트", "배경 스크립트", "대화 스크립트"]
        self.script_type_dropdown = customtkinter.CTkOptionMenu(script_section, width=300, values=script_options, command=self.update_script_display, fg_color=self.WIDGET_COLOR, text_color=self.TEXT_COLOR, dropdown_fg_color=self.WIDGET_COLOR)
        self.script_type_dropdown.grid(row=0, column=1, sticky="w")
        # 텍스트 보기
        self.script_textbox = customtkinter.CTkTextbox(script_section, fg_color=self.WIDGET_COLOR, text_color=self.TEXT_COLOR, border_color=self.BG_COLOR, border_width=1)
        self.script_textbox.grid(row=1, column=0, columnspan=2, padx=0, pady=10, sticky="nsew")
        # 그리드 보기(회화 스크립트용)
        self.script_grid = customtkinter.CTkScrollableFrame(script_section, fg_color=self.WIDGET_COLOR)
        self.script_grid.grid(row=1, column=0, columnspan=2, padx=0, pady=10, sticky="nsew")
        self.script_grid.grid_remove()

        message_section = customtkinter.CTkFrame(tab, fg_color="transparent")
        message_section.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
        message_section.grid_columnconfigure(0, weight=1)
        message_section.grid_rowconfigure(0, weight=1)
        self.message_window = customtkinter.CTkTextbox(message_section, fg_color=self.WIDGET_COLOR, text_color=self.TEXT_COLOR, border_color=self.BG_COLOR, border_width=1)
        self.message_window.grid(row=0, column=0, sticky="nsew")
        # 메시지 창: 더블클릭으로 프리뷰
        self.message_window.bind("<Double-Button-1>", self.on_message_double_click)

        control_button_section = customtkinter.CTkFrame(tab, fg_color="transparent")
        control_button_section.grid(row=3, column=0, padx=10, pady=10, sticky="sew")
        self.audio_gen_button = customtkinter.CTkButton(control_button_section, text="오디오 생성", state="disabled", fg_color=self.BUTTON_COLOR, hover_color=self.BUTTON_HOVER_COLOR, text_color=self.BUTTON_TEXT_COLOR)
        self.audio_gen_button.pack(side="left", padx=5, pady=5)
        self.audio_listen_button = customtkinter.CTkButton(control_button_section, text="오디오 듣기", state="disabled", fg_color=self.BUTTON_COLOR, hover_color=self.BUTTON_HOVER_COLOR, text_color=self.BUTTON_TEXT_COLOR, command=self.start_realtime_audio)
        self.audio_listen_button.pack(side="left", padx=5, pady=5)
        other_buttons = ["썸네일 생성", "회화 비디오", "인트로 비디오", "엔딩 비디오", "대화 비디오", "정지", "종료"]
        for btn_text in other_buttons:
            customtkinter.CTkButton(control_button_section, text=btn_text, fg_color=self.BUTTON_COLOR, hover_color=self.BUTTON_HOVER_COLOR, text_color=self.BUTTON_TEXT_COLOR).pack(side="left", padx=5, pady=5)

    def on_tab_change(self):
        if self.tab_view.get() == "화자 선택":
            self.update_speaker_lists()

    def update_speaker_lists(self):
        if not self.tts_client:
            error_msg = "[ERROR] TTS client not available for voice listing."
            self.message_window.insert("end", error_msg + "\n")
            print(error_msg)
            return

        native_lang_key = self.native_lang_dropdown.get()
        learning_lang_key = self.learning_lang_dropdown.get()
        _, native_lang_code = self.language_map.get(native_lang_key, ("", ""))
        _, learning_lang_code = self.language_map.get(learning_lang_key, ("", ""))

        debug_msg1 = f"[DEBUG] 원어 언어: {native_lang_key} -> {native_lang_code}"
        debug_msg2 = f"[DEBUG] 학습어 언어: {learning_lang_key} -> {learning_lang_code}"
        debug_msg3 = f"[DEBUG] 사용 가능한 TTS 화자 수: {len(self.tts_voices)}"
        
        self.message_window.insert("end", debug_msg1 + "\n")
        self.message_window.insert("end", debug_msg2 + "\n")
        self.message_window.insert("end", debug_msg3 + "\n")
        print(debug_msg1)
        print(debug_msg2)
        print(debug_msg3)

        native_voices = sorted([v.name for v in self.tts_voices if v.language_codes[0] == native_lang_code])
        self.learning_voices = sorted([v.name for v in self.tts_voices if v.language_codes[0] == learning_lang_code])

        debug_msg4 = f"[DEBUG] 원어 화자 수: {len(native_voices)}"
        debug_msg5 = f"[DEBUG] 학습어 화자 수: {len(self.learning_voices)}"
        
        self.message_window.insert("end", debug_msg4 + "\n")
        self.message_window.insert("end", debug_msg5 + "\n")
        print(debug_msg4)
        print(debug_msg5)

        if native_voices:
            debug_msg6 = f"[DEBUG] 원어 화자 목록: {native_voices[:5]}{'...' if len(native_voices) > 5 else ''}"
            self.message_window.insert("end", debug_msg6 + "\n")
            print(debug_msg6)
        
        if self.learning_voices:
            debug_msg7 = f"[DEBUG] 학습어 화자 목록: {self.learning_voices[:5]}{'...' if len(self.learning_voices) > 5 else ''}"
            self.message_window.insert("end", debug_msg7 + "\n")
            print(debug_msg7)

        self.native_speaker_dropdown.configure(values=native_voices if native_voices else ["No voices found"])
        if native_voices:
            self.native_speaker_dropdown.set(native_voices[0])
            success_msg = f"[SUCCESS] 원어 화자 설정: {native_voices[0]}"
            self.message_window.insert("end", success_msg + "\n")
            print(success_msg)
        else:
            self.native_speaker_dropdown.set("No voices found")
            warning_msg = "[WARNING] 해당 언어의 원어 화자를 찾을 수 없습니다."
            self.message_window.insert("end", warning_msg + "\n")
            print(warning_msg)

        self.redraw_learner_speakers()
        if self.speaker_config_to_load:
            self.native_speaker_dropdown.set(self.speaker_config_to_load.get("native_speaker"))
            self.learner_count_dropdown.set(self.speaker_config_to_load.get("learner_count", "4"))
            self.redraw_learner_speakers()
            saved_speakers = self.speaker_config_to_load.get("learner_speakers", [])
            for i, widget_row in enumerate(self.learner_speaker_widgets):
                if i < len(saved_speakers):
                    widget_row['dropdown'].set(saved_speakers[i])
            self.speaker_config_to_load = None

    def redraw_learner_speakers(self, _=None):
        for row in self.learner_speaker_widgets:
            row['frame'].destroy()
        self.learner_speaker_widgets = []

        try:
            count = int(self.learner_count_dropdown.get())
        except (ValueError, TypeError):
            count = 4

        for i in range(count):
            row_frame = customtkinter.CTkFrame(self.learner_speaker_frame, fg_color="transparent")
            row_frame.pack(fill="x", pady=5, anchor="w")
            
            label = customtkinter.CTkLabel(row_frame, text=f"학습어 {i+1}:", width=120, anchor="w")
            label.pack(side="left", padx=(0, 5))
            
            dropdown = customtkinter.CTkOptionMenu(row_frame, width=500, values=self.learning_voices if self.learning_voices else ["No voices found"], fg_color=self.WIDGET_COLOR, text_color=self.TEXT_COLOR, dropdown_fg_color=self.WIDGET_COLOR)
            if self.learning_voices:
                dropdown.set(self.learning_voices[0])
            dropdown.pack(side="left", padx=5)

            preview_button = customtkinter.CTkButton(row_frame, text="미리듣기", width=80, command=lambda v=dropdown: self.preview_voice(v), fg_color=self.BUTTON_COLOR, hover_color=self.BUTTON_HOVER_COLOR, text_color=self.BUTTON_TEXT_COLOR)
            preview_button.pack(side="left", padx=5)

            self.learner_speaker_widgets.append({"frame": row_frame, "dropdown": dropdown})

    def preview_voice(self, voice_dropdown):
        if not self.tts_client:
            self.message_window.insert("end", "[ERROR] TTS client not initialized.\n")
            return
        
        voice_name = voice_dropdown.get()
        if not voice_name or voice_name == "No voices found": return

        lang_code = "-".join(voice_name.split('-')[:2])

        preview_text_map = {
            "ko-KR": "이것은 음성 미리듣기입니다.",
            "ja-JP": "これは音声プレビューです。",
            "cmn-CN": "这是一个语音预览。",
            "vi-VN": "Đây là bản xem trước giọng nói.",
            "id-ID": "Ini adalah pratinjau suara.",
            "it-IT": "Questa è un'anteprima vocale.",
            "es-US": "Esta es una vista previa de voz.",
            "fr-FR": "Ceci est un aperçu vocal.",
            "de-DE": "Dies ist eine Sprachvorschau."
        }
        text_to_speak = preview_text_map.get(lang_code, "This is a voice preview.")

        synthesis_input = texttospeech.SynthesisInput(text=text_to_speak)
        voice = texttospeech.VoiceSelectionParams(language_code=lang_code, name=voice_name)
        audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)

        try:
            self.message_window.insert("end", f"[INFO] Synthesizing preview for {voice_name}...\n")
            response = self.tts_client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
            
            project_name = self.project_name_entry.get()
            identifier = self.identifier_entry.get()
            output_dir = os.path.join("output", project_name, identifier)
            os.makedirs(output_dir, exist_ok=True)
            temp_file = os.path.join(output_dir, f"{identifier}_preview.mp3")

            with open(temp_file, "wb") as out:
                out.write(response.audio_content)
            
            pygame.mixer.music.load(temp_file)
            pygame.mixer.music.play()
            self.message_window.insert("end", "[SUCCESS] Playing preview.\n")

        except Exception as e:
            self.message_window.insert("end", f"[ERROR] Failed to synthesize preview: {e}\n")

    def create_speaker_selection_tab(self, tab):
        main_frame = customtkinter.CTkFrame(tab, fg_color="transparent")
        main_frame.pack(padx=10, pady=10, fill="both", expand=True)

        native_speaker_frame = customtkinter.CTkFrame(main_frame, fg_color="transparent")
        native_speaker_frame.pack(fill="x", pady=5, anchor="w")
        customtkinter.CTkLabel(native_speaker_frame, text="원어 화자:", width=120, anchor="w").pack(side="left", padx=(0, 5))
        self.native_speaker_dropdown = customtkinter.CTkOptionMenu(native_speaker_frame, width=500, values=["N/A"], fg_color=self.WIDGET_COLOR, text_color=self.TEXT_COLOR, dropdown_fg_color=self.WIDGET_COLOR)
        self.native_speaker_dropdown.pack(side="left", padx=5)
        customtkinter.CTkButton(native_speaker_frame, text="미리듣기", width=80, command=lambda: self.preview_voice(self.native_speaker_dropdown), fg_color=self.BUTTON_COLOR, hover_color=self.BUTTON_HOVER_COLOR, text_color=self.BUTTON_TEXT_COLOR).pack(side="left", padx=5)

        self.learner_speaker_frame = customtkinter.CTkFrame(main_frame, fg_color="transparent")
        self.learner_speaker_frame.pack(fill="x", pady=20, anchor="w")

        count_frame = customtkinter.CTkFrame(self.learner_speaker_frame, fg_color="transparent")
        count_frame.pack(fill="x", pady=(0, 10), anchor="w")
        customtkinter.CTkLabel(count_frame, text="학습어 화자 수:", width=120, anchor="w").pack(side="left", padx=(0, 5))
        self.learner_count_dropdown = customtkinter.CTkOptionMenu(count_frame, width=80, values=[str(i) for i in range(1, 11)], command=self.redraw_learner_speakers, fg_color=self.WIDGET_COLOR, text_color=self.TEXT_COLOR, dropdown_fg_color=self.WIDGET_COLOR)
        self.learner_count_dropdown.set("4")
        self.learner_count_dropdown.pack(side="left", padx=5)

        save_button_frame = customtkinter.CTkFrame(main_frame, fg_color="transparent")
        save_button_frame.pack(fill="x", pady=20, anchor="w")
        customtkinter.CTkButton(save_button_frame, text="화자 설정 저장", command=self.save_config, fg_color=self.BUTTON_COLOR, hover_color=self.BUTTON_HOVER_COLOR, text_color=self.BUTTON_TEXT_COLOR).pack(anchor="w")

    def create_image_settings_tab(self, tab):
        # 레이아웃: 공통 설정(행0), 텍스트 설정(행1), 메시지 창(행2), 콘트롤(행3)
        tab.grid_rowconfigure(0, weight=0)
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_rowconfigure(2, weight=1)
        tab.grid_rowconfigure(3, weight=0)
        tab.grid_columnconfigure(0, weight=1)

        # 공통 설정 섹션
        common = customtkinter.CTkFrame(tab, fg_color="transparent")
        common.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))
        for i in range(16):
            common.grid_columnconfigure(i, weight=0)
        common.grid_columnconfigure(16, weight=1)

        # 1행: 화면 비율, 해상도
        customtkinter.CTkLabel(common, text="화면 비율").grid(row=0, column=0, padx=(0, 6), pady=6, sticky="w")
        self.aspect_var = tkinter.StringVar(value="16:9")
        self.aspect_dd = customtkinter.CTkOptionMenu(common, variable=self.aspect_var, values=["16:9", "9:16", "1:1", "4:3"], width=120,
                                                     fg_color=self.WIDGET_COLOR, text_color=self.TEXT_COLOR, dropdown_fg_color=self.WIDGET_COLOR)
        self.aspect_dd.grid(row=0, column=1, padx=(0, 12), pady=6, sticky="w")

        customtkinter.CTkLabel(common, text="해상도").grid(row=0, column=2, padx=(0, 6), pady=6, sticky="w")
        self.res_var = tkinter.StringVar(value="1920x1080")
        self.res_dd = customtkinter.CTkOptionMenu(common, variable=self.res_var, values=["3840x2160", "2560x1440", "1920x1080", "1080x1920", "1080x1080"], width=140,
                                                  fg_color=self.WIDGET_COLOR, text_color=self.TEXT_COLOR, dropdown_fg_color=self.WIDGET_COLOR)
        self.res_dd.grid(row=0, column=3, padx=(0, 12), pady=6, sticky="w")

        # 2행: 배경 설정: 라디오(색상/이미지/비디오), 입력, 찾아보기
        customtkinter.CTkLabel(common, text="배경 설정:").grid(row=1, column=0, padx=(0, 6), pady=6, sticky="w")
        self.bg_type_var = tkinter.StringVar(value="색상")
        customtkinter.CTkRadioButton(common, text="색상", variable=self.bg_type_var, value="색상", command=self.on_change_bg_type).grid(row=1, column=1, padx=(0, 6), pady=6, sticky="w")
        customtkinter.CTkRadioButton(common, text="이미지", variable=self.bg_type_var, value="이미지", command=self.on_change_bg_type).grid(row=1, column=2, padx=(0, 6), pady=6, sticky="w")
        customtkinter.CTkRadioButton(common, text="비디오", variable=self.bg_type_var, value="비디오", command=self.on_change_bg_type).grid(row=1, column=3, padx=(0, 6), pady=6, sticky="w")
        self.ent_bg_value = customtkinter.CTkEntry(common, width=320, placeholder_text="#RRGGBB 또는 경로")
        self.ent_bg_value.grid(row=1, column=4, padx=(8, 6), pady=6, sticky="w")
        customtkinter.CTkButton(common, text="찾아보기", command=self.on_browse_bg).grid(row=1, column=5, padx=(0, 12), pady=6, sticky="w")

        # 3행: 바탕 설정: 바탕색, 투명도(입력), 여백(드롭다운)
        customtkinter.CTkLabel(common, text="바탕 설정:").grid(row=2, column=0, padx=(0, 6), pady=6, sticky="w")
        customtkinter.CTkLabel(common, text="바탕색").grid(row=2, column=1, padx=(0, 6), pady=6, sticky="w")
        self.bg_color_ent = customtkinter.CTkEntry(common, width=120, placeholder_text="#202020")
        self.bg_color_ent.grid(row=2, column=2, padx=(0, 12), pady=6, sticky="w")
        customtkinter.CTkLabel(common, text="투명도").grid(row=2, column=3, padx=(0, 6), pady=6, sticky="w")
        self.opacity_entry = customtkinter.CTkEntry(common, width=100, placeholder_text="1.0")
        self.opacity_entry.grid(row=2, column=4, padx=(0, 12), pady=6, sticky="w")
        customtkinter.CTkLabel(common, text="여백").grid(row=2, column=5, padx=(0, 6), pady=6, sticky="w")
        self.padding_var = tkinter.StringVar(value="16")
        self.padding_dd = customtkinter.CTkOptionMenu(common, variable=self.padding_var, values=["0","4","8","12","16","24","32","48"], width=100,
                                                      fg_color=self.WIDGET_COLOR, text_color=self.TEXT_COLOR, dropdown_fg_color=self.WIDGET_COLOR)
        self.padding_dd.grid(row=2, column=6, padx=(0, 12), pady=6, sticky="w")

        # 4행: 쉐도우 설정
        customtkinter.CTkLabel(common, text="쉐도우 설정:").grid(row=3, column=0, padx=(0, 6), pady=6, sticky="w")
        customtkinter.CTkLabel(common, text="두께").grid(row=3, column=1, padx=(0, 6), pady=6, sticky="w")
        self.shadow_thickness_ent = customtkinter.CTkEntry(common, width=80, placeholder_text="8")
        self.shadow_thickness_ent.grid(row=3, column=2, padx=(0, 12), pady=6, sticky="w")
        customtkinter.CTkLabel(common, text="쉐도우 색상").grid(row=3, column=3, padx=(0, 6), pady=6, sticky="w")
        self.shadow_color_ent = customtkinter.CTkEntry(common, width=120, placeholder_text="#000000")
        self.shadow_color_ent.grid(row=3, column=4, padx=(0, 12), pady=6, sticky="w")

        # 5행: 외곽선 설정
        customtkinter.CTkLabel(common, text="외곽선 설정:").grid(row=4, column=0, padx=(0, 6), pady=6, sticky="w")
        customtkinter.CTkLabel(common, text="두께").grid(row=4, column=1, padx=(0, 6), pady=6, sticky="w")
        self.border_thickness_ent = customtkinter.CTkEntry(common, width=80, placeholder_text="2")
        self.border_thickness_ent.grid(row=4, column=2, padx=(0, 12), pady=6, sticky="w")
        customtkinter.CTkLabel(common, text="외곽선 색상").grid(row=4, column=3, padx=(0, 6), pady=6, sticky="w")
        self.border_color_ent = customtkinter.CTkEntry(common, width=120, placeholder_text="#FFFFFF")
        self.border_color_ent.grid(row=4, column=4, padx=(0, 12), pady=6, sticky="w")

        # 텍스트 설정 섹션(5개 탭) – 기존 그리드 유틸 재사용
        text_frame = customtkinter.CTkFrame(tab, fg_color="transparent")
        text_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        text_frame.grid_rowconfigure(0, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)

        self.text_tabs = customtkinter.CTkTabview(text_frame)
        self.text_tabs.grid(row=0, column=0, sticky="nsew")

        # 기본값(사양)
        self.text_config_defaults = {
            "회화 설정": [
                {"행": "순번", "l": 50, "r": 50, "v": 80, "크기(px)": 100, "폰트(pt)": "KoPubWorldDotum", "색상": "#H00FFFFFF", "굵기": "Bold", "좌우 정렬": "Left", "상하 정렬": "Top"},
                {"행": "원어", "l": 50, "r": 50, "v": 80, "크기(px)": 100, "폰트(pt)": "KoPubWorldDotum", "색상": "#H0000FFFF", "굵기": "Bold", "좌우 정렬": "Left", "상하 정렬": "Top"},
                {"행": "학습어", "l": 50, "r": 50, "v": 80, "크기(px)": 100, "폰트(pt)": "Noto Sans Gothic", "색상": "#H00FF00FF", "굵기": "Bold", "좌우 정렬": "Left", "상하 정렬": "Top"},
                {"행": "읽기", "l": 50, "r": 50, "v": 80, "크기(px)": 100, "폰트(pt)": "KoPubWorldDotum", "색상": "#H00FFFF00", "굵기": "Bold", "좌우 정렬": "Left", "상하 정렬": "Top"},
            ],
            "썸네일 설정": [
                {"행": "1행", "l": 50, "r": 50, "v": 80, "크기(px)": 100, "폰트(pt)": "KoPubWorldDotum", "색상": "#H00FFFFFF", "굵기": "Bold", "좌우 정렬": "Left", "상하 정렬": "Top"},
                {"행": "2행", "l": 50, "r": 50, "v": 80, "크기(px)": 100, "폰트(pt)": "KoPubWorldDotum", "색상": "#H0000FFFF", "굵기": "Bold", "좌우 정렬": "Left", "상하 정렬": "Top"},
                {"행": "3행", "l": 50, "r": 50, "v": 80, "크기(px)": 100, "폰트(pt)": "KoPubWorldDotum", "색상": "#H00FF00FF", "굵기": "Bold", "좌우 정렬": "Left", "상하 정렬": "Top"},
                {"행": "4행", "l": 50, "r": 50, "v": 80, "크기(px)": 100, "폰트(pt)": "KoPubWorldDotum", "색상": "#H00FFFF00", "굵기": "Bold", "좌우 정렬": "Left", "상하 정렬": "Top"},
            ],
            "인트로 설정": [
                {"행": "1행", "l": 50, "r": 50, "v": 80, "크기(px)": 100, "폰트(pt)": "KoPubWorldDotum", "색상": "#H00FFFFFF", "굵기": "Bold", "좌우 정렬": "Left", "상하 정렬": "Top"},
            ],
            "엔딩 설정": [
                {"행": "1행", "l": 50, "r": 50, "v": 80, "크기(px)": 100, "폰트(pt)": "KoPubWorldDotum", "색상": "#H00FFFFFF", "굵기": "Bold", "좌우 정렬": "Left", "상하 정렬": "Top"},
            ],
            "스크립트 설정": [
                {"행": "원어", "l": 50, "r": 50, "v": 80, "크기(px)": 100, "폰트(pt)": "KoPubWorldDotum", "색상": "#H00FFFFFF", "굵기": "Bold", "좌우 정렬": "Left", "상하 정렬": "Top"},
                {"행": "학습어1", "l": 50, "r": 50, "v": 80, "크기(px)": 100, "폰트(pt)": "KoPubWorldDotum", "색상": "#H00FFFFFF", "굵기": "Bold", "좌우 정렬": "Left", "상하 정렬": "Top"},
                {"행": "학습어2", "l": 50, "r": 50, "v": 80, "크기(px)": 100, "폰트(pt)": "KoPubWorldDotum", "색상": "#H00FFFFFF", "굵기": "Bold", "좌우 정렬": "Left", "상하 정렬": "Top"},
            ],
        }

        self.text_tab_frames = {}
        for tab_name, defaults in self.text_config_defaults.items():
            t = self.text_tabs.add(tab_name)
            self.text_tab_frames[tab_name] = t
            self._build_single_text_tab(t, tab_name, defaults)

        # 메시지 창
        msg = customtkinter.CTkFrame(tab, fg_color="transparent")
        msg.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        msg.grid_rowconfigure(0, weight=1)
        msg.grid_columnconfigure(0, weight=1)
        self.img_settings_json = customtkinter.CTkTextbox(msg, fg_color=self.WIDGET_COLOR, text_color=self.TEXT_COLOR, border_color=self.BG_COLOR, border_width=1)
        self.img_settings_json.grid(row=0, column=0, sticky="nsew")
        self._refresh_image_settings_json()

        # 콘트롤 섹션: 설정 저장/읽기
        ctrl = customtkinter.CTkFrame(tab, fg_color="transparent")
        ctrl.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 10))
        customtkinter.CTkButton(ctrl, text="설정 저장", command=self.on_image_settings_save,
                                 fg_color=self.BUTTON_COLOR, hover_color=self.BUTTON_HOVER_COLOR, text_color=self.BUTTON_TEXT_COLOR).pack(side="left", padx=(0, 8))
        customtkinter.CTkButton(ctrl, text="설정 읽기", command=self.on_image_settings_load,
                                 fg_color=self.BUTTON_COLOR, hover_color=self.BUTTON_HOVER_COLOR, text_color=self.BUTTON_TEXT_COLOR).pack(side="left", padx=(0, 8))

    # ----- 이미지 설정 탭: 텍스트 탭 1개 렌더 -----
    def _build_single_text_tab(self, tab, tab_name: str, default_rows: list) -> None:
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        ctrl = customtkinter.CTkFrame(tab, fg_color="transparent")
        ctrl.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        customtkinter.CTkLabel(ctrl, text="텍스트 행수").grid(row=0, column=0, padx=(0, 6), pady=4, sticky="w")
        var = tkinter.StringVar(value=str(len(default_rows)))
        opt = customtkinter.CTkOptionMenu(ctrl, variable=var, values=[str(i) for i in range(1, 11)],
                                          width=80, fg_color=self.WIDGET_COLOR, text_color=self.TEXT_COLOR, dropdown_fg_color=self.WIDGET_COLOR,
                                          command=lambda v, n=tab_name: self._on_change_text_row_count(n, int(v)))
        opt.grid(row=0, column=1, padx=(0, 12), pady=4, sticky="w")
        setattr(self, f"text_count_var_{tab_name}", var)

        grid_container = customtkinter.CTkScrollableFrame(tab, fg_color=self.WIDGET_COLOR)
        grid_container.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        setattr(self, f"text_grid_{tab_name}", grid_container)
        self._render_text_grid(grid_container, list(default_rows), tab_name)
        setattr(self, f"text_rows_{tab_name}", list(default_rows))

    def chars_to_pixels(self, chars: int) -> int:
        try:
            return max(40, int(chars) * 8)
        except Exception:
            return 120

    def _render_text_grid(self, container, rows: list, tab_name: str) -> None:
        for widget in container.winfo_children():
            widget.destroy()

        headers = ["행", "l", "r", "v", "크기(px)", "폰트(pt)", "색상", "굵기", "좌우 정렬", "상하 정렬"]
        col_widths = [5, 5, 5, 6, 5, 30, 10, 8, 8, 8]

        for col, header in enumerate(headers):
            lbl = customtkinter.CTkLabel(container, text=header, fg_color="#2c2c2c")
            lbl.grid(row=0, column=col, padx=6, pady=6, sticky="nsew")
            container.grid_columnconfigure(col, weight=1)

        widgets_map = {}
        for row_idx, row_data in enumerate(rows, start=1):
            # 행
            ent_title = customtkinter.CTkEntry(container, width=self.chars_to_pixels(col_widths[0]), justify="center")
            ent_title.insert(0, str(row_data.get("행", "")))
            ent_title.grid(row=row_idx, column=0, padx=6, pady=4, sticky="nsew")
            widgets_map[(row_idx, "행")] = ent_title

            # l, r, v, 크기(px)
            for i, key in enumerate(["l", "r", "v", "크기(px)"]):
                ent = customtkinter.CTkEntry(container, width=self.chars_to_pixels(col_widths[1 + i]), justify="center")
                ent.insert(0, str(row_data.get(key, "")))
                ent.grid(row=row_idx, column=1 + i, padx=6, pady=4, sticky="nsew")
                widgets_map[(row_idx, key)] = ent

            # 폰트
            ent_font = customtkinter.CTkEntry(container, width=self.chars_to_pixels(col_widths[5]), justify="center")
            ent_font.insert(0, str(row_data.get("폰트(pt)", "")))
            ent_font.grid(row=row_idx, column=5, padx=6, pady=4, sticky="nsew")
            widgets_map[(row_idx, "폰트(pt)")] = ent_font

            # 색상
            ent_color = customtkinter.CTkEntry(container, width=self.chars_to_pixels(col_widths[6]), justify="center")
            ent_color.insert(0, str(row_data.get("색상", "")))
            ent_color.grid(row=row_idx, column=6, padx=6, pady=4, sticky="nsew")
            widgets_map[(row_idx, "색상")] = ent_color

            # 굵기
            weight_var = tkinter.StringVar(value=str(row_data.get("굵기", "Bold")))
            opt_weight = customtkinter.CTkOptionMenu(container, variable=weight_var, values=["Thin", "Regular", "Medium", "Bold"], width=self.chars_to_pixels(col_widths[7]),
                                                    fg_color=self.WIDGET_COLOR, text_color=self.TEXT_COLOR, dropdown_fg_color=self.WIDGET_COLOR)
            opt_weight.grid(row=row_idx, column=7, padx=6, pady=4, sticky="nsew")
            widgets_map[(row_idx, "굵기")] = opt_weight

            # 좌우 정렬
            halign_var = tkinter.StringVar(value=str(row_data.get("좌우 정렬", "Left")))
            opt_halign = customtkinter.CTkOptionMenu(container, variable=halign_var, values=["Left", "Center", "Right"], width=self.chars_to_pixels(col_widths[8]),
                                                    fg_color=self.WIDGET_COLOR, text_color=self.TEXT_COLOR, dropdown_fg_color=self.WIDGET_COLOR)
            opt_halign.grid(row=row_idx, column=8, padx=6, pady=4, sticky="nsew")
            widgets_map[(row_idx, "좌우 정렬")] = opt_halign

            # 상하 정렬
            valign_var = tkinter.StringVar(value=str(row_data.get("상하 정렬", "Top")))
            opt_valign = customtkinter.CTkOptionMenu(container, variable=valign_var, values=["Top", "Middle", "Bottom"], width=self.chars_to_pixels(col_widths[9]),
                                                    fg_color=self.WIDGET_COLOR, text_color=self.TEXT_COLOR, dropdown_fg_color=self.WIDGET_COLOR)
            opt_valign.grid(row=row_idx, column=9, padx=6, pady=4, sticky="nsew")
            widgets_map[(row_idx, "상하 정렬")] = opt_valign

        setattr(self, f"text_widgets_{tab_name}", widgets_map)

    def _on_change_text_row_count(self, tab_name: str, new_count: int) -> None:
        rows = list(getattr(self, f"text_rows_{tab_name}", []))
        if new_count > len(rows):
            # 마지막 행을 복제하여 확장
            template = rows[-1] if rows else {"행": f"{len(rows)+1}행", "l": 50, "r": 50, "v": 80, "크기(px)": 100, "폰트(pt)": "KoPubWorldDotum", "색상": "#H00FFFFFF", "굵기": "Bold", "좌우 정렬": "Left", "상하 정렬": "Top"}
            while len(rows) < new_count:
                new_row = dict(template)
                new_row["행"] = f"{len(rows)+1}행"
                rows.append(new_row)
        elif new_count < len(rows):
            rows = rows[:new_count]
        setattr(self, f"text_rows_{tab_name}", rows)
        grid_container = getattr(self, f"text_grid_{tab_name}")
        self._render_text_grid(grid_container, rows, tab_name)
        self._refresh_image_settings_json()

    # ----- 이미지 설정: 공통 설정 수집/적용/미리보기 JSON -----
    def _collect_image_settings_config(self) -> dict:
        data = {
            "aspect": getattr(self, "aspect_var", tkinter.StringVar(value="16:9")).get(),
            "resolution": getattr(self, "res_var", tkinter.StringVar(value="1920x1080")).get(),
            "bg_type": getattr(self, "bg_type_var", tkinter.StringVar(value="색상")).get(),
            "bg_value": self.ent_bg_value.get().strip() if hasattr(self, "ent_bg_value") else "",
            "bg_color": self.bg_color_ent.get().strip() if hasattr(self, "bg_color_ent") else "",
            "opacity": self._safe_float_get(getattr(self, "opacity_entry", None), default=1.0),
            "padding": getattr(self, "padding_var", tkinter.StringVar(value="16")).get(),
            "shadow_thickness": self.shadow_thickness_ent.get().strip() if hasattr(self, "shadow_thickness_ent") else "",
            "shadow_color": self.shadow_color_ent.get().strip() if hasattr(self, "shadow_color_ent") else "",
            "border_thickness": self.border_thickness_ent.get().strip() if hasattr(self, "border_thickness_ent") else "",
            "border_color": self.border_color_ent.get().strip() if hasattr(self, "border_color_ent") else "",
        }
        # 텍스트 탭 수집
        text_cfg = {}
        for tab_name in getattr(self, "text_config_defaults", {}).keys():
            text_cfg[tab_name] = self._collect_text_tab_rows(tab_name)
        data["text_tabs"] = text_cfg
        return data

    def _collect_text_tab_rows(self, tab_name: str) -> list:
        rows = []
        widgets_map = getattr(self, f"text_widgets_{tab_name}", {})
        if not widgets_map:
            return list(getattr(self, f"text_rows_{tab_name}", []))
        # 찾을 행 인덱스들
        row_indices = sorted({r for (r, _k) in widgets_map.keys()})
        for r in row_indices:
            row = {
                "행": widgets_map[(r, "행")].get().strip() if (r, "행") in widgets_map else "",
                "l": self._safe_int_get(widgets_map.get((r, "l"))),
                "r": self._safe_int_get(widgets_map.get((r, "r"))),
                "v": self._safe_int_get(widgets_map.get((r, "v"))),
                "크기(px)": self._safe_int_get(widgets_map.get((r, "크기(px)"))),
                "폰트(pt)": widgets_map.get((r, "폰트(pt)"), None).get().strip() if (r, "폰트(pt)") in widgets_map else "",
                "색상": widgets_map.get((r, "색상"), None).get().strip() if (r, "색상") in widgets_map else "",
                "굵기": widgets_map.get((r, "굵기"), None).get().strip() if (r, "굵기") in widgets_map else "Bold",
                "좌우 정렬": widgets_map.get((r, "좌우 정렬"), None).get().strip() if (r, "좌우 정렬") in widgets_map else "Left",
                "상하 정렬": widgets_map.get((r, "상하 정렬"), None).get().strip() if (r, "상하 정렬") in widgets_map else "Top",
            }
            rows.append(row)
        return rows

    def _safe_int_get(self, widget) -> int:
        try:
            if widget is None:
                return 0
            return int(widget.get())
        except Exception:
            try:
                return int(float(widget.get()))
            except Exception:
                return 0

    def _safe_float_get(self, widget, default: float = 0.0) -> float:
        try:
            if widget is None:
                return default
            return float(widget.get())
        except Exception:
            return default

    def _apply_image_settings_config(self, cfg: dict) -> None:
        try:
            if not isinstance(cfg, dict):
                return
            if "aspect" in cfg:
                self.aspect_var.set(cfg.get("aspect"))
            if "resolution" in cfg:
                self.res_var.set(cfg.get("resolution"))
            if "bg_type" in cfg:
                self.bg_type_var.set(cfg.get("bg_type"))
            if "bg_value" in cfg and hasattr(self, "ent_bg_value"):
                self.ent_bg_value.delete(0, "end"); self.ent_bg_value.insert(0, cfg.get("bg_value", ""))
            if "bg_color" in cfg and hasattr(self, "bg_color_ent"):
                self.bg_color_ent.delete(0, "end"); self.bg_color_ent.insert(0, cfg.get("bg_color", ""))
            if "opacity" in cfg and hasattr(self, "opacity_entry"):
                self.opacity_entry.delete(0, "end"); self.opacity_entry.insert(0, str(cfg.get("opacity", 1.0)))
            if "padding" in cfg and hasattr(self, "padding_var"):
                self.padding_var.set(str(cfg.get("padding", "16")))
            if "shadow_thickness" in cfg and hasattr(self, "shadow_thickness_ent"):
                self.shadow_thickness_ent.delete(0, "end"); self.shadow_thickness_ent.insert(0, str(cfg.get("shadow_thickness", "")))
            if "shadow_color" in cfg and hasattr(self, "shadow_color_ent"):
                self.shadow_color_ent.delete(0, "end"); self.shadow_color_ent.insert(0, cfg.get("shadow_color", ""))
            if "border_thickness" in cfg and hasattr(self, "border_thickness_ent"):
                self.border_thickness_ent.delete(0, "end"); self.border_thickness_ent.insert(0, str(cfg.get("border_thickness", "")))
            if "border_color" in cfg and hasattr(self, "border_color_ent"):
                self.border_color_ent.delete(0, "end"); self.border_color_ent.insert(0, cfg.get("border_color", ""))

            # 텍스트 탭 적용
            text_tabs = cfg.get("text_tabs", {})
            if isinstance(text_tabs, dict):
                for tab_name, rows in text_tabs.items():
                    grid_container = getattr(self, f"text_grid_{tab_name}", None)
                    if grid_container is not None:
                        setattr(self, f"text_rows_{tab_name}", list(rows))
                        # 행수 셀렉터 갱신
                        var = getattr(self, f"text_count_var_{tab_name}", None)
                        if var is not None:
                            var.set(str(len(rows)))
                        self._render_text_grid(grid_container, rows, tab_name)
        except Exception:
            pass

    def _refresh_image_settings_json(self) -> None:
        try:
            if not hasattr(self, "img_settings_json"):
                return
            cfg = self._collect_image_settings_config()
            self.img_settings_json.delete("1.0", "end")
            self.img_settings_json.insert("1.0", json.dumps(cfg, ensure_ascii=False, indent=2))
        except Exception:
            pass

    def on_image_settings_save(self) -> None:
        try:
            cfg = self._collect_image_settings_config()
            with open("image_settings.json", "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
            if hasattr(self, "message_window"):
                self.message_window.insert("end", "[SUCCESS] 이미지 설정 저장: image_settings.json\n")
                self.message_window.see("end")
            self._refresh_image_settings_json()
        except Exception as e:
            if hasattr(self, "message_window"):
                self.message_window.insert("end", f"[ERROR] 이미지 설정 저장 실패: {e}\n")
                self.message_window.see("end")

    def on_image_settings_load(self) -> None:
        try:
            if not os.path.exists("image_settings.json"):
                if hasattr(self, "message_window"):
                    self.message_window.insert("end", "[INFO] image_settings.json 이(가) 없습니다.\n")
                    self.message_window.see("end")
                return
            with open("image_settings.json", "r", encoding="utf-8") as f:
                cfg = json.load(f)
            self._apply_image_settings_config(cfg)
            self._refresh_image_settings_json()
            if hasattr(self, "message_window"):
                self.message_window.insert("end", "[SUCCESS] 이미지 설정 로드 완료\n")
                self.message_window.see("end")
        except Exception as e:
            if hasattr(self, "message_window"):
                self.message_window.insert("end", f"[ERROR] 이미지 설정 로드 실패: {e}\n")
                self.message_window.see("end")

    def on_change_bg_type(self) -> None:
        try:
            bg_type = self.bg_type_var.get()
            if bg_type == "색상":
                self.ent_bg_value.configure(placeholder_text="#RRGGBB")
            elif bg_type == "이미지":
                self.ent_bg_value.configure(placeholder_text="jpg/png 파일 경로")
            else:
                self.ent_bg_value.configure(placeholder_text="mp4 파일 경로")
            self._refresh_image_settings_json()
        except Exception:
            pass

    def on_browse_bg(self) -> None:
        try:
            bg_type = self.bg_type_var.get()
            if bg_type == "색상":
                color = askcolor(title="배경색 선택")[1]
                if color:
                    self.ent_bg_value.delete(0, "end"); self.ent_bg_value.insert(0, color)
            elif bg_type == "이미지":
                path = filedialog.askopenfilename(filetypes=[("Image Files", "*.jpg;*.jpeg;*.png")])
                if path:
                    self.ent_bg_value.delete(0, "end"); self.ent_bg_value.insert(0, path)
            else:
                path = filedialog.askopenfilename(filetypes=[("Video Files", "*.mp4")])
                if path:
                    self.ent_bg_value.delete(0, "end"); self.ent_bg_value.insert(0, path)
            self._refresh_image_settings_json()
        except Exception as e:
            if hasattr(self, "message_window"):
                self.message_window.insert("end", f"[ERROR] 배경 선택 실패: {e}\n")
                self.message_window.see("end")

    def create_text_setting_grid(self, parent_tab, initial_rows, defaults):
        # 사용되지 않음(호환용)
        return

    # 공용 로그 출력 메서드
    def log(self, message: str) -> None:
        try:
            if hasattr(self, "message_window") and self.message_window is not None:
                self.message_window.insert("end", message + "\n")
                self.message_window.see("end")
            else:
                print(message)
        except Exception:
            print(message)

    # 메시지 창에서 Space로 파일 프리뷰
    def on_message_space_preview(self, event=None):
        try:
            sel = None
            try:
                if self.message_window.tag_ranges("sel"):
                    sel = self.message_window.get("sel.first", "sel.last")
            except Exception:
                sel = None
            if not sel:
                # 현재 커서 라인 사용
                line_start = self.message_window.index("insert linestart")
                line_end = self.message_window.index("insert lineend")
                sel = self.message_window.get(line_start, line_end)
            path = self._extract_path_from_text(sel)
            if not path:
                self.message_window.insert("end", "[INFO] 선택된 텍스트에서 파일 경로를 찾지 못했습니다.\n")
                self.message_window.see("end")
                return
            abs_path = self._to_abs_path(path)
            if not os.path.isfile(abs_path):
                self.message_window.insert("end", f"[INFO] 파일이 존재하지 않습니다: {abs_path}\n")
                self.message_window.see("end")
                return
            self._preview_text_file(abs_path)
        except Exception as e:
            try:
                self.message_window.insert("end", f"[ERROR] 프리뷰 실패: {e}\n")
                self.message_window.see("end")
            except Exception:
                pass

    def _extract_path_from_text(self, text: str) -> str | None:
        if not text:
            return None
        # 경로 후보 추출: /로 시작하는 토큰 또는 output/... 형태
        m = re.search(r"(/[^\s]+)", text)
        if m:
            return m.group(1)
        m2 = re.search(r"\boutput/[^\s]+", text)
        if m2:
            return m2.group(0)
        return None

    def _to_abs_path(self, path: str) -> str:
        if os.path.isabs(path):
            return path
        base = os.path.dirname(__file__)
        return os.path.join(base, path)

    def _preview_text_file(self, abs_path: str) -> None:
        try:
            dlg = customtkinter.CTkToplevel(self)
            dlg.title(os.path.basename(abs_path))
            dlg.geometry("900x600")
            frame = customtkinter.CTkFrame(dlg)
            frame.pack(fill="both", expand=True, padx=8, pady=8)
            txt = customtkinter.CTkTextbox(frame)
            txt.pack(fill="both", expand=True)
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            txt.insert("1.0", content)
            txt.configure(state="disabled")
        except Exception as e:
            self.message_window.insert("end", f"[ERROR] 파일 프리뷰 중 오류: {e}\n")
            self.message_window.see("end")

    def on_message_double_click(self, event=None):
        try:
            # 클릭 좌표의 라인 텍스트 추출
            if event is not None:
                index_start = self.message_window.index(f"@{event.x},{event.y} linestart")
                index_end = self.message_window.index(f"@{event.x},{event.y} lineend")
            else:
                index_start = self.message_window.index("insert linestart")
                index_end = self.message_window.index("insert lineend")
            line_text = self.message_window.get(index_start, index_end)
            path = self._extract_path_from_text(line_text)
            if not path:
                self.message_window.insert("end", "[INFO] 해당 라인에서 파일 경로를 찾지 못했습니다.\n")
                self.message_window.see("end")
                return
            abs_path = self._to_abs_path(path)
            if not os.path.isfile(abs_path):
                self.message_window.insert("end", f"[INFO] 파일이 존재하지 않습니다: {abs_path}\n")
                self.message_window.see("end")
                return
            self._preview_text_file(abs_path)
        except Exception as e:
            self.message_window.insert("end", f"[ERROR] 더블클릭 프리뷰 실패: {e}\n")
            self.message_window.see("end")

    # ---------- AI Prompt 렌더링 유틸 ----------
    def _collect_prompt_vars(self) -> dict:
        native_lang_key = self.native_lang_dropdown.get()
        learning_lang_key = self.learning_lang_dropdown.get()
        native_code, native_locale = self.language_map.get(native_lang_key, ("", ""))
        learning_code, learning_locale = self.language_map.get(learning_lang_key, ("", ""))
        gem = self.ai_settings.get("Gemini", {})
        vars_map = {
            "project_name": self.project_name_entry.get(),
            "identifier": self.identifier_entry.get(),
            "native_lang": native_lang_key,
            "learning_lang": learning_lang_key,
            "native_code": native_code,
            "learning_code": learning_code,
            "native_locale": native_locale,
            "learning_locale": learning_locale,
            "topic": self.topic_entry.get() if self.topic_entry.get() else self.topic_dropdown.get(),
            "level": self.level_dropdown.get(),
            "count": self.count_dropdown.get(),
            "gemini_model": gem.get("model", ""),
            "gemini_locale": gem.get("locale", ""),
        }
        return vars_map

    def _read_ai_prompt_template(self) -> str:
        try:
            base_dir = os.path.dirname(__file__)
            candidates = [
                os.path.join(base_dir, "AI Prompt.txt"),
                os.path.join(base_dir, "AI Prompt"),
            ]
            for prompt_path in candidates:
                if os.path.exists(prompt_path):
                    with open(prompt_path, "r", encoding="utf-8") as f:
                        return f.read()
        except Exception:
            pass
        return ""

    def _render_template(self, template_str: str, variables: dict) -> str:
        # 간단 치환 렌더러: {{key}} 와 한국어 대괄호 토큰([원어] 등) 모두 지원
        rendered = template_str or ""
        try:
            # 1) {{key}} 치환
            for k, v in variables.items():
                rendered = rendered.replace("{{" + k + "}}", str(v))

            # 2) 한국어 대괄호 토큰 치환
            bracket_map = {
                "[원어]": variables.get("native_lang", ""),
                "[학습어]": variables.get("learning_lang", ""),
                "[등급]": variables.get("level", ""),
                "[주제]": variables.get("topic", ""),
                # 코드/로케일 변형
                "[원어코드]": variables.get("native_code", ""),
                "[학습어코드]": variables.get("learning_code", ""),
                "[원어_코드]": variables.get("native_code", ""),
                "[학습어_코드]": variables.get("learning_code", ""),
                "[원어로케일]": variables.get("native_locale", ""),
                "[학습어로케일]": variables.get("learning_locale", ""),
                "[원어_로케일]": variables.get("native_locale", ""),
                "[학습어_로케일]": variables.get("learning_locale", ""),
            }
            for k, v in bracket_map.items():
                rendered = rendered.replace(k, str(v))
        except Exception:
            pass
        return rendered

    # ---------- AI JSON 후처리 (대화 CSV 교정/생성) ----------
    def _contains_hangul(self, text: str) -> bool:
        return any('\uac00' <= ch <= '\ud7a3' for ch in str(text))

    def _maybe_fix_dialogue_csv(self, ai_data: dict, vars_map: dict) -> dict:
        try:
            fvs = ai_data.get("fullVideoScript") or {}
            csv_text = fvs.get("dialogueCsv")
            if not isinstance(csv_text, str) or "순번" not in csv_text:
                return ai_data
            lines = [ln for ln in csv_text.splitlines() if ln.strip()]
            if not lines:
                return ai_data
            header = lines[0].strip()
            rows = [ln.split(',') for ln in lines[1:]]
            # 기대 헤더: 순번,원어,학습어,읽기
            if header.replace(' ', '') != "순번,원어,학습어,읽기":
                # 헤더 교정 시도
                header = "순번,원어,학습어,읽기"
            # 원어/학습어 열 인덱스
            native_idx, learning_idx = 1, 2
            # 한글 분포로 뒤집힘 판단 (원어=한글, 학습어=비한글 가정)
            native_hangul = sum(1 for r in rows if len(r) > 2 and self._contains_hangul(r[native_idx]))
            learning_hangul = sum(1 for r in rows if len(r) > 2 and self._contains_hangul(r[learning_idx]))
            swapped = learning_hangul > native_hangul
            if swapped:
                for r in rows:
                    if len(r) > 2:
                        r[native_idx], r[learning_idx] = r[learning_idx], r[native_idx]
                self.message_window.insert("end", "[INFO] 대화 CSV에서 원어/학습어 열이 뒤바뀐 것을 감지하여 교정했습니다.\n")
            # 재구성
            fixed_lines = [header] + [','.join(r) for r in rows]
            fixed_csv = "\n".join(fixed_lines)
            # '회화 스크립트' 키로 노출 (CSV 문자열)
            ai_data["회화 스크립트"] = fixed_csv
            return ai_data
        except Exception:
            return ai_data

    def _normalize_ai_keys(self, ai_data: dict) -> dict:
        """영문/기타 키를 한국어 표준 키로 정규화해 반환합니다."""
        normalized: dict = {}
        # 이미 표준 키가 있으면 그대로 반영
        for k in ["회화 스크립트", "타이틀 스크립트", "썸네일 스크립트", "인트로 스크립트", "엔딩 스크립트", "키워드 스크립트", "배경 스크립트", "대화 스크립트"]:
            if k in ai_data:
                normalized[k] = ai_data[k]
        # 영문/기타 키 → 표준 키 매핑
        if "videoTitleSuggestions" in ai_data and "타이틀 스크립트" not in normalized:
            v = ai_data.get("videoTitleSuggestions")
            if isinstance(v, list):
                normalized["타이틀 스크립트"] = "\n".join(map(str, v))
        if "thumbnailTextVersions" in ai_data and "썸네일 스크립트" not in normalized:
            v = ai_data.get("thumbnailTextVersions")
            try:
                parts = []
                for item in v if isinstance(v, list) else []:
                    if isinstance(item, dict):
                        text = item.get("text", "")
                        concept = item.get("imageConcept", "")
                        parts.append(f"{text}\n-- {concept}")
                normalized["썸네일 스크립트"] = "\n\n".join(parts)
            except Exception:
                pass
        if "introScript" in ai_data and "인트로 스크립트" not in normalized:
            normalized["인트로 스크립트"] = ai_data.get("introScript")
        if "endingScript" in ai_data and "엔딩 스크립트" not in normalized:
            normalized["엔딩 스크립트"] = ai_data.get("endingScript")
        if "videoKeywords" in ai_data and "키워드 스크립트" not in normalized:
            v = ai_data.get("videoKeywords")
            if isinstance(v, list):
                normalized["키워드 스크립트"] = ", ".join(map(str, v))
        if "dialogueVideoSceneDescription" in ai_data and "대화 스크립트" not in normalized:
            v = ai_data.get("dialogueVideoSceneDescription")
            try:
                normalized["대화 스크립트"] = json.dumps(v, ensure_ascii=False, indent=2)
            except Exception:
                normalized["대화 스크립트"] = str(v)
        # 배경 스크립트는 별도 소스가 없으면 비워둠
        return normalized

    def on_dialogue_video(self) -> None:
        self.log("[비디오] 대화 비디오 실행")

    # ---------- AI 서비스 설정 다이얼로그 ----------
    def open_ai_settings_dialog(self) -> None:
        dlg = customtkinter.CTkToplevel(self)
        dlg.title("AI 서비스 설정 - Gemini")
        dlg.grab_set()
        try:
            dlg.geometry("560x220")
        except Exception:
            pass

        container = customtkinter.CTkFrame(dlg)
        container.pack(fill="both", expand=True, padx=12, pady=12)
        for i in range(4):
            container.grid_rowconfigure(i, weight=0)
        container.grid_columnconfigure(0, weight=0)
        container.grid_columnconfigure(1, weight=1)

        # API Key
        lbl_key = customtkinter.CTkLabel(container, text="API Key")
        lbl_key.grid(row=0, column=0, padx=(8, 6), pady=8, sticky="w")
        ent_gem_key = customtkinter.CTkEntry(container, width=self.winfo_width() // 20, show="*")
        ent_gem_key.grid(row=0, column=1, padx=(0, 8), pady=8, sticky="w")

        # 모델명
        lbl_model = customtkinter.CTkLabel(container, text="모델명")
        lbl_model.grid(row=1, column=0, padx=(8, 6), pady=8, sticky="w")
        ent_gem_model = customtkinter.CTkEntry(container, width=self.winfo_width() // 10)
        ent_gem_model.grid(row=1, column=1, padx=(0, 8), pady=8, sticky="w")

        # 로케일
        lbl_locale = customtkinter.CTkLabel(container, text="로케일")
        lbl_locale.grid(row=2, column=0, padx=(8, 6), pady=8, sticky="w")
        ent_gem_locale = customtkinter.CTkEntry(container, width=self.winfo_width() // 20)
        ent_gem_locale.grid(row=2, column=1, padx=(0, 8), pady=8, sticky="w")

        # 기존 값 채우기
        cur = self.ai_settings.get("Gemini", {})
        if cur.get("api_key"):
            ent_gem_key.insert(0, cur.get("api_key"))
        ent_gem_model.insert(0, cur.get("model", "gemini-2.5-flash"))
        ent_gem_locale.insert(0, cur.get("locale", "en-US"))

        # 버튼들
        btns = customtkinter.CTkFrame(container)
        btns.grid(row=3, column=0, columnspan=2, sticky="w", padx=8, pady=(12, 4))

        def on_save() -> None:
            self.ai_settings["Gemini"] = {
                "api_key": ent_gem_key.get().strip(),
                "model": ent_gem_model.get().strip() or "gemini-2.5-flash",
                "locale": ent_gem_locale.get().strip() or "en-US",
            }
            # .env 파일에도 저장
            try:
                set_key(self.env_path, "GEMINI_API_KEY", self.ai_settings["Gemini"]["api_key"])
                set_key(self.env_path, "GEMINI_MODEL", self.ai_settings["Gemini"]["model"])
                set_key(self.env_path, "GEMINI_LOCALE", self.ai_settings["Gemini"]["locale"])
            except Exception:
                pass
            masked = (self.ai_settings["Gemini"]["api_key"][:4] + "***") if self.ai_settings["Gemini"]["api_key"] else "(미설정)"
            self.log(f"[AI] Gemini 설정 저장 - 모델: {self.ai_settings['Gemini']['model']}, 로케일: {self.ai_settings['Gemini']['locale']}, 키: {masked}")
            dlg.destroy()

        def on_cancel() -> None:
            dlg.destroy()

        btn_save = customtkinter.CTkButton(btns, text="저장", command=on_save)
        btn_save.grid(row=0, column=0, padx=(0, 8), pady=4, sticky="w")
        btn_cancel = customtkinter.CTkButton(btns, text="취소", command=on_cancel)
        btn_cancel.grid(row=0, column=1, padx=(0, 8), pady=4, sticky="w")

    # ---------- 실시간 오디오 듣기 기능 ----------
    def start_realtime_audio(self):
        """실시간 오디오 듣기 시작"""
        if self.is_playing_realtime:
            self.stop_realtime_audio()
            return
        
        # 현재 선택된 스크립트 가져오기
        selected_script_type = self.script_type_dropdown.get()
        if not selected_script_type or selected_script_type == "스크립트 종류 선택":
            self.message_window.insert("end", "[ERROR] 스크립트를 먼저 선택해주세요.\n")
            return
        
        script_data = self.generated_scripts.get(selected_script_type)
        if not script_data:
            self.message_window.insert("end", "[ERROR] 선택된 스크립트에 데이터가 없습니다.\n")
            return
        
        # 화자 설정 확인
        native_speaker = self.native_speaker_dropdown.get()
        debug_msg = f"[DEBUG] 원어 화자: {native_speaker}"
        self.message_window.insert("end", debug_msg + "\n")
        print(debug_msg)
        
        if not native_speaker or native_speaker == "N/A" or native_speaker == "No voices found":
            error_msg = "[ERROR] 원어 화자를 먼저 선택해주세요."
            self.message_window.insert("end", error_msg + "\n")
            print(error_msg)
            return
        
        if not self.learner_speaker_widgets:
            error_msg = "[ERROR] 학습어 화자가 설정되지 않았습니다."
            self.message_window.insert("end", error_msg + "\n")
            print(error_msg)
            return
        
        # 학습어 화자들이 모두 유효한지 확인
        for i, widget in enumerate(self.learner_speaker_widgets):
            learner_voice = widget['dropdown'].get()
            debug_msg = f"[DEBUG] 학습어 화자 {i+1}: {learner_voice}"
            self.message_window.insert("end", debug_msg + "\n")
            print(debug_msg)
            if not learner_voice or learner_voice == "N/A" or learner_voice == "No voices found":
                error_msg = f"[ERROR] 학습어 화자 {i+1}을(를) 먼저 선택해주세요."
                self.message_window.insert("end", error_msg + "\n")
                print(error_msg)
                return
        
        self.is_playing_realtime = True
        self.current_script_index = 0
        self.audio_listen_button.configure(text="정지", fg_color="#FF4444", hover_color="#CC3333")
        
        # 스크립트 파싱 및 오디오 큐 생성
        self.parse_script_and_create_queue(script_data)
        
        # 재생 시작
        self.playing_thread = threading.Thread(target=self.play_audio_queue, daemon=True)
        self.playing_thread.start()
        
        self.message_window.insert("end", "[INFO] 실시간 오디오 듣기를 시작합니다.\n")
    
    def stop_realtime_audio(self):
        """실시간 오디오 듣기 정지"""
        self.is_playing_realtime = False
        self.audio_listen_button.configure(text="오디오 듣기", fg_color=self.BUTTON_COLOR, hover_color=self.BUTTON_HOVER_COLOR)
        pygame.mixer.music.stop()
        self.message_window.insert("end", "[INFO] 실시간 오디오 듣기를 정지했습니다.\n")
    
    def parse_script_and_create_queue(self, script_data):
        """스크립트를 파싱하여 오디오 큐 생성"""
        self.audio_queue = []
        
        try:
            # 스크립트 데이터가 JSON 형태인 경우 파싱
            if isinstance(script_data, str):
                try:
                    script_data = json.loads(script_data)
                except json.JSONDecodeError:
                    # JSON이 아닌 경우: CSV(회화 스크립트) 또는 일반 텍스트 처리
                    lines = [ln for ln in script_data.strip().split('\n') if ln.strip()]
                    if not lines:
                        return
                    header = lines[0]
                    # 회화 CSV 형식: 순번,원어,학습어,읽기
                    if ('순번' in header and '원어' in header) or ('원어' in header and '학습어' in header):
                        for row in lines[1:]:
                            cols = [c.strip() for c in row.split(',')]
                            if len(cols) < 3:
                                continue
                            native_text = cols[1]
                            learning_text = cols[2]
                            if native_text:
                                self.audio_queue.append({'type': 'native', 'text': native_text, 'speaker': 'native'})
                            # 화자간 1초 무음
                            self.audio_queue.append({'type': 'silence', 'duration': 1.0})
                            for i, learner_widget in enumerate(self.learner_speaker_widgets):
                                self.audio_queue.append({
                                    'type': 'learning',
                                    'text': learning_text,
                                    'speaker': f'learner_{i+1}',
                                    'voice_name': learner_widget['dropdown'].get()
                                })
                                if i < len(self.learner_speaker_widgets) - 1:
                                    self.audio_queue.append({'type': 'silence', 'duration': 0.5})
                        return
                    # 일반 텍스트: 각 줄을 원어 화자로 재생
                    for line in lines:
                        self.audio_queue.append({'type': 'native', 'text': line.strip(), 'speaker': 'native'})
                    return
            
            # 대화 스크립트 형식 처리
            if isinstance(script_data, list):
                for item in script_data:
                    if isinstance(item, dict):
                        # 대화 형식: {"speaker": "native", "text": "안녕하세요"}
                        if 'speaker' in item and 'text' in item:
                            self.audio_queue.append({
                                'type': 'dialogue',
                                'speaker': item['speaker'],
                                'text': item['text']
                            })
                        # 테이블 형식: {"순번": 1, "원어": "안녕하세요", "학습어": "Hello", "읽기": "헬로"}
                        elif '원어' in item and '학습어' in item:
                            # 원어 화자
                            self.audio_queue.append({
                                'type': 'native',
                                'text': item['원어'],
                                'speaker': 'native'
                            })
                            # 학습어 화자들 (1초 무음 포함)
                            self.audio_queue.append({
                                'type': 'silence',
                                'duration': 1.0
                            })
                            for i, learner_widget in enumerate(self.learner_speaker_widgets):
                                self.audio_queue.append({
                                    'type': 'learning',
                                    'text': item['학습어'],
                                    'speaker': f'learner_{i+1}',
                                    'voice_name': learner_widget['dropdown'].get()
                                })
                                if i < len(self.learner_speaker_widgets) - 1:
                                    self.audio_queue.append({
                                        'type': 'silence',
                                        'duration': 0.5
                                    })
            
            self.message_window.insert("end", f"[INFO] {len(self.audio_queue)}개의 오디오 항목을 큐에 추가했습니다.\n")
            
        except Exception as e:
            self.message_window.insert("end", f"[ERROR] 스크립트 파싱 중 오류: {e}\n")
    
    def play_audio_queue(self):
        """오디오 큐를 순차적으로 재생"""
        import threading
        import time
        
        for i, audio_item in enumerate(self.audio_queue):
            if not self.is_playing_realtime:
                break
            
            try:
                if audio_item['type'] == 'silence':
                    # 무음 재생
                    time.sleep(audio_item['duration'])
                    continue
                
                elif audio_item['type'] in ['native', 'learning', 'dialogue']:
                    # TTS 음성 생성 및 재생
                    text = audio_item['text']
                    speaker_type = audio_item['speaker']
                    
                    if speaker_type == 'native':
                        voice_name = self.native_speaker_dropdown.get()
                        lang_code = "-".join(voice_name.split('-')[:2])
                    elif speaker_type.startswith('learner_'):
                        voice_name = audio_item['voice_name']
                        lang_code = "-".join(voice_name.split('-')[:2])
                    else:
                        # dialogue 타입의 경우 speaker 필드에서 화자 정보 추출
                        voice_name = self.get_voice_for_speaker(audio_item['speaker'])
                        lang_code = "-".join(voice_name.split('-')[:2])
                    
                    # TTS 음성 생성
                    self.generate_and_play_tts(text, voice_name, lang_code)
                    
                    # 다음 항목까지 잠시 대기
                    time.sleep(0.5)
                
            except Exception as e:
                self.message_window.insert("end", f"[ERROR] 오디오 재생 중 오류: {e}\n")
                continue
        
        # 재생 완료
        if self.is_playing_realtime:
            self.stop_realtime_audio()
            self.message_window.insert("end", "[INFO] 실시간 오디오 듣기가 완료되었습니다.\n")
    
    def get_voice_for_speaker(self, speaker):
        """화자 정보에 따른 음성 선택"""
        if speaker == 'native' or speaker == '원어':
            return self.native_speaker_dropdown.get()
        elif speaker.startswith('learner') or speaker.startswith('학습어'):
            # 학습어 화자 중 첫 번째 사용
            if self.learner_speaker_widgets:
                return self.learner_speaker_widgets[0]['dropdown'].get()
        return self.native_speaker_dropdown.get()  # 기본값
    
    def generate_and_play_tts(self, text, voice_name, lang_code):
        """TTS 음성 생성 및 재생"""
        try:
            synthesis_input = texttospeech.SynthesisInput(text=text)
            voice = texttospeech.VoiceSelectionParams(language_code=lang_code, name=voice_name)
            audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
            
            response = self.tts_client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
            
            # 임시 파일에 저장
            temp_file = f"/tmp/captiongen_realtime_{int(time.time())}.mp3"
            with open(temp_file, "wb") as out:
                out.write(response.audio_content)
            
            # 재생
            pygame.mixer.music.load(temp_file)
            pygame.mixer.music.play()
            
            # 재생 완료까지 대기
            while pygame.mixer.music.get_busy() and self.is_playing_realtime:
                time.sleep(0.1)
            
            # 임시 파일 삭제
            try:
                os.remove(temp_file)
            except:
                pass
                
        except Exception as e:
            self.message_window.insert("end", f"[ERROR] TTS 생성 실패: {e}\n")

if __name__ == "__main__":
    app = App()
    app.mainloop()