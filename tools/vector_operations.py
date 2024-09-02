from math import floor, isnan
from tools.types import Coordinate, Vector

def vector_dot(u: Vector, v: Vector) -> float:
    return u['x'] * v['x'] + u['y'] * v['y']

def vector_multiply(v: Vector, a: float) -> Vector:
    return {
        'x': a * v['x'],
        'y': a * v['y']
    }

def vector_subtract(u: Vector, v: Vector) -> Vector:
    """
    Subtract v from u
    """
    return {
        'x': u['x'] - v['x'],
        'y': u['y'] - v['y']
    }

def vector_add(*args: Vector) -> Vector:
    """
    Add vectors
    """
    x = sum([v['x'] for v in args])
    y = sum([v['y'] for v in args])
    return {
        'x': x,
        'y': y
    }

def vector_flip(v: Vector) -> Vector:
    return {
        'x': -v['x'],
        'y': -v['y']
    }

def vector_project_from(project_onto: Vector, project_me: Coordinate) -> Vector:
    """
    Find the projection of v onto u.
    POINT onto VECTOR for your use case
    """
    numer = vector_dot(project_onto, project_me)
    denom = vector_dot(project_onto, project_onto)

    expr = numer / denom

    w = vector_multiply(project_onto, expr)

    return w

def int_ify_vector(v: Vector) -> Vector:
    return {
        'x': floor(v['x']),
        'y': floor(v['y'])
    }

def check_is_NaN(v: Vector) -> bool:
    return isnan(v['x']) or isnan(v['y'])

def check_equal(u: Vector, v: Vector) -> bool:
    return u['x'] == v['x'] and u['y'] == v['y']