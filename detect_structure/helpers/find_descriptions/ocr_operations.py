import logging
from tools.types import ocr_coords, Coordinate, ocr_analysis, ocr_result
from detect_structure.helpers.find_descriptions.block_operations import *
from tools.cleanup_side import clean_side
from paddleocr import PaddleOCR
from math import floor
import re
import numpy as np
from skimage.io import imsave

logger = logging.getLogger(__name__)

temp_number = 0

def __look_for_texts(color_image: np.ndarray, top_bar: float, low_bar: float, ocr_instance: PaddleOCR, page_offset: Coordinate) -> list[ocr_analysis]:
    global temp_number

    logger.debug(f'Analyzing between {top_bar} and {low_bar}')

    y1 = floor(top_bar)
    y2 = floor(low_bar)
    cropped = color_image[y1:y2]
    cropped = clean_side(cropped, leeway=5, ratio=0.4)

    # imsave(f'simple_texts/lith_block{temp_number}.png', cropped)
    temp_number += 1

    ocr_results = ocr_instance.ocr(cropped, cls=True)

    logger.debug(f'Found results {ocr_results}')

    if ocr_results[0] == None:
        logger.debug('Found end of table?')
        return []
    else:
        results = ocr_results[0]
    
    logger.debug('Results:')
    logger.debug(results)

    ret: list[ocr_analysis] = []
    for r in results:
        corrected_coords: ocr_coords = tuple((c[0], c[1]+top_bar) for c in r[0]) # type: ignore
        a: ocr_analysis = {
            # 'coords_group': r[0],
            'coords_group': corrected_coords,
            'text': r[1][0],
            'confidence': r[1][1],
            'page_offset': page_offset
        }
        ret.append(a)
    
    return ret

def find_text_blobs(depth_lines: list[float],
                    top_depth: float,
                    bottom_depth: float,
                    colored_area,
                    offset: Coordinate,
                    ocr_text_blobs: PaddleOCR) -> list[list[ocr_analysis]]:

    text_blobs: list[list[ocr_analysis]] = []

    # "top_depth" and "bottom_depth" are honorary depth_lines

    if len(depth_lines) > 0:
        first = __look_for_texts(colored_area, top_depth, depth_lines[0], ocr_text_blobs, offset)
        last  = __look_for_texts(colored_area, depth_lines[-1], bottom_depth, ocr_text_blobs, offset)
        text_blobs.append(first)

        if len(depth_lines) > 1:
            for i in range(len(depth_lines) - 1):
                t = __look_for_texts(colored_area, depth_lines[i], depth_lines[i+1], ocr_text_blobs, offset)
                text_blobs.append(t)
        text_blobs.append(last)
    else:
        # No depth lines were recognized in this column. Just look between the top and bottom
        one_blob = __look_for_texts(colored_area, top_depth, bottom_depth, ocr_text_blobs, offset)
        text_blobs.append(one_blob)
    
    return text_blobs

def group_words(text_blobs: list[list[ocr_analysis]], partial_description_width: float) -> list[tuple[list[ocr_analysis], list[ocr_analysis]]]:
    """
    OCR produces text that it thinks is connected left-to-right, but it is not
    always accurate in this. We want to fix that AND combine text that continues
    from one line onto the one below it.

    This takes `text_blobs` which is a list of all the text recognized between
    two depth lines (output from find_text_blobs) as well as `current_top_depth`
    which is the current depth at the top of the current description column.
    """
    
    ret: list[tuple[list[ocr_analysis], list[ocr_analysis]]] = []
    # found_end = False

    logger.debug(f'Grouping texts {[t["text"] for text_blob in text_blobs for t in text_blob]}')

    for blob in text_blobs:

        # if found_end:
        #     raise Exception('Thought we found end but found found something after')

        if len(blob) == 0:
            logger.debug('There were no depths in a block. Might be end of table')
            # found_end = True
            continue
            
        # Remove the depth numbers from the blob but also associate them with this blob
        blob, depths = __remove_BBS_137_REV_8_99_depth_numbers(blob, partial_description_width)
        logger.debug(f'Removed depths {depths}')

        if len(depths) > 1:
            logger.debug('Found multiple depths in a block')
            logger.debug(depths)

        if len(blob) > 1:
            # Combine text snippets by x and then y
            blob = join_horizontal_blocks(blob)
            blob = join_vertical_blocks(blob)

        ret.append((blob, depths))
    
    return ret

