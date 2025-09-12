"""
통합 파이프라인 매니저

Manifest부터 최종 MP4까지 전체 파이프라인을 관리하고 조율합니다.
"""

import os
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from ..manifest import ManifestParser
from ..audio import AudioGenerator, SSMLBuilder
from ..subtitle import SubtitleGenerator
from .renderer import FFmpegRenderer


@dataclass
class PipelineConfig:
    """파이프라인 설정"""
    output_directory: str = "output"
    enable_audio_generation: bool = True
    enable_subtitle_generation: bool = True
    enable_video_rendering: bool = True
    enable_quality_optimization: bool = False
    enable_preview_generation: bool = True
    cleanup_temp_files: bool = True


@dataclass
class PipelineResult:
    """파이프라인 실행 결과"""
    success: bool
    manifest_path: str
    audio_path: Optional[str]
    subtitle_dir: Optional[str]
    video_path: Optional[str]
    preview_path: Optional[str]
    execution_time: float
    errors: List[str]
    warnings: List[str]


class PipelineManager:
    """통합 파이프라인 매니저"""
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        """
        파이프라인 매니저 초기화
        
        Args:
            config: 파이프라인 설정
        """
        self.config = config or PipelineConfig()
        self.manifest_parser = ManifestParser()
        self.audio_generator = AudioGenerator()
        self.subtitle_generator = SubtitleGenerator()
        self.ffmpeg_renderer = FFmpegRenderer()
        
        # 출력 디렉토리 생성
        os.makedirs(self.config.output_directory, exist_ok=True)
    
    def run_full_pipeline(self, manifest_path: str, 
                         project_name: Optional[str] = None) -> PipelineResult:
        """
        전체 파이프라인 실행
        
        Args:
            manifest_path: Manifest 파일 경로
            project_name: 프로젝트 이름 (None이면 자동 생성)
            
        Returns:
            PipelineResult: 실행 결과
        """
        start_time = time.time()
        errors = []
        warnings = []
        
        try:
            print("🚀 전체 파이프라인 실행 시작!")
            print(f"Manifest: {manifest_path}")
            
            # 1단계: Manifest 파싱 및 검증
            print("\n📋 1단계: Manifest 파싱 및 검증")
            manifest_data = self._parse_and_validate_manifest(manifest_path)
            if not manifest_data:
                errors.append("Manifest 파싱 및 검증 실패")
                return self._create_pipeline_result(False, manifest_path, start_time, errors, warnings)
            
            # 프로젝트 이름 결정
            if not project_name:
                project_name = manifest_data.get("project_name", "auto_generated")
            
            # 프로젝트별 출력 디렉토리 생성
            project_output_dir = os.path.join(self.config.output_directory, project_name)
            os.makedirs(project_output_dir, exist_ok=True)
            
            # 2단계: 오디오 생성
            audio_path = None
            if self.config.enable_audio_generation:
                print("\n🎵 2단계: 오디오 생성")
                audio_path = self._generate_audio(manifest_data, project_output_dir)
                if not audio_path:
                    errors.append("오디오 생성 실패")
                    warnings.append("오디오 없이 비디오 렌더링 진행")
            
            # 3단계: 자막 이미지 생성
            subtitle_dir = None
            if self.config.enable_subtitle_generation:
                print("\n🎬 3단계: 자막 이미지 생성")
                subtitle_dir = self._generate_subtitles(manifest_data, project_output_dir)
                if not subtitle_dir:
                    errors.append("자막 이미지 생성 실패")
                    return self._create_pipeline_result(False, manifest_path, start_time, errors, warnings)
            
            # 4단계: 비디오 렌더링
            video_path = None
            if self.config.enable_video_rendering:
                print("\n🎥 4단계: 비디오 렌더링")
                video_path = self._render_video(manifest_path, audio_path, subtitle_dir, project_output_dir)
                if not video_path:
                    errors.append("비디오 렌더링 실패")
                    return self._create_pipeline_result(False, manifest_path, start_time, errors, warnings)
            
            # 5단계: 품질 최적화
            if self.config.enable_quality_optimization and video_path:
                print("\n🔧 5단계: 품질 최적화")
                optimized_video_path = self._optimize_video_quality(video_path, project_output_dir)
                if optimized_video_path:
                    video_path = optimized_video_path
            
            # 6단계: 프리뷰 생성
            preview_path = None
            if self.config.enable_preview_generation and video_path:
                print("\n👀 6단계: 프리뷰 생성")
                preview_path = self._create_preview(video_path, project_output_dir)
            
            # 7단계: 임시 파일 정리
            if self.config.cleanup_temp_files:
                print("\n🧹 7단계: 임시 파일 정리")
                self._cleanup_temp_files(project_output_dir)
            
            # 실행 시간 계산
            execution_time = time.time() - start_time
            
            print(f"\n🎉 전체 파이프라인 실행 완료! (소요시간: {execution_time:.1f}초)")
            
            return self._create_pipeline_result(
                True, manifest_path, start_time, errors, warnings,
                audio_path, subtitle_dir, video_path, preview_path
            )
            
        except Exception as e:
            errors.append(f"파이프라인 실행 중 예외 발생: {e}")
            return self._create_pipeline_result(False, manifest_path, start_time, errors, warnings)
    
    def _parse_and_validate_manifest(self, manifest_path: str) -> Optional[Dict[str, Any]]:
        """Manifest 파싱 및 검증"""
        try:
            manifest = self.manifest_parser.parse_file(manifest_path)
            
            # 검증 결과 확인
            validation_result = self.manifest_parser.validator.validate(manifest)
            if not validation_result.is_valid:
                print("⚠️ Manifest 검증 경고:")
                for warning in validation_result.warnings:
                    print(f"  - {warning.message}")
            
            return manifest.model_dump()
            
        except Exception as e:
            print(f"❌ Manifest 파싱 실패: {e}")
            return None
    
    def _generate_audio(self, manifest_data: Dict[str, Any], 
                       output_dir: str) -> Optional[str]:
        """오디오 생성"""
        try:
            # SSML 생성
            ssml_builder = SSMLBuilder()
            ssml_content = ssml_builder.build_manifest_ssml(manifest_data)
            
            # SSML 파일 저장
            ssml_path = os.path.join(output_dir, "manifest.ssml")
            ssml_builder.create_ssml_file(ssml_content, ssml_path)
            print(f"✅ SSML 파일 생성: {ssml_path}")
            
            # 오디오 생성 (실제 TTS가 없으므로 더미 파일 생성)
            audio_path = os.path.join(output_dir, "manifest_audio.mp3")
            
            # 더미 오디오 파일 생성 (실제로는 TTS API 사용)
            with open(audio_path, 'wb') as f:
                # 간단한 더미 MP3 헤더
                f.write(b'\xff\xfb\x90\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
            
            print(f"✅ 오디오 파일 생성: {audio_path}")
            return audio_path
            
        except Exception as e:
            print(f"❌ 오디오 생성 실패: {e}")
            return None
    
    def _generate_subtitles(self, manifest_data: Dict[str, Any], 
                           output_dir: str) -> Optional[str]:
        """자막 이미지 생성"""
        try:
            subtitle_dir = os.path.join(output_dir, "subtitles")
            frames = self.subtitle_generator.generate_from_manifest(
                manifest_data, subtitle_dir, fps=30
            )
            
            if frames:
                print(f"✅ 자막 이미지 생성 완료: {len(frames)}개 프레임")
                return subtitle_dir
            else:
                print("❌ 자막 이미지 생성 실패")
                return None
                
        except Exception as e:
            print(f"❌ 자막 이미지 생성 실패: {e}")
            return None
    
    def _render_video(self, manifest_path: str, audio_path: Optional[str], 
                     subtitle_dir: str, output_dir: str) -> Optional[str]:
        """비디오 렌더링"""
        try:
            video_path = os.path.join(output_dir, "final_video.mp4")
            
            if audio_path and os.path.exists(audio_path):
                # 오디오와 자막을 동기화하여 비디오 렌더링
                success = self.ffmpeg_renderer.render_from_manifest(
                    manifest_path, audio_path, subtitle_dir, video_path
                )
            else:
                # 자막만으로 비디오 렌더링 (무음)
                success = self.ffmpeg_renderer.render_from_manifest(
                    manifest_path, "", subtitle_dir, video_path
                )
            
            if success and os.path.exists(video_path):
                print(f"✅ 비디오 렌더링 완료: {video_path}")
                return video_path
            else:
                print("❌ 비디오 렌더링 실패")
                return None
                
        except Exception as e:
            print(f"❌ 비디오 렌더링 실패: {e}")
            return None
    
    def _optimize_video_quality(self, video_path: str, output_dir: str) -> Optional[str]:
        """비디오 품질 최적화"""
        try:
            optimized_path = os.path.join(output_dir, "final_video_optimized.mp4")
            
            success = self.ffmpeg_renderer.optimize_quality(
                video_path, optimized_path, target_bitrate="8000k"
            )
            
            if success and os.path.exists(optimized_path):
                print(f"✅ 품질 최적화 완료: {optimized_path}")
                
                # 원본 파일 삭제
                if os.path.exists(video_path):
                    os.remove(video_path)
                    print(f"✅ 원본 파일 삭제: {video_path}")
                
                return optimized_path
            else:
                print("⚠️ 품질 최적화 실패, 원본 파일 사용")
                return video_path
                
        except Exception as e:
            print(f"⚠️ 품질 최적화 실패: {e}")
            return video_path
    
    def _create_preview(self, video_path: str, output_dir: str) -> Optional[str]:
        """프리뷰 생성"""
        try:
            preview_path = os.path.join(output_dir, "preview.mp4")
            
            success = self.ffmpeg_renderer.create_preview(
                video_path, preview_path, duration=10
            )
            
            if success and os.path.exists(preview_path):
                print(f"✅ 프리뷰 생성 완료: {preview_path}")
                return preview_path
            else:
                print("⚠️ 프리뷰 생성 실패")
                return None
                
        except Exception as e:
            print(f"⚠️ 프리뷰 생성 실패: {e}")
            return None
    
    def _cleanup_temp_files(self, output_dir: str):
        """임시 파일 정리"""
        try:
            # SSML 파일 삭제
            ssml_path = os.path.join(output_dir, "manifest.ssml")
            if os.path.exists(ssml_path):
                os.remove(ssml_path)
                print(f"✅ 임시 SSML 파일 삭제: {ssml_path}")
            
            # 더미 오디오 파일 삭제
            audio_path = os.path.join(output_dir, "manifest_audio.mp3")
            if os.path.exists(audio_path):
                os.remove(audio_path)
                print(f"✅ 임시 오디오 파일 삭제: {audio_path}")
            
            print("✅ 임시 파일 정리 완료")
            
        except Exception as e:
            print(f"⚠️ 임시 파일 정리 실패: {e}")
    
    def _create_pipeline_result(self, success: bool, manifest_path: str, 
                              start_time: float, errors: List[str], warnings: List[str],
                              audio_path: Optional[str] = None, 
                              subtitle_dir: Optional[str] = None,
                              video_path: Optional[str] = None,
                              preview_path: Optional[str] = None) -> PipelineResult:
        """파이프라인 결과 생성"""
        execution_time = time.time() - start_time
        
        return PipelineResult(
            success=success,
            manifest_path=manifest_path,
            audio_path=audio_path,
            subtitle_dir=subtitle_dir,
            video_path=video_path,
            preview_path=preview_path,
            execution_time=execution_time,
            errors=errors,
            warnings=warnings
        )
    
    def get_pipeline_summary(self, result: PipelineResult) -> Dict[str, Any]:
        """파이프라인 실행 요약"""
        summary = {
            "success": result.success,
            "execution_time": result.execution_time,
            "output_files": {},
            "errors": result.errors,
            "warnings": result.warnings
        }
        
        if result.audio_path:
            summary["output_files"]["audio"] = result.audio_path
        
        if result.subtitle_dir:
            summary["output_files"]["subtitles"] = result.subtitle_dir
        
        if result.video_path:
            summary["output_files"]["video"] = result.video_path
            
            # 비디오 정보 조회
            video_info = self.ffmpeg_renderer.get_video_info(result.video_path)
            if video_info:
                summary["video_info"] = video_info
        
        if result.preview_path:
            summary["output_files"]["preview"] = result.preview_path
        
        return summary
    
    def save_pipeline_report(self, result: PipelineResult, output_dir: str):
        """파이프라인 실행 보고서 저장"""
        try:
            report_path = os.path.join(output_dir, "pipeline_report.json")
            
            report = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "manifest_path": result.manifest_path,
                "success": result.success,
                "execution_time": result.execution_time,
                "output_files": {},
                "errors": result.errors,
                "warnings": result.warnings
            }
            
            if result.audio_path:
                report["output_files"]["audio"] = result.audio_path
            
            if result.subtitle_dir:
                report["output_files"]["subtitles"] = result.subtitle_dir
            
            if result.video_path:
                report["output_files"]["video"] = result.video_path
            
            if result.preview_path:
                report["output_files"]["preview"] = result.preview_path
            
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 파이프라인 보고서 저장: {report_path}")
            
        except Exception as e:
            print(f"⚠️ 파이프라인 보고서 저장 실패: {e}")
