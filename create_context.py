# create_context.py
import os

# 분석에 필요한 파일 확장자 목록 (필요에 따라 추가/제외)
INCLUDE_EXTS = ['.py', '.json', '.txt', '.md']

# 무시할 디렉토리 및 파일 목록
EXCLUDE_DIRS = ['__pycache__', '.venv', '.git', 'output']
EXCLUDE_FILES = ['create_context.py']

def create_project_context(start_path='.'):
    """
    현재 디렉토리와 하위 디렉토리를 순회하며
    지정된 확장자의 파일 내용을 하나의 문자열로 합칩니다.
    """
    full_context = ""
    
    print("="*50)
    print("프로젝트 구조 및 파일 내용 생성 시작...")
    print(f"시작 경로: {os.path.abspath(start_path)}")
    print(f"포함할 확장자: {INCLUDE_EXTS}")
    print(f"제외할 디렉토리: {EXCLUDE_DIRS}")
    print("="*50 + "\n")

    for root, dirs, files in os.walk(start_path, topdown=True):
        # 제외할 디렉토리 필터링
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        
        for file_name in files:
            # 제외할 파일 및 확장자 필터링
            if file_name in EXCLUDE_FILES:
                continue
            if not any(file_name.endswith(ext) for ext in INCLUDE_EXTS):
                continue

            file_path = os.path.join(root, file_name)
            
            # 파일 경로와 내용 추가
            full_context += f"--- 파일: {file_path} ---\n"
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    full_context += f.read()
                full_context += "\n\n"
            except Exception as e:
                full_context += f"[오류] 파일을 읽을 수 없습니다: {e}\n\n"

    return full_context

if __name__ == "__main__":
    project_context = create_project_context()
    
    # 결과를 파일로 저장하거나, 터미널에 직접 출력할 수 있습니다.
    # 터미널에 출력된 내용을 복사해서 사용하세요.
    print(project_context)
    
    # (선택) 결과를 파일로 저장하고 싶다면 아래 주석을 해제하세요.
    # with open("project_context.txt", "w", encoding="utf-8") as f:
    #     f.write(project_context)
    # print("\n\n✅ project_context.txt 파일로 저장되었습니다.")