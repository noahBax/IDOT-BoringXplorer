import logging
import numpy as np
import os
from math import floor, pi
from pathlib import Path
from typing import Literal, TypedDict
from paddleocr import PaddleOCR
from skimage.io import imsave
from collections import Counter
from detect_structure.helpers.table_structure.table_structure_half import Table_Structure_Half
from document_agenda.document_agenda import Document_Agenda
from tools.stringify_types import Vector
from tools.segment_operations import Segment, int_ify_segment
from line_detection.detect_lines import horizontals
from line_detection.helpers.get_line_segments import get_line_segments
from detect_structure.helpers.soil_depth_ruler.soil_depth_ruler import Soil_Depth_Ruler
from detect_structure.helpers.table_structure.table_structure import Table_Structure, table_half
from line_detection.helpers.draw_visuals import draw_segment_visuals, draw_on_image
from detect_structure.helpers.find_BUM_info.BUM_pair import Pair
from detect_structure.helpers.find_BUM_info.blowcount import BlowCount
import detect_structure.helpers.find_BUM_info.simple_stuff as simple_stuff
from tools.cleanup_side import clean_side

logger = logging.getLogger(__name__)

def find_blow_counts(color_image: np.ndarray,
                     gray_image: np.ndarray,
                     table: Table_Structure|Table_Structure_Half,
                     side: Literal['l', 'r'],
                     document_agenda: Document_Agenda,
                     ocr_cls_true: PaddleOCR,
                     draw_visuals=False,
                     visuals_folder='visuals') -> list[BlowCount]:
    """
    Right now this is just geared for the BBS_137_REV_8_99 format
    """
    
    # First crop image to correct side and find the soil_ruler
    soil_ruler: Soil_Depth_Ruler
    group: table_half
    
    if side == 'l':
        soil_ruler = table.left_soil_depth_ruler
        group = table.left_half
    else:
        if isinstance(table, Table_Structure_Half):
            raise TypeError('Tried to call find_blow_counts on the right side with a half-table')
        
        soil_ruler = table.right_soil_depth_ruler
        group = table.right_half
    blows: _crops = {
        'color': (255-_crop_to_segment(*group['blows'], color_image)),
        'gray': (255-_crop_to_segment(*group['blows'], gray_image)),
        'top_offset': group['blows'][0].highest_point['y']
    }
    ucs: _crops ={
        'color': (255-_crop_to_segment(*group['ucs'], color_image)),
        'gray': (255-_crop_to_segment(*group['ucs'], gray_image)),
        'top_offset': group['ucs'][0].highest_point['y']
    }
    moist: _crops ={
        'color': (255-_crop_to_segment(*group['moisture'], color_image)),
        'gray': (255-_crop_to_segment(*group['moisture'], gray_image)),
        'top_offset': group['moisture'][0].highest_point['y']
    }

    col_width = sum([b.average_x - a.average_x for a,b in [group['blows'], group['ucs'], group['moisture']]]) / 3

    # Now scan for horizontal lines

    blows_info = _get_column_lines(blows['gray'], col_width, soil_ruler, blows['top_offset'])
    ucs_info = _get_column_lines(ucs['gray'], col_width, soil_ruler, ucs['top_offset'])
    moist_info = _get_column_lines(moist['gray'], col_width, soil_ruler, moist['top_offset'])

    if draw_visuals:
        _draw_visuals(visuals_folder, ucs['gray'], ucs['color'], [b[0] for b in ucs_info])

    logger.debug('Found these horizontals:')
    logger.debug([b[0] for b in ucs_info])
    logger.debug([b[1] for b in ucs_info])

    # Get BUM section bounds
    likely_bum_bounds = _take_majority_votes(blows_info, ucs_info, moist_info)
    logger.debug(f'Likely bounds: {likely_bum_bounds}')

    # Get rid of ends
    likely_bum_bounds.sort()
    if len(likely_bum_bounds) > 0 and likely_bum_bounds[-1] == soil_ruler.ending_depth:
        likely_bum_bounds.pop()
    if len(likely_bum_bounds) > 0 and likely_bum_bounds[0] == soil_ruler.starting_depth:
        likely_bum_bounds = likely_bum_bounds[1:]

    if len(likely_bum_bounds) == 0:
        return []

    # In attempt to try to rid of extra lines, narrow the blows just a little bit
    adjustment: Vector = {'x': 3, 'y': 0}
    
    # crop_between = (group['blows'][0].add(adjustment), group['blows'][1].subtract(adjustment))
    crop_between = group['blows']
    
    pairs = Pair.find_bum_pairs(likely_bum_bounds, soil_ruler.starting_depth, soil_ruler.ending_depth)

    if not pairs:
        # No BUM pairs were found
        return []

    # _analyze_pairs(pairs, [b[1] for b in blows_info], 255-_crop_to_segment(*crop_between, color_image), soil_ruler)
    blow_bounds = [b[1] for b in blows_info]
    if soil_ruler.starting_depth not in blow_bounds:
        blow_bounds.append(soil_ruler.starting_depth)
    if soil_ruler.ending_depth not in blow_bounds:
        blow_bounds.append(soil_ruler.ending_depth)

    blow_bounds = [b[1] for b in blows_info]
    colored_blows = (255-_crop_to_segment(*crop_between, color_image))
    colored_blows = clean_side(colored_blows, leeway=6)
    ret = simple_stuff.analyze_pairs(pairs, blow_bounds, colored_blows, soil_ruler, document_agenda, ocr_cls_true)

    return ret

