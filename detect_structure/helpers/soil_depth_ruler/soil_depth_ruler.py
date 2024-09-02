import logging
import os
from math import floor
from pathlib import Path
from typing import Any, Literal, TypedDict
from skimage.io import imsave
from functools import reduce
from tools.types import form_types, ocr_result
from tools.segment_operations import Segment, segment_subtract
from detect_structure.helpers.soil_depth_ruler.find_ruler_lines import detect_ruler_lines
from tools.stringify_types import str_segment
from line_detection.helpers.draw_visuals import draw_segment_on_image
import numpy as np
import statistics

logger = logging.getLogger(__name__)

class _Tick_Number(TypedDict):
    depth: float
    pixels: float
    segment: Segment

class Soil_Depth_Ruler:
    """
    Literally just used so I can tell how far down a bunch of text is in the
    soil

    You'd think this would be a simple task, and for the majority of cases it
    is, but the differing formats all bring something new to the table.

    For the "BBS 137 Rev 8-99" case, the ruler column is just filled with tick
    marks and numbers and usually it is done in feet (one exception is 'Adams
    County/001-0502 SOIL-ROCK 1998.pdf'). In most reports, each individual ruler
    spans over a range of 20 feet (or meters) but it can differ ('Adams
    County/001-0502 SOIL-ROCK 1998.pdf').

    For the "BBS 138 Rev 8-99" format, the same rules from above apply, but the
    start of the first ruler does not have to be at the ground surface
    elevation. I don't think we are aiming to go for Rock Core Logs though.

    For the "BD 137 Rev 9-60" format, usually the ruler column is just filled
    with tick marks and numbers, but sometimes this is not the case ('Adams
    County/001-0033 SOIL 1973.pdf'). In every report I've looked at, each
    individual ruler spans over a range of 22.5 feet. This format in particular
    will be hard to parse though.

    The "BD 137 Rev 4-78" format has the same details as "BD 137 Rev 9-60".

    All of the other formats that are not so clear are all over the place. Most
    of them are in BD 137 format but it's never stated what revision. The tick
    marks are different lengths and ugggh.
    """

    def __init__(
            self,
            gray_image: np.ndarray[Any, Any],
            color_image: np.ndarray[Any, Any],
            ruler_bounds: tuple[Segment, Segment],
            pixel_offset: float,
            starting_depth: float,
            ending_depth: float,
            format: form_types=form_types.Empty,
            draw_visuals=False,
            side: Literal['l','r']='l',
            visuals_folder='visuals') -> None:

        self.starting_depth = starting_depth
        self.ending_depth = ending_depth

        logger.debug('Creating ruler')

        # Crop the area we are looking at to just the ruler
        highest = ruler_bounds[0].highest_point
        lowest = ruler_bounds[1].lowest_point
        x1, y1 = floor(highest['x']), floor(highest['y'])
        x2, y2 = floor(lowest['x']), floor(lowest['y'])

        ruler_image: np.ndarray[Any, Any] = gray_image[y1:y2, x1:x2]
        color_ruler: np.ndarray[Any, Any] = color_image[y1:y2, x1:x2]

        # Write the ruler image
        if draw_visuals:
            Path(visuals_folder).mkdir(parents=True, exist_ok=True)
            imsave(os.path.join(visuals_folder, f'ruler_base_{side}.png'), ruler_image)

        # Analyze the ruler for all ticks
        ruler_ticks = detect_ruler_lines(ruler_image, draw_visuals=draw_visuals)

        # Do we have enough data?
        not_enough_data = len(ruler_ticks) == 0 or len(ruler_ticks) == 1 and not starting_depth == None
        if not_enough_data:
            raise Exception('Could not find enough data points to reliably find ruler data')

        # Find stuff
        ruler_ticks.sort(key=Soil_Depth_Ruler.__average_y)
        diffs = [a.find_y_dif(b) for a, b in zip(ruler_ticks, ruler_ticks[1:])]
        normal_diff = statistics.median(diffs)

        bottom_tick: Segment = Segment(ruler_bounds[0].lowest_point, ruler_bounds[1].lowest_point).subtract(ruler_bounds[0].highest_point)
        top_tick: Segment    = Segment(ruler_bounds[0].highest_point, ruler_bounds[1].highest_point).subtract(ruler_bounds[0].highest_point)
        # top_tick: Segment = Segment({'x': 0, 'y': 0}, {'x': ruler_bounds[1].average_x - ruler_bounds[0].average_x, 'y': 0})
        if len(ruler_ticks) > 19:
            # Check to see if the last tick is the bottom tick
            if bottom_tick.average_y - ruler_ticks[-1].average_y < normal_diff * 0.67:
                bottom_tick = ruler_ticks[-1]

            # Now the top tick
            elif ruler_ticks[0].average_y < normal_diff:
                top_tick = ruler_ticks[0]
            
        # Distance between major ticks is 1 foot anyway. It's change in pixels / 1 foot
        self.pixel_depth_rate = normal_diff
        self.ruler_ticks = ruler_ticks
        self.document_offset_height = pixel_offset + top_tick.average_y

        self.__top_pixels = top_tick.average_y
        self.__bottom_pixels = bottom_tick.average_y

        if draw_visuals:
            for double_depth in range(floor(ending_depth - starting_depth)*2):
                ruler_depth = double_depth/2
                guess = ruler_depth * self.pixel_depth_rate
                draw_me = Segment({'x': 0, 'y': guess}, {'x': color_ruler.shape[1]-1, 'y': guess})
                color_ruler = draw_segment_on_image(color_ruler, draw_me, (255, 0, 0), str(ruler_depth+starting_depth), font_size=30)
            imsave(os.path.join(visuals_folder, f'ruler_demo_{side}.png'), color_ruler)
            

        logger.debug(f'Created soil ruler at {hex(id(self))}')
        logger.debug(f'pixel_offset_height: {self.document_offset_height}')
        logger.debug(f'pixel_depth_rate: {self.pixel_depth_rate}')
        logger.debug(f'starting_depth: {self.starting_depth}')
        logger.debug(f'Top pixels: {self.__top_pixels}')
        logger.debug(f'Bottom pixels: {self.__bottom_pixels}')

        # Below code is for when I analyzed the ruler for text


        # # Create an altered image made easier for ocr
        # # look_for_text = np.array(draw_on_image(color_ruler, raw_ticks, [], draw_text=False, horizontal_segment_color=(255,255,255)))

        # # Analyze the ruler for text
        # ocr = PaddleOCR(cls=False, lang='en', ocr_version='PP-OCRv4')
        # ocr_results: list[ocr_result] = ocr.ocr(np.array(color_ruler, dtype=np.uint8), cls=True)[0]
        # print('Found text results on ruler')
        # print(ocr_results)


        # # Write image with text
        # if draw_visuals:
        #     with_bounds = draw_ocr_text_bounds(ocr_results, (255 - color_ruler))
        #     imsave(os.path.join(visuals_folder, f'ruler_text_{side}.png'), with_bounds)


        # # Refine the results
        # ocr_results = fix_ocr_results(ocr_results)


        # # Attach text numbers to the ticks on the ruler
        # tick_numbers: list[_Tick_Number]
        # tick_numbers, self.ending_depth = Soil_Depth_Ruler.__find_tick_numbers(ruler_ticks, ocr_results, ruler_bounds)
        

        # # If we know what the starting depth is, we can factor that in too
        # if starting_depth != None:
        #     top_tick = segment_subtract(
        #         Segment(ruler_bounds[0].highest_point, ruler_bounds[1].highest_point),
        #         ruler_bounds[0].highest_point
        #     )
        #     tick_numbers.insert(0,{ 'depth': starting_depth, 'pixels': 0, 'segment': top_tick})


        # # Find pixel / depth
        # self.pixel_depth_rate = Soil_Depth_Ruler.__find_depth_rate(tick_numbers)


        # # If we weren't given the starting depth, we gotta find it
        # self.starting_depth = starting_depth if starting_depth != None else Soil_Depth_Ruler.__guess_start(tick_numbers, self.pixel_depth_rate)

        # # If end not found, we gotta find it
        # self.ending_depth = self.ending_depth if self.ending_depth != -1.0 else Soil_Depth_Ruler.__guess_end(ruler_ticks, self.pixel_depth_rate, ruler_bounds, self.starting_depth)


        # top_left = ruler_bounds[0].highest_point
        # ruler_ticks = [segment_add(t, top_left) for t in ruler_ticks]
        # for tick in tick_numbers:
        #     tick['segment'] = segment_add(tick['segment'], ruler_bounds[0].highest_point)

        # self.ruler_ticks = ruler_ticks
        # self.tick_numbers = tick_numbers

    def ask_for_depth(self, pixel_position: float, document_offset_height: float) -> float:

        logger.debug('Asked for depth')
        logger.debug(f'Pixel depth is {pixel_position} and offset is {document_offset_height}')

        pos = pixel_position + document_offset_height - self.document_offset_height
        
        logger.debug(f'Considering those, relative position is {pos}')
        
        guessed = pos / self.pixel_depth_rate
        ret = self.starting_depth + round(guessed * 2) / 2

        logger.debug(f'Relative depth on ruler is {guessed}')
        logger.debug(f'Document relative plus rounding gives {ret}')

        if ret < self.starting_depth:
            ret = self.starting_depth
        elif ret > self.ending_depth:
            ret = self.ending_depth
        
        return ret

    def ask_for_pixels(self, depth: float, document_relative=False) -> float:
        """
        Returns the guessed spot in pixels along the ruler where a depth would
        reside
        """

        logger.debug(f'Asked for pixels at depth {depth}')

        if depth > self.ending_depth or depth < self.starting_depth:
            raise ValueError('Asked for pixels with a depth that is out of range of the ruler')

        ruler_depth = depth - self.starting_depth
        guess: float = ruler_depth * self.pixel_depth_rate

        logger.debug(f'Relative depth on ruler is {ruler_depth}')
        logger.debug(f'Leads to guess of {guess}')

        if guess < self.__top_pixels:
            guess = self.__top_pixels
            logger.debug(f'Guess is outside of the bounds ({self.__top_pixels}) of the ruler')
        elif guess > self.__bottom_pixels:
            guess = self.__bottom_pixels
            logger.debug(f'Guess is outside of the bounds ({self.__bottom_pixels}) of the ruler')

        if document_relative:
            guess += self.document_offset_height

        return guess
    
    @staticmethod
    def __average_y(s: Segment) -> float:
        return (s.pt_1['y'] + s.pt_2['y']) / 2

    @staticmethod
    def __average_of_text(t) -> float:
        s = 0
        for i in range(4):
            s += t[0][i][1]
        return s/4

    @staticmethod
    def __find_tick_numbers(ruler_ticks: list[Segment],
                            ocr_results: list[ocr_result],
                            ruler_bounds: tuple[Segment, Segment]
                        ) -> tuple[list[_Tick_Number], float]:
        """
        Match recognized depths to a tick by essentially snapping each number
        down onto the tick mark below it.

        Returns a list of [depth, pixels, segment] for each recognized string as
        well as the lowest depth if it was found
        """

        tick_numbers: list[_Tick_Number] = []
        ruler_ticks.sort(key=Soil_Depth_Ruler.__average_y)

        # Find the usual difference between major ticks
        diffs = [a.find_y_dif(b) for a, b in zip(ruler_ticks, ruler_ticks[1:])]
        normal_diff = statistics.mean(diffs)

        # Along the way find the lowest depth if we can
        ending_depth = -1.0

        bottom_tick: Segment = Segment(ruler_bounds[0].lowest_point, ruler_bounds[1].lowest_point).subtract(ruler_bounds[0].highest_point)
        top_tick: Segment = Segment({'x': 0, 'y': 0}, {'x': ruler_bounds[0].average_x - ruler_bounds[1].average_x, 'y': 0})
        if len(ruler_ticks) > 19:
            # Check to see if the last tick is the bottom tick
            if bottom_tick.average_y - ruler_ticks[-1].average_y < normal_diff:
                bottom_tick = ruler_ticks[-1]

            # Now the top tick
            elif ruler_ticks[0].average_y < normal_diff:
                top_tick = ruler_ticks[0]
            
        # Distance between major ticks is 1 foot anyway. It's change in pixels / 1 foot

        
        for result in ocr_results:
            logger.debug('Finding tick for', result)
            position = Soil_Depth_Ruler.__average_of_text(result)

            for tick in ruler_ticks:
                logger.debug(f'Trying {str_segment(tick)}')

                if position < tick.average_y:
                    logger.debug('Success')
                    
                    tick_numbers.append({
                        'depth': float(result[1][0]),
                        'pixels': tick.average_y,
                        'segment': tick
                    })
                    break
            else:
                # Possibly the bottom of the table. Check to make sure though
                bottom_y = ruler_bounds[0].lowest_point['y']
                is_bottom_table = (bottom_y - position < normal_diff and ending_depth == -1.0)

                if is_bottom_table:
                    logger.debug('Matched as ending depth')
                    
                    # depth, pixels, segment
                    tick_numbers.append({
                        'depth': float(result[1][0]),
                        'pixels': bottom_y,
                        'segment': bottom_tick
                    })
                    ending_depth = float(result[1][0])
                else:
                    raise Exception('Ruler number has unmatched tick')

        if ending_depth == -1.0:
            # ! **WARNING** This assumption only works for BBS_137_REV_8_99
            lowest = reduce(lambda a, b: a if a['depth'] > b['depth'] else b, tick_numbers)
            threshold = 0.8 * bottom_tick.average_y

            ending_depth = lowest['depth'] if lowest['pixels'] > threshold else -1.0
        
        return tick_numbers, ending_depth
    
    @staticmethod
    def __find_depth_rate(ticks: list[_Tick_Number]) -> float:
        """
        Find the rate of change between all two points and then find the average
        of that.
        """
        rates = [
            abs(ticks[i]['pixels'] - ticks[j]['pixels']) / abs(ticks[i]['depth'] - ticks[j]['depth'])
            for i in range(len(ticks) - 1)
            for j in range(i + 1, len(ticks))
        ]
        return sum(rates) / len(rates)

    @staticmethod
    def __guess_start(tick_numbers: list[_Tick_Number], rate: float) -> float:

        logger.debug(f'Guessing start depth based off of {len(tick_numbers)} points')
    
        start_guess = sum(t['depth'] - (t['pixels'] / rate) for t in tick_numbers)

        if start_guess < 0:
            return 0
        else:
            average_start_guess = start_guess / len(tick_numbers)
            return round(average_start_guess * 2) / 2

    @staticmethod
    def __guess_end(ticks: list[Segment], rate: float, ruler_bounds: tuple[Segment, Segment], start_depth: float) -> float:

        # Try the lowest tick first
        lowest = reduce(lambda a, b: a if a.average_y > b.average_y else b, ticks)
        table_bottom = segment_subtract(
            Segment(ruler_bounds[0].lowest_point, ruler_bounds[1].lowest_point),
            ruler_bounds[0].highest_point
        )
        
        # There are 20 major ticks in BBS_137_REV_8_99
        threshold = 0.95 * table_bottom.average_y

        # If it's not within that last tick, resort to the table bottom
        depth = lowest.average_y if lowest.average_y > threshold else table_bottom.average_y

        guessed = depth / rate
        return start_depth + round(guessed * 2) / 2
