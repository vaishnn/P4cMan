from random import random
from PyQt6.QtGui import QBrush, QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsScene,
    QGraphicsView,
)


class NodeItem(QGraphicsEllipseItem):
    def __init__(self, node_id, x, y, radius, text, node_data=None):
        super().__init__(-radius, radius, radius * 2, radius * 2)

        self.node_id = node_id
        self.setPos(x, y)

    def paint(
        self,
        painter,
        option,
        widget=...,
    ) -> None:
        return super().paint(painter, option, widget)


class NodeConnection(QGraphicsLineItem):
    def __init__(self, node1, node2, edge_data=None):
        self.node1 = node1
        self.node2 = node2


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

    def createBasicNodes(self):
        circle = QGraphicsEllipseItem(-10, -10, 10 * 2, 10 * 2)
        circle.setPos(random(), random())
        circle.setBrush(QBrush(QColor(255, 215, 0, 200)))
        circle.setPen(QPen(QColor(255, 255, 255, 150), 2))
        self._scene.addItem(circle)
        self.update()

    def set_graph(self, graph):
        """Set's networkX graph to internal variable"""
        self.graph = graph
        # self._draw_graph()

    def _draw_graph(self):
        if self.scene() is not None:
            self.scene().clear()  # type: ignore

        self.nodes.clear()
        self.edges.clear()
