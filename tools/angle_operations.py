from math import atan, pi, acos, sqrt
from tools.distance_operations import square_length
from tools.vector_operations import vector_subtract, vector_dot
from tools.types import Coordinate, Vector
from tools.segment_operations import Segment

def __zero_segment(segment: Segment) -> tuple[Vector, Vector]:
    zeroed: Vector = {
        'x': segment.pt_2['x'] - segment.pt_1['x'],
        'y': segment.pt_2['y'] - segment.pt_1['y']
    }
    base: Vector = {
        'x': segment.pt_1['x'],
        'y': segment.pt_1['y']
    }

    return zeroed, base

def find_angle_caused_by_points(pt_1: Coordinate, pt_2: Coordinate) -> float:

    dx = pt_2['x'] - pt_1['x']
    dy = pt_2['y'] - pt_1['x']

    if dx == 0:
        return pi/2

    return atan(dy / dx)  

def find_angle_of_segment(s: Segment) -> float:
    return find_angle_caused_by_points(s.pt_1, s.pt_2)

def find_angle_of_vector(v: Vector) -> float:

    if v['x'] == 0:
        return pi/2

    return atan(v['y'] / v['x'])

def find_angle_between(u: Segment | Vector, v: Segment | Vector) -> float:

    vec_1: Vector
    vec_2: Vector

    if isinstance(u, Segment):
        vec_1 = __zero_segment(u)[0]
    else:
        vec_1 = u

    if isinstance(v, Segment):
        vec_2 = __zero_segment(v)[0]
    else:
        vec_2 = v

    return find_angle_bac(vec_1, {'x': 0, 'y': 0}, vec_2)

def angle_between_two_lines(u: Segment | Vector, v: Segment | Vector) -> float:

    vec_1: Vector
    vec_2: Vector

    if isinstance(u, Segment):
        vec_1 = __zero_segment(u)[0]
    else:
        vec_1 = u

    if isinstance(v, Segment):
        vec_2 = __zero_segment(v)[0]
    else:
        vec_2 = v

    if vec_1['x'] == 0 and vec_2['x'] == 0:
        return 0
    
    if vec_1['x'] == 0:
        return pi/2 - atan(abs(vec_2['y'] / vec_2['x']))

    if vec_2['x'] == 0:
        return pi/2 - atan(abs(vec_1['y'] / vec_1['x']))

    m1 = vec_1['y'] / vec_1['x']
    m2 = vec_2['y'] / vec_2['x']

    temp = abs((m1 - m2) / (1 + m1 * m2))

    return atan(temp)

def find_angle_bac(B: Coordinate, A: Coordinate, C: Coordinate) -> float:

    # Normalize everything
    arm_1 = vector_subtract(B, A)
    arm_2 = vector_subtract(C, A)

    dot = vector_dot(arm_1, arm_2)
    mag_1 = sqrt(square_length(arm_1))
    mag_2 = sqrt(square_length(arm_2))

    temp = dot / (mag_1 * mag_2)
    if temp > 1:
        temp = 1
    elif temp < -1:
        temp = -1

    return acos(temp)