from PyQt6.QtWidgets import (
    QFrame,
    QListWidget,
    QMainWindow,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QLabel,
    QStackedWidget,
)
from PyQt6.QtCore import Qt, pyqtSignal
from components.about.core import About
from components.library.core import Library
from components.settings.core import Setting
from helpers.state_manager import save_state
from components.analysis.core import Analysis
from components.installer.core import Installer
from components.installer.utils import save_file
from components.widgets.control_bar import ControlBar
from components.onboarding.view import OnboardingPage
from components.dependency_tree.core import DependencyTree
from components.onboarding.threads import PythonInterpreters


class P4cMan(QMainWindow):
    """
    Main Window of the Application
    - What someone can do with it, You can start it
    """

    loaded_all_components = pyqtSignal()
    load_libraries = pyqtSignal()
    ui_loaded = pyqtSignal()

    def __init__(self, state_variables, config: dict = {}):
        """
        Initializes the P4cMan application window.

        Args:
            state_variables (dict): A dictionary containing the application's state.
            config (dict, optional): A dictionary containing the application's configuration. Defaults to {}.
        """
        super().__init__()
        self.python_interpreters = {}
        self.setMouseTracking(True)
        self.config = config
        self._extra_content()
        self.python_thread_worker = None

        # State variables
        self.state_variables = state_variables

        self._setting_ui_properties()
        self.container = QFrame()
        self._saving_screen()
        self.container.setObjectName("mainWindowContainer")
        self._setup_main_app_ui()
        self._onboarding_steps()
        self._set_connections()
        self._saving = False

    def _extra_content(self):
        """
        Initializes extra content for the application.
        """
        self.current_libraries = []
        self._installer_populated = False

    def _onboarding_steps(self):
        """
        Initializes the onboarding steps for the application.
        """

        self.main_stack = QStackedWidget(self)

        self.setCentralWidget(self.main_stack)

        # If onboarding was completed in previous runs, no need to hog memory by having onboarding
        if self.state_variables.get("project_folder", "") == "":
            self.onboarding_widget = OnboardingPage(self.config, self)
            self.main_stack.setCurrentWidget(self.onboarding_widget)
            self.main_stack.addWidget(self.onboarding_widget)
            self.main_stack.addWidget(self.container)

        else:
            self.main_stack.addWidget(self.container)
            self.main_stack.setCurrentWidget(self.container)

            self._set_existing_python_env(
                self.state_variables.get("project_folder", ""),
                self.state_variables.get("virtual_env_name", ""),
                self.state_variables.get("loaded_virtual_envs", []),
            )

        self.main_stack.addWidget(self.saving_page)

    def _on_fully_loaded(self):
        pass

    def _set_connections(self):
        """
        Just for setting connection, function for simplicity and devil worship
        """

        if hasattr(self, "onboarding_widget"):
            self.onboarding_widget.location_selected.connect(
                self._set_existing_python_env
            )
            self.onboarding_widget.switch_to_main.connect(self.switch_content)
            self.onboarding_widget.release_python_interpreters.connect(
                self._set_python_interpreters
            )

        self.libraries.current_state.connect(self._set_state_variables)
        self.libraries.libraries_emitter.connect(self._retrieve_libraries_content)
        self.libraries.python_exec.connect(self.installer.set_python_exec)
        self.installer.population_finished.connect(self._set_status_installer)
        self.installer.installed.connect(self.libraries.refetch_libraries)
        self.ui_loaded.connect(self._on_fully_loaded)

    def _set_python_interpreters(self, python_interpreters):
        self.python_interpreters = python_interpreters
        self.libraries.set_python_interpreters(python_interpreters)

    def _set_state_variables(self, project_folder, virtual_env_name, virtual_env_list):
        """
        Sets the state variables for the application.

        Args:
            project_folder (str): The path to the project folder.
            virtual_env_name (str): The name of the virtual environment.
        """
        self.state_variables["project_folder"] = project_folder
        self.state_variables["virtual_env_name"] = virtual_env_name
        self.state_variables["loaded_virtual_envs"] = virtual_env_list

        # Give project folder to other directories
        self._set_project_folder_location_in_different_widgets(project_folder)

    def _set_project_folder_location_in_different_widgets(self, project_folder):
        """Give the project folder's location to every widget which needs it for their functionality"""
        self.dependency_tree.set_project_folder(project_folder)

    def _set_existing_python_env(self, project_folder, current_venv, virtual_envs):
        """
        Sets the existing python environment for the application.

        Args:
            project_folder (str): The project directory.
            current_venv (str): The current virtual environment.
            virtual_envs (list): A list of virtual environments.
        """
        self.main_stack.setCurrentWidget(self.container)
        if self.python_interpreters == {}:
            self.python_thread_worker = PythonInterpreters()
            self.python_thread_worker.finished.connect(self._set_python_interpreters)
            self.python_thread_worker.finished.connect(
                self.python_thread_worker.deleteLater
            )
            self.python_thread_worker.start()

        self.libraries.selection_location_from_main(
            project_folder, current_venv, virtual_envs
        )

        # Give project folder to other directories
        self._set_project_folder_location_in_different_widgets(project_folder)

    def _setup_main_app_ui(self):
        """
        Sets up the main application UI.
        """
        self.libraries = Library(config=self.config)
        self.installer = Installer(config=self.config)
        self.dependency_tree = DependencyTree()
        self.analysis = Analysis()
        self.settings = Setting()
        self.about = About()

        self.contentDict = {
            "Libraries": self.libraries,
            "Installer": self.installer,
            "Dependency Tree": self.dependency_tree,
            "Analysis": self.analysis,
            "Settings": self.settings,
            "About": self.about,
        }
        self.navLists = self.contentDict.keys()
        main_layout = QHBoxLayout(self.container)
        main_layout.setContentsMargins(
            *self.config.get("ui", {})
            .get("window", {})
            .get("mainLayout", {})
            .get("contentsMargin", [0, 0, 0, 0])
        )

        main_layout.setSpacing(
            self.config.get("ui", {})
            .get("window", {})
            .get("mainLayout", {})
            .get("spacing", 0)
        )

        # Add Side Bar
        side_bar, self.navItems = self.side_bar()
        self.content_stack = self.create_content_area()

        main_layout.addWidget(side_bar)
        main_layout.addWidget(self.content_stack, 1)

        self.navItems.currentRowChanged.connect(self.content_stack.setCurrentIndex)

    def _set_status_installer(self):
        self._installer_populated = True
        self.installer.set_status(self.current_libraries)

    def _retrieve_libraries_content(self, libraries: list):
        """
        Retrieves the content of the libraries.
        Args:
            libraries (list): A list of libraries.
        """
        self.current_libraries = [library["name"] for library in libraries]
        if self._installer_populated:
            self._set_status_installer()

    def _page_for_creating_virtual_env(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(QLabel("Create Virtual Environment"))
        layout.addWidget(QPushButton("Create"))
        layout.addWidget(QPushButton("Cancel"))
        return container

    def switch_content(self):
        """
        Switches the content of the application.
        """
        if hasattr(self, "onboarding_widget"):
            self.onboarding_widget.worker.thread_library.deleteLater()
        if self.main_stack.currentWidget() != self.container:
            self.main_stack.setCurrentWidget(self.container)

    def _setting_ui_properties(self):
        """
        Sets the UI properties of the application.
        """
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setGeometry(
            *self.config.get("ui", {})
            .get("window", {})
            .get("geometry", [100, 100, 800, 600])
        )
        self.setMinimumSize(
            *self.config.get("ui", {}).get("window", {}).get("minSize", [800, 600])
        )
        self.appName = self.config.get("application", {}).get("name", "")

    def side_bar(self):
        """
        Creates the side bar of the application.
        Returns:
            tuple: A tuple containing the side bar and the navigation items.
        """
        side_bar = QWidget()
        side_bar.setObjectName("sideBar")
        # sideBar.setFixedWidth(250)
        side_bar.setMinimumWidth(
            self.config.get("ui", {})
            .get("window", {})
            .get("sideBar", {})
            .get("minWidth", 200)
        )
        side_bar.setMaximumWidth(
            self.config.get("ui", {})
            .get("window", {})
            .get("sideBar", {})
            .get("maxWidth", 200)
        )
        side_bar_layout = QVBoxLayout(side_bar)
        side_bar_layout.setContentsMargins(
            *self.config.get("ui", {})
            .get("window", {})
            .get("sideBar", {})
            .get("contentMargins", [10, 10, 10, 10])
        )
        side_bar_layout.setSpacing(
            self.config.get("ui", {})
            .get("window", {})
            .get("sideBar", {})
            .get("spacing", 15)
        )
        self.control_bar = ControlBar(self, self.config)
        self.control_bar.setContentsMargins(2, 2, 0, 0)
        self.control_bar.setObjectName("controlBar")
        side_bar_layout.addWidget(self.control_bar)

        navList = QListWidget()
        navList.setObjectName("navList")
        for navListItems in self.navLists:
            navList.addItem(navListItems)
        navList.setContentsMargins(
            *self.config.get("ui", {})
            .get("window", {})
            .get("sideBar", {})
            .get("navListContentMargin", [0, 0, 0, 0])
        )
        navList.setSpacing(
            self.config.get("ui", {})
            .get("window", {})
            .get("sideBar", {})
            .get("navListSpacing", 3)
        )

        side_bar_layout.addWidget(navList)
        return side_bar, navList

    def showEvent(self, a0):
        self.ui_loaded.emit()
        return super().showEvent(a0)

    def _saving_screen(self):
        """
        Initializes the saving screen widget.

        This screen is displayed when the application is saving its state or other data.
        It is a frameless, application-modal widget with a "Saving..." label centered on it.
        """
        self.saving_page = QWidget()
        self.saving_page.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.saving_page.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.saving_page.setFixedSize(400, 200)
        self.saving_page.setContentsMargins(20, 20, 20, 20)
        layout = QVBoxLayout(self.saving_page)
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)
        label = QLabel("Saving...")
        label.setStyleSheet("color: #fff; font-size: 48px;")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        self.saving_page.setLayout(layout)

    def create_content_area(self):
        """
        Create stack area for all the different pages (eg. libraries, installer ...)
        """
        content_stack = QStackedWidget()
        content_stack.setObjectName("contentStack")

        for index, item_text in enumerate(self.navLists):
            page = QWidget()
            page_layout = QVBoxLayout(page)
            page_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
            label = self.contentDict[item_text]
            page_layout.addWidget(label)
            content_stack.addWidget(page)
        return content_stack

    def closeEvent(self, a0) -> None:
        """
        Saves the current state of the application when the application is closed.

        Args:
            a0 (QCloseEvent): The close event.
        """
        # Set the saving page widget if the saving taking alot of time (thread Processes)
        self.main_stack.setCurrentWidget(self.saving_page)

        # They will always get during every change in env or project folder,
        # it won't be set if user never completed the initial steps so there are no state to be saved
        if not self.state_variables.get("project_folder", "") == "":
            save_state(self.state_variables)
            save_file(self.installer.all_libraries)

        super().closeEvent(a0)
