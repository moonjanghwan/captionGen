# CaptionGen - AI 기반 다국어 학습 오디오 자동화 시스템

## Google Cloud TTS API 설정

### 1. Google Cloud Console에서 서비스 계정 키 생성

1. [Google Cloud Console](https://console.cloud.google.com/)에 접속
2. 프로젝트 선택 또는 새 프로젝트 생성
3. **API 및 서비스** > **라이브러리**에서 다음 API들을 활성화:
   - Cloud Text-to-Speech API
   - Cloud Translation API (선택사항)

4. **API 및 서비스** > **사용자 인증 정보**에서 서비스 계정 생성:
   - **사용자 인증 정보 만들기** > **서비스 계정**
   - 서비스 계정 이름 입력
   - **키 만들기** > **JSON** 선택하여 키 파일 다운로드

### 2. 설정 파일 구성

#### config.json 설정
```json
{
    "native_lang": "한국어 (ko-KR)",
    "learning_lang": "중국어 (cmn-CN)",
    "project_name": "kor-chn",
    "identifier": "kor-chn",
    "google_cloud": {
        "credentials_path": "./credentials.json",
        "project_id": "your-project-id"
    },
    "speaker_config": {
        "native_speaker": "ko-KR-Chirp3-HD-Achernar",
        "learner_count": "4",
        "learner_speakers": [
            "cmn-CN-Chirp3-HD-Achernar",
            "cmn-CN-Chirp3-HD-Achernar",
            "cmn-CN-Chirp3-HD-Achernar",
            "cmn-CN-Chirp3-HD-Achernar"
        ]
    }
}
```

#### credentials.json 파일 위치
- 다운로드한 서비스 계정 키 파일을 `credentials.json`으로 이름 변경
- 프로젝트 루트 디렉토리에 배치
- `config.json`의 `credentials_path`에서 경로 지정

### 3. 실행

```bash
python main.py
```

### 4. 기능

- **실시간 오디오 듣기**: 회화 스크립트를 여러 화자로 순차 재생
- **AI 데이터 생성**: Gemini API를 통한 학습 데이터 자동 생성
- **다국어 지원**: 10개 언어 조합 지원
- **화자 선택**: Google Cloud TTS의 다양한 화자 선택

### 5. 지원 언어

- 한국어 (ko-KR)
- 영어 (en-US)
- 일본어 (ja-JP)
- 중국어 (cmn-CN)
- 베트남어 (vi-VN)
- 인도네시아어 (id-ID)
- 이탈리아어 (it-IT)
- 스페인어 (es-US)
- 프랑스어 (fr-FR)
- 독일어 (de-DE)

### 6. 문제 해결

#### TTS 화자가 "N/A"로 표시되는 경우
1. `credentials.json` 파일이 올바른 위치에 있는지 확인
2. Google Cloud Console에서 TTS API가 활성화되었는지 확인
3. 서비스 계정에 적절한 권한이 부여되었는지 확인
4. 프로그램 재시작 후 "화자 선택" 탭에서 언어 선택

#### 디버그 정보 확인
- 프로그램 실행 시 메시지 창에서 상세한 디버그 정보 확인
- TTS 클라이언트 초기화 상태 및 화자 로드 상태 확인
