from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget


class Analysis(QWidget):
    """
    Analysis page of the application
    """
    def __init__(self):
        super().__init__()
        self.setObjectName("analysis")
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label = QLabel("This is the analysis Page")
        self.main_layout.addWidget(self.label)
        self.setLayout(self.main_layout)
        pass
