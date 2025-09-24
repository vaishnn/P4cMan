import os
import sys
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtCore import Qt
from main_window import P4cMan
from config.loader import load_config, load_font
from helpers.state_manager import load_state
from helpers.utils import resource_path

os.environ["QT_LOGGING_RULES"] = "qt.qpa.cocoa.*.warning=false"

UI_FILE_PATH=resource_path("config/ui.yaml")
CONTROLS_FILE_PATH=resource_path("config/paths.yaml")
PATHS_FILE_PATH=resource_path("config/application.yaml")
APPLICATION_PATH=resource_path("config/controls.yaml")


if __name__ == "__main__":
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
        os.chdir(application_path)
    app = QApplication(sys.argv)


    pixmap = QPixmap(resource_path("assets/icons/appLogo.png"))
    pixmap = pixmap.scaled(400, 400, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    splash = QSplashScreen(pixmap, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
    splash.show()
    app.processEvents()

    state = load_state()
    config: dict = load_config(UI_FILE_PATH, CONTROLS_FILE_PATH, PATHS_FILE_PATH, APPLICATION_PATH)

    app.setApplicationDisplayName(config.get("application", {}).get("name", ""))
    app.setWindowIcon(QIcon(resource_path(config.get("paths", {}).get("assets", {}).get("images", {}).get("appLogo", ""))))
    app.applicationVersion = config.get("app", {}).get("version", "")

    font_path = resource_path(config.get("paths", {}).get("assets", {}).get("fonts", {}).get("main", ""))
    if font_path:
        font_size = config.get("ui", {}).get("dimensions", {}).get('fontSize', {}).get('mainFont', 14)
        app.setFont(load_font(font_path, font_size))

    app.setStyleSheet(config.get("stylesheet", {}).get("main", ""))

    window = P4cMan(state, config)
    window.show()
    splash.finish(window)

    sys.exit(app.exec())
