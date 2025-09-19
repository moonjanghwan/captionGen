#!/usr/bin/env python3
"""
깔끔한 타이밍 JSON 생성기
- 중복 정보 제거
- 간결한 구조
"""

import os
import json
import glob
from typing import Dict, List

def create_clean_timing_json():
    """깔끔한 타이밍 JSON 구조 생성"""
    
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
    
    # 깔끔한 타이밍 구조 생성
    clean_timing = {
        "project_info": {
            "name": "kor-chn",
            "type": "conversation",
            "total_duration": existing_data.get("total_duration", 0)
        },
        "audio_file": audio_file,
        "segments": []
    }
    
    # 각 장면별로 세그먼트 생성
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
            
            clean_timing["segments"].append({
                "id": f"scene_{sequence}_screen1",
                "sequence": int(sequence),
                "screen_type": "screen1",
                "start_time": round(start_time, 2),
                "end_time": round(end_time, 2),
                "duration": round(duration, 2),
                "image_file": screen1_images[i]
            })
        
        # Screen2 세그먼트
        if "screen2" in timings and i < len(screen2_images):
            screen2_timing = timings["screen2"]
            start_time = screen2_timing.get("start", 0) / 1000.0  # ms를 초로 변환
            end_time = screen2_timing.get("end", 0) / 1000.0
            duration = end_time - start_time
            
            clean_timing["segments"].append({
                "id": f"scene_{sequence}_screen2",
                "sequence": int(sequence),
                "screen_type": "screen2",
                "start_time": round(start_time, 2),
                "end_time": round(end_time, 2),
                "duration": round(duration, 2),
                "image_file": screen2_images[i]
            })
    
    # 깔끔한 타이밍 파일 저장
    clean_timing_file = os.path.join(base_dir, "timing", "kor-chn_conversation_clean.json")
    os.makedirs(os.path.dirname(clean_timing_file), exist_ok=True)
    
    with open(clean_timing_file, 'w', encoding='utf-8') as f:
        json.dump(clean_timing, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 깔끔한 타이밍 JSON 생성 완료: {clean_timing_file}")
    print(f"📊 총 {len(clean_timing['segments'])}개 세그먼트")
    
    # FFmpeg concat 파일 생성
    concat_file = os.path.join(base_dir, "video", "clean_concat_list.txt")
    os.makedirs(os.path.dirname(concat_file), exist_ok=True)
    
    with open(concat_file, 'w', encoding='utf-8') as f:
        for segment in clean_timing["segments"]:
            f.write(f"file '{segment['image_file']}'\n")
            f.write(f"duration {segment['duration']}\n")
    
    print(f"✅ FFmpeg concat 파일 생성 완료: {concat_file}")
    
    return clean_timing_file

if __name__ == "__main__":
    create_clean_timing_json()
