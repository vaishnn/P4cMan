from PyQt6.QtCore import QThread, pyqtSignal
from networkx.classes.digraph import DiGraph

from components.dependency_tree.transversal import DependencyNode
from .utils import load_dependency_graph_data


class GNetworkLoader(QThread):
    """Thread class for loading and creating graph data in networkX"""

    graph_data = pyqtSignal(DiGraph, DependencyNode)

    def __init__(self, file_path: str, project_folder: str, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.project_folder = project_folder

    def run(self):
        G, node = load_dependency_graph_data(self.file_path, self.project_folder)
        self.graph_data.emit(G, node)
