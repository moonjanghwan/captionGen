import sys
import os

# 프로젝트의 루트 디렉토리를 Python 경로에 추가하여
# src 폴더 내의 모듈을 절대 경로로 임포트할 수 있도록 합니다.
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from src.ui.main_window import MainWindow

def main():
    """애플리케이션의 메인 실행 함수"""
    app = MainWindow()
    app.mainloop()

if __name__ == "__main__":
    main()
