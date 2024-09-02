import logging
from detect_structure.helpers.find_descriptions.block_operations import *
from tools.types import *
from header_analysis.field_mistakes import MISTAKES
import re

logger = logging.getLogger(__name__)

def find_both_stations(blocks: list[ocr_analysis]) -> tuple[str, str]:
    """
    Finds both the station under struct no and under boring no.

    Returns a tuple of `struct station` and `boring station`
    """

    catch_station = re.compile(r'.*[s$]tat[il1][o0]n\s*', re.IGNORECASE)



    blocks.sort(key=lambda b: left_of_ocr_coords(b['coords_group']))

    has_station = [b for b in blocks if re.search(MISTAKES['station'], b['text'])]

    if len(has_station) < 2:
        logger.warning(f'Could not find enough station instances')
        return '', ''
    else:
        logger.debug(f'Found "station" in {[b["text"] for b in has_station]}')
        station_boring_block = has_station[-1]
        station_struct_block = has_station[-2]

    def catch_around(block: ocr_analysis) -> str:
        
        top_bound = top_of_ocr_coords(block['coords_group']) - 6
        low_bound = bottom_of_ocr_coords(block['coords_group']) + 6 

        def check_within(block: ocr_analysis):
            center = center_ocr_coords(block['coords_group'])
            return center[1] > top_bound and center[1] < low_bound

        important = [ b for b in blocks if check_within(b) ]
        important.sort(key=lambda b: left_of_ocr_coords(b['coords_group']))

        line_str = ' '.join([b['text'] for b in important])

        ret = re.sub(catch_station, '', line_str).strip()

        return ret
    
    return catch_around(station_struct_block), catch_around(station_boring_block)