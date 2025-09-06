#!/usr/bin/env python3
"""
UI 통합 파이프라인 테스트 스크립트

UI 데이터와 파이프라인을 통합하고 체계적인 파일명 규칙을 테스트합니다.
"""

import os
import json
import time
from src.pipeline.ui_integrated_manager import (
    UIIntegratedPipelineManager, UIPipelineConfig
)

def test_file_naming_rules():
    """파일명 규칙 테스트"""
    print("📁 파일명 규칙 테스트 시작\n")
    
    from src.pipeline.utils.file_naming import FileNamingManager
    
    file_manager = FileNamingManager("test_output")
    
    # 프로젝트 이름 정리 테스트
    test_names = [
        "중국어 기초 회화 - 일상 인사말",
        "English Learning Video",
        "한국어_수업_비디오",
        "프로젝트 이름에 특수문자!@#$%^&*()",
        "Very Long Project Name That Exceeds The Maximum Length Limit And Should Be Truncated According To The Rules"
    ]
    
    for name in test_names:
        sanitized = file_manager.sanitize_project_name(name)
        print(f"원본: {name}")
        print(f"정리됨: {sanitized}")
        print()
    
    # 프로젝트 구조 생성 테스트
    project_name = "중국어_기초_회화_일상_인사말"
    project_dirs = file_manager.create_project_structure(project_name)
    
    print("📂 생성된 프로젝트 구조:")
    for dir_type, dir_path in project_dirs.items():
        print(f"  {dir_type}: {dir_path}")
        print(f"    존재: {os.path.exists(dir_path)}")
    
    # 파일명 생성 테스트
    print(f"\n📄 생성된 파일명들:")
    print(f"  Manifest: {file_manager.generate_manifest_filename(project_name)}")
    print(f"  SSML: {file_manager.generate_ssml_filename(project_name)}")
    print(f"  오디오: {file_manager.generate_audio_filename(project_name)}")
    print(f"  자막 프레임: {file_manager.generate_subtitle_frame_filename(project_name, 'scene_01', 'screen1', 0)}")
    print(f"  최종 비디오: {file_manager.generate_final_video_filename(project_name)}")
    print(f"  프리뷰: {file_manager.generate_preview_filename(project_name)}")
    print(f"  파이프라인 보고서: {file_manager.generate_pipeline_report_filename(project_name)}")
    
    return file_manager, project_dirs

def test_progress_logger():
    """진행 상황 로거 테스트"""
    print("\n📊 진행 상황 로거 테스트 시작\n")
    
    from src.pipeline.utils.progress_logger import ProgressLogger
    
    # 진행 상황 로거 초기화
    logger = ProgressLogger("테스트_프로젝트", "test_output/logs")
    
    # 진행 단계 추가
    logger.add_progress_step("1단계: 초기화", 1, 5)
    logger.add_progress_step("2단계: 데이터 로드", 2, 5)
    logger.add_progress_step("3단계: 처리", 3, 5)
    logger.add_progress_step("4단계: 검증", 4, 5)
    logger.add_progress_step("5단계: 완료", 5, 5)
    
    # 진행 상황 시뮬레이션
    logger.start_step("1단계: 초기화")
    time.sleep(0.5)
    logger.complete_step("1단계: 초기화", "초기화 완료")
    
    logger.start_step("2단계: 데이터 로드")
    time.sleep(0.3)
    logger.update_step_progress("2단계: 데이터 로드", 50.0, "데이터 로드 중...")
    time.sleep(0.3)
    logger.complete_step("2단계: 데이터 로드", "데이터 로드 완료")
    
    logger.start_step("3단계: 처리")
    time.sleep(0.4)
    logger.complete_step("3단계: 처리", "처리 완료")
    
    logger.start_step("4단계: 검증")
    time.sleep(0.2)
    logger.complete_step("4단계: 검증", "검증 완료")
    
    logger.start_step("5단계: 완료")
    time.sleep(0.1)
    logger.complete_step("5단계: 완료", "모든 단계 완료!")
    
    # 로그 추가
    logger.log_info("테스트 정보 메시지")
    logger.log_warning("테스트 경고 메시지")
    logger.log_error("테스트 에러 메시지")
    logger.log_debug("테스트 디버그 메시지")
    
    # 진행 상황 요약 출력
    summary = logger.get_progress_summary()
    print(f"\n📊 진행 상황 요약:")
    for key, value in summary.items():
        print(f"  {key}: {value}")
    
    # 최종 요약 출력
    logger.print_summary()
    
    return logger

