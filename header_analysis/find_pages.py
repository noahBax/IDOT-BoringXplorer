import logging
from detect_structure.helpers.find_descriptions.block_operations import *
from xplorer_tools.types import *
from header_analysis.field_mistakes import MISTAKES
from header_analysis.parse_location import number_mistakes
import re

logger = logging.getLogger(__name__)

def find_pages(blocks: list[ocr_analysis]) -> tuple[int | None, int | None]:

    def fix_numbers(s: str) -> str:
        for k in number_mistakes:
            s = s.replace(k, number_mistakes[k])
        return s

    catch_page = re.compile(r'.*pa[g9]e:?\s*', re.IGNORECASE)
    

    blocks.sort(key=lambda b: left_of_ocr_coords(b['coords_group']))
    has_page = [b for b in blocks if re.search(MISTAKES['page'], b['text'])]

    if len(has_page) == 0:
        logger.warning('Could not find "page" in blocks')
        return None, None
        # raise Exception(f'Could not find "page" in blocks')
    else:
        logger.debug(f'Found "page" in {[b["text"] for b in has_page]}')
        page_block = has_page[0]

    top_bound = top_of_ocr_coords(page_block['coords_group']) - 6
    low_bound = bottom_of_ocr_coords(page_block['coords_group']) + 6 

    def check_within(block: ocr_analysis):
        center = center_ocr_coords(block['coords_group'])
        on_right_side = left_of_ocr_coords(block['coords_group']) >= left_of_ocr_coords(page_block['coords_group'])
        return center[1] > top_bound and center[1] < low_bound and on_right_side
    
    important = [ b for b in blocks if check_within(b) ]
    important.sort(key=lambda b: left_of_ocr_coords(b['coords_group']))

    line_str = ' '.join([b['text'] for b in important])
    logger.debug(f'Important string is: {line_str}')

    page_specifier = re.sub(catch_page, '', line_str).strip()

    page_split = re.split(r'\s*[o0][ftl]\s*', page_specifier)

    if len(page_split) <= 1:
        # This means that splitting on 'of' didn't do anything. However, if 'of'
        # was in the original string, then we can look between 'of' and 'page'
        # to at least find the page number
        of_loc = re.search(r'[o0][ftl]', page_specifier)
        if of_loc:
            potential_number = page_specifier[:of_loc.start(0)]
            nums = ''.join(re.findall(r'\d', fix_numbers(potential_number)))
            if len(nums) > 0:
                return int(nums), None
                
        # Any of those fail? At least we tried
        return None, None

    page_u = ''.join(re.findall(r'\d', fix_numbers(page_split[0])))
    total_u = ''.join(re.findall(r'\d', fix_numbers(page_split[1])))

    if page_u == '':
        page_num = None
    else:
        page_num = int(page_u)

    if total_u == '':
        page_total = None
    else:
        page_total = int(total_u)

    return page_num, page_total
