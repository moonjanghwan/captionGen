"""
Step 3: 자막 이미지 생성 (새로운 PNG 직접 생성 방식)

Manifest와 UI 설정값을 바탕으로, PNGRenderer를 사용하여 각 장면에 맞는
자막 이미지를 직접 생성합니다. 제작 사양서에 따라 각 타입별로 PNG 이미지를 생성합니다.
"""
import os
import re
from typing import List, Dict, Any, Tuple

from ..core.context import PipelineContext
from ..renderers import PNGRenderer
from ..utils.file_naming import FileNamingManager


def run(context: PipelineContext):
    """
    자막 이미지 생성 파이프라인의 메인 실행 함수입니다.
    각 타입별로 PNG 이미지를 직접 생성합니다.
    """
    print('--- Step 3: 자막 이미지 생성 시작 ---')
    print(f"📁 프로젝트: {context.project_name}")
    print(f"🆔 식별자: {context.identifier}")

    if not context.manifest:
        print("⚠️ Manifest가 없습니다. 이전 단계를 먼저 실행하세요.")
        return

    print(f"📄 매니페스트 타입: {type(context.manifest)}")
    print(f"📄 매니페스트 내용: {context.manifest}")

    # 1. PNG 렌더러 초기화
    settings_dict = {
        "common": context.settings.common,
        "tabs": context.settings.tabs
    }
    png_renderer = PNGRenderer(settings_dict)
    
    # 2. 파일명 관리자 초기화
    file_manager = FileNamingManager(base_output_dir="output")
    
    # 3. 해상도 파싱
    width, height = map(int, context.manifest.resolution.split('x'))
    resolution = (width, height)
    print(f"🔍 렌더링 해상도: {width}x{height}")
    
    # 4. 선택된 스크립트 타입에 따라 PNG 이미지 생성
    if context.script_type == "회화" or context.script_type == "conversation":
        _create_conversation_images(context, png_renderer, resolution, file_manager)
    elif context.script_type == "인트로" or context.script_type == "intro":
        _create_intro_images(context, png_renderer, resolution, file_manager)
    elif context.script_type == "엔딩" or context.script_type == "ending":
        _create_ending_images(context, png_renderer, resolution, file_manager)
    elif context.script_type == "썸네일" or context.script_type == "thumbnail":
        _create_thumbnail_images(context, png_renderer, resolution, file_manager)
    else:
        print(f"⚠️ 알 수 없는 스크립트 타입: {context.script_type}")
        print("    모든 타입의 이미지를 생성합니다.")
        _create_conversation_images(context, png_renderer, resolution, file_manager)
        _create_intro_images(context, png_renderer, resolution, file_manager)
        _create_ending_images(context, png_renderer, resolution, file_manager)
        _create_thumbnail_images(context, png_renderer, resolution, file_manager)

    print("✅ 자막 이미지 생성 완료")


def _log(context: PipelineContext, message: str, level: str = "INFO"):
    """컨텍스트에 있는 콜백 함수로 로깅을 수행합니다."""
    if context.log_callback:
        context.log_callback(message, level)
    else:
        # 콜백이 없는 경우 콘솔에 직접 출력
        print(f"[{level}] {message}")


def _create_conversation_images(context: PipelineContext, png_renderer: PNGRenderer, 
                               resolution: Tuple[int, int], file_manager: FileNamingManager):
    """
    회화용 PNG 이미지 생성 (2개 독립 화면)
    """
    conversation_scenes = [scene for scene in context.manifest.scenes if scene.type == "conversation"]
    conversation_scenes.sort(key=lambda x: x.sequence)
    
    if not conversation_scenes:
        _log(context, "회화 씬이 없어 생성을 건너뜁니다.", "WARNING")
        return
    
    _log(context, f"총 {len(conversation_scenes)}개의 회화 씬에 대한 이미지 생성을 시작합니다.")
    
    for i, scene in enumerate(conversation_scenes):
        scene_info = f"씬 {scene.sequence}: {scene.native_script[:20]}..."
        _log(context, f"{scene_info} 처리 중..." )
        
        scene_data = {
            'order': str(scene.sequence),
            'native_script': scene.native_script,
            'learning_script': scene.learning_script,
            'reading_script': scene.reading_script
        }
        
        output_filename = f"{context.identifier}_{i+1:03d}.png"
        output_path = os.path.join(context.paths.conversation_dir, output_filename)
        
        # 화면 1, 2 파일명
        screen1_filename = output_filename.replace('.png', '_screen1.png')
        screen2_filename = output_filename.replace('.png', '_screen2.png')
        
        _log(context, f"  -> '{screen1_filename}' 생성 시도")
        _log(context, f"  -> '{screen2_filename}' 생성 시도")

        success = png_renderer.create_conversation_image(
            scene_data, output_path, resolution, png_renderer.raw_settings
        )
        
        if success:
            _log(context, f"✅ {scene_info} 이미지 생성 완료", "SUCCESS")
        else:
            _log(context, f"❌ {scene_info} 이미지 생성 실패", "ERROR")


