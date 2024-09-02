import logging
from detect_structure.helpers.find_descriptions.block_operations import *
from tools.types import *
from header_analysis.field_mistakes import MISTAKES
import re

logger = logging.getLogger(__name__)

# def find_route(blocks: list[ocr_analysis], header: PageHeader):
def find_desc(blocks: list[ocr_analysis]) -> str:

    # Need to find occurrences of description and logged by

    blocks.sort(key=lambda b: left_of_ocr_coords(b['coords_group']))

    has_desc = [b for b in blocks if re.search(MISTAKES['description'], b['text'])]
    if len(has_desc) == 0:
        logger.warning('Could not find "description" in blocks')
        return ''
    else:
        logger.debug(f'Found "description" in {[b["text"] for b in has_desc]}')
        desc_block = has_desc[0]

    has_log = [b for b in blocks if re.search(MISTAKES['logged by'], b['text'])]
    if len(has_log) == 0:
        logger.critical('Could not find "logged by" in blocks')
        logger.warning('Could not find "logged by" in blocks')
        return ''
    else:
        logger.debug(f'Found "logged by" in {[b["text"] for b in has_log]}')
        log_block = has_log[0]

    # For description specifically it can use two lines (max as far as I've
    # seen) so we need to be a bit more thorough when searching

    if desc_block != log_block:

        desc_loc: re.Match[str] = re.search(MISTAKES['description'], desc_block['text']) # type: ignore
        description_at_begin = desc_block['text'].find('desc') < 2
        description_at_begin = desc_loc.start(0) < 2
        description_at_end = len(desc_block['text']) - desc_loc.end(0) < 2

        if description_at_begin:
            left_bound = left_of_ocr_coords(desc_block['coords_group'])
            right_bound = left_of_ocr_coords(log_block['coords_group'])
            text_height = height_span_ocr_coords(desc_block['coords_group'])
            bottom_bound = bottom_of_ocr_coords(desc_block['coords_group'])
            top_bound = bottom_bound - text_height*2
        elif description_at_end:
            left_bound = right_of_ocr_coords(desc_block['coords_group'])
            right_bound = left_of_ocr_coords(log_block['coords_group'])
            text_height = height_span_ocr_coords(desc_block['coords_group'])
            bottom_bound = bottom_of_ocr_coords(desc_block['coords_group'])
            top_bound = bottom_bound - text_height*2
        else:
            return ''
            raise Exception('Unhandled case')

        def check_within(block: ocr_analysis):
            center = center_ocr_coords(block['coords_group'])
            l = center[0] > left_bound
            r = center[0] < right_bound
            u = center[1] > top_bound
            d = center[1] < bottom_bound
            return l and r and u and d

        # Look for centers within those bounds
        important = [
            b for b in blocks if check_within(b)
        ]

        # Remove the word "description" and combine everything laterally and then
        # vertically

        for b in important:
            b['text'] = re.sub('description', '', b['text'], flags=re.IGNORECASE)

        important = join_horizontal_blocks(important)
        important = join_vertical_blocks(important)
        important.sort(key=lambda b: left_of_ocr_coords(b['coords_group']))
        ret = (' '.join([b['text'] for b in important])).strip()

        ret = re.sub(r'^i[Ll]|^lL|^1[Ll]', 'IL', ret)
        ret = re.sub(r'^[uv][s$]', 'US', ret, flags=re.IGNORECASE)
        
        return ret

    else:
        return ''
