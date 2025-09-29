import sys
from PyQt6.QtCore import QModelIndex, QTimer, pyqtSignal
from PyQt6.QtWidgets import QLineEdit, QListView, QSizePolicy, QVBoxLayout, QWidget

# Imports from our new package structure
from .threads import GettingInstallerLibraryDetails, InstallerLibraries, PyPiRunner
from .models import LibraryListModel
from .models import DataRole
from .delegates import PyPIitemDelegate
from helpers.utils import resource_path


class Installer(QWidget):
    """Installer widget for installing libraries"""

    # Current Implementation just brings 30 libraries
    # It is storing all the libraries but it is not displaying them
    populate = pyqtSignal()
    population_finished = pyqtSignal()
    details_fetched = pyqtSignal(str, dict)
    installed = pyqtSignal()

    def __init__(self, parent=None, config: dict = {}):
        super().__init__(parent)
        self.config = config
        self.installer_thread = None
        self.indexes_which_are_installed = []
        self.sorted_matches = []
        self.sorted_match_with_install = []
        self.all_libraries = []
        self.python_exec = ""
        self.setStyleSheet(self.config.get("stylesheet", {}).get("tooltip", ""))
        self.API_ENDPOINT: str = (
            self.config.get("api", {})
            .get("pypi", {})
            .get("libraryDetails", "https://pypi.org/pypi/{package}/json")
        )
        # Setup all the UI Components
        self._setup_ui()

        # Setup timers and signals for fetching list of libraries
        self._setup_timers()
        self._setup_signals_for_fetching_libraries()
        self.get_details = None

    def _setup_ui(self):
        # Initialize the main layout
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.main_layout)

        self._setup_search_bar()
        self._setup_list_model()

    def set_python_exec(self, path):
        self.python_exec = path

    def _setup_search_bar(self):
        # Set a search bar for searching libraries to install
        self.search_bar = QLineEdit()
        self.search_bar.setFixedHeight(30)
        self.search_bar.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.search_bar.setObjectName("searchBarInstaller")
        self.search_bar.setPlaceholderText("Search for libraries to install...")
        self.search_bar.textChanged.connect(
            self._filter_list
        )  # ADDED: Connect search bar to filter method
        self.main_layout.addWidget(self.search_bar)

    def _setup_list_model(self):
        # Using Model/View Architecture
        self.library_list_view = QListView()
        self.library_list_view.setEnabled(True)

        self.library_list_view.setEditTriggers(QListView.EditTrigger.AllEditTriggers)

        self.library_list_view.setContentsMargins(0, 0, 0, 0)
        self.library_list_view.setObjectName("installLibraryListView")
        self.library_list_view.setSpacing(3)
        self.library_list_view.setObjectName("libraryListViewInstaller")
        self.library_list_view.setUniformItemSizes(False)

        # List Model which holds the data for the library list view
        self.source_model = LibraryListModel()
        self.library_list_view.setModel(self.source_model)
        self.delegate = PyPIitemDelegate(self.config, self.library_list_view)
        self.library_list_view.setItemDelegate(self.delegate)
        self.main_layout.addWidget(self.library_list_view)

    def _setup_timers(self):
        # Search Timer
        self.scraper_pypi = PyPiRunner()
        self.search_timer = QTimer()
        self.search_timer.setInterval(300)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._filter_list)

        self.fetch_details_timer = QTimer()
        self.fetch_details_timer.setInterval(1000)
        self.fetch_details_timer.setSingleShot(True)
        self.fetch_details_timer.timeout.connect(self._fetch_details)

    def set_status(self, libraries_list: list):
        for library in self.sorted_matches:
            if library in libraries_list:
                try:
                    index = self.sorted_matches.index(library)
                    self.sorted_match_with_install[index].update(
                        {"status": "installed"}
                    )
                    index_of_model = self.source_model.name_to_row.get(library, -1)
                    if index_of_model != -1:
                        idx = self.source_model.index(index_of_model)
                        self.source_model.dataChanged.emit(idx, idx)
                except ValueError:
                    continue
            else:
                index = self.sorted_matches.index(library)
                if index == -1:
                    continue
                self.sorted_match_with_install[index].update({"status": "install"})
                index_of_model = self.source_model.name_to_row.get(library, -1)
                if index_of_model != -1:
                    idx = self.source_model.index(index_of_model)
                    self.source_model.dataChanged.emit(idx, idx)

    def _fetch_details(self):
        # Fetch details of libraries
        if self.sorted_matches:
            # for the specific platfrom
            platform = sys.platform
            fetcher_config = (
                self.config.get("paths", {})
                .get("executables", {})
                .get("pypiDetailFetcher", {})
            )
            if platform == "win32":
                executable_name = fetcher_config.get(
                    platform, "./pypi_detail_fetcher.exe"
                )
            else:
                executable_name = fetcher_config.get(platform, "./pypi_detail_fetcher")
            self.get_details = GettingInstallerLibraryDetails(
                resource_path(executable_name),
                self.sorted_matches,
            )
            self.get_details.finished.connect(self.source_model.updateData)
            self.get_details.start()

    def _show_installed_flag(self, return_code, model_index: QModelIndex):
        name_of_library = model_index.data(DataRole).get("name")
        self.installed.emit()
        idx = self.sorted_matches.index(name_of_library)
        if return_code == -1:
            self.sorted_match_with_install[idx].update({"status": "failed"})
            self.source_model.dataChanged.emit(model_index, model_index)
        else:
            self.sorted_match_with_install[idx].update({"status": "installed"})
            self.source_model.dataChanged.emit(model_index, model_index)
        self.installer_thread = None

    def _install_library(self, model_index: QModelIndex):
        name_of_library = model_index.data(DataRole).get("name")
        idx = self.sorted_matches.index(name_of_library)
        self.sorted_match_with_install[idx].update({"status": "installing"})
        self.source_model.dataChanged.emit(model_index, model_index)
        self.installer_thread = InstallerLibraries(
            self.python_exec, name_of_library, model_index
        )
        self.installer_thread.finished.connect(self._show_installed_flag)
        self.installer_thread.finished.connect(self.installer_thread.quit)
        self.installer_thread.start()

    def _setup_signals_for_fetching_libraries(self):
        # Threading setup, fetching details of libraries will be in different function
        self.source_model.remove_item.connect(self._remove_garbage_data)
        self.scraper_pypi.list_of_libraries.connect(self._get_all_libraries)
        self.scraper_pypi.startFetching()
        self.delegate.install_clicked.connect(self._install_library)

    def _remove_garbage_data(self, item):
        self.all_libraries.remove(item)
        self._filter_list()

    def _get_all_libraries(self, libraries: list):
        self.all_libraries = libraries
        self.search_bar.setPlaceholderText(
            "Search for libraries to install from the {:,} available libraries".format(
                len(self.all_libraries)
            )
        )
        self._filter_list()

    def _filter_list(self):
        search_text = self.search_bar.text().lower()
        if not search_text:
            self.sorted_matches = self.all_libraries[:50]
            self.sorted_match_with_install = [
                {"name": name, "status": "install"} for name in self.sorted_matches
            ]
        else:
            matches = [
                item for item in self.all_libraries if search_text in item.lower()
            ]
            self.sorted_matches = sorted(
                matches, key=lambda item: item.lower().find(search_text)
            )
            self.sorted_matches = self.sorted_matches[:50]
            self.sorted_match_with_install = [
                {"name": name, "status": "install"} for name in self.sorted_matches
            ]

        self.population_finished.emit()
        self.fetch_details_timer.start(1000)
        self.library_list_view.scrollToTop()
        self.source_model.setDataList(self.sorted_match_with_install)
        self.source_model.set_name_to_row()
