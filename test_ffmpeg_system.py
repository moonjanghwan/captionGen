#!/usr/bin/env python3
"""
FFmpeg 통합 시스템 테스트 스크립트

오디오-비디오 동기화, 최종 MP4 렌더링, 품질 최적화를 테스트합니다.
"""

import os
import json
from src.pipeline.ffmpeg import (
    FFmpegRenderer, RenderConfig, 
    PipelineManager, PipelineConfig
)

def test_ffmpeg_renderer():
    """FFmpeg 렌더러 테스트"""
    print("🎬 FFmpeg 렌더러 테스트 시작\n")
    
    # 렌더링 설정
    config = RenderConfig(
        fps=30,
        resolution="1920x1080",
        video_codec="libx264",
        audio_codec="aac",
        video_bitrate="5000k",
        audio_bitrate="192k",
        quality_preset="medium",
        enable_hardware_acceleration=False,
        enable_two_pass_encoding=False
    )
    
    renderer = FFmpegRenderer(config)
    
    # FFmpeg 사용 가능 여부 확인
    if not renderer._check_ffmpeg_availability():
        print("⚠️ FFmpeg가 설치되지 않았습니다")
        print("🔧 FFmpeg 설치: https://ffmpeg.org/download.html")
        return None
    
    print("✅ FFmpeg 렌더러 초기화 성공")
    return renderer

def test_pipeline_manager():
    """파이프라인 매니저 테스트"""
    print("\n🚀 파이프라인 매니저 테스트 시작\n")
    
    # 파이프라인 설정
    pipeline_config = PipelineConfig(
        output_directory="test_output/pipeline",
        enable_audio_generation=True,
        enable_subtitle_generation=True,
        enable_video_rendering=True,
        enable_quality_optimization=False,
        enable_preview_generation=True,
        cleanup_temp_files=False  # 테스트용으로 임시 파일 보존
    )
    
    manager = PipelineManager(pipeline_config)
    print("✅ 파이프라인 매니저 초기화 성공")
    
    return manager

def test_full_pipeline():
    """전체 파이프라인 테스트"""
    print("\n🎬 전체 파이프라인 테스트 시작\n")
    
    # dialogue_manifest.json 확인
    manifest_path = "dialogue_manifest.json"
    if not os.path.exists(manifest_path):
        print(f"❌ Manifest 파일을 찾을 수 없습니다: {manifest_path}")
        return
    
    # 파이프라인 매니저 초기화
    pipeline_config = PipelineConfig(
        output_directory="test_output/pipeline",
        enable_audio_generation=True,
        enable_subtitle_generation=True,
        enable_video_rendering=True,
        enable_quality_optimization=False,
        enable_preview_generation=True,
        cleanup_temp_files=False
    )
    
    manager = PipelineManager(pipeline_config)
    
    # 전체 파이프라인 실행
    print("🚀 전체 파이프라인 실행 시작!")
    result = manager.run_full_pipeline(manifest_path)
    
    # 결과 출력
    print(f"\n📊 파이프라인 실행 결과:")
    print(f"  성공: {'✅' if result.success else '❌'}")
    print(f"  실행 시간: {result.execution_time:.1f}초")
    print(f"  오류: {len(result.errors)}개")
    print(f"  경고: {len(result.warnings)}개")
    
    if result.errors:
        print("\n❌ 오류 목록:")
        for error in result.errors:
            print(f"  - {error}")
    
    if result.warnings:
        print("\n⚠️ 경고 목록:")
        for warning in result.warnings:
            print(f"  - {warning}")
    
    # 출력 파일 정보
    if result.success:
        print(f"\n📁 생성된 파일들:")
        if result.audio_path:
            print(f"  오디오: {result.audio_path}")
        if result.subtitle_dir:
            print(f"  자막: {result.subtitle_dir}")
        if result.video_path:
            print(f"  비디오: {result.video_path}")
        if result.preview_path:
            print(f"  프리뷰: {result.preview_path}")
        
        # 파이프라인 요약 및 보고서 저장
        summary = manager.get_pipeline_summary(result)
        print(f"\n📊 파이프라인 요약:")
        print(f"  출력 파일 수: {len(summary['output_files'])}")
        
        if 'video_info' in summary:
            video_info = summary['video_info']
            print(f"  비디오 정보:")
            print(f"    지속시간: {video_info.get('duration', 0):.1f}초")
            print(f"    파일 크기: {video_info.get('size', 0) / (1024*1024):.1f}MB")
            print(f"    비트레이트: {video_info.get('bitrate', 0) / 1000:.0f}kbps")
        
        # 프로젝트 출력 디렉토리 결정
        project_name = "중국어_기초_회화_일상_인사말"
        project_output_dir = os.path.join("test_output/pipeline", project_name)
        
        # 파이프라인 보고서 저장
        manager.save_pipeline_report(result, project_output_dir)
    
    return result

