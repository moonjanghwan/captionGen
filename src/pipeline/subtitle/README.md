# 🎬 자막 이미지 생성 시스템

SSML mark 태그 기반으로 정확한 타이밍에 맞춰 PNG 시퀀스를 자동 생성하는 시스템입니다.

## 📋 개요

이 시스템은 **자동화 파이프라인**의 **Phase 1.3: 자막 이미지 생성 시스템**을 구현합니다.

### 🎯 주요 기능
- **SSML mark 태그 기반 정확한 타이밍**: TTS 응답과 완벽 동기화
- **PNG 시퀀스 자동 생성**: 각 장면별로 독립적인 자막 이미지
- **텍스트 설정 적용**: 폰트, 크기, 색상, 위치 등 완전 커스터마이징

## 🏗️ 시스템 구조

```
src/pipeline/subtitle/
├── __init__.py          # 모듈 초기화
├── text_renderer.py     # 텍스트 렌더링 엔진
├── generator.py         # 자막 이미지 생성기
└── README.md           # 이 파일
```

## 🎬 사양서 준수 사항

### **1. 각 행별로 2개의 독립적인 텍스트 화면 생성**
- **화면 1**: 순번 + 원어 텍스트만 표시
- **화면 2**: 순번 + 원어 + 학습어 + 읽기 표시

### **2. SSML mark 태그 기반 정확한 타이밍**
- `scene_{N}_screen1_start/end`: 화면 1 타이밍
- `scene_{N}_screen2_start/end`: 화면 2 타이밍
- TTS API 응답과 완벽 동기화

### **3. PNG 시퀀스 자동 생성**
- 각 화면별로 독립적인 PNG 파일
- FFmpeg concat 리스트 자동 생성
- 정확한 지속 시간 계산

## 🚀 사용법

### **1. 텍스트 렌더러 사용**

```python
from src.pipeline.subtitle import TextRenderer

renderer = TextRenderer()

# 기본 텍스트 렌더링
image = renderer.render_text("안녕하세요!", 800, 600)

# 다중 라인 텍스트 렌더링
lines = ["1", "안녕하세요!", "你好！", "니하오!"]
image = renderer.render_multiline_text(lines, 800, 600)

# conversation 화면 1 렌더링
screen1_image = renderer.render_conversation_screen1(1, "안녕하세요!", 800, 600)

# conversation 화면 2 렌더링
screen2_image = renderer.render_conversation_screen2(
    1, "안녕하세요!", "你好！", "니하오!", 800, 600
)
```

### **2. 자막 생성기 사용**

```python
from src.pipeline.subtitle import SubtitleGenerator

generator = SubtitleGenerator()

# Manifest에서 자막 이미지 시퀀스 생성
frames = generator.generate_from_manifest(manifest_data, "output_dir", fps=30)

# SSML mark 태그에서 자막 이미지 시퀀스 생성
frames = generator.generate_from_ssml_marks(ssml_content, "output_dir", fps=30)

# FFmpeg concat 리스트 생성
generator.create_ffmpeg_concat_list("concat_list.txt")
```

### **3. 텍스트 설정 커스터마이징**

```python
# 사용자 정의 설정 파일
custom_config = {
    "default_settings": {
        "font_size": 60,
        "font_color": "#00FF00",
        "stroke_color": "#000000",
        "stroke_width": 3,
        "background_color": "#000080",
        "padding": 30,
        "line_spacing": 15,
        "alignment": "center"
    }
}

# 설정 파일로 렌더러 초기화
renderer = TextRenderer("custom_config.json")
```

## 📊 생성되는 이미지 구조

### **conversation 타입 예시**

#### **화면 1 (순번 + 원어)**
```
┌─────────────────────┐
│                     │
│          1          │
│                     │
│      안녕하세요!      │
│                     │
└─────────────────────┘
```

#### **화면 2 (순번 + 원어 + 학습어 + 읽기)**
```
┌─────────────────────┐
│                     │
│          1          │
│                     │
│      안녕하세요!      │
│                     │
│       你好！         │
│                     │
│       니하오!        │
│                     │
└─────────────────────┘
```

## 🎨 텍스트 설정 옵션

### **기본 설정**
- **폰트 크기**: 48px (기본값)
- **폰트 색상**: #FFFFFF (흰색)
- **테두리 색상**: #000000 (검은색)
- **테두리 두께**: 2px
- **배경 색상**: #000000 (검은색)
- **패딩**: 20px
- **줄 간격**: 10px
- **정렬**: center (가운데)

### **장면별 설정**
- **intro/ending**: 64px, 흰색 텍스트
- **conversation screen1**: 56px, 흰색 텍스트
- **conversation screen2**: 48px, 흰색 텍스트

### **언어별 폰트 자동 선택**
- **한글**: NanumGothic.ttf
- **한자**: NotoSansCJK-Regular.ttc
- **영문**: NotoSans-Regular.ttf

## 📁 출력 파일

### **생성되는 파일들**
1. **PNG 이미지 시퀀스**: 각 화면별 자막 이미지
2. **`subtitle_frames.json`**: 프레임 정보 및 메타데이터
3. **`concat_list.txt`**: FFmpeg concat 리스트

### **프레임 정보 구조**
```json
{
  "total_frames": 10,
  "resolution": "1920x1080",
  "output_directory": "output_dir",
  "frames": [
    {
      "frame_number": 0,
      "start_time": 0.0,
      "end_time": 5.0,
      "duration": 5.0,
      "scene_id": "conversation_01",
      "screen_type": "screen1",
      "content": ["1", "안녕하세요!"],
      "output_path": "path/to/image.png"
    }
  ]
}
```

## 🔧 FFmpeg 통합

### **concat 리스트 예시**
```
file 'conversation_01_screen1_0000.png'
duration 5.0
file 'conversation_01_screen2_0001.png'
duration 19.0
file 'conversation_02_screen1_0002.png'
duration 5.0
...
```

### **FFmpeg 명령어**
```bash
ffmpeg -f concat -safe 0 -i concat_list.txt -vsync vfr -pix_fmt yuv420p output_video.mp4
```

## 🧪 테스트

### **테스트 실행**
```bash
python test_subtitle_system.py
```

### **테스트 항목**
1. ✅ 텍스트 렌더러 테스트
2. ✅ 자막 생성기 테스트
3. ✅ SSML mark 태그 기반 생성 테스트
4. ✅ 텍스트 설정 테스트

## 🚨 주의사항

### **폰트 파일 설정**
- 기본 폰트 파일들이 `assets/fonts/` 디렉토리에 있어야 함
- 폰트 파일이 없으면 기본 폰트 사용

### **해상도 설정**
- Manifest의 `resolution` 필드에서 자동 감지
- 기본값: 1920x1080

### **타이밍 정확성**
- 현재는 예상 지속 시간 사용
- 실제 TTS API 응답과 통합 시 정확한 타이밍 적용 필요

## 🔮 향후 계획

### **Phase 1.4: FFmpeg 통합**
- 오디오-비디오 동기화
- 최종 MP4 렌더링
- 품질 최적화

### **고급 기능**
- 애니메이션 효과
- 템플릿 시스템
- 실시간 미리보기

## 📞 지원

문제가 발생하거나 질문이 있으시면 개발팀에 문의하세요.

---

**🎬 Manifest 시스템으로 완벽한 비디오 제작 파이프라인을 구축하세요!**
