import pymunk

NODE_RADIUS = 20
PADDING = 50
REST_LENGTH = 500
STIFFNESS = 20
DAMPING = 5
SPRING_CONSTANT = 1000
SPACE_DAMPING = 0.8
ATTRACTION_FORCE = 500
TIMESTEP = 1 / 60
MAX_FORCE = 50000.0
VELOCITY_LIMIT = 0.1

LAYOUT_ITERATION = 1000
LAYOUT_SCALE = 1000
SPRING_ITERATION = 50


def dragged_body_velocity_func(body, gravity, damping, dt):
    """Applying near to infinite damping"""
    pymunk.Body.update_velocity(body, gravity, damping, dt)
    body.velocity *= 0.0005


def neighbour_body_velocity_func(body, gravity, damping, dt):
    """Applying some amount of damping"""
    pymunk.Body.update_velocity(body, gravity, damping, dt)
    body.velocity *= 0.050
