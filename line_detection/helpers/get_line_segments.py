import logging
from math import pi
from copy import deepcopy
from typing import Literal
import numpy as np
from skimage.transform import probabilistic_hough_line
from xplorer_tools.angle_operations import angle_between_two_lines
from xplorer_tools.segment_operations import Segment, check_segments_equivalent, segments_do_intersect, segment_project_from, check_point_is_on_segment
from xplorer_tools.vector_operations import vector_subtract, check_is_NaN
from xplorer_tools.distance_operations import square_distance, square_length
from xplorer_tools.types import Vector, Coordinate
from line_detection.helpers.create_segments import create_segments
from line_detection.helpers.find_average_of_alongside_lines import find_average_of_alongside_lines
from line_detection.helpers.find_average_of_intersecting_lines import find_average_of_intersecting_lines
from xplorer_tools.stringify_types import str_coord

logger = logging.getLogger(__name__)
comparisons_skipped: int = 0

def get_line_segments(
        grayscale_image: np.ndarray,
        thetas,
        line_length=50,
        line_gap=10,
        alongside_gap=10,
        compress_maximum=10,
        max_angle_difference=pi/2,
        base_angle:Vector={'x': 1, 'y': 0},
        angle_threshold=pi/20,
        project_onto: Literal['h','v']|None=None) -> tuple[list[Segment], list[Segment]]:
    """
    Combine lines that were not combined properly during the probabilistic hough transform
    """

    global comparisons_skipped

    raw_segments = probabilistic_hough_line(grayscale_image, line_length=line_length, theta=thetas, line_gap=line_gap)
    line_segments = create_segments(raw_segments)
    ret_copy: list[Segment] = deepcopy(line_segments)

    if project_onto == 'h':
        line_segments = [project_to_horizontal(s) for s in line_segments]
    elif project_onto == 'v':
        line_segments = [project_to_vertical(s) for s in line_segments]
    else:
        # Sort segments by their angle
        line_segments.sort(key=lambda x: x.angle)


    combination_count = 0

    index = 0
    while index < len(line_segments):

        offset = 1
        advance_index = True

        while offset < len(line_segments):
        
            curr = line_segments[index]
            next = line_segments[(index + offset) % len(line_segments)]

            if curr.id in next.compare_fails:
                comparisons_skipped += 1
                break

            logger.debug(f'Comparing {index} and {(index+offset) % len(line_segments)}')
            logger.debug(f'Curr: {curr}')
            logger.debug(f'Next: {next}')

            # Are they close enough in angle
            angle_dif = angle_between_two_lines(curr, next)
            if not angle_dif <= angle_threshold:
                # If the angle difference between them is too big, back out
                logger.debug('Angle difference is too big')
                curr.add_compare_fail(next.id)
                next.add_compare_fail(curr.id)
                break

            # Check for the special case where they are the same
            if check_segments_equivalent(curr, next):
                # If so, get rid of the redundant one
                line_segments.pop((index + offset) % len(line_segments))
                combination_count += 1
                logger.debug('equivalent')
                continue

            # Case 1: segments intersect at some point
            intersecting = segments_do_intersect(curr, next)
            # Case 2: segments are close to each other
            alongside = not intersecting and segments_sufficiently_close(curr, next, threshold=compress_maximum)
            # Case 3: segment ends within threshold
            ends_together = not intersecting and not alongside and segment_ends_within_threshold(curr, next, threshold=alongside_gap)
            # Case 4: overlapping and parallel
            overlap_par = not intersecting and not alongside and not ends_together and segments_overlap_parallel(curr, next, alongside_gap)
            
            if intersecting or ends_together or alongside or overlap_par:

                new_segment: Segment

                if alongside:
                    # Default to more complicated function
                    logger.debug('Alongside')
                    new_segment = find_average_of_alongside_lines(curr, next)
                elif intersecting:
                    # Default to more complicated function
                    logger.debug('Intersecting')
                    new_segment = find_average_of_intersecting_lines(curr, next)
                else:
                    if alongside:
                        logger.debug('Ends together')
                    else:
                        logger.debug('Overlapping and parallel')
                    # Just pick points that are farthest apart
                    distances = (
                        square_distance(curr.pt_1, next.pt_1),
                        square_distance(curr.pt_1, next.pt_2),
                        square_distance(curr.pt_2, next.pt_2),
                        square_distance(curr.pt_2, next.pt_1)
                    )

                    curr_len = square_distance(curr.pt_1, curr.pt_2)
                    next_len = square_distance(next.pt_1, next.pt_2)

                    # Check to see if it makes sense to use the farthest points
                    max_dist = max(distances)
                    farthest_pair = distances.index(max_dist)
                    if curr_len > max_dist:
                        # Collapse everything into curr
                        new_segment = deepcopy(curr)
                    elif next_len > max_dist:
                        # Collapse everything into next
                        new_segment = deepcopy(next)
                    else:
                        
                        pt_1: Coordinate
                        pt_2: Coordinate
                        match farthest_pair:
                            case 0:
                                pt_1 = curr.pt_1
                                pt_2 = next.pt_1
                            case 1:
                                pt_1 = curr.pt_1
                                pt_2 = next.pt_2
                            case 2:
                                pt_1 = curr.pt_2
                                pt_2 = next.pt_2
                            case _: # For linting
                                pt_1 = curr.pt_2
                                pt_2 = next.pt_1

                        new_segment = Segment(pt_1, pt_2)

                # Check to see if the angle produced by this exceeds the maximum
                # specified
                angle_between = angle_between_two_lines(new_segment, base_angle)
                if angle_between > max_angle_difference:
                    logger.debug('Angle between the new segment and the base angle too big')
                    offset += 1
                    curr.add_compare_fail(next.id)
                    next.add_compare_fail(curr.id)
                    continue

                # Insert it into the list

                if check_is_NaN(new_segment.pt_1) or check_is_NaN(new_segment.pt_2):
                    logger.debug(new_segment)
                    raise Exception('Found NaN segment')

                line_segments[index] = new_segment
                removed = line_segments.pop((index + offset) % len(line_segments))
                if not check_segments_equivalent(next, removed):
                    logger.debug('We did not remove the right one!')
                    raise Exception('We did not remove the right one!')

                line_segments.sort(key=lambda x: x.angle)

                # There may be a more efficient way to continue, but this is
                # only being done once and the result is being cached. Bite me.
                index = 0
                advance_index = False
                combination_count += 1
                break
            else:
                curr.add_compare_fail(next.id)
                next.add_compare_fail(curr.id)

            offset += 1
        
        if advance_index:
            index += 1

    return ret_copy, line_segments

