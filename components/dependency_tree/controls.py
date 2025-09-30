from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QPushButton, QVBoxLayout, QWidget


class ControlPanel(QWidget):
    """A control panel for dependency tree, used for resetting, changing or some customisation of the view"""

    reset_signal = pyqtSignal()

    def __init__(self, parent) -> None:
        super().__init__()

        # Important windo flags
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setParent(parent)
        self.setStyleSheet("background-color: grey;")
        # self.setContentsMargins(0, 0, 0, 0)
        self.setGeometry(10, 10, 300, 300)
        self._page()

    def _page(self):
        self._layout = QVBoxLayout()
        self.setLayout(self._layout)

        reset_button = QPushButton("Reset")
        reset_button.clicked.connect(self.reset_signal.emit)
        self._layout.addWidget(reset_button)
