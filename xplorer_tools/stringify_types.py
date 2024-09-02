from xplorer_tools.segment_operations import Segment
from xplorer_tools.types import Vector, Coordinate

def str_coord(coord: Coordinate) -> str:
    return f'({coord["x"]}, {coord["y"]})'

def str_vector(v: Vector) -> str:
    return f'(0, 0), ({v["x"]}, {v["y"]})'

def str_segment(seg: Segment) -> str:
    return f'({seg.pt_1["x"]}, {seg.pt_1["y"]}), ({seg.pt_2["x"]}, {seg.pt_2["y"]})'