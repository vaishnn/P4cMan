import json
import os
import subprocess
from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QPushButton
import logging

logger = logging.getLogger(__name__)


class Uninstall(QThread):
    """
    A QThread subclass to handle the uninstallation of Python packages.
    It runs `pip uninstall` in a separate thread and emits a signal
    with the result upon completion.
    """

    finished = pyqtSignal(
        int, str, str, QPushButton
    )  # (success_code, library_name, python_path, button)

    def __init__(self, python_path, library, uninstall_button):
        super().__init__()
        self.python_path = python_path
        self.library = library
        self.uninstall_button = uninstall_button

    def run(self):
        result = subprocess.run(
            [self.python_path, "-m", "pip", "uninstall", "-y", self.library],
            text=True,
        )

        if result.returncode == 0:
            self.finished.emit(1, self.library, self.python_path, self.uninstall_button)
        else:
            self.finished.emit(
                -1, self.library, self.python_path, self.uninstall_button
            )


class LibraryWorker(QObject):
    """
    A QObject subclass that performs library-related operations
    (fetching details, managing virtual environments) in a separate thread.
    It emits signals upon completion of tasks.
    """

    details_with_virtual_envs = pyqtSignal(str, list, list)
    new_virtual_env = pyqtSignal(int, str, str, list)
    virtual_envs = pyqtSignal(list)
    details = pyqtSignal(list)

    @pyqtSlot(str, str, str)
    def fetch_only_details(self, directory: str, load_library_exe: str, venv_name: str):
        """only fetches details of the library by running the compiled Go Code"""
        if directory == "" or venv_name == "":
            self.details.emit([])
            return

        result_details = subprocess.run(
            [load_library_exe, os.path.join(directory, venv_name)],
            capture_output=True,
            text=True,
        )
        if result_details.stderr:
            logger.error(result_details.stderr)
        if result_details.stdout.strip() == "":
            self.details.emit([])
            return

        try:
            details = json.loads(result_details.stdout).get("installed", [])
            if details is None:
                self.details.emit([])
            else:
                self.details.emit(details)
        except json.JSONDecodeError:
            self.details.emit([])
            return

    @pyqtSlot(str, str)
    def fetch_virtual_envs(self, directory: str, find_env_exe: str):
        """fetches virtual environments by running the compiled Go Code"""
        if not directory or not find_env_exe:
            self.virtual_envs.emit([])
            return

        result_venvs = subprocess.run(
            [find_env_exe, directory],
            capture_output=True,
            text=True,
        )
        if result_venvs.stdout.strip() == "":
            self.virtual_envs.emit([])
        try:
            venvs = json.loads(result_venvs.stdout)
            if venvs is None:
                self.virtual_envs.emit([])
            else:
                self.virtual_envs.emit(venvs)
            return
        except json.JSONDecodeError:
            self.virtual_envs.emit([])
            return

    @pyqtSlot(str, str, str, str)
    def initialize_new_virtual_env(
        self, directory: str, python_path: str, virtual_env_name: str, find_env_exe: str
    ):
        """
        Initializes a new virtual environment in the specified directory
        using the given Python path and virtual environment name.
        After creation, it fetches and emits the updated list of virtual environments.

        Emits:
        new_virtual_env (int, str, str, list): A signal indicating the status
        of the virtual environment creation.
        - (0, "", "", []) if initial validation fails (Needs to be fixed)
        - (1, directory, virtual_env_name, venvs) on successful creation,
            containing the directory, name of the new venv, and the updated list of venvs.
        """
        if not (directory or python_path or virtual_env_name, find_env_exe):
            self.new_virtual_env.emit(1, "", "", "")
        self.new_virtual_env.emit(0, "", "", [])
        is_pip_preset = subprocess.run(
            [python_path, "-m", "pip", "--version"],
            capture_output=True,
            text=True,
        )
        if is_pip_preset.returncode == 1:
            # requires python>=3.4
            subprocess.run([python_path, "-m", "ensurepip", "--upgrade"])
        subprocess.run(
            [python_path, "-m", "venv", virtual_env_name],
            capture_output=True,
            text=True,
            check=False,
            cwd=directory,
        )
        result_venvs = subprocess.run(
            [find_env_exe, directory], capture_output=True, text=True
        )
        try:
            venvs = json.loads(result_venvs.stdout)
        except json.JSONDecodeError:
            venvs = []
        self.new_virtual_env.emit(1, directory, virtual_env_name, venvs)


class LibraryThreads(QObject):
    """
    A QObject subclass that manages a LibraryWorker in a separate QThread
    to perform various library-related operations (fetching details,
    managing virtual environments) concurrently without blocking the GUI thread.
    It acts as an interface, exposing signals to trigger operations in the worker
    thread and relaying the results back through its own signals.
    """

    new_virtual_env = pyqtSignal(int, str, str, list)
    details_with_virtual_envs = pyqtSignal(str, list, list)
    virtual_envs = pyqtSignal(list)
    details = pyqtSignal(list)
    get_details = pyqtSignal(str, str, str)
    get_virtual_envs = pyqtSignal(str, str)
    get_details_with_virtual_envs = pyqtSignal(str, str, str)
    create_virtual_env = pyqtSignal(str, str, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.thread_library = QThread()
        self.worker = LibraryWorker()
        self.worker.moveToThread(self.thread_library)
        self.worker.details_with_virtual_envs.connect(
            self.details_with_virtual_envs.emit
        )
        self.worker.virtual_envs.connect(self.virtual_envs.emit)
        self.worker.details.connect(self.details.emit)
        self.worker.new_virtual_env.connect(self.new_virtual_env.emit)
        self.thread_library.start()
        self.get_details.connect(self.worker.fetch_only_details)
        self.get_virtual_envs.connect(self.worker.fetch_virtual_envs)
        self.create_virtual_env.connect(self.worker.initialize_new_virtual_env)

    def emit_signal_for_details(self, directory, load_library_exe, venv_name):
        self.get_details.emit(directory, load_library_exe, venv_name)

    def emit_signal_for_virtual_envs(self, directory, load_library_exe):
        self.get_virtual_envs.emit(directory, load_library_exe)

    def emit_signal_for_details_with_virtual_envs(
        self, directory, load_library_exe, venv_name
    ):
        self.get_details_with_virtual_envs.emit(directory, load_library_exe, venv_name)

    def emit_create_virtual_env(self, directory, python_path, venv_name, find_env_exe):
        self.create_virtual_env.emit(directory, python_path, venv_name, find_env_exe)

    def quit(self):
        if self.thread_library.isRunning():
            self.thread_library.quit()
            self.thread_library.wait()
