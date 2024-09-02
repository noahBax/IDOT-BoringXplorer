import logging
import re
from header_analysis.find_end_field import find_end_field
from xplorer_tools.types import *
from detect_structure.helpers.find_descriptions.block_operations import *

catch_date = re.compile(r'\d{1,2}\/\d{1,2}\/\d{2,4}')
catch_date_boring = re.compile(r'.*d[ao][tf]e?\s*', re.IGNORECASE)

logger = logging.getLogger(__name__)

def find_date(blocks: list[ocr_analysis]) -> str:
    

    # First look through all of the blocks and see if we can find something that
    # fits the regex
    blocks.sort(key=lambda b: left_of_ocr_coords(b['coords_group']))

    for b in blocks:
        has_date = re.search(catch_date, b['text'])
        if has_date:
            return has_date.group(0)

    # If we didn't find anything, the date stream might be a little mangled
    logger.debug('Could not recognize date string. Resorting to the prior method')
    date = find_end_field(blocks, catch_date_boring, 'date', True)
    date = re.sub(r'[.,]', '', date)

    if sum(c.isdigit() for c in date) < 6:
        return ''

    return date