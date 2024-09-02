import logging
from detect_structure.helpers.find_descriptions.block_operations import *
from tools.types import *
from header_analysis.field_mistakes import MISTAKES
import re

logger = logging.getLogger(__name__)

def find_end_field(blocks: list[ocr_analysis], catch_pattern: re.Pattern, mistakes_key: str, okay_to_fail=False) -> str:

    blocks.sort(key=lambda b: left_of_ocr_coords(b['coords_group']))

    has_ender = [b for b in blocks if re.search(MISTAKES[mistakes_key], b['text'])]

    if len(has_ender) == 0:
        if okay_to_fail:
            logger.warning((f'Could not find "{mistakes_key}" in blocks'))
            return ''
        else:
            raise Exception(f'Could not find "{mistakes_key}" in blocks')
    else:
        logger.debug(f'Found "{mistakes_key}" in {[b["text"] for b in has_ender]}')
        field_block = has_ender[0]

    top_bound = top_of_ocr_coords(field_block['coords_group']) - 6
    low_bound = bottom_of_ocr_coords(field_block['coords_group']) + 6 

    def check_within(block: ocr_analysis):
        center = center_ocr_coords(block['coords_group'])
        return center[1] > top_bound and center[1] < low_bound
    
    important = [ b for b in blocks if check_within(b) ]
    important.sort(key=lambda b: left_of_ocr_coords(b['coords_group']))

    line_str = ' '.join([b['text'] for b in important])

    ret = re.sub(catch_pattern, '', line_str).strip()

    return ret
