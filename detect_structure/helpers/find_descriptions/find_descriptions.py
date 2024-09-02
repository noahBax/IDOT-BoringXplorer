"""
If we are trying to find descriptions, we should look within the bounds of the
table as stated by the table_structure object

I think there are 4 steps to developing this algorithm

1) Find lines spanning the width of the description column. Use those to
   establish lithology_formation's. Looking at the spreadsheets, a
   lithology_formation *can* be more nuanced than that, but this is just a proof
   of concept.
2) Look for words inside the bounds of each lithology_formation
3) Group the words together with some algorithm
4) The topmost group of words is obviously at the start of the section, but for
   the other word groupings, map them onto the soil_ruler and then add that as a
   label to the lithology_formation.
"""

import logging
from math import floor, pi
import os
from pathlib import Path
from typing import Literal
from paddleocr import PaddleOCR
from skimage.io import imsave
from xplorer_tools.stringify_types import str_segment
from xplorer_tools.types import Coordinate, ocr_analysis, ocr_result
from xplorer_tools.segment_operations import Segment, int_ify_segment
from detect_structure.helpers.soil_depth_ruler.soil_depth_ruler import Soil_Depth_Ruler
from detect_structure.helpers.lithology_formation import Lithology_Formation
from detect_structure.helpers.table_structure.table_structure import Table_Structure
from detect_structure.helpers.table_structure.table_structure_half import Table_Structure_Half
from line_detection.helpers.get_line_segments import get_line_segments
from line_detection.helpers.draw_visuals import draw_segment_visuals, draw_on_image
from line_detection.detect_lines import horizontals
from detect_structure.helpers.find_descriptions.block_operations import *
from detect_structure.helpers.find_descriptions.ocr_operations import find_text_blobs, group_words
from detect_structure.helpers.draw_ocr_text_bounds import draw_ocr_text_bounds
from xplorer_tools.cleanup_side import clean_side
import numpy as np

logger = logging.getLogger(__name__)

def find_descriptions(color_image: np.ndarray,
                      gray_image: np.ndarray,
                      table: Table_Structure|Table_Structure_Half,
                      side: Literal['l', 'r'],
                      ocr_cls_false: PaddleOCR,
                      draw_visuals=False,
                      visuals_folder='visuals') -> list[Lithology_Formation]:
    """
    Right now this is just geared for the BBS_137_REV_8_99 format
    """

    # First crop image to correct side and find the soil_ruler
    soil_ruler: Soil_Depth_Ruler
    left: Segment
    right: Segment
    if side == 'l':
        soil_ruler = table.left_soil_depth_ruler
        left, right = table.left_half['partial_description']
        
    else:
        if isinstance(table, Table_Structure_Half):
            raise TypeError('Tried to call find_blow_counts on the right side with a half-table')
        soil_ruler = table.right_soil_depth_ruler
        left, right = table.right_half['partial_description']
    
    left = int_ify_segment(left)
    right = int_ify_segment(right)

    x1, y1 = left.highest_point['x'], left.highest_point['y']
    x2, y2 = right.lowest_point['x'], right.lowest_point['y']
    cropped_color = (255 - color_image[y1:y2, x1:x2])
    cropped_gray = (255 - gray_image[y1:y2, x1:x2])
    partial_description_width = x2 - x1


    # Now scan for horizontal lines

    combined_horizontal: list[Segment]
    _, combined_horizontal = get_line_segments(
        cropped_gray,
        thetas=horizontals,
        line_length=floor(cropped_gray.shape[1] * 0.6),
        line_gap=5,
        alongside_gap=35,
        max_angle_difference=np.pi/5,
        compress_maximum=35,
        angle_threshold=pi/18,
        project_onto='h')


    if draw_visuals:
        __draw_visuals(visuals_folder, cropped_gray, cropped_color, combined_horizontal)

    logger.debug('Found these horizontals:')
    logger.debug([str_segment(s) for s in combined_horizontal])

    # Check to see if the top line got recognized and if not, assign the top of
    # the description column as top line. Do the same for the bottom line.
    top_depth: float
    bottom_depth: float
    depth_lines: list[float]
    top_depth, bottom_depth, depth_lines = __find_top_and_bottom(cropped_color.shape[0], combined_horizontal)
    
    logger.debug('Results')
    logger.debug(f'top: {top_depth}, bottom: {bottom_depth}, remaining: {depth_lines}')

    page_offset_point: Coordinate = { 'x': x1, 'y': y1 }
    actual_depths = [soil_ruler.ask_for_depth(d, page_offset_point['y']) for d in depth_lines]
    actual_depths.insert(0, soil_ruler.ask_for_depth(top_depth, page_offset_point['y']))
    actual_depths.append(soil_ruler.ask_for_depth(bottom_depth, page_offset_point['y']))

    # Get rid of borders
    cropped_color = clean_side(cropped_color, leeway=5)
    
    # Get a list of ocr analyses
    text_blobs = find_text_blobs(
        depth_lines,
        top_depth,
        bottom_depth,
        cropped_color,
        page_offset_point,
        ocr_cls_false)

    if draw_visuals:
        # Draw boundaries of all of the text recognized inside of
        # find_text_blobs. We have to do some messy converting to get them from
        # the ocr_analysis format to the ocr_result, but it works
        draw_these: list[ocr_result] = [
            (b['coords_group'], (b['text'], b['confidence']))
            for blob in text_blobs
            for b in blob
        ]

        # I'm running out of fancy names
        description_with_text = draw_ocr_text_bounds(draw_these, cropped_color)

        imsave(os.path.join(visuals_folder, f'description_text_{side}.png'), description_with_text)
        
    
    # These *should* be different, but just in case
    if len(text_blobs) != len(actual_depths) - 1:
        logger.critical('Text blobs')
        logger.critical(len(text_blobs))
        logger.critical(text_blobs)
        logger.critical('Depths')
        logger.critical(len(actual_depths))
        logger.critical(actual_depths)
        raise Exception('text_blobs and actual_depths do not have the correct relationship') 

    ret: list[Lithology_Formation] = []

    # Between each depth line, find the individual text groupings and associated
    # depths
    word_groups = group_words(text_blobs, partial_description_width)
    last_top = actual_depths[0]
    for index, (group, depths) in enumerate(word_groups):
        top = last_top
        bottom = actual_depths[index+1]
        liths, last_bottom = __create_lithology(group, top, bottom, soil_ruler, depths)
        ret += liths
        last_top = last_bottom

    return ret

