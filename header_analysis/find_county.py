import logging
from detect_structure.helpers.find_descriptions.block_operations import *
from tools.types import *
from header_analysis.field_mistakes import MISTAKES
import re

logger = logging.getLogger(__name__)

def find_county(blocks: list[ocr_analysis]) -> str:

    # Patterns we use to single out the specific section of string we want at the end
    catch_county = re.compile(r'.*[co][o0]un+t[yv]\s*', re.IGNORECASE)
    catch_drill = re.compile(r'\s*dr[il1]ll[il1]ng[\s\.,]*m.?eth[o0]d.*', re.IGNORECASE)



    # Need to find first occurrence of 'drilling method'
    blocks.sort(key=lambda b: left_of_ocr_coords(b['coords_group']))
    has_drill = [b for b in blocks if re.search(MISTAKES['drilling method'], b['text'])]


    if len(has_drill) == 0:
        logger.warning('Could not find "drilling method" in blocks')
        return ''
    else:
        logger.debug(f'Found "drilling method" in {[b["text"] for b in has_drill]}')
        drill_block = has_drill[0]


    top_bound = top_of_ocr_coords(drill_block['coords_group']) - 6
    low_bound = bottom_of_ocr_coords(drill_block['coords_group']) + 6 

    def check_within(block: ocr_analysis):
        center = center_ocr_coords(block['coords_group'])
        return center[1] > top_bound and center[1] < low_bound
    
    important = [ b for b in blocks if check_within(b) ]
    important.sort(key=lambda b: left_of_ocr_coords(b['coords_group']))

    # County *might* appear in the description field, so best to limit it to a
    # more likely location
    has_county = [b for b in important if re.search(MISTAKES['county'], b['text'])]


    if len(has_county) == 0:
        return ''
        raise Exception('Could not find "county" in blocks')
    else:
        logger.debug(f'Found "county" in {[b["text"] for b in has_county]}')
        # section_block = has_section[0]

    line_str = ' '.join([b['text'] for b in important])

    ret = re.sub(catch_county, '', line_str)
    ret = re.sub(catch_drill, '', ret)
    ret = ret.strip()

    return ret
