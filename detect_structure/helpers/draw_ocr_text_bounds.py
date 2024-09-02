import copy
import logging
from math import floor
import numpy as np
from skimage.draw import line
from xplorer_tools.types import ocr_result
from xplorer_tools.segment_operations import Segment
from line_detection.helpers.draw_visuals import draw_segment_on_image

logger = logging.getLogger(__name__)

def draw_ocr_text_bounds(results: list[ocr_result]|list[tuple[Segment, Segment]], image: np.ndarray, in_place=False) -> np.ndarray:
    """
    Returns a copy of the input ndarray. If the image is 2 dimensional, text
    will be drawn with a white border. If 3 dimensional, text will be drawn with
    a red border.
    """

    if results == None or len(results) == 0:
        logger.debug('Nothing to draw')
        return image

    def line_on_image(rr, cc, img_arr):
        if len(img_arr.shape) == 3:
            img_arr[cc, rr, 0] = 255
            img_arr[cc, rr, 1] = 0
            img_arr[cc, rr, 2] = 0
        else:
            img_arr[cc, rr] = 255

    def do_segments(res: list[tuple[Segment, Segment]]):
        nonlocal draw_on_me
        
        for result in res:
            draw_on_me = draw_segment_on_image(draw_on_me, result[0], (0xff, 0, 0))
            draw_on_me = draw_segment_on_image(draw_on_me, result[1], (0xff, 0, 0))
            draw_on_me = draw_segment_on_image(draw_on_me, Segment(result[0].leftmost_point, result[1].leftmost_point), (0xff, 0, 0))
            draw_on_me = draw_segment_on_image(draw_on_me, Segment(result[0].rightmost_point, result[1].rightmost_point), (0xff, 0, 0))


    def do_ocr_results(res: list[ocr_result]):
        for result in res:
            for i in range(4):
                rr, cc = line(
                    floor(result[0][i][0]),
                    floor(result[0][i][1]),
                    floor(result[0][(i+1) % 4][0]),
                    floor(result[0][(i+1) % 4][1]),
                )
                line_on_image(rr, cc, draw_on_me)

    if in_place:
        draw_on_me = image
    else:
        draw_on_me = copy.deepcopy(image)
        
    if isinstance(results[0][0], Segment):
        do_segments(results) # type: ignore
    else:
        do_ocr_results(results) # type: ignore

    return draw_on_me