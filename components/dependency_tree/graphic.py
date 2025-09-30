from networkx.classes.digraph import DiGraph
import pymunk
import os
import networkx as nx

from components.dependency_tree.controls import ControlPanel
from components.dependency_tree.threads import GNetworkLoader
from helpers.utils import resource_path
from .physics import (
    DAMPING,
    ELASTICITY,
    FRICTION,
    LINEWIDTH,
    MASS,
    MAX_FORCE,
    NODE_RADIUS,
    SPACE_DAMPING,
    STIFFNESS,
    TIMESTEP,
    dragged_body_velocity_func,
    neighbour_body_velocity_func,
)
from PyQt6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QGroupBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import QPointF, QRectF, QSize, QTimer, Qt
from PyQt6.QtGui import QBrush, QColor, QFont, QIcon, QPainter, QPen


class NodeItem(QGraphicsEllipseItem):
    """Custom ellipse Item for nodes of our dependency graph"""

    def __init__(self, text, radius, node_data=None):
        super().__init__(0, 0, radius * 2, radius * 2)

        self.setAcceptHoverEvents(True)

        self.label = QGraphicsTextItem(os.path.basename(text))
        font = QFont()
        font.setPointSize(80)
        self.label.setFont(font)
        self.label.setParentItem(self)
        self.label.setPos(
            -self.label.boundingRect().width() / 2 + radius,
            -radius - 50,
        )

        self.tooltip_timer = QTimer()
        self.tooltip_timer.setSingleShot(True)
        self.tooltip_timer.setInterval(500)
        self.tooltip_timer.timeout.connect(self._show_tooltip)

        # self.tooltip = SomeToolTipClass

    def set_font_size(self, size):
        font = self.label.font()
        font.setPointSize(size)
        self.label.setFont(font)
        self.update()

    def _show_tooltip(self):
        pass

    def hoverEnterEvent(self, event):
        """Display some sort of tooltip"""
        print("Entered Hover")
        self.tooltip_timer.start()
        return super().hoverEnterEvent(event)

    def mouseMoveEvent(self, event) -> None:
        print(10)
        return super().mouseMoveEvent(event)

    def hoverLeaveEvent(self, event):
        """if mouse leaves the object stop the timer"""
        print("Leaves Hover")
        self.tooltip_timer.stop()
        return super().hoverLeaveEvent(event)


class NodeConnection(QGraphicsLineItem):
    def __init__(self, node1, node2, edge_data=None):
        self.node1 = node1
        self.node2 = node2


