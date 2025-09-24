from PyQt6.QtCore import QThread, pyqtSignal
from networkx.classes.digraph import DiGraph
from .utils import load_dependency_graph_data


class GNetworkLoader(QThread):
    """Thread class for loading and creating graph data in networkX"""

    graph_data = pyqtSignal(DiGraph)

    def __init__(self, file_path, parent=None):
        self.file_path = file_path
        super().__init__(parent)

    def run(self):
        G = load_dependency_graph_data(self.file_path)
        self.graph_data.emit(G)
