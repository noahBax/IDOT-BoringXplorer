from functools import reduce
import json
import logging
import os
from typing import Any, Literal
import numpy as np
from pathlib import Path
from numpy import ndarray
from skimage.io import imsave
from xplorer_tools.segment_operations import Segment, segment_add
from xplorer_tools.types import Coordinate
from line_detection.helpers.draw_visuals import *
from line_detection.helpers.get_line_segments import get_line_segments

CACHE_LOCATION = r'.\ProcessingReports\line_detection\lineCache.json'
line_cache: dict[str, dict[int, tuple[list[tuple[Coordinate, Coordinate]], list[tuple[Coordinate, Coordinate]]]]]
cache_read = False

OFF_CONSTANT = 1/40 * np.pi
base = 0 + np.pi/2

horizontals = np.linspace(base - OFF_CONSTANT, base + OFF_CONSTANT, 32, endpoint=True)
verticals = np.linspace(0 - OFF_CONSTANT, 0 + OFF_CONSTANT, 32, endpoint=True)

logger = logging.getLogger(__name__)

def check_cache(key: str, page_num: int) -> tuple[list[Segment], list[Segment]] | Literal[False]:
    global line_cache, cache_read

    page = str(page_num)
    
    if not cache_read:
        if os.path.exists(CACHE_LOCATION):
            with open(CACHE_LOCATION) as file:
                logger.debug('Reading line cache file')
                line_cache = json.load(file)
        else:
            logger.debug('No cache file found, creating empty cache array')
            line_cache = {}
        
        cache_read = True

    logger.debug('Checking line cache')
    
    if key in line_cache and page in line_cache[key]:
        # Prep the segments for return
        h_cache =  line_cache[key][page][0]
        v_cache =  line_cache[key][page][1]
        
        horizontals = [Segment(h[0], h[1]) for h in h_cache]
        verticals = [Segment(v[0], v[1]) for v in v_cache]
        
        return horizontals, verticals
    else:
        return False


def update_cache(key_str: str, page: int, value: tuple[list[Segment], list[Segment]]) -> None:

    if not cache_read:
        check_cache('', 0)
    
    # Prep the segments for file
    # arr_str_1 = '||'.join([s.toJSON() for s in value[0]])
    # arr_str_2 = '||'.join([s.toJSON() for s in value[1]])
    
    if key_str not in line_cache:
        line_cache[key_str] = {}
        
    line_cache[key_str][page] = ([s.toSerializable() for s in value[0]], [s.toSerializable() for s in value[1]])

    logger.debug('Writing cache, wait...')
    with open(CACHE_LOCATION, 'w') as file:
        json.dump(line_cache, file)
    logger.debug('Done')


def detect_lines(gray_image: ndarray[Any, Any], color_image: ndarray[Any, Any], use_cache=False, path='', page=-1, draw_visuals=False, visuals_folder='visuals') -> tuple[list[Segment], list[Segment]]:

    if draw_visuals:
        Path(visuals_folder).mkdir(parents=True, exist_ok=True)
        imsave(os.path.join(visuals_folder, 'base.png'), color_image)


    # Check the line cache first
    if use_cache:
        potential_hit = check_cache(path, page)
        if potential_hit:
            logger.debug('Found cache entry, skipping line detection')
            if draw_visuals:
                shape = color_image.shape
                
                refined: np.ndarray = draw_segment_visuals(shape, *potential_hit)
                colored: np.ndarray = draw_on_image((255-color_image), *potential_hit, return_as_array=True)

                imsave(os.path.join(visuals_folder, 'bones.png'), refined)
                imsave(os.path.join(visuals_folder, 'drawing.png'), colored)

            return potential_hit

    # This is the image that we are specifically going to analyze for lines.
    analyze_me = (255 - gray_image)

    # Find segments
    raw_horizontal: list[Segment]
    combined_horizontal: list[Segment]
    raw_vertical: list[Segment]
    combined_vertical: list[Segment]
    
    raw_vertical, combined_vertical = get_line_segments(
        analyze_me,
        thetas=verticals,
        line_length=170,
        line_gap=10,
        alongside_gap=10,
        max_angle_difference=np.pi / 3,
        base_angle={'x': 0, 'y': 1},
        compress_maximum=280,
        project_onto='v')
    
    # Sometimes (e.g. Adams County/001-0019 SOIL 2002.pdf), because weird people
    # scanned the document in weird, you get a page plus some space off to the
    # side where another page would be, but it's not actually there. Weird
    # right? We need to get rid of that extra not-page space.

    # To do that, find the rightmost vertical line, subtract [0,40] from it,
    # crop the page to that area, then re-run the get_line_segments sequence

    if analyze_me.shape[0] < analyze_me.shape[1]:
        logger.debug('Page is ~weird~, rerunning after cropping')

        rightmost_line = reduce(lambda a,b: b if a.rightmost_point['x'] < b.rightmost_point['x'] else a, combined_vertical)
        right_bounds = segment_add(rightmost_line, {'x': -20, 'y': 0})

        x1, y1 = 0, 0
        x2, y2 = round(right_bounds.rightmost_point['x']), analyze_me.shape[0]

        analyze_me = analyze_me[y1:y2, x1:x2]

        raw_vertical, combined_vertical = get_line_segments(
            analyze_me,
            thetas=verticals,
            line_length=170,
            line_gap=10,
            alongside_gap=10,
            max_angle_difference=np.pi / 3,
            base_angle={'x': 0, 'y': 1},
            compress_maximum=280,
            project_onto='v')

    logger.debug('Done with verticals')

    # After that work that might have to be redone, continue1

    raw_horizontal, combined_horizontal = get_line_segments(
        analyze_me,
        thetas=horizontals,
        line_length=170,
        line_gap=10,
        alongside_gap=25,
        max_angle_difference=np.pi/5,
        compress_maximum=121,
        project_onto='h')
    
    # Specifically for the full page, there sometimes is some text that is off
    # to the left side of the page (e.g. Adams County/001-0507 SOIL 2009.pdf
    # page 0) and that messes up things. Ergo, get rid of vertical lines in the
    # first 25% of the page horizontally that are not the biggest
    combined_vertical = get_gud_verticals(combined_vertical, analyze_me.shape)
    
    # Update the line cache with our new result
    if use_cache:
        update_cache(path, page, (combined_horizontal, combined_vertical))

    if draw_visuals:
        shape = color_image.shape
        
        raw = draw_raw_visuals(shape, raw_horizontal, raw_vertical)
        refined = draw_segment_visuals(shape, combined_horizontal, combined_vertical)
        colored = draw_on_image((255-color_image), combined_horizontal, combined_vertical, return_as_array=True)

        imsave(os.path.join(visuals_folder, 'raw.png'), raw)
        imsave(os.path.join(visuals_folder, 'bones.png'), refined)
        imsave(os.path.join(visuals_folder, 'drawing.png'), colored)


    return combined_horizontal, combined_vertical

def get_gud_verticals(combined_vertical: list[Segment], shape) -> list[Segment]:
    page_width: int = shape[1]
    good_verticals = [v for v in combined_vertical if v.average_x > page_width / 4]
    bad_verticals = [v for v in combined_vertical if v.average_x <= page_width / 4]

    # Sort and grab first bad vertical
    bad_verticals.sort(key=lambda v: v.square_length, reverse=True)

    good_verticals.append(bad_verticals[0])

    return good_verticals