def _crop_to_segment(left: Segment, right: Segment, image: np.ndarray) -> np.ndarray:
    l = int_ify_segment(left)
    r = int_ify_segment(right)
    x1, y1 = l.highest_point['x'], l.highest_point['y']
    x2, y2 = r.lowest_point['x'], r.lowest_point['y']
    return image[y1:y2, x1:x2]

def _draw_visuals(visuals_folder: str, cropped_gray: np.ndarray, cropped_color: np.ndarray, horizontals: list[Segment]) -> None:
    Path(visuals_folder).mkdir(parents=True, exist_ok=True)
    shape = cropped_gray.shape
    shape = (shape[0], shape[1], 3)
    refined = draw_segment_visuals(shape, horizontals, [], font_size=20)
    imsave(os.path.join(visuals_folder, 'BUM_bones.png'), refined, check_contrast=False)
    
    text_on_me = draw_on_image(cropped_color, horizontals, [], return_as_array=True)
    imsave(os.path.join(visuals_folder, 'BUM_on_BUM.png'), text_on_me)

def _get_column_lines(gray_image: np.ndarray, width: float, soil_ruler: Soil_Depth_Ruler, column_offset: float) -> list[tuple[Segment, float]]:
    combined_horizontal: list[Segment]
    _, combined_horizontal = get_line_segments(
        gray_image,
        thetas=horizontals,
        line_length=floor(width*1/2),
        line_gap=5,
        alongside_gap=35,
        max_angle_difference=np.pi/5,
        compress_maximum=35,
        angle_threshold=pi/18,
        project_onto='h')

    ret = [(s, soil_ruler.ask_for_depth(s.average_y, column_offset)) for s in combined_horizontal if s.length > width * 2/3]
    return ret

def _take_majority_votes(info_1: list[tuple[Segment, float]], info_2: list[tuple[Segment, float]], info_3: list[tuple[Segment, float]]) -> list[float]:
    """
    Find which columns have lines that fall on the same spot on the ruler.
    Return the ones which have more than 1 occurrence
    """
    
    likely_bum_bounds: list[float] = []
    recorded_depths: list[float] = [b[1] for b in info_1 + info_2 + info_3]

    # Count occurrences of each element
    depth_counts = Counter(recorded_depths)

    # Filter elements that appear more than once and extract them into a list
    likely_bum_bounds = [depth for depth, count in depth_counts.items() if count > 1]

    return likely_bum_bounds


# def _find_text_in_bounds(blows: np.ndarray, pair: Pair, ocr_instance: PaddleOCR, soil_ruler: Soil_Depth_Ruler) -> list[str]:
#     print(f'Looking between {pair.top_bound} and {pair.low_bound}')

#     sections: list[tuple[int, int]]
#     topper = floor(soil_ruler.ask_for_pixels(pair.top_bound))
#     lower = floor(soil_ruler.ask_for_pixels(pair.low_bound))
#     if pair.span == 0.5:
#         y1 = topper
#         y2 = lower
#         sections = [(y1,y2)]
#     elif pair.span == 1.0:
#         y1 = topper
#         y3 = lower
#         y2 = floor((y3 - y1) / 2) + y1
#         sections = [(y1, y2), (y2, y3)]
#     elif pair.span == 1.5:
#         y1 = topper
#         y4 = lower
#         jump = (y4 - y1) / 3
#         y2 = floor(y1 + jump)
#         y3 = floor(y1 + 2*jump)
#         sections = [(y1, y2), (y2, y3), (y3, y4)]
#     else:
#         raise Exception('Unhandled pair span')

class _crops(TypedDict):
    color: np.ndarray
    gray: np.ndarray
    top_offset: float