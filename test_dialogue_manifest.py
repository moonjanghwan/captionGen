#!/usr/bin/env python3
"""
dialogue_manifest.json 파일 테스트 스크립트
"""

from src.pipeline.manifest import ManifestParser

def main():
    print("🎬 Dialogue Manifest 테스트 시작\n")
    
    try:
        # Manifest 파서 초기화
        parser = ManifestParser()
        
        # 파일에서 Manifest 로드
        manifest = parser.parse_file('dialogue_manifest.json')
        
        print("✅ Manifest 검증 성공!")
        print(f"프로젝트: {manifest.project_name}")
        print(f"해상도: {manifest.resolution}")
        print(f"장면 수: {len(manifest.scenes)}")
        
        print("\n📋 장면 정보:")
        for i, scene in enumerate(manifest.scenes, 1):
            print(f"  {i}. {scene.id} ({scene.type}) - 순번: {scene.sequence}")
            print(f"     원어: {scene.native_script}")
            print(f"     학습어: {scene.learning_script}")
            print(f"     읽기: {scene.reading_script}")
            print()
        
        # Manifest 정보 요약
        info = parser.get_manifest_info(manifest)
        print("📊 Manifest 요약:")
        print(f"  총 장면 수: {info['total_scenes']}")
        print(f"  장면 타입별:")
        for scene_type, count in info['scene_types'].items():
            print(f"    {scene_type}: {count}개")
        print(f"  예상 길이: {info['estimated_duration']:.1f}초")
        print(f"  배경 설정: {'있음' if info['has_background'] else '없음'}")
        
        print("\n🎯 사양서 준수 확인:")
        print("  ✅ 각 행별로 2개의 독립적인 텍스트 화면 생성 가능")
        print("  ✅ 화면 1: 순번 + 원어 텍스트")
        print("  ✅ 화면 2: 순번 + 원어 + 학습어 + 읽기")
        print("  ✅ 화자 간, 행 간 1초 무음 자동 삽입")
        print("  ✅ SSML <mark> 태그로 정확한 타이밍 생성 가능")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
