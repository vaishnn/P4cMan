from PyQt6.QtCore import QThread, pyqtSignal
from networkx.classes.digraph import DiGraph
from .utils import load_dependency_graph_data


class GNetworkLoader(QThread):
    """Thread class for loading and creating graph data in networkX"""

    graph_data = pyqtSignal(DiGraph, dict)

    def __init__(self, file_path: str, project_folder: str, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.project_folder = project_folder

    def run(self):
        G, layout = load_dependency_graph_data(self.file_path, self.project_folder)
        self.graph_data.emit(G, layout)