class GraphWidget(QGraphicsView):
    """The main widget making the graph"""

    def __init__(self, parent, config):
        super().__init__()
        self._scene = QGraphicsScene(self)
        self._parent = parent
        self.setScene(self._scene)

        self.config = config
        # self.view = QGraphicsView(self._scene, self)
        # self.view.scale(0.6, 0.6)
        self.scale(0.1, 0.1)

        # Enabling zoom and pan
        self.drag_object_or_screen = {"screen": True, "objects": False}
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

        # Graphic setup
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        # hiding the scrollbar
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._parameters()
        self._setup_control_bar()

    def _parameters(self):
        """for initilizating all the parameters"""

        # Initializing Graph and Position to None
        self.graph = None
        self.graph_nodes_position = None

        # physics pymunk basic setup, can be more complex
        self.space = pymunk.Space()
        self.space.gravity = (0, 0)
        self.space.damping = SPACE_DAMPING

        self.mouse_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        self.mouse_joint = None

        # Maps node_id -> QGraphicEllipseItem
        self.nodes = {}

        # Maps node_id -> pymunk.Body
        self.bodies = {}

        # Maps (body1, body2) -> line
        self.edges = {}

        # Saving the list of modified bodies
        self.modified_bodies = []
        self.original_velocities_functions = {}

        # timer for updating the simulation
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_simulation)

        # for panning
        self._last_pen_pos = None

        # for moving object
        self._moving_object = None

        # for a large pannable scene
        very_large_rect = QRectF(-100000, -100000, 200000, 200000)
        self._scene.setSceneRect(very_large_rect)

        # Object for creating graph
        self.graph_loader = None

        # heighlighted nodes when someone hovers
        self.body_under_mouse = None
        self.heighlighed_nodes = set()
        self.heighlighed_edges = set()

        # custom attributes set by user
        self.hidden_nodes = {}
        self.color_of_nodes = {}

        # timers for color changes
        self.color_change_timer = QTimer()
        self.color_change_timer.setSingleShot(True)
        self.color_change_timer.setInterval(100)
        self.color_change_timer.timeout.connect(self._color_nodes)

        self.color_to_normal_timer = QTimer()
        self.color_to_normal_timer.setSingleShot(True)
        self.color_to_normal_timer.setInterval(200)
        self.color_to_normal_timer.timeout.connect(self._clear_color)

    def _reset_layout(self):
        pass

    def resizeEvent(self, event):
        if hasattr(self, "control_widget"):
            self.control_widget.setGeometry(
                self.frameGeometry().width() - 50, 10, 40, 90
            )

        return super().resizeEvent(event)

    def _setup_control_bar(self):
        # Controls for graph
        self.control_widget = QWidget(self)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # Setting for opening setting panel
        pane_box = QGroupBox()
        pane_box.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(pane_box)
        self.control_widget.setLayout(layout)
        self.control_widget.setGeometry(self.frameGeometry().width() - 50, 10, 40, 90)

        self.setting_button = QPushButton()
        self.setting_button.setIcon(
            QIcon(
                resource_path(
                    self.config.get("paths", {})
                    .get("assets", {})
                    .get("images", {})
                    .get("settings", "")
                )
            )
        )
        sub_layout = QVBoxLayout()

        # reset layout for resetting positions and position of current view
        self.reset_layout_button = QPushButton()
        self.reset_layout_button.setIcon(
            QIcon(
                resource_path(
                    self.config.get("paths", {})
                    .get("assets", {})
                    .get("images", {})
                    .get("reset", "")
                )
            )
        )
        self.setting_button.setIconSize(QSize(24, 24))
        self.reset_layout_button.setIconSize(QSize(24, 24))

        sub_layout.addWidget(self.setting_button)
        sub_layout.addWidget(self.reset_layout_button)
        sub_layout.setContentsMargins(0, 0, 0, 0)
        sub_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pane_box.setLayout(sub_layout)

        self.setting_button.setObjectName("graph_setting_button")
        self.reset_layout_button.setObjectName("graph_reset_layout_button")
        # self.controls = ControlPanel(parent=self)
        # self.controls.reset_signal.connect(self)

    def _changing_layout(self, layout_name):
        pass

    def _home(self):
        pass

    def _update_simulation(self):
        """this will update the position of bodies and nodes"""

        self.space.step(TIMESTEP)

        if self.nodes == {} or self.edges == {} or self.bodies == {}:
            return

        for node_id, ellipse in self.nodes.items():
            body = self.bodies[node_id]
            pos = QPointF(body.position.x - NODE_RADIUS, body.position.y - NODE_RADIUS)
            ellipse.setPos(pos)

        for (u, v), line in self.edges.items():
            pos1 = self.bodies[u].position
            pos2 = self.bodies[v].position
            line.setLine(pos1.x, pos1.y, pos2.x, pos2.y)

        # self._repulsion_strength()

    # This will have a time complexity of O(N^2), so might need to find a better way to have repulsion
    def _repulsion_strength(self):
        for body_a in self.bodies.values():
            for body_b in self.bodies.values():
                if body_a == body_b:
                    continue

                direction_vector = body_a.position - body_b.position
                r = direction_vector.length
                if r < 1:
                    r = 1

                force_magnitute = 50000 / r**2
                force_vector = direction_vector.normalized() * force_magnitute

                body_a.apply_force_at_local_point(force_vector, (0, 0))
                body_b.apply_force_at_local_point(-force_vector, (0, 0))

    def get_graph(self, file_path, project_folder):
        self.graph_loader = GNetworkLoader(file_path, project_folder)
        self.graph_loader.graph_data.connect(self._set_graph_data)
        self.graph_loader.start()
        self.graph_loader.finished.connect(self.graph_loader.deleteLater)

    def _clear_scene(self):
        """Clear the scene before creating a new phone"""

        self._scene.clear()

        # clear the dictionaries
        self.nodes.clear()
        self.bodies.clear()
        self.edges.clear()

        self.heighlighed_nodes.clear()

        # Remove all the shapes
        for shape in list(self.space.shapes):
            self.space.remove(shape)

        # Remove all constraints
        for constraint in list(self.space.constraints):
            self.space.remove(constraint)

        # Remove all bodies
        for body in list(self.space.bodies):
            self.space.remove(body)

    def _set_graph_data(self, G, node):
        self._clear_scene()
        self.graph = G
        self.dependency_node = node
        self._generate_shell_layout()
        self._create_bodies_and_nodes()
        self.timer.start(int(TIMESTEP * 100))

    def _reset_graph_layout(self):
        pass

    def _generate_shell_layout(self):
        """Generate a concentric shell layout"""
        if self.graph is None:
            return {}

        levels = nx.shortest_path_length(self.graph, source=self.dependency_node.path)
        nodes_by_level = {}
        for node_id, level in levels.items():
            if level not in nodes_by_level:
                nodes_by_level[level] = []
            nodes_by_level[level].append(node_id)

        # This is the list we pass to networkx
        shell_list = [nodes for level, nodes in sorted(nodes_by_level.items())]
        self.graph_nodes_position = nx.shell_layout(
            self.graph, nlist=shell_list, scale=5000
        )

    def _create_bodies_and_nodes(self):
        """Create pymunk bodies and nodes for all the nodes in graphs"""

        if self.graph is None or self.graph_nodes_position is None:
            return

        for node_id, attributes in self.graph.nodes(data=True):
            # Can be any number but then all physics will be changed
            mass = MASS
            moment = pymunk.moment_for_circle(mass, 0, NODE_RADIUS)
            body = pymunk.Body(mass, moment)
            body.position = tuple(self.graph_nodes_position[node_id])
            shape = pymunk.Circle(body, NODE_RADIUS)
            shape.friction = FRICTION

            shape.elasticity = ELASTICITY
            shape.node_id = node_id

            self.space.add(body, shape)

            self.original_velocities_functions[body] = body.velocity_func

            ellipse = NodeItem(node_id, NODE_RADIUS)
            # ellipse = QGraphicsEllipseItem(0, 0, 2 * NODE_RADIUS, 2 * NODE_RADIUS)
            ellipse.setBrush(QBrush(QColor("#bfbfbf")))
            ellipse.setToolTip(node_id)

            ellipse.setPen(QPen(Qt.GlobalColor.white))
            self._scene.addItem(ellipse)
            ellipse.setPos(body.position.x - NODE_RADIUS, body.position.y - NODE_RADIUS)
            ellipse.setZValue(1)
            self.nodes[node_id] = ellipse
            self.bodies[node_id] = body

        for u, v in self.graph.edges():
            body1 = self.bodies[u]
            body2 = self.bodies[v]
            distance = (body1.position - body2.position).length
            spring = pymunk.DampedSpring(
                body1,
                body2,
                anchor_a=(0, 0),
                anchor_b=(0, 0),
                rest_length=distance,
                stiffness=STIFFNESS,
                damping=DAMPING,
            )

            self.space.add(spring)
            line = QGraphicsLineItem()
            line.setPen(QPen(QColor("#42484c"), LINEWIDTH))
            self._scene.addItem(line)
            self.edges[(u, v)] = line

    def set_graph_and_position(self, position: dict, graph: DiGraph):
        """Set's networkX graph to internal variable"""
        self.graph = graph
        self.graph_nodes_position = position
        self._create_bodies_and_nodes()
        self.timer.start(int(TIMESTEP * 100))

    def _glow_up_nodes(self):
        pass

    def _hide_nodes(self):
        pass

    def mouseMoveEvent(self, event) -> None:
        """Capture mouse position and convert it into pymunk vector and give the property of our mouse_body object"""

        if event is None or self.graph is None:
            return
        pos = self.mapToScene(event.pos())
        point = pymunk.Vec2d(pos.x(), pos.y())
        self.mouse_body.position = point
        shape_info = self.space.point_query_nearest(point, 0, pymunk.ShapeFilter())

        if shape_info:
            # for converting pan to moving object
            if self.drag_object_or_screen["objects"] is False:
                self.setDragMode(QGraphicsView.DragMode.NoDrag)
                self.drag_object_or_screen = {"screen": False, "objects": True}

            # Heighlight that node and other
            if self.body_under_mouse is None:
                self.body_under_mouse = [shape_info.shape.body, "hover"]
                self.color_change_timer.start()

            elif self.body_under_mouse[1] != "dragged":
                self.body_under_mouse = [shape_info.shape.body, "hover"]
                self.color_change_timer.start()

        else:
            if self.drag_object_or_screen["screen"] is False:
                self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
                self.drag_object_or_screen = {"screen": True, "objects": False}

            if self.body_under_mouse:
                if self.body_under_mouse[1] != "dragged":
                    self.color_to_normal_timer.start()
                    self.body_under_mouse = None

        return super().mouseMoveEvent(event)

    def _color_nodes(self):
        if self.graph is None or self.body_under_mouse is None:
            return

        idx_of_body = {j: i for i, j in self.bodies.items()}[self.body_under_mouse[0]]
        connected_nodes = self.graph.neighbors(idx_of_body)

        # Change the color to a little brighter for node and the connected neighbors
        ellipse = self.nodes[idx_of_body]
        ellipse: QGraphicsEllipseItem
        ellipse.setBrush(QBrush(Qt.GlobalColor.red))
        self.heighlighed_nodes.add(idx_of_body)
        for connected_node in connected_nodes:
            connected_edge = self.edges[(idx_of_body, connected_node)]
            connected_edge: QGraphicsLineItem
            connected_edge.setPen(QPen(Qt.GlobalColor.red, LINEWIDTH + 2))
            self.nodes[connected_node].setBrush(QBrush(Qt.GlobalColor.red))
            self.heighlighed_nodes.add(connected_node)
            self.heighlighed_edges.add(connected_edge)

        for node, ellipse in self.nodes.items():
            if node not in self.heighlighed_nodes:
                ellipse.setOpacity(0.1)
        for nodes, line in self.edges.items():
            if line not in self.heighlighed_edges:
                line.setOpacity(0.1)

    def _clear_color(self):
        if self.heighlighed_nodes:
            for heighlighted_node in self.nodes:
                ellipse = self.nodes[heighlighted_node]
                ellipse.setOpacity(1.0)
                ellipse: QGraphicsEllipseItem
                ellipse.setBrush(QBrush(QColor("#bfbfbf")))
            self.heighlighed_nodes.clear()

        if self.edges:
            for heighlighted_edge in self.edges.values():
                heighlighted_edge.setOpacity(1.0)
                heighlighted_edge.setPen(QPen(QColor("#42484c"), LINEWIDTH))

            self.heighlighed_edges.clear()

    def mousePressEvent(self, event) -> None:
        """Move the object if the tapped place has any nodes"""

        if event is None:
            return

        if self.graph is None:
            return

        if event.button() == Qt.MouseButton.LeftButton:
            # Capture the pos and convert it to global widget coordinates
            pos = self.mapToScene(event.pos())
            self.mouse_body.position = pymunk.Vec2d(pos.x(), pos.y())
            point = pymunk.Vec2d(pos.x(), pos.y())
            shape_info = self.space.point_query_nearest(point, 0, pymunk.ShapeFilter())

            if shape_info is not None:
                dragged_body = shape_info.shape.body
                self.body_under_mouse = [dragged_body, "dragged"]
                dragged_node_id = shape_info.shape.node_id

                self._moving_object = (dragged_body, dragged_node_id)

                if dragged_body is None:
                    return

                # Apply near to infinite damping to the dragged body
                self.modified_bodies.append(dragged_body)
                dragged_body.velocity_func = dragged_body_velocity_func

                # apply damping to the neighbours
                for neighbour_id in self.graph.neighbors(dragged_node_id):
                    neighbour = self.bodies[neighbour_id]
                    if neighbour not in self.modified_bodies:
                        self.modified_bodies.append(neighbour)
                        neighbour.velocity_func = neighbour_body_velocity_func

                self.mouse_joint = pymunk.PivotJoint(
                    self.mouse_body, dragged_body, (0, 0), (0, 0)
                )
                self.mouse_joint.max_force = MAX_FORCE
                # self.mouse_joint.error_bias = pow(0.5, 60)
                # self.mouse_joint.max_bias = 200
                self.space.add(self.mouse_joint)

        return super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        """Clean up after animating"""
        if event is None:
            return

        if event.button() == Qt.MouseButton.LeftButton:
            # Check if the mouse joint exists, which means something was moved
            if self.mouse_joint:
                self.space.remove(self.mouse_joint)
                self.mouse_joint = None

            self._clear_modified_bodies()

        self._moving_object = None
        if self.body_under_mouse:
            self.color_to_normal_timer.start()
            self.body_under_mouse = None

        return super().mouseReleaseEvent(event)

    def _clear_modified_bodies(self):
        """Clean up slowly"""

        if self.modified_bodies != []:
            for body in self.modified_bodies:
                body: pymunk.Body
                body.velocity_func = self.original_velocities_functions[body]
                # body.activate()
            self.modified_bodies.clear()

    def wheelEvent(self, event):
        """For Zooming in and out"""
        if event is None:
            return
        zoom_in_factor = 1.10
        zoom_out_factor = 1 / zoom_in_factor

        # save the old scene pos
        old_pos = self.mapToScene(event.position().toPoint())

        # Zoom
        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor

        new_pos = self.scale(zoom_factor, zoom_factor)

        # Get the new position
        new_pos = self.mapToScene(event.position().toPoint())

        # Move Scene to old position
        delta = new_pos - old_pos
        self.translate(delta.x(), delta.y())
