import logging
from detect_structure.helpers.find_descriptions.block_operations import *
from tools.types import *
from header_analysis.field_mistakes import MISTAKES
import re

logger = logging.getLogger(__name__)

# def find_route(blocks: list[ocr_analysis], header: PageHeader):
def find_section(blocks: list[ocr_analysis]) -> str:

    catch_section = re.compile(r'.*[s$]ect[il1][o0]n\s*', re.IGNORECASE)
    catch_location = re.compile(r'\s*l.?[o0].?ca.?t.?[il1].?[o0].?n.*', re.IGNORECASE)

    # Need to find first occurrence of 'route'
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

    # Section *might* appear in the description field, so best to limit it to a
    # more likely location
    has_section = [b for b in important if re.search(MISTAKES['section'], b['text'])]

    if len(has_section) == 0:
        logger.warning('Could not find "section" in blocks')
        return ''
    else:
        logger.debug(f'Found "section" in {[b["text"] for b in has_section]}')
        # section_block = has_section[0]

    line_str = ' '.join([b['text'] for b in important])

    ret = re.sub(catch_section, '', line_str)
    ret = re.sub(catch_location, '', ret)
    ret = ret.strip()

    return ret
