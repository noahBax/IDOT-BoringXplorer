from __future__ import annotations
import json
from math import atan, floor, pi, sqrt
from tools.types import Vector, Coordinate
from tools.vector_operations import vector_subtract, vector_project_from, vector_add
from functools import cached_property

class Segment:

    _next_id = 0

    def __init__(self, pt_1: Coordinate, pt_2: Coordinate, angle: float|None=None) -> None:
        self.pt_1 = pt_1
        self.pt_2 = pt_2
        self.id = Segment._get_id()
        if angle != None:
            self.angle = angle
        else:
            self.angle = Segment._find_angle_caused_by_points(pt_1, pt_2)

        self.compare_fails: list[int] = []

    @staticmethod
    def _get_id() -> int:
        Segment._next_id += 1
        return Segment._next_id

    @staticmethod
    def _find_angle_caused_by_points(pt_1: Coordinate, pt_2: Coordinate) -> float:

        dx = pt_2['x'] - pt_1['x']
        dy = pt_2['y'] - pt_1['x']

        if dx == 0:
            return pi/2

        return atan(dy / dx)

    def distance_from_center_to(self, pt: Coordinate) -> float:
        m = self.find_midpoint()
        return sqrt(Segment._square_distance(m, pt))

    @staticmethod
    def _square_distance(p1: Coordinate, p2: Coordinate = { 'x': 0, 'y': 0 }) -> float:
        return (p1['x'] - p2['x']) ** 2 + (p1['y'] - p2['y']) ** 2
    
    @property
    def square_length(self) -> float:
        """
        Return square length of segment
        """
        return Segment._square_distance(self.pt_1, self.pt_2)
    
    @property
    def length(self) -> float:
        """
        Return actual length of segment
        """
        return sqrt(self.square_length)
    
    def add_compare_fail(self, id: int) -> None:
        self.compare_fails.append(id)

    @property
    def average_x(self) -> float:
        return (self.pt_1['x'] + self.pt_2['x']) / 2

    @property
    def average_y(self) -> float:
        return (self.pt_1['y'] + self.pt_2['y']) / 2
    
    @property
    def highest_point(self) -> Coordinate:
        if self.pt_1['y'] < self.pt_2['y']:
            return self.pt_1
        else:
            return self.pt_2
    
    @property
    def lowest_point(self) -> Coordinate:
        if self.pt_1['y'] > self.pt_2['y']:
            return self.pt_1
        else:
            return self.pt_2

    @property
    def leftmost_point(self) -> Coordinate:
        if self.pt_1['x'] < self.pt_2['x']:
            return self.pt_1
        else:
            return self.pt_2
    
    @property
    def rightmost_point(self) -> Coordinate:
        if self.pt_1['x'] < self.pt_2['x']:
            return self.pt_2
        else:
            return self.pt_1

    def find_midpoint(self) -> Coordinate:
        middle: Coordinate = {
            'x': (self.pt_1['x'] - self.pt_2['x']) / 2,
            'y': (self.pt_1['y'] - self.pt_2['y']) / 2
        }

        return vector_add(self.pt_2, middle)

    def add(self, vector: Vector) -> Segment:
        return segment_add(self, vector)

    def subtract(self, vector: Vector) -> Segment:
        return segment_subtract(self, vector)

    def find_y_dif(self, s: Segment) -> float:
        return abs(self.average_y - s.average_y)
    
    def toSerializable(self) -> tuple[Coordinate, Coordinate]:
        return (self.pt_1, self.pt_2)

    def __str__(self) -> str:
        return f'({self.pt_1["x"]}, {self.pt_1["y"]}), ({self.pt_2["x"]}, {self.pt_2["y"]})'

    def __repr__(self) -> str:
        return self.__str__()
        

def zero_segment(segment: Segment) -> tuple[Vector, Vector]:
    zeroed: Vector = {
        'x': segment.pt_2['x'] - segment.pt_1['x'],
        'y': segment.pt_2['y'] - segment.pt_1['y']
    }
    base: Vector = {
        'x': segment.pt_1['x'],
        'y': segment.pt_1['y']
    }

    return zeroed, base


def segment_project_from(u: Vector | Segment, v: Coordinate) -> tuple[Vector, Vector]:
    """
    Find the projection of v onto u
    POINT onto SEGMENT for your use case
    """

    project_onto: Vector
    base_coord: Vector
    if isinstance(u, Segment):
        project_onto = u.pt_2
        base_coord = u.pt_1
    else:
        project_onto = u
        base_coord = {'x': 0, 'y': 0}

    project_me = vector_subtract(v, base_coord)
    project_onto = vector_subtract(project_onto, base_coord)

    projection = vector_project_from(project_onto, project_me)

    return vector_add(projection, base_coord), base_coord

def segment_subtract(u: Segment, v: Vector) -> Segment:
    """
    Subtract v from u
    """
    pt_1 = vector_subtract(u.pt_1, v)
    pt_2 = vector_subtract(u.pt_2, v)
    return Segment(pt_1, pt_2, u.angle)

def segment_add(u: Segment, v: Vector) -> Segment:
    """
    Add vectors
    """
    pt_1 = vector_add(u.pt_1, v)
    pt_2 = vector_add(u.pt_2, v)
    return Segment(pt_1, pt_2, u.angle)

