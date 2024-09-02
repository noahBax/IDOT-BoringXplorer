from xplorer_tools.segment_operations import Segment
from xplorer_tools.types import Coordinate, Vector

def find_slope(vector: Segment | Vector) -> float:
    """
    This function assumes that the line is not vertical. Perform a check before
    calling
    """

    if isinstance(vector, Segment):
        return (vector.pt_1['y'] - vector.pt_2['y']) / (vector.pt_1['x'] - vector.pt_2['x'])

    return vector['y'] / vector['x']

def check_valid_slope(v: Segment | Vector) -> bool:

    if not isinstance(v, Segment):
        return v['x'] != 0
    
    return v.pt_2['x'] - v.pt_1['x'] != 0

def square_distance(p1: Coordinate, p2: Coordinate = { 'x': 0, 'y': 0 }) -> float:
    return (p1['x'] - p2['x']) ** 2 + (p1['y'] - p2['y']) ** 2

def square_length(vector: Vector | Segment) -> float:
    if isinstance(vector, Segment):
        return vector.square_length

    return vector['x'] ** 2 + vector['y'] ** 2

def check_points_equivalent(pt_1: Coordinate, pt_2: Coordinate) -> bool:
    return abs(pt_1['x'] - pt_2['x']) < 0.0005 and abs(pt_1['y'] - pt_2['y']) < 0.0005