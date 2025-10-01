import typing
from typing_extensions import Dict, List
from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, pyqtSignal


class Animate:
    """
    A better approach for animating stuff and then cleaning itself
    Args:
        self: class's self scope
        object_to_be_animated: The Object to animate.
        property_to_be_animated: The byte-string name of the property to animate (e.g., b'maximumHeight').
        final_dimension: The final value of the animated property.
        initial_dimension: The starting value of the animated property.
        visibility: If True, the object is visible after the animation; otherwise, it's hidden.
        name: An attribute name to store the QPropertyAnimation instance (e.g., "hide_search_bar").
        animation_type: The easing curve to use for the animation.
        duration: The duration of the animation in milliseconds.
        before: To commit visibility before or after
        continuous: If you want the animation to be looping
    """

    finished = pyqtSignal()

    def __init__(
        self,
        instance: typing.Any,
        object: List[typing.Any] | typing.Any,
        properties: Dict[typing.Any, bytes] | List[bytes] | bytes,
        final_dimension: Dict[typing.Any, typing.Any] | List[typing.Any] | typing.Any,
        initial_dimension: Dict[typing.Any, typing.Any] | typing.Any,
        name: Dict[typing.Any, str] | List[str] | str | None,
        visibility: Dict[typing.Any, bool] | bool = True,
        start: Dict[typing.Any, bool] | bool = True,
        animation_type: List[QEasingCurve.Type]
        | QEasingCurve.Type = QEasingCurve.Type.InQuad,
        duration: List[int] | int = 500,
        before: List[bool] | bool = False,
        continuous: List[bool] | bool = False,
    ):
        self.instance = instance
        self.object = object
        self.properties = properties
        self.final_dimension = final_dimension
        self.initial_dimension = initial_dimension
        self.name = name
        self.visibility = visibility
        self.start = start
        self.animation_type = animation_type
        self.duration = duration
        self.before = before
        self.continuous = continuous
        self.animation = None

        if self.start:
            pass

    def animate(self):
        pass


def animate_object(
    self,
    object_to_be_animated,
    property_to_be_animated: bytes,
    final_dimension,
    initial_dimension,
    visibility: bool,
    name: str,
    animation_type: QEasingCurve.Type = QEasingCurve.Type.InQuad,
    duration: int = 500,
    before: bool = False,
    continuous: bool = False,
):
    """
    Creates and starts a QPropertyAnimation for a given object property.

    Args:
        self: class's self scope
        object_to_be_animated: The Object to animate.
        property_to_be_animated: The byte-string name of the property to animate (e.g., b'maximumHeight').
        final_dimension: The final value of the animated property.
        initial_dimension: The starting value of the animated property.
        visibility: If True, the object is visible after the animation; otherwise, it's hidden.
        name: An attribute name to store the QPropertyAnimation instance (e.g., "hide_search_bar").
        animation_type: The easing curve to use for the animation.
        duration: The duration of the animation in milliseconds.
        before: To commit visibility before or after
    """
    if before:  # this is for when appearing
        object_to_be_animated.setVisible(visibility)
    animation = QPropertyAnimation(object_to_be_animated, property_to_be_animated)
    setattr(self, name, animation)
    animation.setDuration(duration)
    animation.setStartValue(initial_dimension)
    animation.setEndValue(final_dimension)
    if continuous:
        animation.setLoopCount(-1)
    else:
        animation.setLoopCount(1)
    animation.setEasingCurve(animation_type)
    animation.finished.connect(
        lambda: (object_to_be_animated.setVisible(visibility), delattr(self, name))
    )
    animation.start()
