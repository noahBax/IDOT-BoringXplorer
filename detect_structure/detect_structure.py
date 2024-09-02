import logging
import os
import pickle
from xplorer_tools.segment_operations import Segment
from detect_structure.helpers.table_structure.table_structure import Table_Structure
from detect_structure.helpers.table_structure.table_structure_half import Table_Structure_Half
from xplorer_tools.types import *
from numpy import ndarray
from typing import Any, Literal

# At least, the basic structure, is always the same. There is a description
# column, a blows column, a UCS column, and then a moisture column, then it
# repeats

# Of course it could never be that easy and there are certain classes of
# documents that does not work for. Might need to have someone point those out
# manually

# For right now, I'm gonna focus on the "BBS 137 Rev. 8-99" and "BBS 138 Rev.
# 8-99" version

CACHE_LOCATION = './ProcessingReports/detect_structure/structure_cache.pkl'
struct_cache: dict[str, dict[str, (Table_Structure | Table_Structure_Half)]] = {}
cache_read = False

logger = logging.getLogger(__name__)


def check_cache(key: str, page_num: int) -> (Table_Structure | Table_Structure_Half) | Literal[False]:

    logger.debug(f'Checking with key {key} and page {page_num}')
    
    global struct_cache, cache_read

    page = str(page_num)
    
    if not cache_read:
        if os.path.exists(CACHE_LOCATION):
            with open(CACHE_LOCATION, 'rb') as p:
                logger.debug('Reading struct cache file')
                struct_cache = pickle.load(p)
        else:
            logger.debug('No cache file found, creating empty cache array')
            struct_cache = {}
            return False
        
        cache_read = True

    logger.debug('Checking struct cache')
    
    if key in struct_cache and page in struct_cache[key]:
        logger.debug('Using cached version')
        ret = struct_cache[key][page]
        ret.refresh_all_segments()
        return ret
    else:
        return False


def update_cache(key_str: str, page_num: int, value: Table_Structure | Table_Structure_Half) -> None:

    page = str(page_num)

    if not cache_read:
        check_cache('', 0)
    
    if key_str not in struct_cache:
        struct_cache[key_str] = {}
        
    struct_cache[key_str][page] = value

    logger.debug('Writing cache, wait...')
    with open(CACHE_LOCATION, 'wb') as p:
        pickle.dump(struct_cache, p)

    logger.debug('Done')

def detect_structure(horizontals: list[Segment],
                     verticals: list[Segment],
                     gray_image: ndarray[Any, Any],
                     color_image: ndarray[Any, Any], 
                     use_cache=False,
                     path='',
                     page=-1, 
                     draw_visuals=False,
                     visuals_folder='visuals'
                    ) -> Table_Structure|Table_Structure_Half:

    # A page is made up of 2 (or 1) vertical sections. Each vertical section is
    # made up of 1 big description section with a small ruler (elevation)
    # running along its right side and 3 other columns to the right of that.

    # For "BBS 137 Rev. 8-99" and "BBS 138 Rev. 8-99", the longest line that
    # intersects all vertical lines is the TOP of the table

    # Rather unfortunately due to the length of the lines we are working with,
    # the combination process can warp the resultant line so that it doesn't
    # intersect where it's supposed to. Until I possibly fix this, the best way
    # to find the table top is to check to see if it intersects with the longer
    # middle lines

    # Check the cache
    if use_cache:
        hit = check_cache(path, page)
        if hit:
            return hit
        
    # Check to see whether there are 1 or 2 columns
    beegg_verticals = [v for v in verticals if v.length > gray_image.shape[0]/2]
    if len(beegg_verticals) < 9:
        ret = Table_Structure_Half(horizontals, verticals, gray_image, color_image, draw_visuals, visuals_folder)
    else:
        ret = Table_Structure(horizontals, verticals, gray_image, color_image, draw_visuals, visuals_folder)

    # Update cache
    if use_cache:
        update_cache(path, page, ret)
    
    return ret

    # print('Table top:')
    # print(str_segment(table_top))

    # From what it looks like there are now two things to do
    # 1) Look at the larger lithology description columns
    # 2) Look at the 3 smaller columns (BUM columns)

    # * Looking at case 2 first...
    # When dealing with the BUM columns, the particular section we are
    # interested in are going to be enclosed inside two upper and lower lines.
    # This looks like in most cases for the "BBS 137 Rev. 8-99" and "BBS 138
    # Rev. 8-99" formats this goes at a 1 foot sample every 2.5 feet from 4'
    # till 25' and then after goes at a 1 foot sample every 5 feet.

    # USUALLY that is the case. Sometimes they don't follow that pattern.
    # Sometimes the person in charge is just like "Ooooo I had a pink skittle
    # today and that's rare. Let's start 6" earlier!" which is fine, yeah pink
    # skittles are exciting, but it causes the BUM entry to be out of alignment
    # with the bottom of the ruler. This means that we have to single out BUM
    # sections by watching for a line every 1' and can't just do the easy route.
    # If you want to see real hell check out "/Adams County/001-3383 SOIL 1991.pdf"

    # A similar, but more apparent problem is with the Lithology stuff. With
    # both of those in mind, we need to build a kind of continuous ruler/scale
    # that spans everything.