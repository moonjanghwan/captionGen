import os
import traceback
from typing import Tuple, Dict, Any, List

from ..core.context import PipelineContext
from ..renderers import PNGRenderer

# --- Helper Function ---
def _log(context: PipelineContext, message: str, level: str = "INFO"):
    if level.upper() != "INFO":
        log_message = f"[{level.upper()}] {message}"
    else:
        log_message = message
    context.log_callback(log_message)

def _get_style_row_map(context: PipelineContext, tab_name: str) -> Dict[str, Dict]:
    """UI 설정에서 특정 탭의 행(row)들을 가져와 '행' 레이블을 키로 하는 딕셔너리로 만듭니다."""
    try:
        settings_for_tab = context.settings.script_settings.get(tab_name, {})
        rows = settings_for_tab.get('rows', [])
        return {row.get('행'): row for row in rows if row.get('행')}
    except Exception as e:
        _log(context, f"'{tab_name}' 탭의 스타일 설정을 파싱하는 중 오류 발생: {e}", "ERROR")
        return {}

# --- Main Entry Point ---
def run(context: PipelineContext) -> Dict[str, Any]:
    print('🚀 [자막 생성] Step 3: 자막 이미지 생성 시작 ---')
    print(f"🔍 [자막 생성] context.project_name: {context.project_name}")
    print(f"🔍 [자막 생성] context.identifier: {context.identifier}")
    print(f"🔍 [자막 생성] context.script_type: {context.script_type}")
    context.log_callback(f"📁 프로젝트: {context.project_name}")
    context.log_callback(f"🆔 식별자: {context.identifier}")

    if not context.manifest:
        print("❌ [자막 생성] Manifest가 없습니다.")
        _log(context, "Manifest가 없습니다. 이전 단계를 먼저 실행하세요.", "WARNING")
        return {"success": False, "message": "Manifest가 없습니다."}

    print(f"✅ [자막 생성] Manifest 확인 완료: {len(context.manifest.scenes)}개 장면")
    
    settings = context.settings.script_settings
    if not settings:
        print("❌ [자막 생성] 스크립트 설정이 없습니다.")
        _log(context, "스크립트 설정(script_settings)이 없습니다.", "ERROR")
        return {"success": False, "message": "스크립트 설정이 없습니다."}

    print(f"✅ [자막 생성] 스크립트 설정 확인 완료: {list(settings.keys())}")
    print("🚀 [자막 생성] PNGRenderer 초기화 시작...")
    png_renderer = PNGRenderer(settings)
    print("✅ [자막 생성] PNGRenderer 초기화 완료")
    context.log_callback("✅ PNGRenderer 초기화 완료")
    
    script_type = context.script_type
    
    base_subtitle_output_dir = os.path.join(context.paths.output_dir, "subtitles")
    os.makedirs(base_subtitle_output_dir, exist_ok=True)

    _log(context, f"지정된 스크립트 타입 '{script_type}'에 대한 이미지 생성을 시작합니다.")

    if script_type == "conversation":
        _create_conversation_images(context, png_renderer, base_subtitle_output_dir)
    elif script_type == "intro":
        _create_intro_images(context, png_renderer, base_subtitle_output_dir)
    elif script_type == "ending":
        _create_ending_images(context, png_renderer, base_subtitle_output_dir)
    elif script_type == "thumbnail":
        _create_thumbnail_images(context, png_renderer, base_subtitle_output_dir)
    else:
        _log(context, f"지원하지 않거나, 단일 실행이 의미 없는 스크립트 타입입니다: {script_type}", "WARNING")

    context.log_callback("✅ 자막 이미지 생성 완료")
    return {"success": True, "output_dir": base_subtitle_output_dir}

