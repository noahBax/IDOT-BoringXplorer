import logging
from typing import Literal
from math import pi, sqrt
from tools.types import Coordinate, Vector
from tools.segment_operations import find_segment_intersect, segment_project_from, Segment
from tools.angle_operations import find_angle_bac
from tools.distance_operations import check_points_equivalent, square_distance, square_length
from tools.vector_operations import vector_subtract, vector_project_from, vector_multiply, vector_add

logger = logging.getLogger(__name__)

def find_average_of_intersecting_lines(left: Segment, right: Segment) -> Segment:
    """
    Segments that cross over each other at a single point are a similar problem
    to the "average" of alongside lines, but are made harder by the fact that
    the average line cannot simply be somewhere in the middle of the two. 

    For the simplest case, what could essentially be described as an X where two
    lines intersect at a point and both are of equal length and the intersection
    point is at the same point on both lines, then the average line is just one
    that is drawn up and through the middle.

    When you stray away from that, it becomes different. If we keep the same X
    shape but just lengthen one of the lines on one end. Then the "average" is
    going to have an angle that more resembles the longer line. What if we
    lengthen the other line but on the same side of the X that the first one
    was? While it was questionable before, clearly, the "average" line cannot
    pass through the intersection point anymore and must exist almost entirely
    on the side of the X that had its ends lengthened.

    I solved this problem by finding a point along the line segments that is
    proportionately far away from the intersection point weighted by its size.
    That is a very loose definition of what goes on here though, and it breaks
    down entirely when considering edge cases, so read the code.
    """


    # Edge case 1: the two segments share a point and intersect at one end
    check_shared = check_sharing_point(left, right)
    if check_shared:
        return check_shared

    # Edge case 2: the intersection point lies ON one of the segments
    inter: Coordinate = find_segment_intersect(left, right)
    check_3 = check_3_segments(left, right, inter)
    if check_3:
        return check_3

    # In order to find the average, we need to work with two pairs of partial
    # segments that form acute angles

    tri_1 = left.pt_1
    tri_2 = right.pt_2

    angle_between = find_angle_bac(tri_1, inter, tri_2)

    pt_1: Coordinate
    pt_2: Coordinate

    if angle_between < pi / 2: # Acute
        pt_1 = find_partial_point(right.pt_2, left.pt_1, inter)
        pt_2 = find_partial_point(right.pt_1, left.pt_2, inter)
    else: # Obtuse
        pt_1 = find_partial_point(right.pt_1, left.pt_1, inter)
        pt_2 = find_partial_point(right.pt_2, left.pt_2, inter)

    partial_average = Segment(pt_1, pt_2)

    # Now project all endpoints onto the line and pick the two that are farthest
    # apart

    possible_points = [
        segment_project_from(partial_average, left.pt_1)[0],
        segment_project_from(partial_average, left.pt_2)[0],
        segment_project_from(partial_average, right.pt_1)[0],
        segment_project_from(partial_average, right.pt_2)[0],
    ]

    farthest_distance = square_distance(possible_points[2], possible_points[3])
    segment_ends = possible_points[2], possible_points[3]

    for i in range(2):
        for j in range(3-i):

            dist = square_distance(possible_points[i], possible_points[i+j+1])
            if dist > farthest_distance:
                farthest_distance = dist
                segment_ends = possible_points[i], possible_points[i+j+1]

    return Segment(*segment_ends)
        

def find_partial_point(end_1: Coordinate, end_2: Coordinate, inter: Coordinate) -> Coordinate:

    vec_1 = vector_subtract(end_1, inter)
    vec_2 = vector_subtract(end_2, inter)

    if square_distance(vec_1) > square_distance(vec_2):
        long_end = vec_1
        short_end = vec_2
    else:
        long_end = vec_2
        short_end = vec_1

    # Find the projection of the short end onto the long end
    proj = vector_project_from(long_end, short_end)
    
    # The projection we want to vary over is from the longer end to the shorter end
    vary_me = vector_subtract(proj, short_end)

    short = sqrt(square_length(short_end))
    long = sqrt(square_length(long_end))
    length_ratio = long / (short + long)

    final_project = vector_multiply(vary_me, length_ratio)
    ret = vector_add(final_project, short_end, inter)

    return ret

def check_sharing_point(left: Segment, right: Segment) -> Segment | Literal[False]:
    """
    Check if the segments share a common point on one end. If not return False.
    Otherwise return the correct result
    """

    # Check to see if any of the ends are equivalent.
    # Only two can be, duplicate segments are taken care of in main

    if check_points_equivalent(left.pt_1, right.pt_1):
        return find_shared_average(left.pt_1, left.pt_2, right.pt_2)

    if check_points_equivalent(left.pt_1, right.pt_2):
        return find_shared_average(left.pt_1, left.pt_2, right.pt_1)

    if check_points_equivalent(left.pt_2, right.pt_1):
        return find_shared_average(left.pt_2, left.pt_1, right.pt_2)

    if check_points_equivalent(left.pt_2, right.pt_2):
        return find_shared_average(left.pt_2, left.pt_1, right.pt_1)

    return False

