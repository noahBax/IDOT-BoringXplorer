import logging
from detect_structure.helpers.find_descriptions.block_operations import *
from xplorer_tools.types import *
from header_analysis.field_mistakes import MISTAKES
import re

logger = logging.getLogger(__name__)

# def find_route(blocks: list[ocr_analysis], header: PageHeader):
def find_route(blocks: list[ocr_analysis]) -> str:

    catch_route = re.compile(r'\s*r?oute\s*', re.IGNORECASE)
    catch_desc = re.compile(r'\s*de[s$]cr[il1]pt[il1][o0]n.*', re.IGNORECASE)

    # Need to find first occurrence of 'route'
    blocks.sort(key=lambda b: left_of_ocr_coords(b['coords_group']))

    has_route = [b for b in blocks if re.search(MISTAKES['route'], b['text'])]
    if len(has_route) == 0:
        logger.warning('Could not find "route" in blocks')
        return ''
    else:
        logger.debug(f'Found "route" in {[b["text"] for b in has_route]}')
        route_block = has_route[0]
        # If there is more than one route, the first one is most likely to be
        # correct

    # Perform the same routine for description
    has_desc = [b for b in blocks if re.search(MISTAKES['description'], b['text'])]
    if len(has_desc) == 0:
        logger.warning('Could not find "description" in blocks')
        return ''
    else:
        logger.debug(f'Found "description" in {[b["text"] for b in has_desc]}')
        desc_block = has_desc[0]

    # If they are in the same group, that makes things simpler
    if route_block == desc_block:

        t = route_block['text']
        
        # Should mean that it as simple as finding where "route" is and where
        # "description" is and getting the text in between
        route_begins = re.search(r'^\s*route', t, re.IGNORECASE)

        if not route_begins:
            raise Exception('Unhandled case')

        # Just replace the ends and take the result
        t = re.sub(catch_route, '', t)
        t = re.sub(catch_desc, '', t)

        return t
    
    # If they are not in the same group, we need to get all of the blocks between those two
    else:
        # Grab all text blocks within the same horizontal axis as the two
        axes = (
            average_y_of_ocr_coords(route_block['coords_group']),
            average_y_of_ocr_coords(desc_block['coords_group'])
        )
        top_bound = min(axes) - 6
        low_bound = max(axes) + 6

        between = [
            b for b in blocks
            if average_y_of_ocr_coords(b['coords_group']) < low_bound and average_y_of_ocr_coords(b['coords_group']) > top_bound
        ]

        # If there's just two of them
        if len(between) == 2:
            # Combine them and repeat above
            t = route_block['text'] + desc_block['text']
            t = re.sub(catch_route, '', t)
            t = re.sub(catch_desc, '', t)

            return t
        else:
            # Sort them then combine
            between.sort(key=lambda b: left_of_ocr_coords(b['coords_group']))
            t = ' '.join([b['text'] for b in between])
            t = re.sub(catch_route, '', t)
            t = re.sub(catch_desc, '', t)

            return t

    