def __find_top_and_bottom(guessed_bottom: float, horizontals: list[Segment]) -> tuple[float, float, list[float]]:
    top_depth: float = 0.0
    bottom_depth: float = guessed_bottom
    logger.debug('Finding top and bottom')
    for s in horizontals:
        logger.debug(s)

    if len(horizontals) == 0:
        # Boring case
        return top_depth, bottom_depth, []

    if len(horizontals) == 1:
        # Less boring case
        depth = horizontals[0].average_y
        if depth <= 40:
            return depth, bottom_depth, []
        elif bottom_depth - depth <= 40:
            return top_depth, depth, []
        else:
            return top_depth, bottom_depth, [depth]

    # Normal case
    
    depth_lines = [s.average_y for s in horizontals]
    depth_lines.sort()
    if depth_lines[0] <= 40:
        top_depth = depth_lines[0]
        depth_lines = depth_lines[1:]

    if bottom_depth - depth_lines[-1] <= 40:
        bottom_depth = depth_lines[-1]
        depth_lines = depth_lines[:-1]

    return top_depth, bottom_depth, depth_lines


def __create_lithology(text_blocks: list[ocr_analysis],
                       top_depth: float,
                       bottom_depth: float,
                       soil_ruler: Soil_Depth_Ruler,
                       depth_list: list[ocr_analysis]) -> tuple[list[Lithology_Formation], float]:
    """
    Create lithology off of text blocks between two depth lines

    Returns a list tuple of a list of all of the Lithology_Formations that could
    be created and the bottommost depth of the last formation.
    """

    bottommost_depth = bottom_depth

    if bottom_depth - top_depth == 0.5 and len(text_blocks) == 0:
        logger.debug('Found an empty block matching a continuation. Shortcutting')
        l = Lithology_Formation('(continued)', top_depth, bottom_depth)
        return [l], bottom_depth

    """
    We are using depths to actually be the decider of bounds between
    Lithology_Sections. There are a few situations in which depths can appear

    a) No depths: This happens when a Lithology section continues after one
       column into the next
    b) One depth; doesn't continue: In this case, the depth is usually just
       above the ending line of the lithology section. There is no text below
       the depth number. The most common case.
    c) One depth; does continue: In this case, the depth marker is the end of
       one section and signals the start of another. The one that it signals the
       start of continues on into the next column though, so there won't be
       another depth in the section. (See Menard County/I-49 Peoria Rd over
       unnamed creek.pdf page 3)
    d) Multiple depths; doesn't continue: There are multiple depths listed and
       each signals the start of a new section. The last depth is usually within
       the last 1' of the ending line.
    e) Multiple depths; does continue: Arguably the same case as one depth; does
       continue.

    Given this, the plan should be find the ruler depths of all elevation
    depths. Partition each text_block into groups where each group has their top
    depth at or above an elevation depth.

    IF there are leftover text_block's, put them into a starting partition

    IF the deepest ruler depth has no partition members, it means it is not
    actually the bottom of the Lithology section and should be discarded

    ELSE bottommost_depth is set as the last elevation depth

    Anyway, each partition gets turned into a Lithology_Section
    """
    
    depth_locations = [
        soil_ruler.ask_for_depth(average_of_bottom_ocr_coords(depth['coords_group']), depth['page_offset']['y'])
        for depth in depth_list
    ]
    logger.debug(f'Found {len(depth_locations)} depth locations')
    logger.debug(depth_locations)
    logger.debug(f'Top depth: {top_depth}')
    logger.debug(f'Bottom depth: {bottom_depth}')

    text_blocks.sort(key=lambda t: average_of_top_ocr_coords(t['coords_group']))

    if len(depth_locations) == 0:
        logger.debug(f'NO depth locations. Creating lithology with text {text_blocks[0]["text"]} between {top_depth} and {bottom_depth}')
        l = Lithology_Formation(text_blocks[0]['text'], top_depth, bottom_depth)

        if len(text_blocks) == 1:
            logger.debug('No modifiers to add')

        else:
            logger.debug(f'Adding {len(text_blocks)-1} modifiers')
            for block in text_blocks[1:]:
                top_pos = average_of_top_ocr_coords(block['coords_group'])
                depth_in_soil = soil_ruler.ask_for_depth(top_pos, block['page_offset']['y'])

                logger.debug(f'Adding modifier "{block["text"]}" at {depth_in_soil} with source at {top_pos}')

                l.add_modifier(block['text'], depth_in_soil)

        return [l], bottom_depth

    else:

        logger.debug(f'There are {len(depth_locations)} depth locations')
        depth_locations.sort()
        partitions: dict[float, list[ocr_analysis]] = {key: [] for key in depth_locations}

        unallocated: list[ocr_analysis] = []

        # depth_locations are sorted in ascending order. So comparisons will
        # happen from the shallowest to deepest
        for block in text_blocks:

            # Given the sorted order
            top = soil_ruler.ask_for_depth(average_of_top_ocr_coords(block['coords_group']), block['page_offset']['y'])
            logger.debug(f'Partitioning ({top}) {block["text"]}')
            for d in depth_locations:
                logger.debug(f'Comparing to {d}')
                if top < d:
                    partitions[d].append(block)
                    break
            else:
                # It's in the bottommost partition
                unallocated.append(block)

        logger.debug(f'Resulting partitions: {partitions}')

        if len(unallocated) > 0:
            partitions[bottom_depth] = unallocated
            true_bottom = bottom_depth
        else:
            true_bottom = depth_locations

        # Create lithology's
        ret: list[Lithology_Formation] = []
        
        top_of_next = top_depth
        logger.debug('Creating lithologies')
        for bottom_of_part in sorted(partitions.keys()):
            
            blocks = partitions[bottom_of_part]
            logger.debug(f'Looking at {bottom_of_part}')

            # Odd case but it can happen
            blocks.sort(key=lambda o: average_of_top_ocr_coords(o['coords_group']))

            if len(blocks) == 0:
                logger.debug(f'Creating lithology with EMPTY text between {top_of_next} and {bottom_of_part}')
                l = Lithology_Formation('(continued)', top_of_next, bottom_of_part)
            else:
                logger.debug(f'Creating lithology with text {blocks[0]["text"]} between {top_of_next} and {bottom_of_part}')
                l = Lithology_Formation(blocks[0]['text'], top_of_next, bottom_of_part)

            logger.debug(f'Adding {max(0,len(blocks)-1)} modifiers')
            for block in blocks[1:]:

                top_pos = average_of_top_ocr_coords(block['coords_group'])
                depth_in_soil = soil_ruler.ask_for_depth(top_pos, block['page_offset']['y'])

                logger.debug(f'Adding modifier "{block["text"]}" at {depth_in_soil} with source at {top_pos}')

                l.add_modifier(block['text'], depth_in_soil)
            
            ret.append(l)
            top_of_next = bottom_of_part

        return ret, top_of_next


def __draw_visuals(visuals_folder: str, cropped_gray: np.ndarray, cropped_color: np.ndarray, horizontals: list[Segment]):
    Path(visuals_folder).mkdir(parents=True, exist_ok=True)
    shape = cropped_gray.shape
    shape = (shape[0], shape[1], 3)
    refined = draw_segment_visuals(shape, horizontals, [], font_size=20)
    imsave(os.path.join(visuals_folder, 'description_bones.png'), refined)
    
    text_on_me = draw_on_image(cropped_color, horizontals, [])
    text_on_me.save(os.path.join(visuals_folder, 'description_on_description.png'))