from PyQt6.QtCore import QEvent, QPoint, QRect, QTimer, QUrl, Qt
from PyQt6.QtGui import QCursor, QDesktopServices
from PyQt6.QtWidgets import QFrame, QLabel, QScrollArea, QVBoxLayout, QWidget


class InteractiveToolTip(QFrame):
    """
    A Custom tooltip for interactibility, scrollability
    """

    def __init__(self, parent) -> None:
        super().__init__(parent)

        self.setWindowFlag(
            Qt.WindowType.ToolTip
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        self.setMaximumSize(800, 400)
        self.widget = QWidget(self)
        layout = QVBoxLayout(self.widget)
        layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_area = QScrollArea(self.widget)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll_area.setMaximumHeight(200)  # Prevents tooltip from being too tall
        self.content_label = QLabel()
        self.content_label.setContentsMargins(10, 10, 10, 10)
        self.content_label.setWordWrap(True)
        self.content_label.setTextFormat(Qt.TextFormat.RichText)
        self.content_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextBrowserInteraction
        )
        self.content_label.linkActivated.connect(self._handle_link_click)
        self.content_label.setStyleSheet(
            "background-color: transparent;"
        )  # Inherit background
        self.scroll_area.setWidget(self.content_label)
        layout.addWidget(self.scroll_area)
        self.widget.setLayout(layout)

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.setInterval(200)  # Hide delay in ms
        self._hide_timer.timeout.connect(self.hide)

        self._show_timer = QTimer(self)
        self._show_timer.setSingleShot(True)
        self._show_timer.setInterval(800)  # Show delay in ms
        self._show_timer.timeout.connect(self._show_at_cursor)

        self._target_widget = None

        self._polling_timer = QTimer(self)
        self._polling_timer.setInterval(250)  # Check cursor position every 250ms
        self._polling_timer.timeout.connect(self._check_cursor_position)

    def _handle_link_click(self, link: str):
        QDesktopServices.openUrl(QUrl(link))

    def schedule_show(self, content, pos, target_widget):
        """Starts a timer to show the tooltip, now tracking the target widget."""
        self.scroll_area.verticalScrollBar().setValue(0)  # type: ignore
        self._hide_timer.stop()
        self._pending_content = content
        self._pending_pos = pos
        self._target_widget = target_widget  # Store the target
        self._show_timer.start()

    def _execute_show(self):
        """This method is called by the show_timer's timeout."""
        if self._pending_content and self._pending_pos:
            self.set_content(self._pending_content)

            self.scroll_area.verticalScrollBar().setValue(0)  # type: ignore
            self.scroll_area.adjustSize()
            self.setFixedWidth(550)
            self.adjustSize()
            self.move(self._pending_pos)
            self.show()
            self._polling_timer.start()  # Start polling when shown

    def hide_now(self):
        """A robust hide method that stops all timers."""
        self.scroll_area.verticalScrollBar().setValue(0)  # type: ignore
        self._show_timer.stop()
        self._hide_timer.stop()
        self._polling_timer.stop()
        self.hide()

    def schedule_hide(self):
        """Cancels any pending show and starts a timer to hide the tooltip."""
        self._show_timer.stop()
        self._hide_timer.start()

    # --- ADD THE POLLING LOGIC ---

    def _check_cursor_position(self):
        """Periodically checks if the cursor is still over a valid area."""
        # This can happen if the target widget is destroyed
        if not self or not self._target_widget:
            self.hide_now()
            return

        cursor_pos = QCursor.pos()

        # Get the target widget's area in global screen coordinates
        target_rect = self._target_widget.rect()
        global_target_rect = QRect(
            self._target_widget.mapToGlobal(target_rect.topLeft()), target_rect.size()
        )

        # Hide if the cursor is outside BOTH the tooltip and its target widget
        if not self.geometry().contains(cursor_pos) and not global_target_rect.contains(
            cursor_pos
        ):
            self.hide_now()

    def set_object_name(self, name):
        self.scroll_area.setObjectName(f"{name}ScrollArea")

    def set_content(self, html: str):
        self.content_label.setText(html)

    def install_on(self, widget):
        """Installs an event filter on the target widget to trigger the tooltip."""
        if not widget:
            return
        try:
            widget.installEventFilter(self)
        except Exception:
            widget.installSceneEventFilter(widget)
        self._target_widget = widget

    def eventFilter(self, watched_obj, event) -> bool:  # type: ignore
        """Filters events from the watched widget."""
        if watched_obj == self._target_widget:
            if event.type() == QEvent.Type.Enter:
                self._hide_timer.stop()
                self._show_timer.start()
            elif event.type() == QEvent.Type.Leave:
                self._show_timer.stop()
                self._hide_timer.start()
        return super().eventFilter(watched_obj, event)

    def _show_at_cursor(self):
        """Shows the tooltip at the current cursor position."""
        if not self._target_widget:
            return

        cursor_pos = self._target_widget.cursor().pos()
        # Adjust position to be below and to the right of the cursor
        self.move(cursor_pos + QPoint(15, 15))
        self.show()
        # Ensure the tooltip resizes to its content
        self.adjustSize()
        self._polling_timer.start()

    def enterEvent(self, event) -> None:
        """When the mouse enters the tooltip itself, cancel any pending hide action."""
        self._hide_timer.stop()
        self._polling_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, a0):
        """When the mouse leaves the tooltip, start the hide timer."""
        self._hide_timer.start()
        super().leaveEvent(a0)
