#!/usr/bin/env python3
"""
개선된 타이밍 JSON 생성기
- MP3 파일 경로
- 이미지 파일 경로
- 시간별 이미지 매칭
- 오디오 합치기 가능한 구조
"""

import os
import json
import glob
from typing import Dict, List

def create_improved_timing_json():
    """개선된 타이밍 JSON 구조 생성"""
    
    # 기본 경로 설정
    base_dir = "output/kor-chn/kor-chn"
    timing_file = os.path.join(base_dir, "timing", "kor-chn_conversation.json")
    audio_file = os.path.join(base_dir, "mp3", "kor-chn_conversation.mp3")
    image_dir = os.path.join(base_dir, "conversation")
    
    # 기존 타이밍 파일 로드
    if os.path.exists(timing_file):
        with open(timing_file, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
    else:
        print(f"❌ 타이밍 파일을 찾을 수 없습니다: {timing_file}")
        return
    
    # 이미지 파일 목록 가져오기
    screen1_images = sorted(glob.glob(os.path.join(image_dir, "*_screen1.png")))
    screen2_images = sorted(glob.glob(os.path.join(image_dir, "*_screen2.png")))
    
    print(f"📁 Screen1 이미지: {len(screen1_images)}개")
    print(f"📁 Screen2 이미지: {len(screen2_images)}개")
    
    # 개선된 타이밍 구조 생성
    improved_timing = {
        "project_info": {
            "name": "kor-chn",
            "type": "conversation",
            "total_duration": existing_data.get("total_duration", 0),
            "created_at": "2024-01-01T00:00:00Z"
        },
        "audio": {
            "file_path": audio_file,
            "duration": existing_data.get("total_duration", 0),
            "format": "mp3",
            "sample_rate": 44100
        },
        "video_segments": []
    }
    
    # 각 장면별로 비디오 세그먼트 생성
    scenes = existing_data.get("scenes", [])
    
    for i, scene in enumerate(scenes):
        sequence = scene.get("sequence", str(i+1))
        timings = scene.get("timings", {})
        
        # Screen1 세그먼트
        if "screen1" in timings and i < len(screen1_images):
            screen1_timing = timings["screen1"]
            start_time = screen1_timing.get("start", 0) / 1000.0  # ms를 초로 변환
            end_time = screen1_timing.get("end", 0) / 1000.0
            duration = end_time - start_time
            
            improved_timing["video_segments"].append({
                "segment_id": f"scene_{sequence}_screen1",
                "sequence": int(sequence),
                "screen_type": "screen1",
                "start_time": round(start_time, 2),
                "end_time": round(end_time, 2),
                "duration": round(duration, 2),
                "image": {
                    "file_path": screen1_images[i],
                    "filename": os.path.basename(screen1_images[i]),
                    "exists": os.path.exists(screen1_images[i])
                },
                "audio": {
                    "start_time": round(start_time, 2),
                    "end_time": round(end_time, 2),
                    "duration": round(duration, 2)
                }
            })
        
        # Screen2 세그먼트
        if "screen2" in timings and i < len(screen2_images):
            screen2_timing = timings["screen2"]
            start_time = screen2_timing.get("start", 0) / 1000.0  # ms를 초로 변환
            end_time = screen2_timing.get("end", 0) / 1000.0
            duration = end_time - start_time
            
            improved_timing["video_segments"].append({
                "segment_id": f"scene_{sequence}_screen2",
                "sequence": int(sequence),
                "screen_type": "screen2",
                "start_time": round(start_time, 2),
                "end_time": round(end_time, 2),
                "duration": round(duration, 2),
                "image": {
                    "file_path": screen2_images[i],
                    "filename": os.path.basename(screen2_images[i]),
                    "exists": os.path.exists(screen2_images[i])
                },
                "audio": {
                    "start_time": round(start_time, 2),
                    "end_time": round(end_time, 2),
                    "duration": round(duration, 2)
                }
            })
    
    # FFmpeg concat 파일 생성용 정보 추가
    improved_timing["ffmpeg_concat"] = {
        "concat_file": os.path.join(base_dir, "video", "concat_list.txt"),
        "output_file": os.path.join(base_dir, "video", "kor-chn_conversation_improved.mp4"),
        "segments": []
    }
    
    # FFmpeg concat 세그먼트 정보 생성
    for segment in improved_timing["video_segments"]:
        if segment["image"]["exists"]:
            improved_timing["ffmpeg_concat"]["segments"].append({
                "file": f"file '{segment['image']['file_path']}'",
                "duration": segment["duration"],
                "start_time": segment["start_time"],
                "end_time": segment["end_time"]
            })
    
    # 개선된 타이밍 파일 저장
    improved_timing_file = os.path.join(base_dir, "timing", "kor-chn_conversation_improved.json")
    os.makedirs(os.path.dirname(improved_timing_file), exist_ok=True)
    
    with open(improved_timing_file, 'w', encoding='utf-8') as f:
        json.dump(improved_timing, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 개선된 타이밍 JSON 생성 완료: {improved_timing_file}")
    print(f"📊 총 {len(improved_timing['video_segments'])}개 세그먼트")
    
    # FFmpeg concat 파일 생성
    concat_file = improved_timing["ffmpeg_concat"]["concat_file"]
    os.makedirs(os.path.dirname(concat_file), exist_ok=True)
    
    with open(concat_file, 'w', encoding='utf-8') as f:
        for segment in improved_timing["ffmpeg_concat"]["segments"]:
            f.write(f"{segment['file']}\n")
            f.write(f"duration {segment['duration']}\n")
    
    print(f"✅ FFmpeg concat 파일 생성 완료: {concat_file}")
    
    return improved_timing_file

if __name__ == "__main__":
    create_improved_timing_json()
