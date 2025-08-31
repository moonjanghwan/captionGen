import sys
import os


def _ensure_project_root_on_path():
    try:
        project_root = os.path.dirname(os.path.abspath(__file__))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
    except Exception:
        pass


def main():
    _ensure_project_root_on_path()
    from src.main import main as app_main
    app_main()


if __name__ == "__main__":
    main()


