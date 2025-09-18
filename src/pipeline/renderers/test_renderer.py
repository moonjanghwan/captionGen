# test_renderer.py
import os
from png_renderer import PNGRenderer  # 우리가 테스트할 클래스를 임포트합니다.

def run_test():
    """PNGRenderer를 독립적으로 테스트하여 숨겨진 오류를 찾는 스크립트"""
    print("🚀 렌더러 테스트를 시작합니다...")

    # 1. 테스트용 설정 데이터 (가짜 MergedSettings)
    # 실제 settings 구조와 동일하게 만듭니다.
    mock_settings = {
        'common': {
            'bg': {
                'enabled': True,
                'type': '색상',  # '이미지'로 변경하여 테스트 가능
                'value': '', # 배경 이미지 경로 (필요시 입력)
                'color': '#4a4a4a',
                'alpha': '0.8',
                'margin': '10'
            }
        },
        'tabs': {
            '인트로 설정': {
                'rows': [
                    {
                        '행': '1행',
                        'x': '50', 'y': '980', 'w': '1820',
                        '크기(pt)': '90',
                        '폰트(pt)': 'KoPubWorld돋움체',
                        '색상': '#FFFFFF',
                        '굵기': 'Bold',
                        '좌우 정렬': 'center',
                        '상하 정렬': 'bottom',
                        '바탕': True,
                        '쉐도우': False,
                        '외곽선': False
                    }
                ]
            }
        }
    }

    # 2. 테스트용 파라미터
    test_text = "이 텍스트가 정상적으로 보이나요?\n두 번째 줄도 테스트합니다."
    output_dir = "test_output"
    output_filename = "test_intro_image.png"
    output_path = os.path.join(output_dir, output_filename)
    resolution = (1920, 1080)
    
    # 출력 폴더 생성
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"📁 '{output_dir}' 폴더를 생성했습니다.")

    try:
        # 3. PNGRenderer 인스턴스 생성 및 함수 호출
        print("\n[단계 1] PNGRenderer 인스턴스 생성...")
        renderer = PNGRenderer(merged_settings=mock_settings)
        print("✅ 인스턴스 생성 성공!")

        print("\n[단계 2] create_intro_ending_image 함수 호출...")
        success = renderer.create_intro_ending_image(
            text=test_text,
            output_path=output_path,
            resolution=resolution,
            script_type='인트로'  # 필수 인자를 정확히 전달
        )
        
        if success:
            print(f"\n🎉 테스트 성공! '{output_path}' 파일을 확인하세요.")
        else:
            print(f"\n❌ 테스트 함수는 실행되었으나, 내부에서 실패했습니다.")

    except Exception as e:
        # 4. 숨겨진 오류 출력!
        print("\n🔥🔥🔥 치명적인 오류 발견! 🔥🔥🔥")
        print("아래 오류 메시지를 복사해서 알려주세요:\n")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_test()