import sys
import os


def get_app_support_directory(app_name: str = "P4cMan") -> str:
    """Returns the application support directory path for macOS."""
    # Just creates the directory if it doesn't exist

    if sys.platform == "win32":
        # for windows
        app_support_dir = os.path.join(os.getenv("APPDATA"), app_name)
    elif sys.platform == "darwin":
        # for macOS
        app_support_dir = os.path.expanduser(
            f"~/Library/Application Support/{app_name}"
        )
    else:
        # for linux and unix based system (not tested)
        app_support_dir = os.path.join(os.path.expanduser("~/.config"), app_name)

    os.makedirs(app_support_dir, exist_ok=True)

    return app_support_dir


def resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS  # type: ignore
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)