def _create_conversation_images(context: PipelineContext, png_renderer: PNGRenderer, 
                               base_output_dir: str):
    _log(context, "--- 회화(Conversation) 이미지 생성 시작 ---")
    
    output_dir = os.path.join(base_output_dir, "conversation")
    os.makedirs(output_dir, exist_ok=True)

    conversation_scenes = [s for s in context.manifest.scenes if s.type == "conversation"]
    if not conversation_scenes:
        _log(context, "회화 장면(scene) 데이터가 없어 생성을 건너뜁니다.", "INFO")
        return

    # 첫 장면의 설정을 기준으로 해상도 결정
    resolution_str = conversation_scenes[0].settings.get('해상도', '1920x1080')
    width, height = map(int, resolution_str.split('x'))
    resolution = (width, height)
    _log(context, f"[conversation] 렌더링 해상도: {width}x{height}")

    style_map = _get_style_row_map(context, "conversation")
    if not style_map:
        _log(context, "'conversation' 탭에 대한 스타일이 정의되지 않았습니다. 생성을 건너뜁니다.", "WARNING")
        return

    # Semantic mapping for style settings
    semantic_style_map = {}
    for row_key, row_settings in style_map.items():
        # 행 키의 값을 텍스트 라벨로 사용
        text_label = row_settings.get('행', '')
        
        if text_label:
            semantic_style_map[text_label] = row_settings

    for i, scene_data in enumerate(conversation_scenes):
        base_filename = f"{context.identifier}_conversation_{i+1:03d}"
        
        scenes_for_screen1 = []
        if '순번' in semantic_style_map:
            scenes_for_screen1.append({'text': str(scene_data.sequence), 'settings': semantic_style_map['순번']})
        if '원어' in semantic_style_map:
            scenes_for_screen1.append({'text': scene_data.native_script, 'settings': semantic_style_map['원어']})
        
        if scenes_for_screen1:
            output_path1 = os.path.join(output_dir, f"{base_filename}_screen1.png")
            png_renderer.render_image(scenes_for_screen1, output_path1, resolution, "conversation")

        scenes_for_screen2 = []
        if '순번' in semantic_style_map:
            scenes_for_screen2.append({'text': str(scene_data.sequence), 'settings': semantic_style_map['순번']})
        if '원어' in semantic_style_map:
            scenes_for_screen2.append({'text': scene_data.native_script, 'settings': semantic_style_map['원어']})
        if '학습어' in semantic_style_map:
            scenes_for_screen2.append({'text': scene_data.learning_script, 'settings': semantic_style_map['학습어']})
        if '읽기' in semantic_style_map:
            scenes_for_screen2.append({'text': scene_data.reading_script, 'settings': semantic_style_map['읽기']})

        if scenes_for_screen2:
            output_path2 = os.path.join(output_dir, f"{base_filename}_screen2.png")
            png_renderer.render_image(scenes_for_screen2, output_path2, resolution, "conversation")

def _create_intro_images(context: PipelineContext, png_renderer: PNGRenderer,
                        base_output_dir: str):
    _log(context, "--- 인트로(Intro) 이미지 생성 시작 ---")
    
    output_dir = os.path.join(base_output_dir, "intro")
    os.makedirs(output_dir, exist_ok=True)

    intro_scenes = [s for s in context.manifest.scenes if s.type == "intro"]
    if not intro_scenes:
        _log(context, "인트로 장면(scene)이 없어 생성을 건너뜁니다.", "INFO")
        return

    # 첫 장면의 설정을 기준으로 해상도 결정
    resolution_str = intro_scenes[0].settings.get('해상도', '1920x1080')
    width, height = map(int, resolution_str.split('x'))
    resolution = (width, height)
    _log(context, f"[intro] 렌더링 해상도: {width}x{height}")

    style_map = _get_style_row_map(context, "intro")
    if not style_map:
        _log(context, "'intro' 탭에 대한 스타일이 정의되지 않았습니다. 생성을 건너뜁니다.", "WARNING")
        return

    # 첫 번째 스타일 사용 (인트로는 보통 하나의 스타일)
    first_style_key = list(style_map.keys())[0] if style_map else None
    if not first_style_key:
        _log(context, "인트로 스타일을 찾을 수 없습니다.", "WARNING")
        return
    
    style_to_use = style_map[first_style_key]
    
    # 각 intro scene의 text를 사용하여 이미지 생성
    for i, scene in enumerate(intro_scenes):
        sentence = scene.text
        if not sentence or not sentence.strip():
            continue
            
        output_path = os.path.join(output_dir, f"{context.identifier}_intro_{i+1:03d}.png")
        scenes_to_render = [{'text': sentence, 'settings': style_to_use}]
        png_renderer.render_image(scenes_to_render, output_path, resolution, "intro")