def _create_intro_images(context: PipelineContext, png_renderer: PNGRenderer,
                        resolution: Tuple[int, int], file_manager: FileNamingManager):
    """인트로용 PNG 이미지를 문장별로 생성합니다."""
    intro_scenes = [scene for scene in context.manifest.scenes if scene.type == "intro"]
    
    if not intro_scenes:
        _log(context, "인트로 씬이 없어 생성을 건너뜁니다.", "WARNING")
        return

    # 인트로 타입은 보통 씬이 하나라고 가정
    full_script = intro_scenes[0].full_script if intro_scenes else ""
    sentences = [s.strip() for s in full_script.split('\n') if s.strip()]

    if not sentences:
        _log(context, "인트로 스크립트 내용이 없습니다.", "WARNING")
        return

    _log(context, f"총 {len(sentences)}개의 인트로 문장에 대한 이미지 생성을 시작합니다.")

    for i, sentence in enumerate(sentences):
        sentence_info = f"인트로 문장 {i+1}: {sentence[:30]}..."
        _log(context, f"{sentence_info} 처리 중...")

        output_filename = f"{context.identifier}_intro_{i+1:03d}.png"
        output_path = os.path.join(context.paths.intro_dir, output_filename)

        _log(context, f"  -> '{output_filename}' 생성 시도")

        success = png_renderer.create_intro_ending_image(
            sentence, output_path, resolution, "인트로"
        )
        
        if success:
            _log(context, f"✅ {sentence_info} 이미지 생성 완료", "SUCCESS")
        else:
            _log(context, f"❌ {sentence_info} 이미지 생성 실패", "ERROR")


def _create_ending_images(context: PipelineContext, png_renderer: PNGRenderer,
                         resolution: Tuple[int, int], file_manager: FileNamingManager):
    """엔딩용 PNG 이미지를 문장별로 생성합니다."""
    ending_scenes = [scene for scene in context.manifest.scenes if scene.type == "ending"]
    
    if not ending_scenes:
        _log(context, "엔딩 씬이 없어 생성을 건너뜁니다.", "WARNING")
        return

    # 엔딩 타입은 보통 씬이 하나라고 가정
    full_script = ending_scenes[0].full_script if ending_scenes else ""
    sentences = [s.strip() for s in full_script.split('\n') if s.strip()]

    if not sentences:
        _log(context, "엔딩 스크립트 내용이 없습니다.", "WARNING")
        return

    _log(context, f"총 {len(sentences)}개의 엔딩 문장에 대한 이미지 생성을 시작합니다.")

    for i, sentence in enumerate(sentences):
        sentence_info = f"엔딩 문장 {i+1}: {sentence[:30]}..."
        _log(context, f"{sentence_info} 처리 중...")

        output_filename = f"{context.identifier}_ending_{i+1:03d}.png"
        output_path = os.path.join(context.paths.ending_dir, output_filename)

        _log(context, f"  -> '{output_filename}' 생성 시도")

        success = png_renderer.create_intro_ending_image(
            sentence, output_path, resolution, "엔딩"
        )
        
        if success:
            _log(context, f"✅ {sentence_info} 이미지 생성 완료", "SUCCESS")
        else:
            _log(context, f"❌ {sentence_info} 이미지 생성 실패", "ERROR")



def _create_thumbnail_images(context: PipelineContext, png_renderer: PNGRenderer,
                            resolution: Tuple[int, int], file_manager: FileNamingManager):
    """
    썸네일용 PNG 이미지 생성 (AI JSON 파싱, 3세트, 터미널 출력)
    """
    # AI 데이터 로드 (실제 구현에서는 context에서 가져와야 함)
    ai_data = getattr(context, 'ai_data', {})
    
    if not ai_data:
        print("    - AI 데이터가 없습니다.")
        return
    
    print(f"    [썸네일 이미지 생성]")
    
    # 출력 파일명 생성
    output_filename = f"{context.identifier}_thumbnail.png"
    output_path = os.path.join(context.paths.thumbnail_dir, output_filename)
    
    # 썸네일 이미지 생성
    success = png_renderer.create_thumbnail_image(
        ai_data, output_path, resolution
    )
    
    if success:
        print(f"        ✅ 썸네일 이미지 생성 완료: {output_filename}")
    else:
        print(f"        ❌ 썸네일 이미지 생성 실패: {output_filename}")
