import logging
from detect_structure.helpers.find_descriptions.block_operations import *
from tools.types import *
from header_analysis.field_mistakes import MISTAKES
import re

logger = logging.getLogger(__name__)

# def find_route(blocks: list[ocr_analysis], header: PageHeader):
def find_logger(blocks: list[ocr_analysis]) -> str:

    catch_log = re.compile(r'.*logged ?[bs8][yv]\s*', re.IGNORECASE)

    # Need to find first occurrence of 'logged by'
    blocks.sort(key=lambda b: left_of_ocr_coords(b['coords_group']))

    has_log = [b for b in blocks if re.search(MISTAKES['logged by'], b['text'])]
    if len(has_log) == 0:
        logger.warning('Could not find "logged by" in blocks, but it is okay')
        return ''
        # raise Exception('Could not find "logged by" in blocks')
    else:
        logger.debug(f'Found "logged by" in {[b["text"] for b in has_log]}')
        log_block = has_log[0]

    # log_loc: re.Match[str] = re.search(MISTAKES['logged_by'], log_block['text']) # type: ignore
    
    top_bound = top_of_ocr_coords(log_block['coords_group']) - 6
    low_bound = bottom_of_ocr_coords(log_block['coords_group']) + 6

    def check_within(block: ocr_analysis):
        center = center_ocr_coords(block['coords_group'])
        return center[1] > top_bound and center[1] < low_bound

    important = [ b for b in blocks if check_within(b) ]
    important.sort(key=lambda b: left_of_ocr_coords(b['coords_group']))

    line_str = ' '.join([b['text'] for b in important])

    # Replace "logged by" and everything before it
    ret = re.sub(catch_log, '', line_str).strip()

    return ret
