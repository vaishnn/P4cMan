from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import QGraphicsScene, QGraphicsView


class GraphWidget(QGraphicsView):
    """The main widget making the graph"""
    def __init__(self):
        super().__init__()
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        self.setObjectName("GraphWidget")

        self.nodes = {}
        self.edges = []

    def set_graph(self, graph):
        """Set's networkX graph to internal variable"""
        self.graph = graph
        # self._draw_graph()

    def _draw_graph(self):
        if self.scene() is not None:
            self.scene().clear() #type: ignore

        self.nodes.clear()
        self.edges.clear()
