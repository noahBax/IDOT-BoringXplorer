import logging
from math import floor, pi
import os
from typing import Any
import numpy as np
from pathlib import Path
from numpy import ndarray
from skimage.io import imsave
from tools.segment_operations import Segment
from line_detection.helpers.draw_visuals import *
from line_detection.helpers.get_line_segments import get_line_segments
from tools.angle_operations import find_angle_between
from line_detection.detect_lines import horizontals

logger = logging.getLogger(__name__)

def detect_ruler_lines(gray_image: ndarray[Any, Any], draw_visuals=False, visuals_folder='visuals') -> list[Segment]:

    # This is the image that we are specifically going to analyze for lines.
    analyze_me = (255 - gray_image)
    image_width = gray_image.shape[1]

    # Find segments
    raw_horizontal: list[Segment]
    combined_horizontal: list[Segment]
    raw_horizontal, combined_horizontal = get_line_segments(
        analyze_me,
        thetas=horizontals,
        line_length=floor(image_width * 2/3),
        line_gap=3,
        alongside_gap=35,
        max_angle_difference=np.pi/5,
        compress_maximum=35,
        angle_threshold=pi/18,
        project_onto='h')
    
    # Limit the horizontals down to stuff that is completely horizontal
    b = len(combined_horizontal)
    combined_horizontal = [h for h in combined_horizontal if close_to_horizontal(h)]
    logger.debug(f'{b - len(combined_horizontal)} horizontals removed')
    logger.debug(f'Found {len(combined_horizontal)} ruler lines')

    if len(combined_horizontal) < 19:
        raise Exception('Could not find enough ruler ticks')
    
    if draw_visuals:
        shape = gray_image.shape
        shape = (shape[0]+100, shape[1]+100, 3)
        Path(visuals_folder).mkdir(parents=True, exist_ok=True)
        
        raw = draw_raw_visuals(shape, raw_horizontal, [])

        imsave(os.path.join(visuals_folder, 'ruler_raw.png'), raw)

    return combined_horizontal

def close_to_horizontal(seg: Segment) -> bool:
    dif = find_angle_between(seg, {'x': 1, 'y': 0})
    if dif > pi/2:
        dif = pi - dif
    return dif < pi/18