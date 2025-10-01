import os
import sys
import logging
from PyQt6.QtCore import Qt
from main_window import P4cMan
from PyQt6.QtGui import QIcon, QPixmap
from helpers.utils import resource_path
from helpers.logging import setup_logging
from helpers.state_manager import load_state
from config.loader import load_config, load_font
from PyQt6.QtWidgets import QApplication, QSplashScreen


UI_FILE_PATH = resource_path("config/ui.yaml")
CONTROLS_FILE_PATH = resource_path("config/paths.yaml")
PATHS_FILE_PATH = resource_path("config/application.yaml")
APPLICATION_PATH = resource_path("config/controls.yaml")
STYLE_SHEET_PATH = resource_path("config/style.yaml")


def setup_application(app: QApplication, config: dict) -> None:
    """Configures and returns the application instance"""

    # Set application specifics like name, version and icon
    app.setApplicationDisplayName(config.get("application", {}).get("name", ""))
    app.setWindowIcon(
        QIcon(
            resource_path(
                config.get("paths", {})
                .get("assets", {})
                .get("images", {})
                .get("appLogo", "")
            )
        )
    )
    app.setApplicationVersion(config.get("application", {}).get("version", ""))

    # set font and style sheet to the application
    font_path = resource_path(
        config.get("paths", {}).get("assets", {}).get("fonts", {}).get("main", "")
    )
    if font_path:
        font_size = (
            config.get("ui", {})
            .get("dimensions", {})
            .get("fontSize", {})
            .get("mainFont", 14)
        )
        app.setFont(load_font(font_path, font_size))

    app.setStyleSheet(config.get("stylesheet", {}).get("main", ""))


def main():
    """Entry Point to the P4cMan Application"""

    # when we run .app or .exe current directory can change, this fixes by checking frozen attribute in sys package
    # Thing changes from which ever directory the app may be launched from
    if getattr(sys, "frozen", False):
        application_path = os.path.dirname(sys.executable)
        os.chdir(application_path)

    app = QApplication(sys.argv)

    # Splash screen
    pixmap = QPixmap(resource_path("assets/icons/appLogo.png"))
    pixmap = pixmap.scaled(
        400,
        400,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    splash = QSplashScreen(
        pixmap,
        Qt.WindowType.FramelessWindowHint
        | Qt.WindowType.WindowStaysOnTopHint
        | Qt.WindowType.Tool,
    )
    splash.show()
    app.processEvents()

    # load config and state
    state = load_state()
    config: dict = load_config(
        UI_FILE_PATH,
        CONTROLS_FILE_PATH,
        PATHS_FILE_PATH,
        APPLICATION_PATH,
        STYLE_SHEET_PATH,
    )

    # setup application specifics and run app
    setup_application(app, config)

    window = P4cMan(state, config)
    window.show()
    splash.finish(window)

    sys.exit(app.exec())


if __name__ == "__main__":
    setup_logging()
    logger = logging.getLogger(__name__)
    os.environ["QT_LOGGING_RULES"] = "qt.qpa.cocoa.*.warning=false"
    main()
