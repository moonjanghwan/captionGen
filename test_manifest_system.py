#!/usr/bin/env python3
"""
Manifest 시스템 테스트 파일

이 파일은 Manifest 파싱/검증 시스템의 기본 기능을 테스트합니다.
"""

import json
import os
from src.pipeline.manifest import (
    ManifestParser, 
    ManifestValidator, 
    ManifestGenerator,
    Manifest
)


def test_basic_manifest():
    """기본 Manifest 생성 및 검증 테스트"""
    print("=== 기본 Manifest 테스트 ===")
    
    # Manifest 생성기 초기화
    generator = ManifestGenerator()
    
    # 템플릿에서 Manifest 생성
    manifest = generator.create_from_template("basic_conversation", "테스트 프로젝트")
    
    print(f"프로젝트명: {manifest.project_name}")
    print(f"해상도: {manifest.resolution}")
    print(f"장면 수: {len(manifest.scenes)}")
    
    # 장면 정보 출력
    for i, scene in enumerate(manifest.scenes):
        print(f"  장면 {i+1}: {scene.id} ({scene.type})")
    
    return manifest


def test_manifest_validation():
    """Manifest 검증 테스트"""
    print("\n=== Manifest 검증 테스트 ===")
    
    # 검증기 초기화
    validator = ManifestValidator()
    
    # 테스트용 Manifest 데이터 (오류 포함)
    test_data = {
        "project_name": "",  # 오류: 빈 프로젝트명
        "resolution": "1920x1080",
        "scenes": [
            {
                "id": "intro_01",
                "type": "intro",
                "full_script": "인트로 스크립트"
            },
            {
                "id": "conversation_01",  # 오류: 필수 필드 누락
                "type": "conversation"
            }
        ]
    }
    
    # 검증 수행
    try:
        manifest = Manifest.from_dict(test_data)
        validation_result = validator.validate(manifest)
        
        print(f"검증 결과: {'성공' if validation_result.is_valid else '실패'}")
        print(f"오류 수: {len(validation_result.errors)}")
        print(f"경고 수: {len(validation_result.warnings)}")
        
        # 오류 상세 정보
        for error in validation_result.errors:
            print(f"  오류: {error.field} - {error.message}")
            if error.scene_id:
                print(f"    장면: {error.scene_id}")
        
        # 경고 상세 정보
        for warning in validation_result.warnings:
            print(f"  경고: {warning.field} - {warning.message}")
            if warning.scene_id:
                print(f"    장면: {warning.scene_id}")
                
    except Exception as e:
        print(f"검증 중 오류 발생: {e}")


def test_manifest_operations():
    """Manifest 조작 기능 테스트"""
    print("\n=== Manifest 조작 기능 테스트 ===")
    
    generator = ManifestGenerator()
    
    # 기본 Manifest 생성
    manifest = generator.create_from_template("basic_conversation", "조작 테스트")
    
    print(f"초기 장면 수: {len(manifest.scenes)}")
    
    # 장면 추가
    new_scene_data = {
        "id": "conversation_02",
        "type": "conversation",
        "sequence": 2,
        "native_script": "How old are you?",
        "learning_script": "몇 살이세요?",
        "reading_script": "Myeot sa-ri-se-yo?"
    }
    
    manifest = generator.add_scene(manifest, new_scene_data)
    print(f"장면 추가 후 장면 수: {len(manifest.scenes)}")
    
    # 장면 업데이트
    manifest = generator.update_scene(manifest, "intro_01", {
        "full_script": "업데이트된 인트로 스크립트입니다!"
    })
    
    # 업데이트된 장면 확인
    intro_scene = next(scene for scene in manifest.scenes if scene.id == "intro_01")
    print(f"업데이트된 인트로: {intro_scene.full_script}")
    
    return manifest


def test_manifest_save_load():
    """Manifest 저장/로드 테스트"""
    print("\n=== Manifest 저장/로드 테스트 ===")
    
    parser = ManifestParser()
    generator = ManifestGenerator()
    
    # Manifest 생성
    manifest = generator.create_from_template("advanced_conversation", "저장/로드 테스트")
    
    # 임시 파일로 저장
    temp_file = "temp_manifest.json"
    try:
        parser.save_manifest(manifest, temp_file)
        print(f"Manifest 저장 완료: {temp_file}")
        
        # 파일에서 다시 로드
        loaded_manifest = parser.parse_file(temp_file)
        print(f"Manifest 로드 완료: {loaded_manifest.project_name}")
        
        # 정보 비교
        print(f"원본 장면 수: {len(manifest.scenes)}")
        print(f"로드된 장면 수: {len(loaded_manifest.scenes)}")
        
        # 장면 타입별 개수 비교
        for scene_type in ["intro", "conversation", "ending"]:
            original_count = len(manifest.get_scenes_by_type(scene_type))
            loaded_count = len(loaded_manifest.get_scenes_by_type(scene_type))
            print(f"  {scene_type}: {original_count} vs {loaded_count}")
        
    finally:
        # 임시 파일 정리
        if os.path.exists(temp_file):
            os.remove(temp_file)
            print(f"임시 파일 삭제: {temp_file}")


def test_available_templates():
    """사용 가능한 템플릿 테스트"""
    print("\n=== 사용 가능한 템플릿 테스트 ===")
    
    generator = ManifestGenerator()
    templates = generator.get_available_templates()
    
    print(f"사용 가능한 템플릿 수: {len(templates)}")
    for template in templates:
        print(f"  {template['id']}: {template['name']}")
        print(f"    설명: {template['description']}")


def main():
    """메인 테스트 함수"""
    print("🎬 Manifest 시스템 테스트 시작\n")
    
    try:
        # 1. 기본 Manifest 테스트
        manifest = test_basic_manifest()
        
        # 2. 검증 테스트
        test_manifest_validation()
        
        # 3. 조작 기능 테스트
        test_manifest_operations()
        
        # 4. 저장/로드 테스트
        test_manifest_save_load()
        
        # 5. 템플릿 테스트
        test_available_templates()
        
        print("\n✅ 모든 테스트가 성공적으로 완료되었습니다!")
        
    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