def segment_ends_within_threshold(segment_1: Segment, segment_2: Segment, threshold=100) -> bool:
    distances = [
        square_distance(segment_1.pt_1, segment_2.pt_1),
        square_distance(segment_1.pt_1, segment_2.pt_2),
        square_distance(segment_1.pt_2, segment_2.pt_2),
        square_distance(segment_1.pt_2, segment_2.pt_1)
    ]
    return min(distances) < threshold

def check_within(segment: Segment, point: Coordinate, threshold: float, count_zero: int, count_close: int):
    projection, _ = segment_project_from(segment, point)
    dist_squared = square_length(vector_subtract(projection, point))
    logger.debug(str_coord(projection))
    logger.debug(str_coord(point))
    logger.debug(dist_squared)
    
    count_zero += dist_squared == 0
    count_close += dist_squared < threshold and check_point_is_on_segment(segment, projection)

    return count_close, count_zero


def segments_sufficiently_close(left: Segment, right: Segment, threshold=200):
    """
    Detect lines that run alongside each other within a certain distance
    """
    logger.debug('Testing alongside')

    count_close: int = 0
    count_zero: int  = 0

    count_close, count_zero = check_within(right, left.pt_1, threshold, count_zero, count_close)
    
    count_close, count_zero = check_within(right, left.pt_2, threshold, count_zero, count_close)
    
    count_close, count_zero = check_within(left, right.pt_1, threshold, count_zero, count_close)

    count_close, count_zero = check_within(left, right.pt_2, threshold, count_zero, count_close)

    logger.debug(f'count_close: {count_close}')

    if count_zero == 4:
        return False
    else:
        return count_close >= 2
    
    
def project_to_horizontal(seg: Segment) -> Segment:
    avg_y = (seg.pt_1['y'] + seg.pt_2['y']) / 2

    return Segment(
        {'x': seg.pt_1['x'], 'y': avg_y},
        {'x': seg.pt_2['x'], 'y': avg_y}
    )

def project_to_vertical(seg: Segment) -> Segment:
    avg_x = (seg.pt_1['x'] + seg.pt_2['x']) / 2

    return Segment(
        {'x': avg_x, 'y': seg.pt_1['y']},
        {'x': avg_x, 'y': seg.pt_2['y']}
    )

def segments_overlap_parallel(left: Segment, right: Segment, threshold: float):
    """
    Detect lines that are parallel and do overlap
    """
    logger.debug('Testing parallel')

    count_close: int = 0
    count_zero: int  = 0

    count_close, count_zero = check_within(right, left.pt_1, threshold, count_zero, count_close)
    
    count_close, count_zero = check_within(right, left.pt_2, threshold, count_zero, count_close)
    
    count_close, count_zero = check_within(left, right.pt_1, threshold, count_zero, count_close)

    count_close, count_zero = check_within(left, right.pt_2, threshold, count_zero, count_close)

    return count_zero == 4 and count_close >= 2
