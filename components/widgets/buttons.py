from PyQt6.QtGui import QIcon, QPainter
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtCore import QRectF, QSize, QEasingCurve, QPropertyAnimation, pyqtProperty #type: ignore


class RotatingPushButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._angle = 0
        self.animation_prop = False

        # Initialize animation once
        self.animation = QPropertyAnimation(self, b"angle")
        self.animation.setDuration(2000)
        self.animation.setEasingCurve(QEasingCurve.Type.Linear)

    def get_angle(self):
        return self._angle

    def set_angle(self, value):
        self._angle = value
        self.update()  # This triggers paintEvent

    # Declare the property for QPropertyAnimation
    angle = pyqtProperty(float, get_angle, set_angle)

    def enterEvent(self, event):
        """Start rotation animation when mouse enters the button"""
        self.animation_prop = True

        # Stop any existing animation
        self.animation.stop()

        # Set up continuous rotation
        self.animation.setStartValue(self._angle)
        self.animation.setEndValue(self._angle + 360)
        self.animation.setLoopCount(-1)  # Infinite loop
        self.animation.start()

        super().enterEvent(event)

    def leaveEvent(self, a0):
        """Stop rotation and return to 0 degrees when mouse leaves"""
        # Stop the continuous animation
        self.animation.stop()

        # Calculate the shortest path back to 0
        current_angle = self._angle % 360
        if current_angle > 180:
            target_angle = current_angle - 360
        else:
            target_angle = 0

        # Animate back to 0 degrees
        self.animation.setStartValue(current_angle)
        self.animation.setEndValue(target_angle)
        self.animation.setLoopCount(1)  # Single animation
        self.animation.setDuration(500)  # Faster return

        # Connect to reset when animation finishes
        self.animation.finished.connect(self._reset_animation)
        self.animation.start()

        super().leaveEvent(a0)

    def _reset_animation(self):
        """Reset animation properties and angle after leave animation completes"""
        self._angle = 0
        self.animation_prop = False
        self.animation.setDuration(2000)  # Reset to original duration

        # Disconnect the signal to avoid multiple connections
        try:
            self.animation.finished.disconnect(self._reset_animation)
        except TypeError:
            pass  # Signal wasn't connected

        self.update()  # Final repaint

    def paintEvent(self, a0):
        painter = QPainter(self)
        painter.setRenderHints(
            QPainter.RenderHint.LosslessImageRendering |
            QPainter.RenderHint.Antialiasing
        )

        icon_pixmap = self.icon().pixmap(QSize(10, 10))
        if icon_pixmap.isNull():
            return  # Don't paint if no icon

        painter.save()

        if self.animation_prop and self._angle != 0:
            center = QRectF(self.rect()).center()
            painter.translate(center)
            painter.rotate(self._angle)  # Use the animated angle
            painter.translate(-center)

        icon_rect = QRectF(icon_pixmap.rect())
        icon_rect.moveCenter(QRectF(self.rect()).center())
        painter.drawPixmap(icon_rect, icon_pixmap, QRectF(icon_pixmap.rect()))
        painter.restore()



class HoverIconButton(QPushButton):
    """
    A custom QPushButton that shows an icon on hover and controls its size.
    """
    def __init__(self, icon_path, size=6, parent=None):
        super().__init__(parent)
        self._icon_path = icon_path
        self._icon = QIcon(self._icon_path)
        self._icon_size = QSize(size, size)

    def enterEvent(self, event):
        super().enterEvent(event)
        self.setIcon(self._icon)
        self.setIconSize(self._icon_size)

    def leaveEvent(self, event): # type: ignore
        super().leaveEvent(event)
        self.setIcon(QIcon()) # Set an empty icon to hide it
