from scipy.stats import norm
from tools.distance_operations import square_distance, square_length
from tools.vector_operations import vector_add, vector_multiply, check_is_NaN
from tools.segment_operations import segment_project_from, check_point_is_on_segment, Segment, check_segments_equivalent, zero_segment
from tools.types import Coordinate

def find_average_of_alongside_lines(left_segment: Segment, right_segment: Segment) -> Segment:
    """
    Segments that run alongside each other and are significantly close can
    create lines that exceed the maximum angle threshold distance when just
    going between the furthest two points. Because of that, a better solution is
    to create a new line segment that is the "average" of both lines.

    This works well in theory for lines that are of roughly equal length or that
    have equal slope as "finding the average" creates a line that makes sense.
    Where it fails is with lines that are very short and running at a extreme
    angle relative to a much longer line. Finding the average of the two would
    create a line that is more extremely skewed and looks nothing like the
    original.
    
    With that in mind, this function attempts to rectify that by finding the
    projection of either line onto the other, picking a point somewhere along
    that projection vector, creating a segment between those points, and then
    extending that segment out to encompass the full length of the combined
    lines.

    If that's inadequate, read the code.
    """
    # There are technically 3 cases for this
    # 1) There are only two points that when projected onto the other line
    # 2) There are 3 points
    # 3) There are 4 points
    # Cases 2 and 3 can occur when the two segments are parallel, but the
    # segments will just be connections between the end points

    left_length = square_length(left_segment)
    right_length = square_length(right_segment)

    length_ratio = (right_length - left_length) / ((left_length + right_length) / 2)
    left_lean_value: float = norm.cdf(length_ratio) # type: ignore

    vec_list: list[tuple[Coordinate, Coordinate]] = []
    not_list: list[tuple[Coordinate, Coordinate]] = []

    # Project ends of each segment onto the other segment and check to see
    # whether that projection lies within that segment

    proj, _ = segment_project_from(left_segment, right_segment.pt_1)
    if check_point_is_on_segment(left_segment, proj):
        vec_list.append((proj, right_segment.pt_1))
    else:
        not_list.append((proj, right_segment.pt_1))

    proj, _ = segment_project_from(left_segment, right_segment.pt_2)
    if check_point_is_on_segment(left_segment, proj):
        vec_list.append((proj, right_segment.pt_2))
    else:
        not_list.append((proj, right_segment.pt_2))

    proj, _ = segment_project_from(right_segment, left_segment.pt_1)
    if check_point_is_on_segment(right_segment, proj):
        vec_list.append((left_segment.pt_1, proj))
    else:
        not_list.append((left_segment.pt_1, proj))

    proj, _ = segment_project_from(right_segment, left_segment.pt_2)
    if check_point_is_on_segment(right_segment, proj):
        vec_list.append((left_segment.pt_2, proj))
    else:
        not_list.append((left_segment.pt_2, proj))

    # Get rid of duplicates
    projection_vectors = eliminate_duplicates(vec_list, not_list)

    # Find the points that determine the average line

    vec1, base1 = zero_segment(projection_vectors[0])
    vec1 = vector_multiply(vec1, left_lean_value)
    pt1 = vector_add(vec1, base1)

    vec2, base2 = zero_segment(projection_vectors[1])
    vec2 = vector_multiply(vec2, left_lean_value)
    pt2 = vector_add(vec2, base2)

    partial_average = Segment(pt1, pt2)

    # Now project all endpoints onto the line and pick the two that are farthest
    # apart

    possible_points = [
        segment_project_from(partial_average, left_segment.pt_1)[0],
        segment_project_from(partial_average, left_segment.pt_2)[0],
        segment_project_from(partial_average, right_segment.pt_1)[0],
        segment_project_from(partial_average, right_segment.pt_2)[0],
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
    

def eliminate_duplicates(vectors: list[tuple[Coordinate, Coordinate]], anti_vectors):

    # Length 2
    if len(vectors) == 2:
        seg_1 = Segment(*vectors[0])
        seg_2 = Segment(*vectors[1])

        # Check the edge case where the two alongside segments are parallel and
        # align at only one point.
        if check_segments_equivalent(seg_1, seg_2):
            return (Segment(*anti_vectors[0]), Segment(*anti_vectors[1]))
        else:
            return (seg_1, seg_2)

    # More than 2 so need to reduce
    seg_1 = Segment(*vectors[0])
    seg_2 = Segment(*vectors[1])
    
    if check_segments_equivalent(seg_1, seg_2): # Indices 0 and 1 are duplicates
        return (seg_1, Segment(*vectors[2]))

    else: # Indices 0 and 1 are NOT duplicates
        return (Segment(*vectors[0]), Segment(*vectors[1]))
