# 🎵 오디오 생성 시스템

사양서에 따른 SSML 기반 TTS 및 오디오 세그먼트 분석을 제공하는 시스템입니다.

## 📋 개요

이 시스템은 **자동화 파이프라인**의 **Phase 1.2: 오디오 생성 시스템**을 구현합니다.

### 🎯 주요 기능
- **SSML 빌더**: 사양서 룰에 따른 SSML 생성
- **오디오 생성기**: Google Cloud TTS를 사용한 MP3 생성
- **세그먼터**: 정확한 타이밍 정보 추출 및 분석

## 🏗️ 시스템 구조

```
src/pipeline/audio/
├── __init__.py          # 모듈 초기화
├── ssml_builder.py      # SSML 생성 로직
├── generator.py         # TTS 오디오 생성
├── segmenter.py         # 오디오 세그먼트 분석
└── README.md           # 이 파일
```

## 🎬 사양서 준수 사항

### **1. 각 행별로 2개의 독립적인 텍스트 화면 생성**
- **화면 1**: 순번 + 원어 텍스트만 표시
- **화면 2**: 순번 + 원어 + 학습어 + 읽기 표시

### **2. 화자 간, 행 간 1초 무음 자동 삽입**
- 원어 화자 → 학습어 화자 1,2,3,4 순서로 재생
- 각 화자 간 1초 무음 자동 삽입

### **3. SSML `<mark>` 태그로 정확한 타이밍 생성**
- `scene_{N}_screen1_start/end`: 화면 1 타이밍
- `scene_{N}_screen2_start/end`: 화면 2 타이밍
- 정확한 오디오-자막 동기화

## 🚀 사용법

### **1. SSML 빌더 사용**

```python
from src.pipeline.audio import SSMLBuilder

builder = SSMLBuilder()

# conversation 타입 SSML 생성
scene_data = {
    "sequence": 1,
    "native_script": "안녕하세요!",
    "learning_script": "你好！",
    "reading_script": "니하오!"
}

ssml_content = builder.build_conversation_ssml(scene_data)
```

### **2. 오디오 생성기 사용**

```python
from src.pipeline.audio import AudioGenerator

# Google Cloud 인증 파일 경로 (선택사항)
generator = AudioGenerator(credentials_path="path/to/credentials.json")

# SSML에서 MP3 생성
success = generator.generate_audio_from_ssml(ssml_content, "output.mp3")

# Manifest에서 전체 오디오 생성
success, mp3_path = generator.generate_audio_from_manifest(manifest_data, "output_dir")
```

### **3. 세그먼터 사용**

```python
from src.pipeline.audio import AudioSegmenter

segmenter = AudioSegmenter()

# SSML에서 mark 태그 분석
marks = segmenter.analyze_ssml_marks(ssml_content)

# 타이밍 세그먼트 생성
segments = segmenter.create_timing_segments(marks, estimated_duration)

# 타이밍 일관성 검증
errors = segmenter.validate_timing_consistency(segments)
```

## 📊 생성되는 SSML 구조

### **conversation 타입 예시**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<speak version="1.1" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="ko-KR">
    <!-- 화면 1: 원어 -->
    <voice name="ko-KR-Standard-A">
        <mark name="scene_1_screen1_start"/>
        <prosody rate="medium" pitch="medium">안녕하세요!</prosody>
        <mark name="scene_1_screen1_end"/>
    </voice>
    <break time="1s"/>
    
    <!-- 화면 2: 학습어 (4명의 화자) -->
    <mark name="scene_1_screen2_start"/>
    <voice name="cmn-CN-Standard-A">
        <prosody rate="medium" pitch="medium">你好！</prosody>
    </voice>
    <break time="1s"/>
    <voice name="cmn-CN-Standard-B">
        <prosody rate="medium" pitch="medium">你好！</prosody>
    </voice>
    <break time="1s"/>
    <voice name="cmn-CN-Standard-C">
        <prosody rate="medium" pitch="medium">你好！</prosody>
    </voice>
    <break time="1s"/>
    <voice name="cmn-CN-Standard-D">
        <prosody rate="medium" pitch="medium">你好！</prosody>
    </voice>
    <mark name="scene_1_screen2_end"/>
</speak>
```

## 🎭 화자 설정

### **음성 프로필**
- **원어 화자**: `ko-KR-Standard-A` (한국어 여성)
- **학습어 화자 1**: `cmn-CN-Standard-A` (중국어 여성)
- **학습어 화자 2**: `cmn-CN-Standard-B` (중국어 남성)
- **학습어 화자 3**: `cmn-CN-Standard-C` (중국어 여성)
- **학습어 화자 4**: `cmn-CN-Standard-D` (중국어 남성)

## ⚙️ 설정 옵션

### **오디오 설정**
```python
audio_config = AudioConfig(
    audio_encoding=AudioEncoding.MP3,
    sample_rate_hertz=22050,
    effects_profile_id=["headphone-class-device"]
)
```

### **SSML 설정**
- **언어**: 한국어 (ko-KR)
- **속도**: 중간 (medium)
- **음높이**: 중간 (medium)
- **무음 간격**: 1초

## 🔧 의존성

### **필수 패키지**
```bash
pip install google-cloud-texttospeech
```

### **선택사항**
- Google Cloud 인증 파일 (실제 TTS 사용 시)
- FFmpeg (오디오 병합 시)

## 📁 출력 파일

### **생성되는 파일들**
1. **`manifest.ssml`**: 전체 Manifest SSML
2. **`manifest_audio.mp3`**: 통합 MP3 오디오
3. **`timing_info.json`**: 타이밍 정보
4. **`manifest_timing.json`**: Manifest 타이밍 분석

### **타이밍 정보 구조**
```json
{
  "audio_file": "path/to/audio.mp3",
  "total_duration": 150.0,
  "marks": [...],
  "scenes": [...]
}
```

## 🧪 테스트

### **테스트 실행**
```bash
python test_audio_system.py
```

### **테스트 항목**
1. ✅ SSML 빌더 테스트
2. ✅ 오디오 생성기 테스트
3. ✅ 오디오 세그먼터 테스트
4. ✅ Manifest 기반 오디오 생성 테스트

## 🚨 주의사항

### **Google Cloud TTS 사용 시**
1. **인증 파일**: `GOOGLE_APPLICATION_CREDENTIALS` 환경변수 설정
2. **API 할당량**: 월별 사용량 제한 확인
3. **비용**: 사용량에 따른 과금

### **로컬 TTS 대안**
- Google Cloud TTS 연결 실패 시 로컬 TTS 서비스 사용 고려
- pyttsx3, gTTS 등 대안 라이브러리

## 🔮 향후 계획

### **Phase 1.3: 자막 이미지 생성 시스템**
- SSML mark 태그 기반 정확한 타이밍
- PNG 시퀀스 자동 생성
- 텍스트 설정 적용

### **Phase 1.4: FFmpeg 통합**
- 오디오-비디오 동기화
- 최종 MP4 렌더링
- 품질 최적화

## 📞 지원

문제가 발생하거나 질문이 있으시면 개발팀에 문의하세요.

---

**🎬 Manifest 시스템으로 완벽한 비디오 제작 파이프라인을 구축하세요!**