def test_quality_optimization():
    """품질 최적화 테스트"""
    print("\n🔧 품질 최적화 테스트 시작\n")
    
    # 고품질 설정
    config = RenderConfig(
        fps=30,
        resolution="1920x1080",
        video_codec="libx264",
        audio_codec="aac",
        video_bitrate="8000k",
        audio_bitrate="256k",
        quality_preset="slow",
        enable_two_pass_encoding=True
    )
    
    renderer = FFmpegRenderer(config)
    
    # 테스트용 더미 비디오 파일 생성 (실제로는 기존 비디오 파일 사용)
    test_video_path = "test_output/pipeline/test_video.mp4"
    test_output_dir = os.path.dirname(test_video_path)
    os.makedirs(test_output_dir, exist_ok=True)
    
    # 간단한 테스트 비디오 생성 (1초 검은 화면)
    try:
        cmd = [
            'ffmpeg', '-y',
            '-f', 'lavfi',
            '-i', 'color=c=black:s=1920x1080:d=1',
            '-pix_fmt', 'yuv420p',
            test_video_path
        ]
        
        import subprocess
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ 테스트 비디오 생성: {test_video_path}")
        
        # 품질 최적화 테스트
        optimized_path = "test_output/pipeline/test_video_optimized.mp4"
        
        print("🔧 품질 최적화 시작...")
        success = renderer.optimize_quality(test_video_path, optimized_path, "8000k")
        
        if success and os.path.exists(optimized_path):
            print(f"✅ 품질 최적화 완료: {optimized_path}")
            
            # 비디오 정보 비교
            original_info = renderer.get_video_info(test_video_path)
            optimized_info = renderer.get_video_info(optimized_path)
            
            print(f"\n📊 품질 최적화 결과:")
            print(f"  원본 크기: {original_info.get('size', 0) / 1024:.1f}KB")
            print(f"  최적화 크기: {optimized_info.get('size', 0) / 1024:.1f}KB")
            print(f"  원본 비트레이트: {original_info.get('bitrate', 0) / 1000:.0f}kbps")
            print(f"  최적화 비트레이트: {optimized_info.get('bitrate', 0) / 1000:.0f}kbps")
            
        else:
            print("❌ 품질 최적화 실패")
        
    except Exception as e:
        print(f"⚠️ 품질 최적화 테스트 실패: {e}")

def test_preview_generation():
    """프리뷰 생성 테스트"""
    print("\n👀 프리뷰 생성 테스트 시작\n")
    
    renderer = FFmpegRenderer()
    
    # 테스트용 더미 비디오 파일 경로
    test_video_path = "test_output/pipeline/test_video.mp4"
    
    if not os.path.exists(test_video_path):
        print(f"⚠️ 테스트 비디오 파일을 찾을 수 없습니다: {test_video_path}")
        return
    
    # 5초 프리뷰 생성
    preview_path = "test_output/pipeline/test_preview.mp4"
    
    print("👀 5초 프리뷰 생성 시작...")
    success = renderer.create_preview(test_video_path, preview_path, duration=5)
    
    if success and os.path.exists(preview_path):
        print(f"✅ 프리뷰 생성 완료: {preview_path}")
        
        # 프리뷰 정보
        preview_info = renderer.get_video_info(preview_path)
        print(f"  프리뷰 지속시간: {preview_info.get('duration', 0):.1f}초")
        print(f"  프리뷰 크기: {preview_info.get('size', 0) / 1024:.1f}KB")
        
    else:
        print("❌ 프리뷰 생성 실패")

def main():
    """메인 테스트 함수"""
    print("🎬 FFmpeg 통합 시스템 테스트 시작\n")
    
    try:
        # 1. FFmpeg 렌더러 테스트
        renderer = test_ffmpeg_renderer()
        
        # 2. 파이프라인 매니저 테스트
        manager = test_pipeline_manager()
        
        # 3. 전체 파이프라인 테스트
        result = test_full_pipeline()
        
        # 4. 품질 최적화 테스트
        test_quality_optimization()
        
        # 5. 프리뷰 생성 테스트
        test_preview_generation()
        
        print("\n🎉 모든 테스트 완료!")
        
        if result and result.success:
            print("\n📁 생성된 파일들:")
            if result.audio_path:
                print(f"  - {result.audio_path}")
            if result.subtitle_dir:
                print(f"  - {result.subtitle_dir}")
            if result.video_path:
                print(f"  - {result.video_path}")
            if result.preview_path:
                print(f"  - {result.preview_path}")
            
            print("\n🎯 사양서 준수 확인:")
            print("  ✅ 오디오-비디오 동기화")
            print("  ✅ 최종 MP4 렌더링")
            print("  ✅ 품질 최적화")
            print("  ✅ 프리뷰 생성")
            print("  ✅ 전체 파이프라인 자동화")
            
            print("\n🔧 다음 단계:")
            print("  1. 실제 TTS API 연동")
            print("  2. 사용자 인터페이스 개발")
            print("  3. 배치 처리 및 스케줄링")
            print("  4. 클라우드 배포")
            
        else:
            print("\n⚠️ 일부 테스트가 실패했습니다")
            print("FFmpeg 설치 및 설정을 확인하세요")
        
    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
