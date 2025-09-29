from PyQt6.QtCore import QEvent, QModelIndex, QPoint, QRect, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPixmap
from PyQt6.QtWidgets import QStyle, QStyledItemDelegate
from ..widgets.tooltip import InteractiveToolTip
from .models import DataRole
from helpers.utils import resource_path


class PyPIitemDelegate(QStyledItemDelegate):
    """
    A custom QStyledItemDelegate for rendering PyPI package items in a QListView.

    This delegate provides a rich, interactive user interface for each library
    item. It customizes the painting to display the library's name, version,
    and an install status icon. It also handles mouse events to provide hover
    effects, show detailed tooltips with package information, and detect clicks
    on the install icon to trigger an installation process.

    Signals:
        install_clicked (QModelIndex): Emitted when the user clicks the install icon for an item.
    """

    install_clicked = pyqtSignal(QModelIndex)

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.config = config
        self.tooltip = InteractiveToolTip(parent)
        self.tooltip.set_object_name("PyPIitemDelegateTooltip")
        self._pressed_index = QModelIndex()
        self.color_hover = QColor(
            self.config.get("ui", {})
            .get("colors", {})
            .get("background", {})
            .get("hover", QColor(255, 255, 255))
        )
        self.text_color = QColor(
            self.config.get("ui", {})
            .get("colors", {})
            .get("text", {})
            .get("normal", QColor(0, 0, 0))
        )
        self.color_muted = QColor(
            self.config.get("ui", {})
            .get("colors", {})
            .get("text", {})
            .get("muted", QColor(128, 128, 128))
        )
        self.button_color = QColor(
            self.config.get("ui", {})
            .get("colors", {})
            .get("button", {})
            .get("install", QColor(0, 128, 255))
        )
        self.button_color_hover = QColor(
            self.config.get("ui", {})
            .get("colors", {})
            .get("button", {})
            .get("primaryHover", QColor(0, 128, 255))
        )
        self.padding = 10
        self._hovered_index = None
        self.rounded_corner_radius = (
            self.config.get("ui", {})
            .get("window", {})
            .get("installer", {})
            .get("roundedCornerRadius", 8)
        )

    def paint(self, painter: QPainter, option, index):  # type: ignore
        # Let the base class handle background colors for selection, hover, etc.
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = option.rect
        path = QPainterPath()
        path.addRoundedRect(
            rect.toRectF(), self.rounded_corner_radius, self.rounded_corner_radius
        )

        # Draw the hover effect
        if option.state & QStyle.StateFlag.State_MouseOver:
            # painter.fillRect(rect, self.color_hover)
            painter.fillPath(path, self.color_hover)
            if self._hovered_index != index:
                self._hovered_index = index

                if option.widget:
                    option.widget.update()
        else:
            if self._hovered_index == index:
                self._hovered_index = None

        item_data = index.data(DataRole)
        if not item_data:
            painter.restore()
            return

        # Item layout
        padding = 15
        padding_for_button = 15
        button_width = 20
        version_height = 20
        name_height = 20

        install_rect = QRect(
            rect.right() - button_width - padding_for_button,
            rect.top() + padding_for_button,
            button_width,
            button_width,
        )
        version_rect = QRect(
            rect.center().x(),
            rect.top() + padding,
            int(rect.width() / 2) - install_rect.width(),
            version_height,
        )
        name_rect = QRect(
            rect.left() + padding,
            rect.top() + padding,
            rect.width() - padding - version_rect.width(),
            name_height,
        )
        old_font = painter.font()
        font = painter.font()
        font.setItalic(True)
        painter.setFont(font)

        version_text = item_data.get("version", "...")
        # painter.setPen(self.color_muted)
        painter.setPen(self.color_muted)
        painter.drawText(
            version_rect,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            version_text,
        )

        painter.setFont(old_font)
        library_name = item_data.get("name", "")
        painter.setPen(self.text_color)
        painter.drawText(
            name_rect,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            library_name,
        )
        painter.restore()

        status_install = item_data.get("status", "install")
        mouse_pos = (
            option.widget.mapFromGlobal(option.widget.cursor().pos())
            if option.widget
            else QPoint(-1, -1)
        )
        is_hovering_install = install_rect.contains(mouse_pos)

        if status_install == "install":
            if is_hovering_install:
                self._draw_coloured_pixmap(
                    painter,
                    install_rect,
                    QPixmap(
                        resource_path(
                            self.config.get("paths", {})
                            .get("assets", {})
                            .get("images", {})
                            .get("install", "")
                        )
                    ),
                    self.button_color,
                    "#929292",
                )
            else:
                self._draw_coloured_pixmap(
                    painter,
                    install_rect,
                    QPixmap(
                        resource_path(
                            self.config.get("paths", {})
                            .get("assets", {})
                            .get("images", {})
                            .get("install", "")
                        )
                    ),
                    self.button_color,
                )
        elif status_install == "installed":
            self._draw_coloured_pixmap(
                painter,
                install_rect,
                QPixmap(
                    resource_path(
                        self.config.get("paths", {})
                        .get("assets", {})
                        .get("images", {})
                        .get("installed", "")
                    )
                ),
                self.button_color,
            )
        elif status_install == "installing":
            self._draw_coloured_pixmap(
                painter,
                install_rect,
                QPixmap(
                    resource_path(
                        self.config.get("paths", {})
                        .get("assets", {})
                        .get("images", {})
                        .get("installing", "")
                    )
                ),
                self.button_color,
            )
        elif status_install == "failed":
            self._draw_coloured_pixmap(
                painter,
                install_rect,
                QPixmap(
                    resource_path(
                        self.config.get("paths", {})
                        .get("assets", {})
                        .get("images", {})
                        .get("failed", "")
                    )
                ),
                self.button_color,
            )

    def helpEvent(self, event, view, option, index) -> bool:
        if event is None:
            return False

        if event.type() == QEvent.Type.ToolTip:  # type: ignore
            # Get the full data dictionary from the model
            item_data = index.data(DataRole)
            if not item_data or "description" not in item_data:
                self.tooltip.hide()
                return True

            if item_data:
                target = view.viewport()  # type: ignore
                self.tooltip.set_content(item_data["description"])
                self.tooltip.adjustSize()
                self.tooltip.schedule_show(
                    item_data["description"], event.globalPos() + QPoint(15, 15), target
                )  # type: ignore
                return True

        self.tooltip.hide()
        return super().helpEvent(event, view, option, index)

    def updateEditorGeometry(self, editor, option, index) -> None:
        return super().updateEditorGeometry(editor, option, index)

    def editorEvent(self, event, model, option, index: QModelIndex) -> bool:
        if event.type() == QEvent.Type.MouseMove:  # type: ignore
            if option.widget:
                option.widget.update(index)  # type: ignore

        item_data = index.data(DataRole)
        if item_data and item_data.get("status", "install") == "install":
            if event.type() == QEvent.Type.MouseButtonRelease:  # type: ignore
                padding = 10
                button_width = 30
                install_rect = QRect(
                    option.rect.right() - button_width - padding,
                    option.rect.top() + padding,
                    button_width,
                    button_width,
                )

                if install_rect.contains(event.pos()):  # type: ignore
                    self.install_clicked.emit(index)
                    return True
        return super().editorEvent(event, model, option, index)

    def sizeHint(self, option, index):
        # Use of item Hint, it's more than just a hint
        return QSize(0, 55)

    def _draw_coloured_pixmap(
        self,
        painter,
        rect: QRect,
        pixmap: QPixmap,
        color,
        bg_color="",
        mask_color: QColor = QColor(Qt.GlobalColor.transparent),
    ):
        """
        Draws a pixmap tinted with a specified color, optionally with a background.
        It uses the pixmap's mask to apply the color, making it appear as a colored icon.
        """
        mask = pixmap.createMaskFromColor(QColor(Qt.GlobalColor.transparent))
        painter.save()
        path = QPainterPath()
        path.addRoundedRect(
            QRect(
                rect.x() - 5, rect.y() - 5, rect.width() + 10, rect.height() + 10
            ).toRectF(),
            self.rounded_corner_radius,
            self.rounded_corner_radius,
        )
        if bg_color != "":
            painter.fillPath(path, QColor(bg_color))
        painter.setPen(color)
        painter.drawPixmap(rect, mask)
        painter.restore()