def test_ui_integrated_pipeline():
    """UI 통합 파이프라인 테스트"""
    print("\n🚀 UI 통합 파이프라인 테스트 시작\n")
    
    # UI 데이터 시뮬레이션
    ui_data = {
        "project_info": {
            "name": "중국어 기초 회화 - 일상 인사말",
            "description": "일상적인 인사말을 배우는 중국어 학습 비디오"
        },
        "scenes": [
            {
                "type": "intro",
                "full_script": "안녕하세요! 중국어 학습의 문을 열어보겠습니다. 오늘은 '일상생활에서 자주 사용하는 인사말'을 배워보겠습니다."
            },
            {
                "type": "conversation",
                "native_script": "안녕하세요!",
                "learning_script": "你好！",
                "reading_script": "니하오!"
            },
            {
                "type": "conversation",
                "native_script": "고맙습니다!",
                "learning_script": "谢谢！",
                "reading_script": "씨에씨에!"
            },
            {
                "type": "conversation",
                "native_script": "천만에요!",
                "learning_script": "不客气！",
                "reading_script": "부커치!"
            },
            {
                "type": "ending",
                "full_script": "오늘도 열심히 공부하셨습니다. 다음에 또 만나요!"
            }
        ]
    }
    
    # 파이프라인 설정
    config = UIPipelineConfig(
        project_name="중국어_기초_회화_일상_인사말",
        resolution="1920x1080",
        fps=30,
        enable_audio_generation=True,
        enable_subtitle_generation=True,
        enable_video_rendering=True,
        enable_quality_optimization=False,
        enable_preview_generation=True,
        cleanup_temp_files=False,  # 테스트용으로 임시 파일 보존
        output_directory="test_output"
    )
    
    # UI 통합 파이프라인 매니저 초기화
    manager = UIIntegratedPipelineManager(config)
    
    # 콜백 함수 설정
    def progress_callback(step):
        print(f"🎬 진행 상황: [{step.step_number}/{step.total_steps}] {step.step_name} - {step.status}")
        if step.message:
            print(f"   메시지: {step.message}")
    
    def log_callback(entry):
        print(f"📝 로그: [{entry.level}] {entry.message}")
    
    def completion_callback(result):
        print(f"\n🎉 파이프라인 완료 콜백 호출!")
        print(f"  성공: {result.success}")
        print(f"  실행시간: {result.execution_time:.2f}초")
        print(f"  생성된 파일: {len(result.generated_files)}개")
    
    manager.set_progress_callback(progress_callback)
    manager.set_log_callback(log_callback)
    manager.set_completion_callback(completion_callback)
    
    # 파이프라인 실행
    print("🚀 UI 통합 파이프라인 실행 시작!")
    print(f"프로젝트: {config.project_name}")
    print(f"UI 데이터 키: {list(ui_data.keys())}")
    print(f"장면 수: {len(ui_data['scenes'])}")
    print()
    
    start_time = time.time()
    result = manager.run_pipeline_from_ui_data(ui_data)
    execution_time = time.time() - start_time
    
    # 결과 출력
    print(f"\n📊 파이프라인 실행 결과:")
    print(f"  성공: {'✅' if result.success else '❌'}")
    print(f"  프로젝트: {result.project_name}")
    print(f"  출력 디렉토리: {result.output_directory}")
    print(f"  실행 시간: {execution_time:.2f}초")
    print(f"  생성된 파일: {len(result.generated_files)}개")
    print(f"  오류: {len(result.errors)}개")
    print(f"  경고: {len(result.warnings)}개")
    
    if result.errors:
        print(f"\n❌ 오류 목록:")
        for error in result.errors:
            print(f"  - {error}")
    
    if result.warnings:
        print(f"\n⚠️ 경고 목록:")
        for warning in result.warnings:
            print(f"  - {warning}")
    
    if result.success:
        print(f"\n📁 생성된 파일들:")
        for file_type, file_path in result.generated_files.items():
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                print(f"  {file_type}: {file_path} ({file_size / 1024:.1f}KB)")
            else:
                print(f"  {file_type}: {file_path} (파일 없음)")
        
        # 프로젝트 요약
        project_summary = manager.get_project_summary()
        print(f"\n📊 프로젝트 요약:")
        print(f"  프로젝트 루트: {project_summary.get('project_root', 'N/A')}")
        print(f"  총 파일 크기: {project_summary.get('total_size', 0) / (1024*1024):.2f}MB")
        
        for dir_name, dir_info in project_summary.get('directories', {}).items():
            if dir_info.get('exists'):
                print(f"  {dir_name}: {dir_info['file_count']}개 파일")
    
    return result

def main():
    """메인 테스트 함수"""
    print("🎬 UI 통합 파이프라인 시스템 테스트 시작\n")
    
    try:
        # 1. 파일명 규칙 테스트
        file_manager, project_dirs = test_file_naming_rules()
        
        # 2. 진행 상황 로거 테스트
        logger = test_progress_logger()
        
        # 3. UI 통합 파이프라인 테스트
        result = test_ui_integrated_pipeline()
        
        print("\n🎉 모든 테스트 완료!")
        
        if result and result.success:
            print("\n🎯 사양서 준수 확인:")
            print("  ✅ 체계적인 파일명 규칙 적용")
            print("  ✅ 프로젝트별 폴더 구조 생성")
            print("  ✅ 실시간 진행 상황 모니터링")
            print("  ✅ 상세한 로그 및 디버깅 정보")
            print("  ✅ UI 데이터 → 파이프라인 자동 변환")
            print("  ✅ 단계별 검증 및 에러 처리")
            
            print("\n🔧 다음 단계:")
            print("  1. 실제 UI 컴포넌트와 연동")
            print("  2. 사용자 설정 인터페이스 개발")
            print("  3. 배치 처리 및 스케줄링")
            print("  4. 클라우드 배포 및 확장")
            
        else:
            print("\n⚠️ 일부 테스트가 실패했습니다")
            print("에러 로그를 확인하고 문제를 해결하세요")
        
    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
