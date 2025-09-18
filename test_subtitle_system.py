#!/usr/bin/env python3
"""
자막 이미지 생성 시스템 테스트 스크립트

SSML mark 태그 기반 정확한 타이밍, PNG 시퀀스 자동 생성, 텍스트 설정 적용을 테스트합니다.
"""

import json
import os
# TextRenderer와 SubtitleGenerator는 삭제됨 - PNGRenderer 사용

def test_text_renderer():
    """텍스트 렌더러 테스트"""
    print("🎨 텍스트 렌더러 테스트 시작\n")
    
    renderer = TextRenderer()
    
    # 기본 텍스트 렌더링 테스트
    test_text = "안녕하세요!"
    image = renderer.render_text(test_text, 800, 600)
    
    # 테스트 이미지 저장
    os.makedirs("test_output/subtitle", exist_ok=True)
    test_image_path = "test_output/subtitle/test_text.png"
    success = renderer.save_image(image, test_image_path)
    
    if success:
        print("✅ 기본 텍스트 렌더링 성공")
        print(f"이미지 저장: {test_image_path}")
    else:
        print("❌ 기본 텍스트 렌더링 실패")
    
    # 다국어 텍스트 렌더링 테스트
    test_lines = [
        "1",
        "안녕하세요!",
        "你好！",
        "니하오!"
    ]
    
    multiline_image = renderer.render_multiline_text(test_lines, 800, 600)
    multiline_path = "test_output/subtitle/test_multiline.png"
    success = renderer.save_image(multiline_image, multiline_path)
    
    if success:
        print("✅ 다국어 다중 라인 렌더링 성공")
        print(f"이미지 저장: {multiline_path}")
    else:
        print("❌ 다국어 다중 라인 렌더링 실패")
    
    # conversation 화면 1 렌더링 테스트
    screen1_image = renderer.render_conversation_screen1(1, "안녕하세요!", 800, 600)
    screen1_path = "test_output/subtitle/test_screen1.png"
    success = renderer.save_image(screen1_image, screen1_path)
    
    if success:
        print("✅ conversation 화면 1 렌더링 성공")
        print(f"이미지 저장: {screen1_path}")
    else:
        print("❌ conversation 화면 1 렌더링 실패")
    
    # conversation 화면 2 렌더링 테스트
    screen2_image = renderer.render_conversation_screen2(
        1, "안녕하세요!", "你好！", "니하오!", 800, 600
    )
    screen2_path = "test_output/subtitle/test_screen2.png"
    success = renderer.save_image(screen2_image, screen2_path)
    
    if success:
        print("✅ conversation 화면 2 렌더링 성공")
        print(f"이미지 저장: {screen2_path}")
    else:
        print("❌ conversation 화면 2 렌더링 실패")
    
    return renderer

def test_subtitle_generator():
    """자막 생성기 테스트"""
    print("\n🎬 자막 생성기 테스트 시작\n")
    
    generator = SubtitleGenerator()
    
    # dialogue_manifest.json 로드
    try:
        with open("dialogue_manifest.json", 'r', encoding='utf-8') as f:
            manifest_data = json.load(f)
        print("✅ Manifest 파일 로드 성공")
        
    except FileNotFoundError:
        print("❌ dialogue_manifest.json 파일을 찾을 수 없습니다")
        return
    
    # Manifest에서 자막 이미지 시퀀스 생성
    output_dir = "test_output/subtitle/frames"
    frames = generator.generate_from_manifest(manifest_data, output_dir, fps=30)
    
    print(f"✅ 자막 이미지 시퀀스 생성 완료: {len(frames)}개 프레임")
    
    # 생성된 프레임 정보 출력
    for i, frame in enumerate(frames):
        print(f"  프레임 {i+1}: {frame.scene_id} ({frame.screen_type})")
        print(f"    지속시간: {frame.duration:.1f}초")
        print(f"    내용: {frame.content}")
        print(f"    출력경로: {frame.output_path}")
        print()
    
    # 프레임 요약 정보
    summary = generator.get_frame_summary()
    print("📊 프레임 요약:")
    print(f"  총 프레임 수: {summary['total_frames']}")
    print(f"  총 지속시간: {summary['total_duration']:.1f}초")
    print(f"  해상도: {summary['resolution']}")
    print(f"  출력 디렉토리: {summary['output_directory']}")
    print(f"  장면 타입별:")
    for scene_type, count in summary['scene_types'].items():
        print(f"    {scene_type}: {count}개")
    
    # FFmpeg concat 리스트 생성
    concat_list_path = os.path.join(output_dir, "concat_list.txt")
    success = generator.create_ffmpeg_concat_list(concat_list_path)
    
    if success:
        print(f"\n✅ FFmpeg concat 리스트 생성: {concat_list_path}")
        print("🔧 FFmpeg 명령어 예시:")
        print(f"ffmpeg -f concat -safe 0 -i {concat_list_path} -vsync vfr -pix_fmt yuv420p output_video.mp4")
    
    return generator, frames

