import json
import subprocess
from .utils import load_data
from PyQt6.QtCore import QModelIndex, QObject, QThread, pyqtSignal
import logging

logger = logging.getLogger(__name__)


class GetAllLibraryFromPyPI(QThread):
    def __init__(self, parent=None):
        super().__init__(parent)


class GettingInstallerLibraryDetails(QThread):
    """
    A QThread subclass that fetches details for a list of Python libraries
    using an external Go executable.

    It executes the Go program with the provided list of libraries, captures
    its JSON output, and emits the parsed dictionary result via the
    `finished` signal.
    """

    finished = pyqtSignal(dict)

    def __init__(self, go_executable, list_of_libraries, parent=None):
        super().__init__(parent)
        self.go_executable = go_executable
        self.list_of_libraries = list_of_libraries

    def run(self):
        if self.list_of_libraries:
            result = subprocess.run(
                [self.go_executable, *self.list_of_libraries],
                capture_output=True,
                text=True,
            )
            if result.stderr:
                logger.error(result.stderr)
            try:
                data = json.loads(result.stdout)
                if isinstance(data, dict):
                    self.finished.emit(data)
            except Exception as e:
                self.finished.emit({})
                logger.error(e)
                logger.info(result.stdout)
        else:
            self.finished.emit({})


class InstallerLibraries(QThread):
    """
    A QThread subclass for installing a single Python library using pip
    in a separate background thread.

    It executes the 'pip install' command with the specified Python executable
    and library name, capturing the output and emitting a signal upon completion
    indicating success or failure.
    """

    finished = pyqtSignal(int, QModelIndex)

    def __init__(
        self, python_exec_path, library_name, model_index: QModelIndex
    ) -> None:
        super().__init__()
        self.python_exec_path = python_exec_path
        self.library_name = library_name
        self.model_index = model_index

    def run(self):
        try:
            # subprocess.run is a blocking call, which is now safely in the background
            result = subprocess.run(
                [self.python_exec_path, "-m", "pip", "install", self.library_name],
                capture_output=True,
                text=True,
                check=False,  # Don't raise an exception on non-zero exit codes
            )

            if result.stderr:
                logger.error(result.stderr)

            if result.returncode == 0:
                self.finished.emit(1, self.model_index)
            else:
                self.finished.emit(-1, self.model_index)

        except Exception as e:
            logger.error(f"An exception occurred: {e}")
            self.finished.emit(-1, self.model_index)  # Use -1 for exceptions


class PyPiRunner(QObject):
    """This class is for fetching libraries for PyPI"""

    list_of_libraries = pyqtSignal(list)

    def __init__(self, appName: str = "P4cMan", fileName: str = "library_list.txt"):
        super().__init__()
        self.thread_runner = QThread()
        self.worker = PyPiWorker(appName, fileName)
        self.worker.moveToThread(self.thread_runner)

        self.worker.finished.connect(self.thread_runner.quit)
        self.thread_runner.started.connect(self.worker.run)
        self.worker.list_of_libraries.connect(self.list_of_libraries)

        self.worker.finished.connect(self.worker.deleteLater)
        self.thread_runner.finished.connect(self.thread_runner.deleteLater)

    def startFetching(self):
        self.thread_runner.start()


class PyPiWorker(QObject):
    """Worker for fetching libraries from PyPI"""

    list_of_libraries = pyqtSignal(list)
    finished = pyqtSignal()

    def __init__(self, appName: str = "P4cMan", fileName: str = "library_list.txt"):
        super().__init__()
        self.appName = appName
        self.fileName = fileName

    def run(self):
        librarylist = load_data(self.appName, self.fileName)
        self.list_of_libraries.emit(librarylist)
        self.finished.emit()
