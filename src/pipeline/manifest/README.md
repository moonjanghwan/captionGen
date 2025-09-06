# 🎬 Manifest 파싱/검증 시스템

비디오 제작을 위한 Manifest 파일을 파싱하고 검증하는 완전 자동화 시스템입니다.

## 📋 **개요**

이 시스템은 JSON 형태의 Manifest 파일을 기반으로:
- **자동 파싱**: JSON 파일을 Python 객체로 변환
- **강력한 검증**: 데이터 구조, 일관성, 비즈니스 로직 검증
- **편집 기능**: 장면 추가/삭제/수정/순서 변경
- **템플릿 시스템**: 미리 정의된 구조로 빠른 생성

## 🏗️ **시스템 구조**

```
src/pipeline/manifest/
├── models.py          # 데이터 모델 정의 (Pydantic)
├── parser.py          # JSON 파싱 및 파일 I/O
├── validator.py       # 데이터 검증 및 오류 처리
├── generator.py       # Manifest 생성 및 편집
└── __init__.py        # 모듈 초기화
```

## 🚀 **빠른 시작**

### **1. 기본 사용법**

```python
from src.pipeline.manifest import ManifestParser, ManifestGenerator

# 파서 초기화
parser = ManifestParser()

# 파일에서 Manifest 로드
manifest = parser.parse_file("example_manifest.json")

# Manifest 정보 확인
print(f"프로젝트: {manifest.project_name}")
print(f"장면 수: {len(manifest.scenes)}")

# 특정 타입의 장면들 가져오기
conversation_scenes = manifest.get_scenes_by_type("conversation")
```

### **2. 템플릿에서 생성**

```python
# 생성기 초기화
generator = ManifestGenerator()

# 템플릿에서 Manifest 생성
manifest = generator.create_from_template(
    "basic_conversation", 
    "내 프로젝트"
)

# 사용자 정의 적용
manifest = generator.create_from_template(
    "basic_conversation",
    "내 프로젝트",
    customizations={"resolution": "1280x720"}
)
```

### **3. Manifest 편집**

```python
# 장면 추가
new_scene = {
    "id": "conversation_06",
    "type": "conversation",
    "sequence": 6,
    "native_script": "What's your name?",
    "learning_script": "你叫什么名字？",
    "reading_script": "니 쟈오 선마 밍츠?"
}

manifest = generator.add_scene(manifest, new_scene)

# 장면 업데이트
manifest = generator.update_scene(manifest, "intro_01", {
    "full_script": "새로운 인트로 스크립트"
})

# 장면 제거
manifest = generator.remove_scene(manifest, "dialogue_01")
```

## 📊 **Manifest 구조**

### **기본 구조**
```json
{
  "project_name": "프로젝트 이름",
  "resolution": "1920x1080",
  "default_background": "배경_파일_경로",
  "scenes": [
    // 장면들...
  ]
}
```

### **장면 타입**

#### **1. Intro/Ending**
```json
{
  "id": "intro_01",
  "type": "intro",
  "full_script": "전체 스크립트 내용"
}
```

#### **2. Conversation**
```json
{
  "id": "conversation_01",
  "type": "conversation",
  "sequence": 1,
  "native_script": "원어",
  "learning_script": "학습어",
  "reading_script": "읽기"
}
```

#### **3. Dialogue**
```json
{
  "id": "dialogue_01",
  "type": "dialogue",
  "script": [
    {"speaker": "A", "text": "대사 내용"},
    {"speaker": "B", "text": "대사 내용"}
  ]
}
```

## ✅ **검증 기능**

### **자동 검증 항목**
- ✅ **구조 검증**: 필수 필드, 데이터 타입
- ✅ **일관성 검증**: ID 중복, sequence 연속성
- ✅ **비즈니스 로직**: 장면 구성, 길이 추정
- ✅ **파일 경로**: 배경 파일 존재 여부

### **검증 결과**
```python
from src.pipeline.manifest import ManifestValidator

validator = ManifestValidator()
result = validator.validate(manifest)

if result.is_valid:
    print("✅ Manifest 검증 성공")
else:
    print(f"❌ 검증 실패: {len(result.errors)}개 오류")
    for error in result.errors:
        print(f"  - {error.field}: {error.message}")
```

## 🎨 **템플릿 시스템**

### **사용 가능한 템플릿**
1. **basic_conversation**: 기본 회화 구조
2. **dialogue_focused**: 대화 중심 구조  
3. **advanced_conversation**: 고급 회화 구조

### **템플릿 정보 확인**
```python
templates = generator.get_available_templates()
for template in templates:
    print(f"{template['name']}: {template['description']}")
```

## 🔧 **고급 기능**

### **장면 타입 변환**
```python
# conversation → dialogue 변환
manifest = generator.convert_scene_type(manifest, "conversation_01", "dialogue")
```

### **장면 순서 변경**
```python
new_order = ["intro_01", "conversation_02", "conversation_01", "ending_01"]
manifest = generator.reorder_scenes(manifest, new_order)
```

### **장면 복제**
```python
manifest = generator.duplicate_scene(manifest, "conversation_01")
```

### **Manifest 병합**
```python
merged = generator.merge_manifests([manifest1, manifest2])
```

## 📁 **파일 I/O**

### **저장**
```python
parser.save_manifest(manifest, "output/manifest.json")
```

### **로드**
```python
# 파일에서 로드
manifest = parser.parse_file("manifest.json")

# 문자열에서 로드
manifest = parser.parse_string(json_string)

# 딕셔너리에서 로드
manifest = parser.parse_dict(data_dict)
```

### **스키마 내보내기**
```python
generator.export_manifest_schema("manifest_schema.json")
```

## 🧪 **테스트**

### **테스트 실행**
```bash
python test_manifest_system.py
```

### **테스트 항목**
- ✅ 기본 Manifest 생성
- ✅ 검증 시스템
- ✅ 편집 기능
- ✅ 저장/로드
- ✅ 템플릿 시스템

## 📈 **성능 특징**

- **빠른 파싱**: Pydantic 기반 고성능 검증
- **메모리 효율**: 불변 객체로 안전한 편집
- **캐싱**: 파싱된 Manifest 자동 캐싱
- **확장성**: 새로운 장면 타입 쉽게 추가

## 🚨 **오류 처리**

### **일반적인 오류**
- `FileNotFoundError`: Manifest 파일을 찾을 수 없음
- `ValueError`: 데이터 검증 실패
- `JSONDecodeError`: JSON 형식 오류

### **오류 처리 예시**
```python
try:
    manifest = parser.parse_file("manifest.json")
except FileNotFoundError:
    print("Manifest 파일을 찾을 수 없습니다")
except ValueError as e:
    print(f"검증 오류: {e}")
except Exception as e:
    print(f"예상치 못한 오류: {e}")
```

## 🔮 **향후 계획**

- [ ] **UI 편집기**: 시각적 Manifest 편집 도구
- [ ] **버전 관리**: Manifest 변경 이력 추적
- [ ] **협업 기능**: 팀원 간 Manifest 공유
- [ ] **플러그인**: 사용자 정의 검증 규칙
- [ ] **API 서버**: RESTful Manifest 관리 API

## 📞 **지원**

문제가 있거나 기능 제안이 있으시면 이슈를 등록해 주세요.

---

**🎬 Manifest 시스템으로 완벽한 비디오 제작 파이프라인을 구축하세요!**
