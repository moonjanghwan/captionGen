#!/usr/bin/env python3
"""
수정된 렌더링 테스트
중앙정렬, 바탕, 스마트줄바꿈이 제대로 작동하는지 확인
"""

import os
import sys
sys.path.append('src')

from pipeline.renderers.png_renderer import PNGRenderer

def test_fixed_rendering():
    """수정된 렌더링 테스트"""
    print("=== 수정된 렌더링 테스트 ===")
    
    # 인트로 설정과 동일한 설정으로 테스트
    test_settings = {
        "common": {
            "bg": {
                "enabled": True,
                "type": "색상",
                "value": "#000000",
                "color": "#000000"
            },
            "shadow": {
                "enabled": True,
                "offx": 3,
                "offy": 3,
                "color": "#000000"
            },
            "border": {
                "enabled": True,
                "thick": 4,
                "color": "#000000"
            }
        },
        "tabs": {
            "인트로 설정": {
                "행수": "1",
                "비율": "16:9",
                "해상도": "1920x1080",
                "rows": [
                    {
                        "행": "1행",
                        "x": "50",
                        "y": "980",
                        "w": "1820",
                        "크기(pt)": "90",
                        "폰트(pt)": "KoPubWorld돋움체",
                        "색상": "#FFFFFF",
                        "굵기": "Bold",
                        "좌우 정렬": "Center",
                        "상하 정렬": "Bottom",
                        "바탕": "True",
                        "쉐도우": "True",
                        "외곽선": "True"
                    }
                ]
            }
        }
    }
    
    try:
        # PNG 렌더러 초기화
        renderer = PNGRenderer(test_settings)
        print("✅ PNGRenderer 초기화 성공")
        
        # 병합된 설정 확인
        merged_settings = renderer.merged_settings
        if '인트로 설정' in merged_settings.script_types:
            row = merged_settings.script_types['인트로 설정'].rows[0]
            print(f"\n📊 설정 확인:")
            print(f"  - 위치: ({row.x}, {row.y})")
            print(f"  - 너비: {row.w}px")
            print(f"  - 크기: {row.font_size}pt")
            print(f"  - 색상: {row.color}")
            print(f"  - 정렬: {row.h_align}/{row.v_align}")
            print(f"  - 바탕: {row.background}")
            print(f"  - 쉐도우: {row.shadow}")
            print(f"  - 외곽선: {row.border}")
        
        # 긴 텍스트로 테스트 (줄바꿈 확인)
        long_text = "일상생활 필수 중국어 회화 5가지를 배워볼 거예요. 카페에서 주문할 때, 길을 물어볼 때, 인사할 때 등 정말 유용하게 쓰일 표현들이 가득하니까요."
        
        success = renderer.create_intro_ending_image(
            text_content=long_text,
            output_path="test_output/test_fixed_rendering.png",
            resolution=(1920, 1080),
            script_type="인트로"
        )
        
        if success:
            print("\n✅ 수정된 렌더링 테스트 성공")
            print("📁 생성된 파일: test_output/test_fixed_rendering.png")
            
            # 파일 크기 확인
            if os.path.exists("test_output/test_fixed_rendering.png"):
                file_size = os.path.getsize("test_output/test_fixed_rendering.png")
                print(f"📊 파일 크기: {file_size:,} bytes")
            
            return True
        else:
            print("\n❌ 수정된 렌더링 테스트 실패")
            return False
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_fixed_rendering()
    if success:
        print("\n🎉 수정된 렌더링 테스트가 성공했습니다!")
        print("💡 이제 생성된 이미지를 확인해서 다음이 제대로 반영되었는지 확인해보세요:")
        print("   - 텍스트가 화면 하단 중앙에 위치")
        print("   - 1820px 너비 내에서 줄바꿈")
        print("   - 바탕색, 그림자, 외곽선 효과")
    else:
        print("\n💥 수정된 렌더링 테스트가 실패했습니다.")
