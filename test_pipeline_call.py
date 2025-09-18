#!/usr/bin/env python3
"""
파이프라인에서 create_intro_ending_image 호출 테스트
"""

import os
import sys

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_pipeline_call():
    """파이프라인에서 create_intro_ending_image 호출 테스트"""
    print("=" * 80)
    print("🔥 파이프라인에서 create_intro_ending_image 호출 테스트")
    print("=" * 80)
    
    try:
        from src.pipeline.steps.create_subtitles import run as create_subtitles_run
        from src.pipeline.core.context import PipelineContext
        
        # 테스트용 컨텍스트 생성
        print("🚀 테스트용 PipelineContext 생성 중...")
        
        # 간단한 테스트 설정
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
                "인트로 설정": {
                    "rows": [
                        {"행": "인트로", "폰트(pt)": "Noto Sans KR", "크기(pt)": 80, "색상": "#FFFFFF", "x": 50, "y": 540, "w": 1820, "상하 정렬": "Center", "좌우 정렬": "Center", "쉐도우": True, "바탕": False}
                    ]
                }
            }
        }
        
        # 테스트용 매니페스트 데이터
        class TestManifest:
            def __init__(self):
                self.resolution = "1920x1080"
                self.scenes = [
                    type('Scene', (), {
                        'type': 'intro',
                        'sequence': 1,
                        'full_script': '안녕하세요! 이것은 테스트 인트로입니다. 문장 단위로 나누어져야 합니다.'
                    })()
                ]
        
        # 테스트용 경로 설정
        class TestPaths:
            def __init__(self):
                self.intro_dir = "test_output/pipeline_test"
                os.makedirs(self.intro_dir, exist_ok=True)
        
        # PipelineContext 생성
        context = PipelineContext.create(
            project_name="테스트_프로젝트",
            identifier="test_001",
            script_type="인트로",
            manifest=TestManifest(),
            settings=test_settings
        )
        
        print("✅ PipelineContext 생성 완료")
        print(f"   - 프로젝트: {context.project_name}")
        print(f"   - 식별자: {context.identifier}")
        print(f"   - 스크립트 타입: {context.script_type}")
        print(f"   - 해상도: {context.manifest.resolution}")
        print(f"   - 씬 개수: {len(context.manifest.scenes)}")
        
        # 파이프라인 실행
        print("\n🔥 파이프라인 실행 시작...")
        create_subtitles_run(context)
        print("✅ 파이프라인 실행 완료!")
        
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_pipeline_call()
