import logging
from detect_structure.helpers.find_descriptions.block_operations import *
from tools.types import *
from header_analysis.field_mistakes import MISTAKES
import re

logger = logging.getLogger(__name__)

def find_location(blocks: list[ocr_analysis]) -> str:

    catch_location = re.compile(r'.*locat[il1!][o0]n\s*', re.IGNORECASE)



    # Need to find first occurrence of 'location'
    blocks.sort(key=lambda b: left_of_ocr_coords(b['coords_group']))

    has_location = [b for b in blocks if re.search(MISTAKES['location'], b['text'])]

    if len(has_location) == 0:
        logger.warning('Could not find "location" in blocks')
        return ''
    else:
        logger.debug(f'Found "location" in {[b["text"] for b in has_location]}')
        location_block = has_location[0]

    top_bound = top_of_ocr_coords(location_block['coords_group']) - 6
    low_bound = bottom_of_ocr_coords(location_block['coords_group']) + 6 

    def check_within(block: ocr_analysis):
        center = center_ocr_coords(block['coords_group'])
        return center[1] > top_bound and center[1] < low_bound
    
    important = [ b for b in blocks if check_within(b) ]
    important.sort(key=lambda b: left_of_ocr_coords(b['coords_group']))

    line_str = ' '.join([b['text'] for b in important])

    # Replace "logged by" and everything before it
    ret = re.sub(catch_location, '', line_str).strip()

    return ret
