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
    
    # 4. 타입별로 PNG 이미지 생성
    _create_conversation_images(context, png_renderer, resolution, file_manager)
    _create_intro_images(context, png_renderer, resolution, file_manager)
    _create_ending_images(context, png_renderer, resolution, file_manager)
    _create_thumbnail_images(context, png_renderer, resolution, file_manager)

    print("✅ 자막 이미지 생성 완료")


def _create_conversation_images(context: PipelineContext, png_renderer: PNGRenderer, 
                               resolution: Tuple[int, int], file_manager: FileNamingManager):
    """
    회화용 PNG 이미지 생성 (2개 독립 화면)
    """
    # 회화 씬들만 필터링
    conversation_scenes = [scene for scene in context.manifest.scenes if scene.type == "conversation"]
    conversation_scenes.sort(key=lambda x: x.sequence)
    
    if not conversation_scenes:
        print("    - 회화 씬이 없습니다.")
        return
    
    print(f"    [회화 이미지 생성]")
    print(f"      - 총 {len(conversation_scenes)}개 회화 씬 발견")
    
    for i, scene in enumerate(conversation_scenes):
        print(f"      - 씬 {scene.sequence}: {scene.content.order}")
        
        # 씬 데이터 준비
        scene_data = {
            'order': scene.content.order,
            'native_script': scene.content.native_script,
            'learning_script': scene.content.learning_script,
            'reading_script': scene.content.reading_script
        }
        
        # 출력 파일명 생성
        output_filename = f"{context.identifier}_{i+1:03d}.png"
        output_path = os.path.join(context.paths.conversation_dir, output_filename)
        
        # 회화 이미지 생성 (2개 독립 화면)
        success = png_renderer.create_conversation_image(
            scene_data, output_path, resolution, png_renderer.settings
        )
        
        if success:
            print(f"        ✅ 회화 이미지 생성 완료: {output_filename}")
        else:
            print(f"        ❌ 회화 이미지 생성 실패: {output_filename}")


def _create_intro_images(context: PipelineContext, png_renderer: PNGRenderer,
                        resolution: Tuple[int, int], file_manager: FileNamingManager):
    """
    인트로용 PNG 이미지 생성 (MD 인라인 스크립트, 스마트 줄바꿈)
    """
    # 인트로 씬들만 필터링
    intro_scenes = [scene for scene in context.manifest.scenes if scene.type == "intro"]
    
    if not intro_scenes:
        print("    - 인트로 씬이 없습니다.")
        return
    
    print(f"    [인트로 이미지 생성]")
    print(f"      - 총 {len(intro_scenes)}개 인트로 씬 발견")
    
    for i, scene in enumerate(intro_scenes):
        print(f"      - 씬 {scene.id}: {scene.content.text[:50]}...")
        
        # 출력 파일명 생성
        output_filename = f"{context.identifier}_{i+1:03d}.png"
        output_path = os.path.join(context.paths.intro_dir, output_filename)
        
        # 인트로 이미지 생성
        success = png_renderer.create_intro_ending_image(
            scene.content.text, output_path, resolution, 
            png_renderer.settings, "인트로"
        )
        
        if success:
            print(f"        ✅ 인트로 이미지 생성 완료: {output_filename}")
        else:
            print(f"        ❌ 인트로 이미지 생성 실패: {output_filename}")


def _create_ending_images(context: PipelineContext, png_renderer: PNGRenderer,
                         resolution: Tuple[int, int], file_manager: FileNamingManager):
    """
    엔딩용 PNG 이미지 생성 (MD 인라인 스크립트, 스마트 줄바꿈)
    """
    # 엔딩 씬들만 필터링
    ending_scenes = [scene for scene in context.manifest.scenes if scene.type == "ending"]
    
    if not ending_scenes:
        print("    - 엔딩 씬이 없습니다.")
        return
    
    print(f"    [엔딩 이미지 생성]")
    print(f"      - 총 {len(ending_scenes)}개 엔딩 씬 발견")
    
    for i, scene in enumerate(ending_scenes):
        print(f"      - 씬 {scene.id}: {scene.content.text[:50]}...")
        
        # 출력 파일명 생성
        output_filename = f"{context.identifier}_{i+1:03d}.png"
        output_path = os.path.join(context.paths.ending_dir, output_filename)
        
        # 엔딩 이미지 생성
        success = png_renderer.create_intro_ending_image(
            scene.content.text, output_path, resolution, 
            png_renderer.settings, "엔딩"
        )
        
        if success:
            print(f"        ✅ 엔딩 이미지 생성 완료: {output_filename}")
        else:
            print(f"        ❌ 엔딩 이미지 생성 실패: {output_filename}")


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
        ai_data, output_path, resolution, png_renderer.settings
    )
    
    if success:
        print(f"        ✅ 썸네일 이미지 생성 완료: {output_filename}")
    else:
        print(f"        ❌ 썸네일 이미지 생성 실패: {output_filename}")
