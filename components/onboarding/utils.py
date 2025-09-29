import re
import os
from pathlib import Path
import subprocess
import sys

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QMovie
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout

from components.widgets.helper_classes import Toast


def locations_of_python_list():
    platform = sys.platform

    if platform == "win32":
        pass


def where_python_location(
    searching_paths: list[str] = [
        "/Library/Frameworks/Python.framework/Versions",
        "/opt/homebrew/bin",
        "/usr/local/bin",
        "/usr/bin",
    ],
) -> dict[str, str]:
    """
    This function searches for python interpreters in the given paths.
    """

    found_interpreters = {}
    python_executable_pattern = re.compile(r"^python(2|3)(\.\d+)?$")

    # for windows
    if sys.platform == "win32":
        result = subprocess.run(
            ["where", "python"], capture_output=True, text=True, check=True
        )
        paths = result.stdout.strip().split("\n")
        for path in paths:
            version = subprocess.check_output(
                [path, "--version"], capture_output=True, text=True, check=True
            )
            found_interpreters[path] = version.stdout.strip()

    else:
        # For macOS and Linux

        if sys.platform == "darwin":
            # macOS specific paths
            search_paths = [
                "/Library/Frameworks/Python.framework/Versions",
                "/opt/homebrew/bin",
                "/usr/local/bin",
                "/usr/bin",
            ]
        else:
            # Linux specific paths
            search_paths = [
                os.path.expanduser("~/.local/bin"),
                "/usr/local/sbin",
                "/usr/local/bin",
                "/usr/sbin",
                "/usr/bin",
                "/sbin",
                "/bin",
                "/opt/bin",
            ]
            search_paths
        for folder in searching_paths:
            if not Path(folder).is_dir() and os.access(folder, os.X_OK):
                continue

            # Case for framework Path

            for files in Path(folder).iterdir():
                if "Framework" in folder:
                    bin_dir = files / "bin"
                    if bin_dir.exists():
                        for file in bin_dir.iterdir():
                            if python_executable_pattern.match(file.name) and os.access(
                                file, os.X_OK
                            ):
                                just_path = file
                                try:
                                    abs_path = just_path.resolve()

                                    if abs_path not in found_interpreters:
                                        version = subprocess.check_output(
                                            [str(abs_path), "--version"],
                                            stderr=subprocess.STDOUT,
                                        )
                                        found_interpreters[str(abs_path)] = (
                                            version.decode().strip()
                                        )
                                        break
                                except Exception:
                                    continue  # This is for python named but doesn't have version and any other errors
                else:
                    if python_executable_pattern.match(files.name) and os.access(
                        files, os.X_OK
                    ):
                        just_path = files
                        try:
                            abs_path = just_path.resolve()
                            if str(abs_path) not in found_interpreters:
                                version = subprocess.check_output(
                                    [str(abs_path), "--version"],
                                    stderr=subprocess.STDOUT,
                                )
                                found_interpreters[str(abs_path)] = (
                                    version.decode().strip()
                                )
                        except Exception:
                            continue

    # for
    return found_interpreters


def loading_virtual_env():
    """
    Creates a widget displaying a loading spinner.

    This static method generates a QFrame containing a QLabel with a QMovie
    (spinner GIF) to indicate a loading state. It's used to show progress
    while the application is performing an operation, such as searching
    for virtual environments.

    Returns:
        QFrame: A widget with a centered loading spinner.
    """
    container = QFrame()
    layout = QVBoxLayout(container)
    spinner_label = QLabel()
    spinner_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    movie = QMovie("./assets/icons/spinner.gif")
    movie.setScaledSize(QSize(32, 32))
    spinner_label.setMovie(movie)
    layout.addWidget(spinner_label)
    movie.start()
    return container


def commit_action(parent, message: str):
    """
    Displays a toast message to the user.
    """
    toast = Toast(parent, message=message)
    toast.show()


if __name__ == "__main__":
    pass
