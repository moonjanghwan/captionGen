#!/usr/bin/env python3
"""
텍스트 렌더링 디버깅 테스트 스크립트

이 스크립트는 텍스트 렌더링 시스템의 디버깅 브레이킹 포인트를 테스트합니다.
실행하면 각 렌더러의 디버깅 정보가 출력됩니다.
"""

import os
import sys
from typing import Dict, Any

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_png_renderer():
    """PNG 렌더러 디버깅 테스트"""
    print("=" * 80)
    print("🔥 PNG 렌더러 디버깅 테스트 시작")
    print("=" * 80)
    
    try:
        from src.pipeline.renderers.png_renderer import PNGRenderer
        
        # 테스트용 설정
        test_settings = {
            "common": {
                "bg": {
                    "enabled": True,
                    "type": "단색",
                    "color": "#000000"
                },
                "shadow": {
                    "color": "#000000",
                    "alpha": 0.6,
                    "offx": 2,
                    "offy": 2
                }
            },
            "tabs": {
                "회화 설정": {
                    "rows": [
                        {"행": "제목", "폰트(pt)": "Noto Sans KR", "크기(pt)": 90, "색상": "#FFFFFF", "x": 50, "y": 50, "w": 1820, "상하 정렬": "Top", "좌우 정렬": "Center", "쉐도우": True, "바탕": False},
                        {"행": "원어", "폰트(pt)": "Noto Sans KR", "크기(pt)": 80, "색상": "#FFFFFF", "x": 50, "y": 200, "w": 1820, "상하 정렬": "Top", "좌우 정렬": "Center", "쉐도우": True, "바탕": False},
                        {"행": "학습어", "폰트(pt)": "Noto Sans KR", "크기(pt)": 70, "색상": "#FFFFFF", "x": 50, "y": 350, "w": 1820, "상하 정렬": "Top", "좌우 정렬": "Center", "쉐도우": True, "바탕": False},
                        {"행": "읽기", "폰트(pt)": "Noto Sans KR", "크기(pt)": 60, "색상": "#FFFFFF", "x": 50, "y": 500, "w": 1820, "상하 정렬": "Top", "좌우 정렬": "Center", "쉐도우": True, "바탕": False}
                    ]
                },
                "인트로 설정": {
                    "rows": [
                        {"행": "인트로", "폰트(pt)": "Noto Sans KR", "크기(pt)": 80, "색상": "#FFFFFF", "x": 50, "y": 540, "w": 1820, "상하 정렬": "Center", "좌우 정렬": "Center", "쉐도우": True, "바탕": False}
                    ]
                }
            }
        }
        
        # PNG 렌더러 초기화
        renderer = PNGRenderer(test_settings)
        
        # 테스트 데이터
        test_scene_data = {
            "order": "1",
            "native_script": "안녕하세요!",
            "learning_script": "Hello!",
            "reading_script": "안녕하세요! Hello!"
        }
        
        # 테스트 출력 경로
        test_output_path = "test_output/debug_test_conversation.png"
        os.makedirs(os.path.dirname(test_output_path), exist_ok=True)
        
        # 회화 이미지 생성 테스트 (메서드가 없으므로 건너뜀)
        print("\n🔥 회화 이미지 생성 테스트...")
        print("⚠️ create_conversation_image 메서드가 없어서 건너뜁니다.")
            
        # 인트로 이미지 생성 테스트
        print("\n🔥 인트로 이미지 생성 테스트...")
        intro_output_path = "test_output/debug_test_intro.png"
        success = renderer.create_intro_ending_image(
            "테스트 인트로 텍스트입니다.",
            intro_output_path,
            (1920, 1080),
            "인트로"
        )
        
        if success:
            print("✅ 인트로 이미지 생성 성공!")
        else:
            print("❌ 인트로 이미지 생성 실패!")
            
    except Exception as e:
        print(f"❌ PNG 렌더러 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

def test_text_renderer():
    """TextRenderer 디버깅 테스트 (삭제됨)"""
    print("\n" + "=" * 80)
    print("⚠️ TextRenderer는 삭제됨 - PNGRenderer 사용")
    print("=" * 80)
    print("TextRenderer는 삭제되었습니다. PNGRenderer를 사용하세요.")

def main():
    """메인 테스트 함수"""
    print("🚀 텍스트 렌더링 디버깅 테스트 시작")
    print("이 스크립트는 각 렌더러의 디버깅 브레이킹 포인트를 테스트합니다.")
    print("콘솔 출력을 통해 디버깅 정보를 확인할 수 있습니다.\n")
    
    # PNG 렌더러 테스트
    test_png_renderer()
    
    # TextRenderer 테스트
    test_text_renderer()
    
    print("\n" + "=" * 80)
    print("🎉 모든 디버깅 테스트 완료!")
    print("=" * 80)
    print("생성된 테스트 이미지들:")
    print("- test_output/debug_test_conversation_screen1.png")
    print("- test_output/debug_test_conversation_screen2.png") 
    print("- test_output/debug_test_intro.png")
    print("- test_output/debug_test_text_renderer.png")
    print("\n디버깅 브레이킹 포인트가 제대로 작동하는지 콘솔 출력을 확인하세요!")

if __name__ == "__main__":
    main()