def find_shared_average(shared_pt: Coordinate, end_1: Coordinate, end_2: Coordinate) -> Segment:

    angle_between = find_angle_bac(end_1, shared_pt, end_2)

    partial_pt_1: Coordinate
    partial_pt_2: Coordinate

    if angle_between < pi/2: # Acute
        # We just need to find one partial point because we already know one of the ends
        partial_pt_1 = shared_pt
        partial_pt_2: Coordinate = find_partial_point(end_1, end_2, shared_pt)

        partial_segment = Segment(partial_pt_1, partial_pt_2)

        proj_1, _ = segment_project_from(partial_segment, end_1)
        proj_2, _ = segment_project_from(partial_segment, end_2)

        end: Segment

        if square_distance(shared_pt, proj_1) > square_distance(shared_pt, proj_2):
            end = Segment(shared_pt, proj_1)
        else:
            end = Segment(shared_pt, proj_2)

        return end

        # This could arguably be better by finding a second point on the shorter
        # line and using that instead of the shared_pt. Feel free to implement
        # this in the future, but I don't think it will make much difference
        # considering the small scale of the angles we are working with.
        
    else: # Obtuse
        # We need to find two partial points

        # Kinda simple, but why not just pick partial points that are along the
        # line proportional to how long it is over the whole. However weird that
        # sounds.

        left_len = sqrt(square_distance(shared_pt, end_1))
        right_len = sqrt(square_distance(shared_pt, end_2))

        partial_pt_1 = vector_subtract(end_1, shared_pt)
        pt_1_ratio: float = left_len / (left_len + right_len)
        partial_pt_1 = vector_multiply(partial_pt_1, pt_1_ratio)
        partial_pt_1 = vector_add(partial_pt_1, shared_pt)
        
        partial_pt_2 = vector_subtract(end_2, shared_pt)
        pt_2_ratio: float = right_len / (left_len + right_len)
        partial_pt_2 = vector_multiply(partial_pt_2, pt_2_ratio)
        partial_pt_2 = vector_add(partial_pt_2, shared_pt)

        # Now that we have partial points, project the two ends onto that vector. Those points are the ends of the line by definition
        partial_segment = Segment(partial_pt_1, partial_pt_2)
        ret_1, _ = segment_project_from(partial_segment, end_1)
        ret_2, _ = segment_project_from(partial_segment, end_2)

        return Segment(ret_1, ret_2)

def check_3_segments(left: Segment, right: Segment, intersect: Coordinate):

    # Go through each end and check to see if the end is equivalent to the intersect
    if check_points_equivalent(left.pt_1, intersect):
        return find_3_pt_average(right, left.pt_2, intersect)

    if check_points_equivalent(left.pt_2, intersect):
        return find_3_pt_average(right, left.pt_1, intersect)

    if check_points_equivalent(right.pt_1, intersect):
        return find_3_pt_average(left, right.pt_2, intersect)

    if check_points_equivalent(right.pt_2, intersect):
        return find_3_pt_average(left, right.pt_1, intersect)

    return False

def find_3_pt_average(full: Segment, half: Coordinate, intersect: Coordinate) -> Segment:

    logger.debug('Is 3 points')

    # First need to find 
    dist_top = sqrt(square_distance(full.pt_1, intersect))
    dist_bottom = sqrt(square_distance(full.pt_2, intersect))
    dist_half = sqrt(square_distance(half, intersect))
    total_distance = dist_bottom + dist_top + dist_half
    
    half_vector = vector_subtract(half, intersect)
    half_vector = vector_multiply(half_vector, dist_half / total_distance)

    partial_half: Coordinate = vector_add(half_vector, intersect)
    partial_full: Coordinate

    pt_1: Coordinate
    pt_2: Coordinate

    tail_vector: Vector
    c_1: Coordinate
    c_2: Coordinate

    # Choose that vector to vary the partial point over
    # if dist_top > dist_bottom:
    if find_angle_bac(half, intersect, full.pt_1) > pi/2:
        tail_vector = vector_subtract(intersect, full.pt_1)
        tail_vector = vector_multiply(tail_vector, dist_top / total_distance)

        partial_full = vector_add(tail_vector, full.pt_1)
        partial_segment = Segment(partial_full, partial_half)

        pt_1, _ = segment_project_from(partial_segment, full.pt_1)

        c_1, _ = segment_project_from(partial_segment, full.pt_2)
        c_2, _ = segment_project_from(partial_segment, half)

        if square_distance(pt_1, c_1) > square_distance(pt_1, c_2):
            pt_2 = c_1
        else:
            pt_2 = c_2
    else:
        tail_vector = vector_subtract(intersect, full.pt_2)
        tail_vector = vector_multiply(tail_vector, dist_bottom / total_distance)

        partial_full = vector_add(tail_vector, full.pt_2)
        partial_segment = Segment(partial_full, partial_half)

        pt_1, _ = segment_project_from(partial_segment, full.pt_2)

        c_1, _ = segment_project_from(partial_segment, full.pt_1)
        c_2, _ = segment_project_from(partial_segment, half)

        if square_distance(pt_1, c_1) > square_distance(pt_1, c_2):
            pt_2 = c_1
        else:
            pt_2 = c_2

    return Segment(pt_1, pt_2)