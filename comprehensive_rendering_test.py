#!/usr/bin/env python3
"""
종합 렌더링 테스트
텍스트와 바탕 일치 문제 및 투명도 문제 전체 검토
"""

import os
import sys
import json
from PIL import Image, ImageDraw, ImageFont

sys.path.append('src')

from pipeline.renderers.png_renderer import PNGRenderer

def test_comprehensive_rendering():
    """종합 렌더링 테스트"""
    print("=== 종합 렌더링 테스트 ===")
    
    # 설정 로드
    settings_path = "output/kor-chn/kor-chn/_text_settings.json"
    with open(settings_path, 'r', encoding='utf-8') as f:
        settings = json.load(f)
    
    try:
        renderer = PNGRenderer(settings)
        print("✅ PNGRenderer 초기화 성공")
        
        # 설정 확인
        print(f"\n=== 설정 확인 ===")
        common_bg = renderer.merged_settings.get('common', {}).get('bg', {})
        print(f"공통 바탕 설정:")
        print(f"  활성화: {common_bg.get('enabled', False)}")
        print(f"  색상: {common_bg.get('color', '#000000')}")
        print(f"  투명도: {common_bg.get('alpha', '1.0')}")
        print(f"  마진: {common_bg.get('margin', '5')}")
        print(f"  타입: {common_bg.get('type', '단색')}")
        print(f"  값: {common_bg.get('value', '')}")
        
        # 인트로 설정 확인
        intro_settings = renderer.merged_settings.get('tabs', {}).get('인트로 설정', {})
        intro_rows = intro_settings.get('rows', [])
        if intro_rows:
            intro_row = intro_rows[0]
            print(f"\n인트로 설정:")
            print(f"  위치: ({intro_row.get('x', 50)}, {intro_row.get('y', 540)})")
            print(f"  너비: {intro_row.get('w', 1820)}")
            print(f"  정렬: {intro_row.get('좌우 정렬', 'Center')} / {intro_row.get('상하 정렬', 'Center')}")
            print(f"  바탕: {intro_row.get('바탕', False)}")
            print(f"  폰트 크기: {intro_row.get('크기(pt)', 80)}")
        
        # 회화 설정 확인
        conversation_settings = renderer.merged_settings.get('tabs', {}).get('회화 설정', {})
        conversation_rows = conversation_settings.get('rows', [])
        print(f"\n회화 설정:")
        for i, row in enumerate(conversation_rows):
            print(f"  행 {i+1} ({row.get('행', f'행{i+1}')}):")
            print(f"    위치: ({row.get('x', 50)}, {row.get('y', 200)})")
            print(f"    너비: {row.get('w', 1820)}")
            print(f"    정렬: {row.get('좌우 정렬', 'Center')} / {row.get('상하 정렬', 'Top')}")
            print(f"    바탕: {row.get('바탕', False)}")
            print(f"    폰트 크기: {row.get('크기(pt)', 80)}")
        
        # 1. 인트로 이미지 테스트
        print(f"\n=== 1. 인트로 이미지 테스트 ===")
        test_text = "현지에서 바로 쓸 수 있는 거 회화' 5가지를 배워볼 예요."
        
        success = renderer.create_intro_ending_image(
            text_content=test_text,
            output_path="test_output/comprehensive_intro_test.png",
            resolution=(1920, 1080),
            script_type="인트로"
        )
        
        if success:
            print("✅ 인트로 이미지 생성 성공")
            analyze_image("test_output/comprehensive_intro_test.png", "인트로", intro_row)
        else:
            print("❌ 인트로 이미지 생성 실패")
        
        # 2. 회화 이미지 테스트
        print(f"\n=== 2. 회화 이미지 테스트 ===")
        test_scene_data = {
            'order': '1',
            'native_script': '안녕하세요!',
            'learning_script': '你好！',
            'reading_script': '니하오!'
        }
        
        success = renderer.create_conversation_image(
            scene_data=test_scene_data,
            output_path="test_output/comprehensive_conversation_test.png",
            resolution=(1920, 1080),
            settings=settings
        )
        
        if success:
            print("✅ 회화 이미지 생성 성공")
            
            # 화면1 분석
            screen1_path = "test_output/comprehensive_conversation_test_screen1.png"
            if os.path.exists(screen1_path):
                analyze_image(screen1_path, "회화 화면1", conversation_settings.rows[0])
                analyze_image(screen1_path, "회화 화면1", conversation_settings.rows[1])
            
            # 화면2 분석
            screen2_path = "test_output/comprehensive_conversation_test_screen2.png"
            if os.path.exists(screen2_path):
                for i, row in enumerate(conversation_settings.rows):
                    analyze_image(screen2_path, f"회화 화면2 행{i+1}", row)
        else:
            print("❌ 회화 이미지 생성 실패")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def analyze_image(image_path: str, title: str, row_settings):
    """이미지 분석"""
    print(f"\n--- {title} 분석 ---")
    
    if not os.path.exists(image_path):
        print(f"❌ 이미지 파일 없음: {image_path}")
        return
    
    with Image.open(image_path) as img:
        print(f"이미지 크기: {img.size}")
        
        # 설정된 위치 확인
        x, y, w = row_settings.x, row_settings.y, row_settings.w
        print(f"설정된 위치: ({x}, {y}), 너비: {w}")
        
        # 중앙 정렬 계산
        if row_settings.h_align == "center":
            center_x = x + w // 2
            print(f"중앙 정렬 위치: {center_x}")
            
            # 중앙 정렬 위치에서 픽셀 확인
            test_points = [
                (center_x, y, "중앙 정렬 위치"),
                (center_x - 100, y, "중앙-100"),
                (center_x + 100, y, "중앙+100"),
                (x, y, "설정된 시작 위치"),
                (x + w, y, "설정된 끝 위치")
            ]
        else:
            # 좌측 정렬
            test_points = [
                (x, y, "설정된 위치"),
                (x + 100, y, "시작+100"),
                (x + w, y, "설정된 끝 위치")
            ]
        
        print(f"\n픽셀 색상 확인:")
        for px, py, desc in test_points:
            if 0 <= px < img.size[0] and 0 <= py < img.size[1]:
                pixel = img.getpixel((px, py))
                print(f"  {desc} ({px}, {py}): RGB={pixel[:3]}, A={pixel[3]}")
                
                # 바탕 색상 확인
                if pixel[:3] == (51, 51, 51):  # #333333
                    print(f"    → 바탕 색상 감지됨")
                elif pixel[3] < 255:
                    print(f"    → 투명도 적용됨 (알파: {pixel[3]})")
                else:
                    print(f"    → 배경 이미지 색상")
            else:
                print(f"  {desc} ({px}, {py}): 범위 밖")

if __name__ == "__main__":
    print("종합 렌더링 테스트 시작")
    
    success = test_comprehensive_rendering()
    
    if success:
        print("\n🎉 종합 테스트 완료!")
        print("📁 생성된 이미지들:")
        print("   - test_output/comprehensive_intro_test.png")
        print("   - test_output/comprehensive_conversation_test_screen1.png")
        print("   - test_output/comprehensive_conversation_test_screen2.png")
    else:
        print("\n💥 종합 테스트 실패")
