from PyQt6.QtWidgets import (
    QFrame, QListWidget, QMainWindow, QHBoxLayout, QPushButton,
    QVBoxLayout, QWidget, QLabel, QStackedWidget,
)
from PyQt6.QtCore import  Qt, pyqtSignal
from components.onboarding.view import OnboardingPage
from components.dependency_tree.core import DependencyTree
from components.library.core import Library
from components.widgets.control_bar import ControlBar
from components.about.core import About
from components.installer.core import Installer
from components.installer.utils import save_file
from components.analysis.core import Analysis
from components.settings.core import Setting
from helpers.state_manager import save_state
from components.onboarding.threads import PythonInterpreters

class PacMan(QMainWindow):
    """
    Main Window of the Application
    - What someone can do with it, You can start it
    """

    loaded_all_components = pyqtSignal()
    load_libraries = pyqtSignal()
    def __init__(
        self,
        state_variables,
        config: dict = {}
    ):
        """
        Initializes the PacMan application window.

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
        self.onboarding_widget = OnboardingPage(self.config, self)
        self.onboarding_widget.location_selected.connect(self._set_existing_python_env)
        self.onboarding_widget.switch_to_main.connect(self.switchContent)
        self.onboarding_widget.release_python_interpreters.connect(self._set_python_interpreters)

        self.main_stack = QStackedWidget(self)
        self.main_stack.addWidget(self.onboarding_widget)
        self.main_stack.addWidget(self.container)
        self.main_stack.addWidget(self.saving_page)

        self.setCentralWidget(self.main_stack)
        if self.state_variables.get('project_folder', "") == "":
            self.main_stack.setCurrentWidget(self.onboarding_widget)
        else:
            self.main_stack.setCurrentWidget(self.container)
            self._set_existing_python_env(
                self.state_variables.get('project_folder', ''),
                self.state_variables.get('virtual_env_name', ''),
                self.state_variables.get('loaded_virtual_envs', [])
            )


    def _set_python_interpreters(self, python_interpreters):
        self.python_interpreters = python_interpreters
        print(python_interpreters)
        self.libraries.set_python_interpreters(python_interpreters)

    def _set_state_variables(self, project_folder, virtual_env_name, virtual_env_list):
        """
        Sets the state variables for the application.

        Args:
            project_folder (str): The path to the project folder.
            virtual_env_name (str): The name of the virtual environment.
        """
        self.state_variables['project_folder'] = project_folder
        self.state_variables['virtual_env_name'] = virtual_env_name
        self.state_variables['loaded_virtual_envs'] = virtual_env_list

    def _set_existing_python_env(self, curr_dir, current_venv, virtual_envs):
        """
        Sets the existing python environment for the application.

        Args:
            curr_dir (str): The current directory.
            current_venv (str): The current virtual environment.
            virtual_envs (list): A list of virtual environments.
        """
        self.main_stack.setCurrentWidget(self.container)
        if self.python_interpreters == {}:
            self.python_thread_worker = PythonInterpreters()
            self.python_thread_worker.finished.connect(self._set_python_interpreters)
            self.python_thread_worker.finished.connect(self.python_thread_worker.deleteLater)
            self.python_thread_worker.start()

        self.libraries.selection_location_from_main(curr_dir, current_venv, virtual_envs)

    def _setup_main_app_ui(self):
        """
        Sets up the main application UI.
        """
        self.libraries = Library(config = self.config)
        self.installer = Installer(config = self.config)
        self.analysis = Analysis()
        self.dependency_tree = DependencyTree()
        self.settings = Setting()
        self.about = About()

        self.contentDict = {
            "Libraries": self.libraries,
            "Installer": self.installer,
            "Analysis": self.analysis,
            "Dependency Tree": self.dependency_tree,
            "Settings": self.settings,
            "About": self.about
        }
        self.navLists = ["Libraries", "Installer", "Analysis", "Dependency Tree", "Settings", "About"]

        self.libraries.current_state.connect(self._set_state_variables)
        self.libraries.libraries_emitter.connect(self._retrieve_libraries_content)
        self.libraries.python_exec.connect(self.installer.set_python_exec)
        self.installer.populationFinished.connect(self._set_status_installer)
        self.installer.installed.connect(self.libraries.refetch_libraries)

        mainLayout = QHBoxLayout(self.container)
        mainLayout.setContentsMargins(
            *self.config.get("ui", {}).get('window', {}).get('mainLayout', {}).get('contentsMargin', [0, 0, 0, 0])
        )

        mainLayout.setSpacing(
            self.config.get("ui", {}).get('window', {}).get('mainLayout', {}).get('spacing', 0)
        )

        # Add Side Bar
        sideBar, self.navItems = self.sideBar()
        self.contentStack = self.createContentArea()

        mainLayout.addWidget(sideBar)
        mainLayout.addWidget(self.contentStack, 1)

        self.navItems.currentRowChanged.connect(
            self.contentStack.setCurrentIndex)

    def _set_status_installer(self):
        self._installer_populated = True
        self.installer.set_status(self.current_libraries)

    def _retrieve_libraries_content(self, libraries:list):
        """
        Retrieves the content of the libraries.
        Args:
            libraries (list): A list of libraries.
        """
        self.current_libraries = [library['name'] for library in libraries]
        if self._installer_populated:
            self._set_status_installer()

    def _page_for_creating_virtual_env(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(QLabel("Create Virtual Environment"))
        layout.addWidget(QPushButton("Create"))
        layout.addWidget(QPushButton("Cancel"))
        return container

    def switchContent(self):
        """
        Switches the content of the application.
        """
        self.main_stack.setCurrentWidget(self.container)

    def _setting_ui_properties(self):
        """
        Sets the UI properties of the application.
        """
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setGeometry(*self.config.get("ui", {}).get('window', {}).get("geometry", [100, 100, 800, 600]))
        self.setMinimumSize(*self.config.get("ui", {}).get('window', {}).get("minSize", [800, 600]))
        self.appName = self.config.get("application", {}).get("name", "")

    def sideBar(self):
        """
        Creates the side bar of the application.
        Returns:
            tuple: A tuple containing the side bar and the navigation items.
        """
        sideBar = QWidget()
        sideBar.setObjectName("sideBar")
        # sideBar.setFixedWidth(250)
        sideBar.setMinimumWidth(
            self.config.get("ui", {}).get('window', {}).get("sideBar", {}).get("minWidth", 100)
        )
        sideBar.setMaximumWidth(
            self.config.get("ui", {}).get('window', {}).get("sideBar", {}).get("maxWidth", 200)
        )
        sideBarLayout = QVBoxLayout(sideBar)
        sideBarLayout.setContentsMargins(
            *self.config.get("ui", {}).get('window', {}).get("sideBar", {}).get('contentMargins', [10, 10, 10, 10])
        )
        sideBarLayout.setSpacing(
            self.config.get('ui', {}).get('window', {}).get("sideBar", {}).get('spacing', 15)
        )
        self.control_bar = ControlBar(self, self.config)
        self.control_bar.setContentsMargins(2, 2, 0, 0)
        self.control_bar.setObjectName("controlBar")
        sideBarLayout.addWidget(self.control_bar)

        navList = QListWidget()
        navList.setObjectName("navList")
        for navListItems in self.navLists:
            navList.addItem(navListItems)
        navList.setContentsMargins(
            *self.config.get('ui', {}).get('window', {}).get("sideBar", {}).get('navListContentMargin', [0, 0, 0, 0])
        )
        navList.setSpacing(
            self.config.get('ui', {}).get('window', {}).get("sideBar", {}).get('navListSpacing', 3)
        )

        sideBarLayout.addWidget(navList)


        return sideBar, navList

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

    def createContentArea(self):
        """
        Create stack area for all the different pages (eg. libraries, installer ...)
        """
        contentStack = QStackedWidget()
        contentStack.setObjectName("contentStack")

        for index, item_text in enumerate(self.navLists):
            page = QWidget()
            pageLayout = QVBoxLayout(page)
            pageLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
            label = self.contentDict[item_text]
            pageLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
            pageLayout.addWidget(label)
            contentStack.addWidget(page)

        return contentStack

    def closeEvent(self, a0) -> None:
        """
        Saves the current state of the application when the application is closed.

        Args:
            a0 (QCloseEvent): The close event.
        """
        self.main_stack.setCurrentIndex(3)
        if not self.state_variables.get('project_folder', "") == "":
            save_state(
                self.state_variables
            )
            save_file(self.installer.allLibraries)
        super().closeEvent(a0)
