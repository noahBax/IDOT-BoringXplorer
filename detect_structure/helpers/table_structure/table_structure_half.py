from copy import deepcopy
import logging
import os
from pathlib import Path
from tools.segment_operations import Segment, find_lines_that_intersect, segment_add, segment_subtract
from tools.vector_operations import int_ify_vector, vector_add, vector_subtract
from tools.types import Coordinate, Vector
from tools.distance_operations import square_distance
from line_detection.helpers.draw_visuals import draw_segment_on_image, draw_on_image
from line_detection.helpers.get_line_segments import get_line_segments
from line_detection.detect_lines import verticals
from detect_structure.helpers.soil_depth_ruler.soil_depth_ruler import Soil_Depth_Ruler
from skimage.io import imsave
from statistics import mean
from functools import reduce
from numpy import ndarray
import numpy as np
from typing import Any, TypedDict
from detect_structure.helpers.table_structure.table_structure import table_half

logger = logging.getLogger(__name__)

"""
Refer to the Table_Structure class for most of the documentation. This is
essentially a clone of that but with only half (he-he) of the functionality. It
is meant to deal with pages that only have one column.

For compatibility with existing code, it must implement all of the same
properties that Table_Structure has
"""

class Table_Structure_Half:

    def __init__(self, 
                 horizontals: list[Segment],
                 verticals: list[Segment],
                 gray_image: ndarray[Any, Any],
                 color_image: ndarray[Any, Any],
                 draw_visuals=False,
                 visuals_folder='visuals'
                ) -> None:

        logger.debug('Starting table analysis')
        self.table_top: Segment
        self.header_top: Segment
        self.table_top  =  Table_Structure_Half.__find_table_top(horizontals,
                                                                 verticals,
                                                                 gray_image.shape[1],
                                                                 gray_image.shape[0],
                                                                 width_min=1580)
        
        logger.debug(f'Found table top at {self.table_top}')
        self.header_top = Table_Structure_Half.__find_header_top(horizontals,
                                                                 verticals,
                                                                 self.table_top.find_midpoint()['x'],
                                                                 gray_image.shape[0],
                                                                 gray_image.shape[1],
                                                                 self.table_top)
        
        logger.debug(f'Found header top at {self.header_top}')

        # Search between the table and header top to find the vertical lines
        # defining the columns.
        seps = Table_Structure_Half.__find_column_separators(self.table_top, self.header_top, gray_image, draw_visuals=draw_visuals, visuals_folder=visuals_folder)
        seps.sort(key=lambda s: s.average_x)
        self.header_separators = seps

        # Limit the right side of the header/table top to the rightmost column
        # separator and the same for the left side of the header top
        seps.sort(key=lambda s: s.average_x)
        max_x = seps[-1].average_x
        min_x = seps[0].average_x
        self.table_top = Segment(self.table_top.leftmost_point, {'x': max_x, 'y': self.table_top.average_y})
        self.header_top = Segment({'x': min_x, 'y': self.header_top.average_y}, {'x': max_x, 'y': self.header_top.average_y})

        logger.debug(f'Hey max_x is {max_x}')
        logger.debug(f'Seps have xs at {[s.average_x for s in seps]}')

        # Find left and right of table
        verticals.sort(key=lambda v: v.pt_1['x'])

        self.table_bottom = Table_Structure_Half.__find_table_bottom(self.table_top, horizontals, verticals, gray_image.shape[0], gray_image.shape[1])

        # Now create the column bounds
        seps.sort(key=lambda v: v.pt_1['x'])
        self.left_half: table_half = {
            'full_description': (
                Segment(self.table_top.leftmost_point, self.table_bottom.leftmost_point),
                Table_Structure_Half.__connect_header_to_bottom(seps[1], self.table_bottom)
            ),
            'partial_description': (
                Segment(self.table_top.leftmost_point, self.table_bottom.leftmost_point),
                Table_Structure_Half.__connect_header_to_bottom(seps[0], self.table_bottom)
            ),
            'ruler': (
                Table_Structure_Half.__connect_header_to_bottom(seps[0], self.table_bottom),
                Table_Structure_Half.__connect_header_to_bottom(seps[1], self.table_bottom)
            ),
            'blows': (
                Table_Structure_Half.__connect_header_to_bottom(seps[1], self.table_bottom),
                Table_Structure_Half.__connect_header_to_bottom(seps[2], self.table_bottom)
            ),
            'ucs': (
                Table_Structure_Half.__connect_header_to_bottom(seps[2], self.table_bottom),
                Table_Structure_Half.__connect_header_to_bottom(seps[3], self.table_bottom)
            ),
            'moisture': (
                Table_Structure_Half.__connect_header_to_bottom(seps[3], self.table_bottom),
                Table_Structure_Half.__connect_header_to_bottom(seps[4], self.table_bottom)
            )
        }


        if draw_visuals:
            Path(visuals_folder).mkdir(parents=True, exist_ok=True)

            shape = color_image.shape
            bones: np.ndarray
            bones = np.zeros(shape, dtype=np.uint8)
            bones = draw_segment_on_image(bones, self.table_top, (255, 165, 0), 'table top')
            bones = draw_segment_on_image(bones, self.header_top, (0, 0, 255), 'header top')
            bones = draw_segment_on_image(bones, self.table_bottom, (0, 255, 0), 'table bottom')
            bones = draw_on_image(bones, [], self.header_separators, draw_text=False, return_as_array=True)

            for section in self.left_half:
                bones = draw_segment_on_image(bones, self.left_half[section][0], (0xFF, 0xC0, 0xCB), section)

            # left_tick_offset: Vector = {'x': self.left_half['ruler'][0].highest_point['x'], 'y': self.table_top.average_y}

            # for tick in self.left_soil_depth_ruler.ruler_ticks:
            #     bones = draw_segment_on_image(bones, tick.add(left_tick_offset), (0, 0x80, 0x80))

            imsave(os.path.join(visuals_folder, 'table_structure.png'), bones, check_contrast=False)

            colored: np.ndarray = (255-color_image)
            colored = draw_segment_on_image(colored, self.table_top, (255, 165, 0), 'table top')
            colored = draw_segment_on_image(colored, self.header_top, (0, 0, 255), 'header top')
            colored = draw_segment_on_image(colored, self.table_bottom, (0, 128, 128), 'table bottom')
            colored = draw_on_image(colored, [], self.header_separators, draw_text=False, return_as_array=True)

            for section in self.left_half:
                colored = draw_segment_on_image(colored, self.left_half[section][0], (0xFF, 0xC0, 0xCB), section)
            
            imsave(os.path.join(visuals_folder, 'draw_on_table_structure.png'), colored)


    def find_rulers(self,
                    left_ends: tuple[float, float],
                    right_ends: tuple[float, float],
                    color_image: np.ndarray,
                    gray_image: np.ndarray,
                    draw_visuals=False) -> None:
        # right_ends is not used, but is there for symmetry with a full table
        self.left_soil_depth_ruler = Soil_Depth_Ruler(gray_image,
                                                      color_image,
                                                      self.left_half['ruler'],
                                                      self.table_top.average_y,
                                                      *left_ends,
                                                      draw_visuals=draw_visuals,
                                                      side='l')

    def draw_structure(self, color_image: np.ndarray, visuals_folder='visuals') -> None:
        Path(visuals_folder).mkdir(parents=True, exist_ok=True)

        shape = color_image.shape
        bones: np.ndarray
        bones = np.zeros(shape, dtype=np.uint8)
        bones = draw_segment_on_image(bones, self.table_top, (255, 165, 0), 'table top')
        bones = draw_segment_on_image(bones, self.header_top, (0, 0, 255), 'header top')
        bones = draw_segment_on_image(bones, self.table_bottom, (0, 255, 0), 'table bottom')
        bones = draw_on_image(bones, [], self.header_separators, draw_text=False, return_as_array=True)

        for section in self.left_half:
            bones = draw_segment_on_image(bones, self.left_half[section][0], (0xFF, 0xC0, 0xCB), section)

        # left_tick_offset: Vector = {'x': self.left_half['ruler'][0].highest_point['x'], 'y': self.table_top.average_y}
        # right_tick_offset: Vector = {'x': self.right_half['ruler'][0].highest_point['x'], 'y': self.table_top.average_y}
        # for tick in self.left_soil_depth_ruler.ruler_ticks:
        #     bones = draw_segment_on_image(bones, tick.add(left_tick_offset), (0, 0x80, 0x80))
        # for tick in self.right_soil_depth_ruler.ruler_ticks:
        #     bones = draw_segment_on_image(bones, tick.add(right_tick_offset), (0, 0x80, 0x80))

        imsave(os.path.join(visuals_folder, 'table_structure.png'), bones, check_contrast=False)

        colored: np.ndarray = (255-deepcopy(color_image))
        colored = draw_segment_on_image(colored, self.table_top, (255, 165, 0), 'table top')
        colored = draw_segment_on_image(colored, self.header_top, (0, 0, 255), 'header top')
        colored = draw_segment_on_image(colored, self.table_bottom, (0, 128, 128), 'table bottom')
        colored = draw_on_image(colored, [], self.header_separators, draw_text=False, return_as_array=True)

        for section in self.left_half:
            colored = draw_segment_on_image(colored, self.left_half[section][0], (0xFF, 0xC0, 0xCB), section)
        
        imsave(os.path.join(visuals_folder, 'draw_on_table_structure.png'), colored)


    def refresh_all_segments(self) -> None:
        self.table_top.compare_fails = []
        self.header_top.compare_fails = []
        for s in self.header_separators:
            s.compare_fails = []
        self.table_bottom.compare_fails = []
        for key in self.left_half:
            self.left_half[key][0].compare_fails = []
            self.left_half[key][1].compare_fails = []

    @staticmethod
    def __find_table_top(horizontals: list[Segment], verticals: list[Segment], width: int, height: int, height_min=0, width_min=0) -> Segment:
        """
        Find the top of the actual table (excluding the headers). This is NOT
        the top of the columns. So it's not the tippy top, so to speak.
        """

        # Procedure here is the same as in the full table structure, but we only
        # need 4 lines and they are going to be the closest to the center anyway

        # Sort by center distance
        verticals.sort(key=lambda v: abs(v.average_x - width/2))

        # Limit by height and pick top 4
        valid_verticals = [v for v in verticals if v.length > height/2][:4]

        # Limit horizontals based on threshold
        valid_horizontals = [h for h in horizontals if h.length > width_min]

        logger.debug('Limiting by verticals')
        for v in valid_verticals:
            logger.debug(v)
            valid_horizontals = find_lines_that_intersect(v, valid_horizontals)

        if len(valid_horizontals) == 0:
            raise Exception('length of table headers is 0')

        # Grab the topmost horizontal line
        valid_horizontals.sort(key=lambda h: h.average_y)
        return valid_horizontals[0]

    @staticmethod
    def __find_header_top(horizontals: list[Segment], verticals: list[Segment], center_x: int|float, height: int, width: int, table_top: Segment) -> Segment:
        """
        `center_x` should be the center of the table top
        
        Find the top of all the header columns. Using the same terminology as
        before, this IS the tippy top.


        I can't do the same things as in Table_Structure, so this is a different
        method. I'm not as confident this will work since I haven't necessarily
        put the line detection algorithm through all it's paces yet, but it will
        probably work most of the time.
        """


        if len(horizontals) == 0 or len(verticals) == 0:
            raise Exception('Tried to find header top with no vertical and/or horizontal lines')

        # # Limit horizontals to just those who have a center within the last few vertical lines
        # verticals.sort(key=lambda v: v.average_x, reverse=True)
        # max_x = verticals[0].average_x
        # min_x = verticals[2].average_x
        # def within(v: Segment):
        #     less = v.average_x < max_x
        #     more = v.average_x > min_x
        #     return more and less
        # cool_h = [h for h in horizontals if within(h)]

        # Sometimes scans can be weird and they have really faint lines at the
        # top. Gotta ignore these (see Christian County/011-7050 SOIL 2012.pdf)
        top_h = [h for h in horizontals if h.average_y > 350 and h.average_y < 1000 and h != table_top]

        # Should be longer than half the page
        top_h = [h for h in top_h if h.length > width / 2]

        # Should have centers on the right half of the page
        top_h = [h for h in top_h if h.find_midpoint()['x'] >= width * 0.39]

        # Find top 5 longest horizontal lines
        top_h.sort(key=lambda h: h.square_length, reverse=True)
        top_h = top_h[:5]

        # Find the column lines
        # Sort by center distance
        # Limit by height and pick top 5
        # Make sure they are not the left line
        top_v = [v for v in verticals if v.average_x > width * 0.2]
        top_v = [v for v in top_v if v.length > height/2]
        top_v.sort(key=lambda v: abs(v.average_x - center_x))
        top_v = top_v[:6]

        # Those include both the left and right sides, we want only the right
        # side
        top_v.sort(key=lambda v: v.average_x)
        top_v = top_v[1:]

        # Find the average y-value
        avg_top_y = mean(v.highest_point['y'] for v in top_v)

        # Now find the closest horizontal line
        top_h.sort(key=lambda c: abs(avg_top_y - c.average_y))
        closest = top_h[0]

        # In some weird cases, the line recognized as the header top might not
        # extend all the way across the header. So we might have to artificially
        # extend it to cover everything.

        # If there are 7 total recognized vertical lines, then the smallest is
        # most likely to be the ruler bound. So we should make sure that the
        # table top extends to cover it

        verticals.sort(key=lambda v: abs(v.average_x - center_x))

        possible_ruler_bound_s = [v for v in verticals if v.average_x < top_v[0].average_x and v.length < height/2]
        possible_ruler_bound_s.sort(key=lambda v: v.average_x, reverse=True)
        min_x = possible_ruler_bound_s[0].leftmost_point['x']

        max_x = top_v[-1].rightmost_point['x']

        logger.debug(f'Picked header top with average y {closest.average_y}')

        ret = Segment({'x': min_x, 'y': closest.average_y}, {'x': max_x, 'y': closest.average_y})

        return ret

    @staticmethod
    def __find_column_separators(table_top: Segment, header_top: Segment, gray_image: ndarray[Any, Any], draw_visuals=False, visuals_folder='visuals') -> list[Segment]:
        
        # First crop the image to just the area containing the headers
        top_left = int_ify_vector(header_top.leftmost_point)
        top_left = vector_add(top_left, {'x': -5, 'y': 0})
        x1, y1 = top_left['x'], top_left['y']

        bottom_right = int_ify_vector(table_top.rightmost_point)
        bottom_right = vector_add(bottom_right, {'x': 5, 'y': 0})
        x2, y2 = bottom_right['x'], bottom_right['y']

        top_right = int_ify_vector(header_top.rightmost_point)
        top_right = vector_add(top_right, {'x': 5, 'y': 0})
        x3, y3 = top_right['x'], top_right['y']

        # Take whichever line extends out the longest
        # ? It might be better to just take the vertical line that is leftmost?
        if x2 > x3:
            cropped = gray_image[y1:y2, x1:x2]
        else:
            cropped = gray_image[y1:y2, x1:x3]

        if draw_visuals:
            Path(visuals_folder).mkdir(parents=True, exist_ok=True)
            imsave(os.path.join(visuals_folder, 'header_section.png'), cropped, check_contrast=False)

        cropped = (255 - cropped)

        # Search for vertical lines
        _, header_seps = get_line_segments(
            cropped,
            thetas=verticals,
            line_length=160,
            line_gap=10,
            alongside_gap=10,
            max_angle_difference=np.pi / 3,
            base_angle={'x': 0, 'y': 1},
            compress_maximum=280,
            project_onto='v')
        
        # Try to limit by length
        header_seps = [h for h in header_seps if h.length > 200]
        
        # There should be 6 lines
        if len(header_seps) != 6:
            raise Exception(f'{len(header_seps)} lines were recognized in the header section')

        header_seps = [segment_add(c, top_left) for c in header_seps]
        
        return header_seps

    @staticmethod
    def __find_table_bottom(table_top: Segment, horizontals: list[Segment], verticals: list[Segment], page_height: int, page_width: int):

        # For the BBS_137_REV_8_99 format there is a line at the bottom of the
        # table, but for the other formats there is not. Given that, I think
        # it's best to say the bottom of the table is a line equal to the
        # table_top but at a lower elevation. This won't work for all of the
        # unlabeled formats (Adams County/001-3003 SOIL 1999.pdf for example),
        # but it will hit the majority of cases.

        # Now I am working strictly for the BBS_137_REV_8_99 format, so we go
        # for the longest line in the last 1/8 of the page

        last_eight = [h for h in horizontals if h.average_y > page_height * 5/6]
        last_eight.sort(key=lambda s: s.square_length, reverse=True)

        # To deal with messy situations, find (out of lines longer than half the
        # page) which line is closest to the average of the bottom of the 8
        # longest verticals
        verticals.sort(key=lambda v: v.square_length, reverse=True)
        top_v = verticals[:8]

        # Average of bottom of verticals
        avg_low_y = mean([v.lowest_point['y'] for v in top_v])

        # Limit last portion to lines longer than half the page
        last_eight = [l for l in last_eight if l.length > page_width / 2]

        # Now find the closest horizontal line
        closest = sorted(last_eight, key=lambda h: abs(h.average_y - avg_low_y))

        lowest_y = closest[0].average_y

        bottom = segment_add(table_top, {'x': 0, 'y': lowest_y - table_top.average_y})
        
        return bottom

    @staticmethod
    def __connect_header_to_bottom(header_separator: Segment, table_bottom: Segment):

        top = header_separator.lowest_point
        bottom: Coordinate = {'x': top['x'], 'y': table_bottom.pt_1['y']}

        return Segment(top, bottom)