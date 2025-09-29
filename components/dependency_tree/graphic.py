import pymunk
import os
from .physics import (
    DAMPING,
    ELASTICITY,
    FRICTION,
    LINEWIDTH,
    MASS,
    MAX_FORCE,
    NODE_RADIUS,
    REPULSION_STRENGTH,
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
)
from networkx.classes import DiGraph
from PyQt6.QtCore import QPointF, QTimer, Qt
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen


class NodeItem(QGraphicsEllipseItem):
    def __init__(self, text, radius, node_data=None):
        super().__init__(0, 0, radius * 2, radius * 2)

        self.label = QGraphicsTextItem(os.path.basename(text))
        self.label.setParentItem(self)
        self.label.setPos(0, -radius)
        font = QFont()
        font.setPointSize(20)
        self.label.setFont(font)

    def set_font_size(self, size):
        font = self.label.font()
        font.setPointSize(size)
        self.label.setFont(font)
        self.update()


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

        # Temprary colors
        self.dot_spacing = 200
        self.dot_radius = 20
        self.dot_color = QColor("#cccccc")  # A light gray
        self.background_color = QColor("#ffffff")  # White background

        # for panning
        self._last_pen_pos = None

        # for moving object
        self._moving_object = None

    def _update_simulation(self):
        """this will update the position of bodies and nodes"""

        self.space.step(TIMESTEP)

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

                force_magnitute = REPULSION_STRENGTH / r**2
                force_vector = direction_vector.normalized() * force_magnitute

                body_a.apply_force_at_local_point(force_vector, (0, 0))
                body_b.apply_force_at_local_point(-force_vector, (0, 0))

    def _create_bodies_and_nodes(self):
        """Create pymunk bodies and nodes for all the nodes in graphs"""

        if self.graph is None or self.graph_nodes_position is None:
            return

        for idx, node_id in enumerate(self.graph.nodes()):
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
            ellipse.setBrush(QBrush(QColor("lightblue")))
            ellipse.setToolTip(node_id)

            ellipse.setPen(QPen(Qt.GlobalColor.black))
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
            line.setPen(QPen(Qt.GlobalColor.black, LINEWIDTH))
            self._scene.addItem(line)
            self.edges[(u, v)] = line

    def _draw_background(
        self, painter, rect
    ) -> None:  # Can be implemented for preference look
        """This event handler is called whenever the widget needs to be repainted."""
        if painter is None:
            return

        # Set a solid background color first
        painter.fillRect(self.rect(), self.background_color)

        # Configure the painter for drawing dots
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)  # No outline for the dots
        painter.setBrush(self.dot_color)

        # Get the dimensions of the widget
        width = self.width()
        height = self.height()

        # Draw the grid of dots using nested loops
        for x in range(0, width, self.dot_spacing):
            for y in range(0, height, self.dot_spacing):
                # The painter draws relative to the widget's top-left corner
                painter.drawEllipse(x, y, self.dot_radius * 2, self.dot_radius * 2)
        painter.restore()
        painter.save()

    def set_graph_and_position(self, position: dict, graph: DiGraph):
        """Set's networkX graph to internal variable"""
        self.graph = graph
        self.graph_nodes_position = position
        self._create_bodies_and_nodes()
        self.timer.start(int(TIMESTEP * 100))

    def mouseMoveEvent(self, event) -> None:
        """Capture mouse position and convert it into pymunk vector and give the property of our mouse_body object"""

        if event is None:
            return
        pos = self.mapToScene(event.pos())
        point = pymunk.Vec2d(pos.x(), pos.y())
        self.mouse_body.position = point
        shape_info = self.space.point_query_nearest(point, 0, pymunk.ShapeFilter())

        if shape_info:
            if self.drag_object_or_screen["objects"] is False:
                self.setDragMode(QGraphicsView.DragMode.NoDrag)
                self.drag_object_or_screen = {"screen": False, "objects": True}

        else:
            if self.drag_object_or_screen["screen"] is False:
                self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
                self.drag_object_or_screen = {"screen": True, "objects": False}

        return super().mouseMoveEvent(event)

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