def __majority_numbers(query: str) -> bool:
    numbers = sum(c.isdigit() for c in query)
    dots = query.count('.')

    ratio = (numbers + dots) / len(query)

    if len(query) > 3:
        return ratio > 0.8
    else:
        return numbers + dots == len(query)
    
# Mistakes that cause humans to trip up. I've seen machines do it too
possible_mistakes = {
    'G': '6',
    'b': '6',
    'I': '1',
    'i': '1',
    'L': '1',
    'l': '1',
    'O': '0',
    'o': '0',
    'g': '9',
    'A': '4',
    'E': '8',
    'U': '0',
    'v': '0'
}
    
def __remove_BBS_137_REV_8_99_depth_numbers(results: list[ocr_analysis],
                                            column_width: float
                                        ) -> tuple[list[ocr_analysis], list[ocr_analysis]]:
    """
    Returns a list of the 
    
    BBS_137_REV_8_99 format has depth annotations at the bottom of each
    lithographic section if there is one following it. It is numbers and is on
    the right side of the description column

    Because the BBS_137_REV_8_99 handling so far is using the partial
    description, the depth numbers should be in the rightmost 16% of the column
    """

    past_this = column_width * 0.76
    result: list[ocr_analysis] = []
    depths: list[ocr_analysis] = []

    logger.debug('Asked to remove')
    logger.debug(results)

    for r in results:
        if center_ocr_coords(r['coords_group'])[0] > past_this:
            fix_me = r['text']
            # Replace possible mistakes
            for k in possible_mistakes:
                fix_me = fix_me.replace(k, possible_mistakes[k])
            
            # Check to see if this is a depth marker
            if __majority_numbers(fix_me):

                # I've had this issue once where a speck was misread as a . and
                # I think the best way to handle this is to just default to the
                # last period (this is America).

                if fix_me.count('.') > 1:
                    fix_me = fix_me.replace('.', '', fix_me.count('.')-1)
                    fix_me = re.sub(r'(?<=\d)[, :](?=\d)', '.', fix_me)

                has_dot = re.search(r'\d\.\d|^\.\d', fix_me)
                if not has_dot:
                    has_comma = re.search(r'\d\,\d|^\,\d', fix_me)
                    if has_comma and len(has_comma.groups()) == 1:
                        fix_me = re.sub(r',(?=\d)', '.', fix_me)

                try:
                    float(fix_me)
                    depths.append(r)
                except ValueError as e:
                    logger.warning(f'Tried to convert value {fix_me} to float and failed. Logging 0 instead')
                    r['text'] = '0'
                    depths.append(r)
                
                continue
                

        result.append(r)

    return result, depths

def fix_ocr_results(ocr_results: list[ocr_result], check_number=True):

    def try_number(s: str):
        try:
            float(s)
        except ValueError:
            raise Exception(f'OCR recognized non-number string:', s)

    logger.debug(f'Fixing {ocr_results}')

    # First modify the OCR results
    for index, result in enumerate(ocr_results):
        
        corrected_text: str = result[1][0]
        
        # Remove negatives. Everywhere. Because it's a robot
        corrected_text = re.sub(r'[-.~"](?=\d)', '', corrected_text)
                    
        # Replace possible mistakes
        for k in possible_mistakes:
            corrected_text = corrected_text.replace(k, possible_mistakes[k])

        # And check to see if it can be represented as a number
        if check_number:
            try_number(corrected_text)

        replacement = (corrected_text, result[1][1])
        ocr_results[index] = (result[0], replacement)
    
    return ocr_results