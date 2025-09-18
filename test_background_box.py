#!/usr/bin/env python3
"""
바탕 박스가 있는 이미지 생성 테스트
"""

import os
import sys

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_background_box():
    """바탕 박스가 있는 이미지 생성 테스트"""
    print("=" * 80)
    print("🔥 바탕 박스가 있는 이미지 생성 테스트")
    print("=" * 80)
    
    try:
        from src.pipeline.renderers.png_renderer import PNGRenderer
        
        # 바탕 박스가 활성화된 테스트 설정
        test_settings = {
            "common": {
                "bg": {
                    "enabled": True,
                    "type": "단색",
                    "color": "#000000",
                    "alpha": "0.7",
                    "margin": "10"
                },
                "shadow": {
                    "color": "#000000",
                    "alpha": 0.6,
                    "offx": 2,
                    "offy": 2
                }
            },
            "tabs": {
                "인트로 설정": {
                    "rows": [
                        {"행": "인트로", "폰트(pt)": "Noto Sans KR", "크기(pt)": 80, "색상": "#FFFFFF", "x": 50, "y": 540, "w": 1820, "상하 정렬": "Center", "좌우 정렬": "Center", "쉐도우": "True", "바탕": "True"}
                    ]
                }
            }
        }
        
        # PNG 렌더러 초기화
        renderer = PNGRenderer(test_settings)
        
        # 테스트 텍스트 (여러 줄)
        test_text = "오늘은 여러분이 중국 현지에서 바로 쓸 수 있는 '일상생활 필수 중국어 회화' 5가지를 배워볼 거예요."
        
        # 출력 디렉토리
        output_dir = "test_output/background_test"
        os.makedirs(output_dir, exist_ok=True)
        
        # 바탕 박스가 있는 이미지 생성
        print("\n🔥 바탕 박스가 있는 이미지 생성 테스트...")
        created_files = renderer.create_intro_ending_images_by_sentences(
            test_text,
            output_dir,
            (1920, 1080),
            "인트로"
        )
        
        if created_files:
            print(f"\n✅ 바탕 박스가 있는 이미지 생성 성공!")
            print(f"   - 생성된 파일 수: {len(created_files)}")
            for file_path in created_files:
                print(f"   - {os.path.basename(file_path)}")
        else:
            print(f"\n❌ 바탕 박스가 있는 이미지 생성 실패!")
            
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_background_box()