def check_point_is_on_segment(seg: Segment, pt: Coordinate) -> bool:
    """
    This function assumes that the point generated lies somewhere on the line
    function attached to the segment. It is ONLY for seeing if the point is
    inside of the segment
    """

    dx = seg.pt_2['x'] - seg.pt_1['x']
    dy = seg.pt_2['y'] - seg.pt_1['y']

    ret: bool

    if dx == 0: # Lines are vertical

        if dy > 0: # Point 2 above point 1
            ret = (pt['y'] - seg.pt_1['y'] >= -0.005 and
                    seg.pt_2['y'] - pt['y'] >= -0.005)
        else:
            ret = (seg.pt_1['y'] - pt['y'] >= -0.005 and
                    pt['y'] - seg.pt_2['y'] >= -0.005)
    else: # Lines are NOT vertical

        if dx > 0: # Point 2 after point 1
            ret = (pt['x'] - seg.pt_1['x'] >= -0.005 and
                   seg.pt_2['x'] - pt['x'] >= -0.005)
        else:
            ret = (seg.pt_1['x'] - pt['x'] >= -0.005 and
                   pt['x'] - seg.pt_2['x'] >= -0.005)

    return ret

def find_segment_intersect(segment_1: Segment, segment_2: Segment) -> Coordinate:
    """
    This function assumes that the lines you returned are not parallel

    This function will return the intersection of the two lines that the
    segments lay on. There is no validation to check if it is actually within
    that segment
    """

    dx_1 = segment_1.pt_2['x'] - segment_1.pt_1['x']
    dy_1 = segment_1.pt_2['y'] - segment_1.pt_1['y']

    dx_2 = segment_2.pt_2['x'] - segment_2.pt_1['x']
    dy_2 = segment_2.pt_2['y'] - segment_2.pt_1['y']

    if dx_1 == 0: # seg 1 is vertical
        slope = dy_2 / dx_2
        inter = segment_2.pt_1['y'] - slope * segment_2.pt_1['x']

        x = segment_1.pt_1['x']
        y = slope * x + inter

        return {
            'x': x,
            'y': y
        }
    elif dx_2 == 0: # seg 2 is vertical
        slope = dy_1 / dx_1
        inter = segment_1.pt_1['y'] - slope * segment_1.pt_1['x']

        x = segment_2.pt_1['x']
        y = slope * x + inter

        return {
            'x': x,
            'y': y
        }
    else: # Neither line is vertical
        slope_1 = dy_1 / dx_1
        inter_1 = segment_1.pt_1['y'] - slope_1 * segment_1.pt_1['x']

        slope_2 = dy_2 / dx_2
        inter_2 = segment_2.pt_1['y'] - slope_2 * segment_2.pt_1['x']

        x_intersect = (inter_2 - inter_1) / (slope_1 - slope_2)
        y_intersect = x_intersect * slope_1 + inter_1
        return { 'x': x_intersect, 'y': y_intersect}

def check_segments_parallel(segment_1: Segment, segment_2: Segment) -> bool:

    v1 = __check_valid_slope(segment_1)
    v2 = __check_valid_slope(segment_2)

    if v1 != v2:
        return False
    
    if not v1 and not v2:
        return True

    m1 = __find_slope(segment_1)
    m2 = __find_slope(segment_2)

    return m1 == m2


def check_segments_equivalent(left: Segment, right: Segment):

    directly_equal = (
        abs(left.pt_1['x'] - right.pt_1['x']) < 0.01 and
        abs(left.pt_1['y'] - right.pt_1['y']) < 0.01 and
        abs(left.pt_2['x'] - right.pt_2['x']) < 0.01 and
        abs(left.pt_2['y'] - right.pt_2['y']) < 0.01)
    
    oppositely_equal = (
        abs(left.pt_1['x'] - right.pt_2['x']) < 0.01 and
        abs(left.pt_1['y'] - right.pt_2['y']) < 0.01 and
        abs(left.pt_2['x'] - right.pt_1['x']) < 0.01 and
        abs(left.pt_2['y'] - right.pt_1['y']) < 0.01)

    return directly_equal or oppositely_equal


def int_ify_segment(seg: Segment) -> Segment:

    pt_1: Coordinate = {
        'x': int(floor(seg.pt_1['x'])),
        'y': int(floor(seg.pt_1['y']))
    }
    pt_2: Coordinate = {
        'x': int(floor(seg.pt_2['x'])),
        'y': int(floor(seg.pt_2['y']))
    }
    return Segment(pt_1, pt_2, seg.angle)


def segments_do_intersect(left, right) -> bool:

    if check_segments_parallel(left, right):
        return False

    possible = find_segment_intersect(left, right)

    return (check_point_is_on_segment(left, possible) and
            check_point_is_on_segment(right, possible))

def __find_slope(vector: Segment | Vector) -> float:
    """
    This function assumes that the line is not vertical. Perform a check before
    calling
    """

    if isinstance(vector, Segment):
        return (vector.pt_1['y'] - vector.pt_2['y']) / (vector.pt_1['x'] - vector.pt_2['x'])

    return vector['y'] / vector['x']

def __check_valid_slope(v: Segment | Vector) -> bool:

    if not isinstance(v, Segment):
        return v['x'] != 0
    
    return v.pt_2['x'] - v.pt_1['x'] != 0

def find_lines_that_intersect(leader: Segment, candidates: list[Segment]) -> list[Segment]:
    return [c for c in candidates if segments_do_intersect(leader, c)]