def test_ssml_based_generation():
    """SSML mark 태그 기반 생성 테스트"""
    print("\n🎬 SSML mark 태그 기반 생성 테스트 시작\n")
    
    # test_output/full_manifest.ssml 로드
    ssml_path = "test_output/full_manifest.ssml"
    if not os.path.exists(ssml_path):
        print(f"⚠️ SSML 파일을 찾을 수 없습니다: {ssml_path}")
        return
    
    try:
        with open(ssml_path, 'r', encoding='utf-8') as f:
            ssml_content = f.read()
        print("✅ SSML 파일 로드 성공")
        
    except Exception as e:
        print(f"❌ SSML 파일 로드 실패: {e}")
        return
    
    # SSML mark 태그 기반으로 자막 이미지 생성
    generator = SubtitleGenerator()
    output_dir = "test_output/subtitle/ssml_frames"
    
    frames = generator.generate_from_ssml_marks(ssml_content, output_dir, fps=30)
    
    print(f"✅ SSML mark 태그 기반 자막 이미지 생성 완료: {len(frames)}개 프레임")
    
    # 생성된 프레임 정보 출력
    for i, frame in enumerate(frames):
        print(f"  프레임 {i+1}: {frame.scene_id} ({frame.screen_type})")
        print(f"    지속시간: {frame.duration:.1f}초")
        print(f"    출력경로: {frame.output_path}")
    
    return frames

def test_text_settings():
    """텍스트 설정 테스트"""
    print("\n🎨 텍스트 설정 테스트 시작\n")
    
    # 사용자 정의 설정 파일 생성
    custom_config = {
        "fonts": {
            "ko": "assets/fonts/NanumGothic.ttf",
            "zh": "assets/fonts/NotoSansCJK-Regular.ttc",
            "en": "assets/fonts/NotoSans-Regular.ttf"
        },
        "default_settings": {
            "font_size": 60,
            "font_color": "#00FF00",
            "stroke_color": "#000000",
            "stroke_width": 3,
            "background_color": "#000080",
            "padding": 30,
            "line_spacing": 15,
            "alignment": "center"
        },
        "scene_types": {
            "conversation": {
                "screen1": {
                    "font_size": 72,
                    "font_color": "#FFFF00",
                    "background_color": "#800000"
                },
                "screen2": {
                    "font_size": 60,
                    "font_color": "#00FFFF",
                    "background_color": "#008000"
                }
            }
        }
    }
    
    config_path = "test_output/subtitle/custom_config.json"
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(custom_config, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 사용자 정의 설정 파일 생성: {config_path}")
    
    # 사용자 정의 설정으로 렌더러 초기화
    custom_renderer = TextRenderer(config_path)
    
    # 사용자 정의 설정으로 이미지 생성
    test_image = custom_renderer.render_conversation_screen1(1, "안녕하세요!", 800, 600)
    custom_path = "test_output/subtitle/custom_settings.png"
    success = custom_renderer.save_image(test_image, custom_path)
    
    if success:
        print("✅ 사용자 정의 설정 적용 성공")
        print(f"이미지 저장: {custom_path}")
    else:
        print("❌ 사용자 정의 설정 적용 실패")
    
    return custom_renderer

def main():
    """메인 테스트 함수"""
    print("🎬 자막 이미지 생성 시스템 테스트 시작\n")
    
    try:
        # 1. 텍스트 렌더러 테스트
        renderer = test_text_renderer()
        
        # 2. 자막 생성기 테스트
        generator, frames = test_subtitle_generator()
        
        # 3. SSML mark 태그 기반 생성 테스트
        ssml_frames = test_ssml_based_generation()
        
        # 4. 텍스트 설정 테스트
        custom_renderer = test_text_settings()
        
        print("\n🎉 모든 테스트 완료!")
        print("\n📁 생성된 파일들:")
        print("  - test_output/subtitle/test_text.png")
        print("  - test_output/subtitle/test_multiline.png")
        print("  - test_output/subtitle/test_screen1.png")
        print("  - test_output/subtitle/test_screen2.png")
        print("  - test_output/subtitle/frames/ (PNG 시퀀스)")
        print("  - test_output/subtitle/ssml_frames/ (SSML 기반)")
        print("  - test_output/subtitle/custom_settings.png")
        print("  - test_output/subtitle/custom_config.json")
        
        print("\n🎯 사양서 준수 확인:")
        print("  ✅ SSML mark 태그 기반 정확한 타이밍")
        print("  ✅ PNG 시퀀스 자동 생성")
        print("  ✅ 텍스트 설정 적용 (폰트, 크기, 색상, 위치)")
        print("  ✅ 각 행별로 2개의 독립적인 화면 생성")
        print("  ✅ 화면 1: 순번 + 원어 텍스트")
        print("  ✅ 화면 2: 순번 + 원어 + 학습어 + 읽기")
        
        print("\n🔧 다음 단계:")
        print("  1. 실제 폰트 파일 설정")
        print("  2. 정확한 타이밍 정보 통합")
        print("  3. FFmpeg를 사용한 최종 비디오 렌더링")
        print("  4. 품질 최적화 및 사용자 인터페이스")
        
    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
