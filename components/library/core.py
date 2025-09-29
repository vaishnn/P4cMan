import os
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QLineEdit,
    QMessageBox,
    QStackedWidget,
    QWidget,
    QVBoxLayout,
    QListWidget,
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
)
from PyQt6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QTimer,
    Qt,
    pyqtSignal,
    QSize,
    pyqtSlot,
)
from ..widgets.helper_classes import LineEdit
from ..onboarding.utils import commit_action
from ..onboarding.utils import loading_virtual_env
from ..widgets.tooltip import InteractiveToolTip
from ..widgets.buttons import RotatingPushButton
from .threads import LibraryThreads, Uninstall
from .utils import rank_query, human_readable_size, format_tooltip_html
from copy import deepcopy
from helpers.utils import resource_path


class Library(QWidget):
    """
    This class is for all Library Related Widgets

    What it does:
    - Provide a list of installed libraries
    - Allow user to search for libraries
    - Display details of selected library
    - Allow user to uninstall selected library
    - And more if we want
    """

    venv_loaded = pyqtSignal(str, str, list)
    show_env_box = pyqtSignal()
    libraries_emitter = pyqtSignal(list)
    current_state = pyqtSignal(
        str, str, list
    )  # Current state of selected Project Folder and Virtual Env name selected
    python_exec = pyqtSignal(str)

    def __init__(self, config, parent=None):
        super().__init__(parent)
        if not hasattr(self, "config"):
            self.config = config
        self.setObjectName("library")
        self._init_properties()
        self._worker_thread()
        self._init_ui()
        self._connect_signals()

    def _init_properties(self):
        """Initializes non-UI properties, caches, and maps."""
        self.item_map = {}
        self.animate_env_box = False
        self.search_bar_hiding_animations = False
        self.search_bar_showing_animations = False
        self.create_virtual_env_animation_hiding = False
        self.create_virtual_env_animation_showing = False
        self.current_loaded_virtual_envs_list = []
        self.current_virtual_env = ""
        self.python_exec_path = ""
        self.env_creator: LibraryThreads
        self.index_for_stacked_pages = {}
        self.already_inside_project = False
        self.current_dir = ""
        self.uninstall_manager = None

    def _worker_thread(self):
        """Initializes worker threads for fetching library details and virtual environment lists."""
        self.worker = LibraryThreads()
        self.worker.details.connect(self._handle_list_libraries)
        self.worker.virtual_envs.connect(self._venv_loaded_connected)

    def _init_ui(self):
        """Initializes the main user interface layout and components."""
        self.setObjectName("library")
        self.setStyleSheet(self.config.get("stylesheet", {}).get("tooltip", ""))

        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)

        self._setup_path_selection_bar(page_layout)

        # Create a container for the search bar and list
        library_section_layout = QVBoxLayout()
        library_section_layout.setContentsMargins(0, 2, 0, 0)
        library_section_layout.setSpacing(0)

        self._setup_search_bar(library_section_layout)
        self._setup_library_list(library_section_layout)

        page_layout.addLayout(library_section_layout)

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

    def _setup_path_selection_bar(self, parent_layout):
        """Creates the top bar for selecting the virtual environment path."""
        layout = QHBoxLayout()
        margin = (
            self.config.get("ui", {})
            .get("window", {})
            .get("library", {})
            .get("labelLocation", {})
            .get("contentMargin", [0, 0, 0, 0])
        )
        layout.setContentsMargins(*margin)

        # Label for selecting path
        self.label_location = QLabel("Select Path")
        self.label_location.setObjectName("labelLocation")
        self.label_location.setFixedHeight(30)
        self.label_location.setCursor(Qt.CursorShape.PointingHandCursor)
        self.label_location.mousePressEvent = self._select_location  # type: ignore

        # for changing the virtual env in the same directory
        self.change_env_in_same_directory = QComboBox()
        self.change_env_in_same_directory.setMaximumHeight(30)
        self.change_env_in_same_directory.setMaximumWidth(0)
        self.change_env_in_same_directory.setVisible(False)
        self.change_env_in_same_directory.currentIndexChanged.connect(
            self._on_env_inventory_in_same_directory
        )
        self.change_env_in_same_directory.setObjectName("change_env_in_same_directory")

        self.initialize_env_button = RotatingPushButton()
        self.initialize_env_button.setIcon(
            QIcon(
                resource_path(
                    self.config.get("paths", {})
                    .get("assets", {})
                    .get("images", {})
                    .get("add", "assets/images/add.svg")
                )
            )
        )
        # self.initialize_env_button.setIconSize(QSize(12, 12))
        self.initialize_env_button.setMaximumSize(15, 15)
        self.initialize_env_button.setContentsMargins(0, 0, 0, 0)
        self.initialize_env_button.setObjectName("initializeEnvironmentButton")
        self.initialize_env_button.clicked.connect(self._create_new_virtual_env)

        layout.addWidget(self.label_location, 1)
        layout.addWidget(self.change_env_in_same_directory, 2)
        layout.addWidget(self.initialize_env_button)
        parent_layout.addLayout(layout)

    def _create_new_virtual_env(self):
        """Prepares the UI to allow the user to create a new virtual environment."""
        self.stacked_library_with_loading_screen.setCurrentWidget(self.create_new_env)
        self._animate(
            self.search_bar, b"maximumHeight", 0, 30, False, "hide_search_bar"
        )
        self._animate(
            self.change_env_in_same_directory,
            b"maximumWidth",
            0,
            150,
            False,
            "hide_env_box",
        )
        self._animate(
            self.initialize_env_button,
            b"maximumWidth",
            0,
            15,
            False,
            "hide_initialize_button",
            QEasingCurve.Type.InQuad,
        )

    def _on_env_inventory_in_same_directory(self):
        """Handles the selection of a different virtual environment from the QComboBox."""
        self.stacked_library_with_loading_screen.setCurrentWidget(self.loading_page)
        current_location = self.current_dir
        current_virtual_env = self.change_env_in_same_directory.currentText()
        self._change_virtual_env(current_location, current_virtual_env)

    def _expand_change_env(self):
        """Animtes the virtual env selector"""
        if self.animate_env_box:
            return

        self.animate_env_box = True
        self.change_env_in_same_directory.setVisible(True)
        # final_width = self.change_env_in_same_directory.sizeHint().height()
        final_width = 150
        self.animation = QPropertyAnimation(
            self.change_env_in_same_directory, b"maximumWidth"
        )
        self.animation.setDuration(1000)
        self.animation.setStartValue(0)
        self.animation.setEndValue(final_width)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuart)
        self.animation.finished.connect(lambda: setattr(self, "animate_env_box", False))
        self.animation.start()

    def _page_for_creating_new_virtual_env(self):
        """Creates and returns a QWidget that provides the UI for creating a new virtual environment."""
        container = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_of_venv = LineEdit()
        name_of_venv.setMaximumHeight(40)
        name_of_venv.setContentsMargins(0, 0, 0, 0)
        name_of_venv.setPlaceholderText(
            "Type name of your virtual environment, default: venv"
        )
        name_of_venv.setObjectName("customVirtualName")

        self.drop_down_for_creating_python_env = QComboBox()
        create_virtual_env_button = QPushButton("Create New Environment")
        create_virtual_env_button.setObjectName("createVirtualEnvButton")

        create_virtual_env_button.clicked.connect(
            lambda: self._create_virtual_env(name_of_venv.toPlainText().strip())
        )

        second_layout = QHBoxLayout()
        cancel_button = QPushButton("Cancel")
        cancel_button.setObjectName("cancelEnvironmentCreatorButton")
        cancel_button.clicked.connect(
            lambda: (
                self.stacked_library_with_loading_screen.setCurrentWidget(
                    self.library_list
                ),
                self._check_for_hidden(),
            )
        )

        second_layout.addSpacing(10)
        second_layout.setAlignment(Qt.AlignmentFlag.AlignRight)

        second_layout.addWidget(cancel_button)
        layout.addWidget(name_of_venv)
        layout.addWidget(self.drop_down_for_creating_python_env)
        layout.addWidget(create_virtual_env_button)
        layout.addLayout(second_layout)
        layout.addSpacing(20)

        container.setLayout(layout)
        return container

    def _create_virtual_env(self, text):
        venv_names = [
            cur_venv["venv_name"] for cur_venv in self.current_loaded_virtual_envs_list
        ]
        if text == "":
            text = "venv"

        if text in venv_names:
            commit_action(self, "Same name environment already exist")
        else:
            self.stacked_library_with_loading_screen.setCurrentWidget(self.loading_page)
            self.env_creator = LibraryThreads()
            self.env_creator.emit_create_virtual_env(
                self.current_dir,
                self.drop_down_for_creating_python_env.currentText()
                .split(":")[1]
                .strip(),
                text,
                resource_path(
                    self.config.get("paths", {})
                    .get("executables", {})
                    .get("find_local_environment", {})
                    .get("darwin")
                ),
            )
            self.env_creator.new_virtual_env.connect(self._on_creating_new_virtual_env)

    def _on_creating_new_virtual_env(
        self, success_code, directory, virtual_env_name, venvs
    ):
        if success_code == 1:
            self.selection_location_from_main(directory, virtual_env_name, venvs)
        elif success_code == 0:
            self.stacked_library_with_loading_screen.setCurrentWidget(self.loading_page)
        else:
            commit_action(self, "Unknown error")

    def _change_virtual_env(self, directory, venv_name):
        """Changes the currently active virtual environment and triggers a refresh of the library list."""
        if not directory or not venv_name:
            return
        self.current_state.emit(
            directory, venv_name, self.current_loaded_virtual_envs_list
        )
        self.current_virtual_env = venv_name
        self._set_python_exec_path(
            [
                env["python_path"]
                for env in self.current_loaded_virtual_envs_list
                if env["venv_name"] == venv_name
            ][0]
        )
        self.worker.emit_signal_for_details(
            self.current_dir,
            resource_path(
                self.config.get("paths", {})
                .get("executables", {})
                .get("load_library", {})
                .get("darwin")
            ),
            self.current_virtual_env,
        )

    def _setup_search_bar(self, parent_layout):
        """Creates the search bar and its associated typing timer."""
        self.search_bar = QLineEdit()
        self.search_bar.hide()
        self.search_bar.setContentsMargins(0, 0, 0, 0)
        self.search_bar.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.search_bar.setMaximumHeight(30)
        self.search_bar.setPlaceholderText("Search for libraries")
        self.search_bar.setObjectName("searchBarInLibraryListWidget")
        self.search_bar.textChanged.connect(self._sort_items_list)
        parent_layout.addWidget(self.search_bar)

    def _setup_library_list(self, parent_layout):
        """Creates the main QListWidget for displaying the libraries."""
        library_layout = QVBoxLayout()
        library_layout.setContentsMargins(0, 10, 0, 0)
        self.stacked_library_with_loading_screen = QStackedWidget()
        self.library_list = QListWidget()
        self.stacked_library_with_loading_screen.addWidget(self.library_list)
        self.loading_page = loading_virtual_env()
        self.stacked_library_with_loading_screen.addWidget(self.loading_page)
        self.page_no_env = self._page_no_virtual_env_found()
        self.stacked_library_with_loading_screen.addWidget(self.page_no_env)
        self.create_new_env = self._page_for_creating_new_virtual_env()
        self.stacked_library_with_loading_screen.addWidget(self.create_new_env)

        self.library_list.setObjectName("libraryList")
        library_layout.addWidget(self.stacked_library_with_loading_screen)

        parent_layout.addLayout(library_layout)

    def _page_no_virtual_env_found(self):
        container = QWidget()
        layout = QVBoxLayout(container)

        label = QLabel()
        label.setText(
            "No Virtual Environments Found in this directory\nCreate a new one using the plus icon above"
        )
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setContentsMargins(0, 0, 0, 20)
        label.setObjectName("noVirtualEnvLabel")
        layout.addWidget(label)
        container.setLayout(layout)

        return container

    def set_python_interpreters(self, interpreters: dict):
        self.python_interpreters = interpreters
        if interpreters != {}:
            for interpreter_path, python_version in interpreters.items():
                self.drop_down_for_creating_python_env.addItem(
                    f"{python_version}: {interpreter_path}"
                )

    def _connect_signals(self):
        """Connects the class's own signals to their respective slots."""
        self.show_env_box.connect(self._expand_change_env)
        self.venv_loaded.connect(self._on_venv_loaded)

    def _set_python_exec_path(self, path):
        self.python_exec_path = path
        self.python_exec.emit(path)

    def _handle_list_libraries(self, libraries: list):
        self._add_items(libraries)

    def _check_for_hidden(self):
        if not self.search_bar.isVisible():
            self._animate(
                self.search_bar,
                b"maximumHeight",
                30,
                0,
                True,
                "show_search_bar",
                before=True,
            )
        if not self.initialize_env_button.isVisible():
            self._animate(
                self.initialize_env_button,
                b"maximumWidth",
                15,
                0,
                True,
                "show_initialize_environment_button",
                before=True,
            )
        if not self.change_env_in_same_directory.isVisible():
            self._animate(
                self.change_env_in_same_directory,
                b"maximumWidth",
                150,
                0,
                True,
                "show_change_environment_button",
                before=True,
            )

    def _on_venv_loaded(self, directory_path, current_venv, virtual_env_names):
        # Block signals to prevent the signal loop
        self._check_for_hidden()
        self.change_env_in_same_directory.clear()
        self.change_env_in_same_directory.blockSignals(True)

        if virtual_env_names:
            for env in deepcopy(virtual_env_names):
                if os.path.exists(env["venv_path"]):
                    self.change_env_in_same_directory.addItem(env["venv_name"])
                else:
                    virtual_env_names.remove(env)
                    if current_venv == env["venv_name"]:
                        current_venv = self.change_env_in_same_directory.currentText()

            self.stacked_library_with_loading_screen.setCurrentWidget(self.loading_page)
            self.current_loaded_virtual_envs_list = virtual_env_names
            self._expand_change_env()  # Animate the box
            self.change_env_in_same_directory.setCurrentText(self.current_virtual_env)

            # Unblock signals now that we are done modifying
            self.change_env_in_same_directory.blockSignals(False)

            # Manually trigger the load for the first item
            self._change_virtual_env(self.current_dir, self.current_virtual_env)
        else:
            self.library_list.clear()  # No venvs found
            QMessageBox.information(
                self,
                "No Environments",
                "No virtual environments found in this directory.",
            )
            self.change_env_in_same_directory.blockSignals(False)

    def _select_location(self, event):
        directory_path = QFileDialog.getExistingDirectory(
            self, "Select Directory", directory=os.path.expanduser("~")
        )
        if directory_path:
            self.current_dir = directory_path
            self.already_inside_project = False
            self.label_location.setText(directory_path)
            self.worker.emit_signal_for_virtual_envs(
                directory_path,
                resource_path(
                    self.config.get("paths", {})
                    .get("executables", {})
                    .get("find_local_environment", {})
                    .get("darwin")
                ),
            )

    def _venv_loaded_connected(self, venv_list):
        """Handles the list of virtual environments received from the worker thread."""
        if isinstance(venv_list, list):
            if venv_list == []:
                self.change_env_in_same_directory.clear()
                self.current_loaded_virtual_envs_list = []
                self.current_virtual_env = None
                self.change_env_in_same_directory.setPlaceholderText("--")
                self.stacked_library_with_loading_screen.setCurrentWidget(
                    self.page_no_env
                )
                self._animate(
                    self.search_bar, b"maximumHeight", 0, 30, False, "hide_search_bar"
                )
                self._animate(
                    self.change_env_in_same_directory,
                    b"maximumWidth",
                    0,
                    150,
                    False,
                    "hide_env_box",
                )
                if not self.initialize_env_button.isVisible():
                    self._animate(
                        self.initialize_env_button,
                        b"maximumWidth",
                        15,
                        0,
                        True,
                        "show_initialize_environment_button",
                        before=True,
                    )

                return
            self.current_virtual_env = venv_list[0].get("venv_name")
            self.venv_loaded.emit(
                self.current_dir, venv_list[0].get("venv_name"), venv_list
            )

    def selection_location_from_main(self, directoryPath, venv_name, virtual_envs):
        """
        Updates the library view and internal state based on a selected project folder and virtual environment.
        """
        if hasattr(self, "env_creator"):
            self.env_creator.quit()

        self.current_dir = directoryPath
        self.label_location.setText(f"{directoryPath}")
        self.current_virtual_env = venv_name
        self.venv_loaded.emit(directoryPath, venv_name, virtual_envs)

    def _add_items(self, itemsList):
        """
        Populates the library list with provided items and triggers a UI refresh.
        """
        self.search_bar.show()
        self.all_items_data = [items["metadata"] for items in itemsList]
        self.libraries_emitter.emit(self.all_items_data)
        self._sort_items_list()

    def _sort_items_list(self):
        """
        Updates the library list with the provided items, applying search and sorting.

        Args:
            itemsList (list): A list of dictionaries, where each dictionary contains
                              metadata about an installed library.
            emit (bool, optional): Whether to emit the list_library_refreshed signal after
                                   updating the list. Defaults to False, which starts a timer
                                   to delay the signal emission.
        """
        self.search_bar.show()
        query = self.search_bar.text()
        items = []
        if not query:
            items = sorted(self.all_items_data, key=lambda x: x["name"])
        else:
            items = rank_query([item_data for item_data in self.all_items_data], query)

        # Clear the UI and re-populate it with the sorted list
        self.library_list.clear()
        self.item_map.clear()
        for item in items:
            list_lbrary_widget = QWidget()
            list_lbrary_widget.setObjectName("listLibraryWidget")
            list_lbrary_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            list_widget_layout = QHBoxLayout(list_lbrary_widget)
            # All the QLabels

            # Name of the Library
            name_library_panel = QLabel(item["name"])
            name_library_panel.setAlignment(Qt.AlignmentFlag.AlignVCenter)
            name_library_panel.setObjectName("nameLibraryPanel")

            # Version of the Library
            version_library_panel = QLabel(item["version"])
            version_library_panel.setAlignment(Qt.AlignmentFlag.AlignCenter)
            version_library_panel.setObjectName("versionLibraryPanel")

            # Tag of The Library I means Installed outside and D means Downloaded from the world wide web
            size_panel = QLabel()
            size_panel.setText(human_readable_size(item["size"]))
            size_panel.setFixedWidth(60)
            size_panel.setObjectName("sizeLibraryPanel")

            # Changing Properties of QLabels
            uninstall_button = QPushButton()
            uninstall_button.setFixedSize(30, 30)
            uninstall_button.setObjectName("deleteButtonFromLibraryListWidget")
            uninstall_button.setIcon(
                QIcon(
                    resource_path(
                        self.config.get("paths", {})
                        .get("assets", {})
                        .get("images", {})
                        .get("uninstall")
                    ),
                )
            )
            uninstall_button.setIconSize(QSize(22, 22))

            classifiers = item.get("classifier", [])
            classifiers = classifiers if classifiers else []
            license = ""
            if item.get("license_expression", "") != "":
                license = item["license_expression"].strip()
            for classifier in classifiers:
                if "License :: OSI Approved" in classifier:
                    license = classifier.split("::")[-1].strip()
            if license == "":
                for classifier in classifiers:
                    if "License :: OSI Approved" in classifier:
                        license = classifier.split("::")[-1].strip()
                if item.get("license", "") != "":
                    license = item["license"].strip()

            license_panel = QLabel()
            license_panel.setText(license.replace("License", "").strip())
            license_panel.setAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
            # license_panel.setFixedWidth(100)
            license_panel.setObjectName("licenseLibraryPanel")
            license_panel.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
            )

            # Adding Widget in proper Order
            list_widget_layout.addWidget(size_panel)
            list_widget_layout.addWidget(name_library_panel)
            list_widget_layout.addWidget(license_panel)
            list_widget_layout.addWidget(version_library_panel)
            list_widget_layout.addSpacing(100)
            list_widget_layout.addWidget(uninstall_button)
            listItem = QListWidgetItem(self.library_list)
            listItem.setSizeHint(QSize(0, 55))
            self.library_list.addItem(listItem)
            self.library_list.setItemWidget(listItem, list_lbrary_widget)

            interactiveToolTip = InteractiveToolTip(self)
            interactiveToolTip.install_on(list_lbrary_widget)
            interactiveToolTip.set_object_name("listLibraryWidgetToolTip")
            interactiveToolTip.set_content(format_tooltip_html(item, "figtree"))

            self.item_map[item["name"]] = (list_lbrary_widget, listItem)
            uninstall_button.clicked.connect(
                lambda checked=False,
                packageName=item["name"],
                uninstall_button=uninstall_button: self.start_library_uninstaller(
                    packageName, uninstall_button
                )
            )

        self.stacked_library_with_loading_screen.setCurrentWidget(self.library_list)

    def start_library_uninstaller(self, packageName, uninstall_button: QPushButton):
        """
        Initiates the uninstallation process for a specified library.
        Displays a confirmation dialog and starts a separate thread for the uninstall operation.
        """
        reply = QMessageBox.warning(
            self,
            "Confirm Uninstall",
            f"Uninstalling {packageName}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            if packageName in self.item_map:
                uninstall_button.setIcon(
                    QIcon(
                        resource_path(
                            self.config.get("paths", {})
                            .get("assets", {})
                            .get("images", {})
                            .get("uninstalling", "")
                        )
                    )
                )
            self.uninstall_manager = Uninstall(
                self.python_exec_path, packageName, uninstall_button
            )
            self.uninstall_manager.finished.connect(self.on_uninstall_finished)
            self.uninstall_manager.finished.connect(self.uninstall_manager.deleteLater)
            self.uninstall_manager.start()

    def refetch_libraries(self):
        self._change_virtual_env(self.current_dir, self.current_virtual_env)

    @pyqtSlot(int, str, str, QPushButton)
    def on_uninstall_finished(
        self, success, package_name, python_path, uninstall_button: QPushButton
    ):
        """
        Handles the completion of an uninstall process.

        Updates the UI to reflect the success or failure of the uninstall operation,
        including changing the icon of the uninstall button and, upon success,
        removing the item from the list after a short delay.

        Args:
            success (int): 1 if the uninstall was successful, 0 otherwise.
            package_name (str): The name of the package that was attempted to be uninstalled.
            python_path (str): The path to the Python executable used for the uninstall.
            uninstall_button (QPushButton): The button associated with the uninstalled package.
        """

        def _pop_item_in_sometime(self):
            listItem = self.item_map.pop(package_name)
            if listItem:
                row = self.library_list.row(listItem[1])
                self.library_list.takeItem(row)

        if success:
            uninstall_button.setIcon(
                QIcon(
                    resource_path(
                        self.config.get("paths", {})
                        .get("assets", {})
                        .get("images", {})
                        .get("uninstalled", "")
                    )
                )
            )
            QTimer.singleShot(2000, lambda: _pop_item_in_sometime(self))
        else:
            uninstall_button.setIcon(
                QIcon(
                    resource_path(
                        self.config.get("paths", {})
                        .get("assets", {})
                        .get("images", {})
                        .get("failed", "")
                    )
                )
            )
            uninstall_button.setEnabled(False)
        self.uninstall_manager = None
