import os
import networkx as nx

from .graphic import GraphWidget

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PyQt6.QtWidgets import QFileDialog, QLabel, QWidget, QVBoxLayout
import logging

logger = logging.getLogger(__name__)

os.environ["QT_LOGGING_RULES"] = "qt.qpa.cocoa.*.warning=false"


class DependencyTree(QWidget):
    """Create the Dependecny Graph"""

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self._parent = parent
        self.config = config
        self.setObjectName("dependencyTree")
        self.setContentsMargins(0, 0, 0, 0)

        # layout storing the page
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.main_layout)

        # for loading graph data in DiGraph
        self.graph_loader = None
        self.G = None
        self.graph_layout = None

        self.current_file = None
        self.project_folder = None
        self._file_path_selector_page()

    def _setup_stacked_widget(self):
        pass

    def set_project_folder(self, project_folder):
        """Set the project folder's location as other functions need it"""
        self.project_folder = project_folder

    def _file_path_selector_page(self):
        # Push button for selecting location
        self.file_selector = QLabel()
        self.file_selector.setContentsMargins(0, 5, 0, 5)
        self.file_selector.setText("Select the main file")
        self.file_selector.setObjectName("dependencyTreeFileSelection")
        self.file_selector.setMaximumHeight(30)
        self.file_selector.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.spacer_item = QWidget()
        self.spacer_item.setObjectName("GraphWidget")
        self.graph_widget = GraphWidget(self, self.config)
        self.graph_widget.setMaximumHeight(0)
        self.graph_widget.setVisible(False)
        self.spacer_item.setMinimumHeight(self.geometry().height() // 2)
        self.main_layout.addWidget(self.spacer_item, 0, Qt.AlignmentFlag.AlignTop)
        self.main_layout.addWidget(self.file_selector)
        self.main_layout.addWidget(self.graph_widget)

        # if the selected is clicked store the location selector button in class as object
        self.file_selector.mousePressEvent = self._on_file_selected  # type: ignore

    def _animate(
        self,
        object_to_be_animated,
        property_to_be_animated: bytes,
        final_dimension: int,
        initial_dimension: int,
        visibility: bool,
        name: str,
        animation_type=QEasingCurve.Type.InQuad,
        duration: int = 500,
        before: bool = False,
        continuous: bool = False,
    ):
        """
        Creates and starts a QPropertyAnimation for a given object property.

        Args:
            object_to_be_animated: The Object to animate.
            property_to_be_animated: The byte-string name of the property to animate (e.g., b'maximumHeight').
            final_dimension: The final value of the animated property.
            initial_dimension: The starting value of the animated property.
            visibility: If True, the object is visible after the animation; otherwise, it's hidden.
            name: An attribute name to store the QPropertyAnimation instance (e.g., "hide_search_bar").
            animation_type: The easing curve to use for the animation.
            duration: The duration of the animation in milliseconds.
            before: To commit visibility before or after
        """
        if before:  # this is for when appearing
            object_to_be_animated.setVisible(visibility)
        animation = QPropertyAnimation(object_to_be_animated, property_to_be_animated)
        setattr(self, name, animation)
        animation.setDuration(duration)
        animation.setStartValue(initial_dimension)
        animation.setEndValue(final_dimension)
        if continuous:
            animation.setLoopCount(-1)
        else:
            animation.setLoopCount(1)
        animation.setEasingCurve(animation_type)
        animation.finished.connect(
            lambda: (object_to_be_animated.setVisible(visibility), delattr(self, name))
        )
        animation.start()

    def _on_file_selected(self, event):
        # only let the user select python file, there can be one more way by project toml or something similar structure
        file_path, _ = QFileDialog.getOpenFileName(
            None, "Select a Python file", "", "Python Files (*.py);;All Files (*)"
        )
        if file_path:
            # Implement a logic: when the comman
            # path of project dir and file is not project directory display a toast message
            self.current_file = file_path
            self.file_selector.setText(file_path)
            self._animate(
                object_to_be_animated=self.spacer_item,
                property_to_be_animated=b"minimumHeight",
                final_dimension=0,
                initial_dimension=self.spacer_item.minimumHeight(),
                visibility=False,
                name="spacer_animation",
            )

            if self.project_folder is None:
                return

            self._get_graph_data()

    def _get_graph_data(self):
        """Now start the construction of GraphicItems when we reiceve graph data"""
        self.graph_widget.get_graph(self.current_file, self.project_folder)

        # Animating the graph layout
        self._animate(
            object_to_be_animated=self.graph_widget,
            property_to_be_animated=b"maximumHeight",
            final_dimension=4000,  # to move the limit past the possible size
            initial_dimension=0,
            visibility=True,
            name="graph_widget_animation",
            before=True,
        )
        self.graph_widget.setVisible(True)

    def _directory_file_check(self):
        """This is for checking if the file is a valid python file and is in project folder"""
        pass

    def _page_for_invalid_file(self):
        """
        page when the file is invalid or the file is not in the project directory,
        for sneaky people trying to give non project python file
        """
        pass

    def _get_import_libraries(self):
        pass

    def _convert_to_networkx(self):
        g = nx.DiGraph()
        g.add_node("root")