def _create_ending_images(context: PipelineContext, png_renderer: PNGRenderer,
                         base_output_dir: str):
    _log(context, "--- 엔딩(Ending) 이미지 생성 시작 ---")

    output_dir = os.path.join(base_output_dir, "ending")
    os.makedirs(output_dir, exist_ok=True)

    ending_scenes = [s for s in context.manifest.scenes if s.type == "ending"]
    if not ending_scenes:
        _log(context, "엔딩 장면(scene)이 없어 생성을 건너뜁니다.", "INFO")
        return

    # 첫 장면의 설정을 기준으로 해상도 결정
    resolution_str = ending_scenes[0].settings.get('해상도', '1920x1080')
    width, height = map(int, resolution_str.split('x'))
    resolution = (width, height)
    _log(context, f"[ending] 렌더링 해상도: {width}x{height}")

    style_map = _get_style_row_map(context, "ending")
    if not style_map:
        _log(context, "'ending' 탭에 대한 스타일이 정의되지 않았습니다. 생성을 건너킵니다.", "WARNING")
        return

    # 첫 번째 스타일 사용 (엔딩은 보통 하나의 스타일)
    first_style_key = list(style_map.keys())[0] if style_map else None
    if not first_style_key:
        _log(context, "엔딩 스타일을 찾을 수 없습니다.", "WARNING")
        return
    
    style_to_use = style_map[first_style_key]

    for i, scene in enumerate(ending_scenes):
        sentence = scene.text
        if not sentence or not sentence.strip():
            continue

        output_path = os.path.join(output_dir, f"{context.identifier}_ending_{i+1:03d}.png")
        scenes_to_render = [{'text': sentence, 'settings': style_to_use}]
        png_renderer.render_image(scenes_to_render, output_path, resolution, "ending")

def _create_thumbnail_images(context: PipelineContext, png_renderer: PNGRenderer,
                           base_output_dir: str):
    _log(context, "--- 썸네일(Thumbnail) 이미지 생성 시작 ---")
    
    output_dir = os.path.join(base_output_dir, "thumbnail")
    os.makedirs(output_dir, exist_ok=True)

    thumbnail_scenes = [s for s in context.manifest.scenes if s.type == "thumbnail"]
    if not thumbnail_scenes:
        _log(context, "썸네일 장면(scene) 데이터가 없어 생성을 건너뜁니다.", "INFO")
        return

    # 첫 장면의 설정을 기준으로 해상도 결정
    resolution_str = thumbnail_scenes[0].settings.get('해상도', '1920x1080')
    width, height = map(int, resolution_str.split('x'))
    resolution = (width, height)
    _log(context, f"[thumbnail] 렌더링 해상도: {width}x{height}")

    try:
        rows_styles = context.settings.script_settings.get("thumbnail", {}).get('rows', [])
    except Exception:
        rows_styles = []

    if not rows_styles:
        _log(context, "썸네일 탭에 정의된 행(row) 스타일이 없습니다.", "WARNING")
        return

    thumbnail_scenes = [s for s in context.manifest.scenes if s.type == "thumbnail"]
    if not thumbnail_scenes:
        _log(context, "썸네일 장면(scene) 데이터가 없어 생성을 건너뜁니다.", "INFO")
        return

    for i, scene in enumerate(thumbnail_scenes):
        text_content = scene.text
        if not text_content or not text_content.strip():
            continue

        lines = [line.strip() for line in text_content.split('\n')]
        
        scenes_to_render = []
        for line_index, line_text in enumerate(lines):
            if line_index < len(rows_styles):
                style_to_use = rows_styles[line_index]
                scenes_to_render.append({'text': line_text, 'settings': style_to_use})
            else:
                scenes_to_render.append({'text': line_text, 'settings': rows_styles[-1]})

        if scenes_to_render:
            output_path = os.path.join(output_dir, f"{context.identifier}_thumbnail_{i+1}.png")
            png_renderer.render_image(scenes_to_render, output_path, resolution, "thumbnail")
            _log(context, f"✅ 썸네일 이미지 생성: {os.path.basename(output_path)}")