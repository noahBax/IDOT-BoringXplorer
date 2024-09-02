from math import pi, atan
from xplorer_tools.segment_operations import Segment


def create_segments(raw_segments: list[tuple[tuple[float, float], tuple[float, float]]]) -> list[Segment]:

    ret: list[Segment] = []
    for segment in raw_segments:
        ret.append(Segment(
            {'x': segment[0][0], 'y': segment[0][1]},
            {'x': segment[1][0], 'y': segment[1][1]}
        ))

    return ret