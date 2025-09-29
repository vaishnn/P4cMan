import os
from PyQt6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QWidget,
    QLabel,
    QStackedWidget,
    QComboBox,
    QFileDialog,
    QPushButton,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal, QEasingCurve, QPropertyAnimation
from ..library.core import LibraryThreads
from .threads import PythonInterpreters
from ..widgets.helper_classes import LineEdit
from .utils import loading_virtual_env, commit_action
from ..widgets.control_bar import ControlBar
from helpers.utils import resource_path


class OnboardingPage(QWidget):
    """
    A widget representing the onboarding page of the application.

    This page allows the user to select a project directory, choose an existing
    virtual environment, or create a new one. It guides the user through the
    initial setup process.

    Signals:
        location_selected (pyqtSignal(str, str, list)): Emitted when a project
            location and virtual environment are selected.  The arguments are:
                - project location (str)
                - virtual environment name (str)
                - list of all virtual environments (list of dicts)
        find_env_in_pc (pyqtSignal): Emitted to trigger the search for existing
            virtual environments on the system.
        switch_to_main (pyqtSignal): Emitted when the onboarding process is
            finished and the application should switch to the main window.
    """

    location_selected = pyqtSignal(str, str, list)
    find_env_in_pc = pyqtSignal()
    release_python_interpreters = pyqtSignal(dict)
    switch_to_main = pyqtSignal()

    def __init__(self, config, parent):
        super().__init__(parent)

        self.setObjectName("onboardingWidget")
        self.config = config
        self.setStyleSheet(config.get("stylesheet", {}).get("main", ""))

        self._variables_setup()

        self.worker = LibraryThreads()
        self.worker.virtual_envs.connect(self._display_env)
        self.worker.new_virtual_env.connect(self._update_widget)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.frame = QFrame(self)
        self.frame.setObjectName("mainWindowContainer")
        main_layout.addWidget(self.frame)

        self.frame_layout = QVBoxLayout(self.frame)

        self.controlBar = ControlBar(parent, config)
        self.frame_layout.addWidget(self.controlBar)

        self.stacked_widget = QStackedWidget()
        self.frame_layout.addWidget(self.stacked_widget)

        self._setup_pages()

    def _variables_setup(self):
        """For setting up variables of the class"""
        self.project_location = ""

        # variables for setting up animations
        self.venv_start_up_animation = False

        self.python_interpreters = None
        self.found_python_interpreters = {}
        self.current_env = []

    def _setup_pages(self):
        """
        Sets up the individual pages that compose the onboarding flow and adds them to the stacked widget.
        """
        self.stacked_widget.addWidget(self._create_location_page())
        self.stacked_widget.addWidget(loading_virtual_env())
        self.stacked_widget.setCurrentIndex(0)

    def _create_location_page(self):
        """
        Creates the first page of the onboarding process, allowing the user to select
        a project directory and providing options for virtual environment setup.

        This page consists of:
        - A `browse_label` (within `location_container`) which, when clicked,
            triggers the `_select_location` method to open a file dialog.
        - A `select_env` container, initially hidden, which will display options
            to select an existing virtual environment or create a new one, once
            a project directory has been chosen.

        Returns:
            QWidget: The fully configured container widget for the location
                        and environment selection page.
        """
        container = QWidget()
        self.page_layout = QVBoxLayout(container)
        self.page_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.location_container = QFrame(container)
        self.location_container.setFixedHeight(50)
        self.location_container.setObjectName("locationContainer")
        location_layout = QVBoxLayout(self.location_container)
        location_layout.setContentsMargins(0, 0, 0, 0)
        location_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.browse_label = QLabel("Select Project Directory")
        self.browse_label.setObjectName("browseLabel")
        self.browse_label.setFixedHeight(50)
        self.browse_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.browse_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.browse_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.browse_label.mousePressEvent = self._select_location  # type: ignore
        location_layout.addWidget(self.browse_label)

        self.select_env = QFrame(container)
        self.select_env.setObjectName("selectEnv")
        self._populate_environment_container()

        self.page_layout.addWidget(self.location_container)
        self.page_layout.addWidget(self.select_env, 1)

        self.select_env.setVisible(False)
        self.select_env.setFixedHeight(0)

        return container

    def _populate_environment_container(self):
        """
        Populates the `self.select_env` frame with widgets for selecting or creating
        virtual environments.

        This method sets up the UI elements that allow the user to:
        1. View and select an existing virtual environment found within the project directory.
        2. Input a name for a new virtual environment and choose a global Python
           interpreter from which to create it.

        It initializes labels, combo boxes, line edits, and buttons, connecting
        their actions to the appropriate methods for environment management.
        """
        layout = QVBoxLayout(self.select_env)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.found_virtual_envs_label = QLabel(
            "Searching for existing virtual environments..."
        )
        self.found_virtual_envs_label.setFixedHeight(30)
        self.drop_down_for_selecting_virtual_env = QComboBox()
        self.use_selecting_virtual_env_button = QPushButton("Use this Environment")
        self.use_selecting_virtual_env_button.setObjectName("selectVirtualEnvButton")
        self.use_selecting_virtual_env_button.clicked.connect(
            self._set_existing_python_env
        )
        self.use_selecting_virtual_env_button.setObjectName(
            "useSelectingVirtualEnvButton"
        )

        self.create_virtual_env_information = QLabel(
            "Searching for existing global environments..."
        )
        self.create_virtual_env_information.setFixedHeight(30)
        self.name_of_venv = LineEdit()
        self.name_of_venv.setFixedHeight(38)
        self.name_of_venv.setContentsMargins(0, 0, 0, 0)
        self.name_of_venv.setPlaceholderText(
            "Type name of your virtual environment, default: venv"
        )
        self.name_of_venv.setObjectName("customVirtualName")

        self.drop_down_for_creating_python_env = QComboBox()
        self.create_virtual_env_button = QPushButton("Create New Environment")
        # self.create_virtual_env_button.setObjectName("createVirtualEnv")

        self.create_virtual_env_button.clicked.connect(self._create_virtual_env)
        self.create_virtual_env_button.setObjectName("createVirtualEnvButton")

        # self.find_env.finished.connect(self._display_env)
        layout.addWidget(self.found_virtual_envs_label)
        layout.addWidget(self.drop_down_for_selecting_virtual_env)
        layout.addWidget(self.use_selecting_virtual_env_button)

        layout.addSpacing(30)

        layout.addWidget(self.create_virtual_env_information)
        layout.addWidget(self.name_of_venv)
        layout.addWidget(self.drop_down_for_creating_python_env)
        layout.addWidget(self.create_virtual_env_button)
        # layout.addStretch()

    def _set_existing_python_env(self):
        """
        Emits the selected project location and virtual environment details.
        """
        current_venv = ""
        curr_dir = "".join(
            self.drop_down_for_selecting_virtual_env.currentText().split(":")[1:]
        ).strip()
        virtual_envs = []
        for env in self.env:
            virtual_envs.append(env)
            if env.get("venv_path") == curr_dir:
                current_venv = env.get("venv_name")

        self.location_selected.emit(self.project_location, current_venv, virtual_envs)

    def _create_virtual_env(self):
        """
        Initiates the creation of a new virtual environment.
        Validates the environment name and triggers environment creation via a worker.
        """
        text = self.name_of_venv.toPlainText()
        env_names = [env.split(os.path.sep)[-1] for env in self.list_of_virtual_env]

        if text == "":
            text = "venv"
        if text in env_names:
            commit_action(self, "Same name environment already exist")
        else:
            self.worker.emit_create_virtual_env(
                self.project_location,
                self.drop_down_for_creating_python_env.currentText()
                .split(":")[1]
                .strip(),
                text,
                resource_path(
                    self.config.get("paths", {})
                    .get("executables", {})
                    .get("find_local_environment", {})
                    .get("darwin", "./find_local_env")
                ),
            )

    def _update_widget(self, code: int, venv_path: str, venv_name, all_venv_names):
        """
        Updates the UI based on the result of a virtual environment creation or discovery operation.
        Switches to a loading screen or emits location_selected based on the provided code.
        """
        if code == 0:
            self.stacked_widget.setCurrentIndex(1)
        if code == 1:
            self.location_selected.emit(venv_path, venv_name, all_venv_names)

    def _select_location(self, event):
        """
        Handles the mouse press event to select a project directory.
        Opens a file dialog, updates the UI with the selected directory,
        and initiates animations and data fetching for virtual environments.
        """
        if self.venv_start_up_animation:
            return

        directory = QFileDialog.getExistingDirectory(
            self, "Selecting Directory", directory=os.path.expanduser("~")
        )
        if directory:
            self.worker.emit_signal_for_virtual_envs(
                directory,
                resource_path(
                    self.config.get("paths", {})
                    .get("executables", {})
                    .get("find_local_environment", {})
                    .get("darwin", "./find_local_env")
                ),
            )
            self.project_location = directory
            self.browse_label.setText(f"Selected: {directory}")
            self.python_interpreters = PythonInterpreters()

            if self.found_python_interpreters == {}:
                self.python_interpreters.finished.connect(
                    self._display_python_interpreters
                )
                self.python_interpreters.finished.connect(
                    self.release_python_interpreters
                )
                # self.python_interpreters.finished.connect(self.python_interpreters.quit)
                self.python_interpreters.start()
            else:
                self._display_python_interpreters(self.found_python_interpreters)

            self.find_env_in_pc.emit()

            self.venv_start_up_animation = True
            self.select_env.setVisible(True)

            final_height = self.select_env.sizeHint().height()

            self.animation_virtual_env_selection = QPropertyAnimation(
                self.select_env, b"maximumHeight"
            )
            self.animation_virtual_env_selection.setDuration(1000)
            self.animation_virtual_env_selection.setStartValue(0)
            self.animation_virtual_env_selection.setEndValue(final_height)
            self.animation_virtual_env_selection.setEasingCurve(
                QEasingCurve.Type.InOutQuart
            )
            self.animation_virtual_env_selection.finished.connect(
                lambda: setattr(self, "venv_start_up_animation", False)
            )
            self.animation_virtual_env_selection.start()

    def _display_env(self, env: list):
        self.env = env
        self.drop_down_for_selecting_virtual_env.clear()
        self.list_of_virtual_env = []
        if env:
            # found_env = "\n".join([f"{item['path']} : {item['version']}" for item in env])
            self.found_virtual_envs_label.setText(
                f"found {len(env)} virtual environments"
            )
            for item in env:
                self.list_of_virtual_env.append(item.get("venv_path"))

                self.drop_down_for_selecting_virtual_env.addItem(
                    f"{item.get('python_version')}: {item.get('venv_path')}"
                )
            self.drop_down_for_selecting_virtual_env.setVisible(True)
            self.use_selecting_virtual_env_button.setVisible(True)
        else:
            self.found_virtual_envs_label.setText("No virtual environment found")
            self.drop_down_for_selecting_virtual_env.setVisible(False)
            self.use_selecting_virtual_env_button.setVisible(False)

    def _display_python_interpreters(self, interpreters: dict):
        self.found_python_interpreters = interpreters
        self.drop_down_for_creating_python_env.clear()
        if interpreters != {}:
            self.create_virtual_env_information.setText(
                f"found {len(interpreters)} global python interpreters"
            )
            for item in interpreters:
                self.drop_down_for_creating_python_env.addItem(
                    f"{item} : {interpreters[item]}"
                )
        else:
            self.create_virtual_env_information.setText("No Python interpreter found")

    def _finished_flow(self):
        self.switch_to_main.emit()
