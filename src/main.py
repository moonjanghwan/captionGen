import sys
import os
import subprocess
import signal
import psutil

# 프로젝트의 루트 디렉토리를 Python 경로에 추가하여
# src 폴더 내의 모듈을 절대 경로로 임포트할 수 있도록 합니다.
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from src.ui.main_window import MainWindow

def kill_existing_processes():
    """기존에 실행 중인 captionGen 프로세스를 종료합니다."""
    try:
        current_pid = os.getpid()
        killed_count = 0
        
        # 현재 프로세스와 같은 스크립트를 실행하는 프로세스들을 찾습니다
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['pid'] == current_pid:
                    continue
                    
                cmdline = proc.info['cmdline']
                if cmdline and len(cmdline) > 0:
                    # main.py 또는 captionGen 관련 프로세스인지 확인
                    script_path = ' '.join(cmdline)
                    if ('main.py' in script_path or 
                        'captionGen' in script_path or
                        'python' in script_path and 'src/main.py' in script_path):
                        
                        print(f"🔄 기존 프로세스 종료: PID {proc.info['pid']} - {script_path}")
                        proc.terminate()
                        killed_count += 1
                        
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        if killed_count > 0:
            print(f"✅ {killed_count}개의 기존 프로세스를 종료했습니다.")
            # 프로세스 종료를 위한 잠시 대기
            import time
            time.sleep(1)
        else:
            print("ℹ️ 종료할 기존 프로세스가 없습니다.")
            
    except Exception as e:
        print(f"⚠️ 프로세스 종료 중 오류 발생: {e}")

def main():
    """애플리케이션의 메인 실행 함수"""
    print("🚀 CaptionGen 애플리케이션 시작...")
    
    # 기존 프로세스 종료
    kill_existing_processes()
    
    print("🎨 UI 초기화 중...")
    app = MainWindow()
    app.mainloop()

if __name__ == "__main__":
    main()
