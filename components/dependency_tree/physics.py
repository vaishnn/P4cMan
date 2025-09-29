import pymunk

NODE_RADIUS = 50
PADDING = 50
REST_LENGTH = 100
STIFFNESS = 0.8
DAMPING = 0.2
SPRING_CONSTANT = 10000
SPACE_DAMPING = 0.1
ATTRACTION_FORCE = 500
TIMESTEP = 1 / 60
MAX_FORCE = 50000.0
VELOCITY_LIMIT = 0.1

LAYOUT_ITERATION = 1000
LAYOUT_SCALE = 1000
SPRING_ITERATION = 50

FRICTION = 0.9
ELASTICITY = 0.8
MASS = 1.0

LINEWIDTH = 3


def dragged_body_velocity_func(body, gravity, damping, dt):
    """Applying near to infinite damping"""
    pymunk.Body.update_velocity(body, gravity, damping, dt)
    body.velocity *= 0.0005


def neighbour_body_velocity_func(body, gravity, damping, dt):
    """Applying some amount of damping"""
    pymunk.Body.update_velocity(body, gravity, damping, dt)
    body.velocity *= 0.050


def repulsion_handler(arbiter, space, data):
    body_a = arbiter.shapes[0].body
    body_b = arbiter.shapes[1].body

    # Calculate the vector from body_a to body_b
    repulsion_vector = body_b.position - body_a.position

    # Normalize the vector
    distance = repulsion_vector.length
    if distance > 0:
        repulsion_direction = repulsion_vector / distance
    else:
        repulsion_direction = pymunk.Vec2d(1, 0)

    # Repuslion Strenght
    repulsion_strength = 50000

    impulse_magnitude = repulsion_strength / distance**2

    body_a.apply_impulse_at_local_point(repulsion_direction * impulse_magnitude, (0, 0))
    body_b.apply_impulse_at_local_point(
        -repulsion_direction * impulse_magnitude, (0, 0)
    )

    return True
