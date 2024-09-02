"""
I had something working before, but it took up WAY too much memory when it came
to large documents that had lots of soil boring logs. For the sake of speed, a
page image is held by the main loop so that it can be used quickly later on as
opposed to having to ask pymupdf to go and open up the document again. I lost my
train of thought while writing this, but the goal is to find page groups using
just the header before we determine structure data. Then we can use the page
groups we find a ahead of time to put the main loops inside an outer loop that
only gives the inner loops the current group. I'd imagine that the max length of
a document is something like 8 pages? Which is around 200 MiB at 8 bit color
depth. That's way better than larger documents that have something like 34 soil
boring logs in them. By itself that's not much, but there are enough copies and
smaller sections of it floating around and it adds up fast. I can't honestly say
whether it is the code I have written or whether it is PaddlePaddle (likely the
latter, it's caused issues before)
"""

import logging
from math import floor
import os
import numpy as np
from paddleocr import PaddleOCR
from skimage.io import imsave
from xplorer_tools.types import *
from detect_structure.helpers.find_descriptions.block_operations import join_horizontal_blocks
from detect_structure.helpers.draw_ocr_text_bounds import draw_ocr_text_bounds
from header_analysis.find_pages import find_pages
from header_analysis.find_page_groups import doc_state

logger = logging.getLogger(__name__)


def get_page_nums(ocr_cls_false: PaddleOCR, color_image: np.ndarray, draw_visuals=False, visuals_folder='visuals') -> tuple[int | None, int | None]:

    # Crop to the top 30% and right 50%
    left = floor(color_image.shape[1] / 2)
    bottom = floor(color_image.shape[0]*0.13)
    crop_top = color_image[:bottom, left:]

    # Get text blocks
    texts = ocr_cls_false.ocr(crop_top, cls=False)[0]
    if texts == None:
        raise Exception('Second scan of page top gave no text? Is this possible?')

    # Convert these to the much nicer ocr_analysis
    blocks: list[ocr_analysis] = [
        {
            'coords_group': text[0],
            'confidence': text[1][1],
            'page_offset': { 'x': 0, 'y': 0 },
            'text': text[1][0]
        }
        for text in texts
    ]

    blocks = join_horizontal_blocks(blocks, lateral_threshold=16)

    if draw_visuals:
        path = os.path.join(visuals_folder, f'page_top_get_nums.png')
        with_text = draw_ocr_text_bounds(texts, crop_top, in_place=False)
        imsave(path, with_text)

    page_num, page_total = find_pages(blocks)
    return page_num, page_total

class Page_Group_Builder(TypedDict):
    current_doc: list[int]
    DOCUMENT_STATE: doc_state
    page_limit: int
    
def get_empty_page_builder() -> Page_Group_Builder:
    return {
        'current_doc': [],
        'DOCUMENT_STATE': doc_state.waiting_for_new,
        'page_limit': -1
    }

def build_page_group(current_builder: Page_Group_Builder, page_num: int | None, page_total: int | None, doc_page_num: int, is_last_page: bool) -> tuple[list[list[int]], Page_Group_Builder]:

    return_group: list[list[int]] = []

    # Check to see that the pages are at least in order
    if current_builder['DOCUMENT_STATE'] != doc_state.waiting_for_new and doc_page_num != current_builder['current_doc'][-1] + 1:
        logger.debug('Received a page that was not adjacent to the last recorded in the current group')
        logger.debug('Purging the current document in the assumption this is intentional')

        return_group.append(current_builder['current_doc'])

        current_builder['current_doc'] = []
        current_builder['DOCUMENT_STATE'] = doc_state.waiting_for_new
        current_builder['page_limit'] = -1
        

    match current_builder['DOCUMENT_STATE']:
        case doc_state.waiting_for_new:

            # Sanity check to make sure pages are not out of order
            if page_num != None and page_num > 1:
                logger.critical(f'New page listed as page {page_num}')
                raise Exception('Received pages out of order')

            if page_total == 1:
                logger.debug('Creating a new document of length 1')
                return_group.append([doc_page_num])
            else:
                logger.debug('Creating a new document')
                current_builder['current_doc'] = [doc_page_num]

                if page_total == None:
                    logger.debug('"page total" field is missing')
                    current_builder['DOCUMENT_STATE'] = doc_state.building_but_no_limit
                else:
                    logger.debug(f'Page total is {page_total}')
                    current_builder['page_limit'] = page_total
                    current_builder['DOCUMENT_STATE'] = doc_state.building_with_limit

        case doc_state.building_but_no_limit:
            
            # See if document isn't continued later by a rock core log
            if page_num != None and page_num == 1:

                return_group = __handle_core_log(page_total, return_group, doc_page_num, current_builder)
                return return_group, current_builder

            current_builder['current_doc'].append(doc_page_num)

            # Check to see if we can update that limit
            if page_total != None:
                current_builder['page_limit'] = page_total

                # Is the page limit valid?
                if page_total < len(current_builder['current_doc']):
                    logger.critical(f'Updated page limit to {page_total} while length of current document is {len(current_builder["current_doc"])}')
                    raise Exception('Received pages in unknown order')

                logger.debug('Found a page limit')
                current_builder['DOCUMENT_STATE'] = doc_state.building_with_limit

                # Sanity check
                if page_num != None and page_num != len(current_builder['current_doc']):
                    logger.critical(f'New page has number {page_num} and current doc has {len(current_builder["current_doc"])} pages')
                    raise Exception('Received pages out of order')

                return_group = __check_at_page_limit(return_group, current_builder)

        case doc_state.building_with_limit:

            # See if document isn't continued later by a rock core log
            if page_num != None and page_num == 1:
                
                return_group = __handle_core_log(page_total, return_group, doc_page_num, current_builder)
                return return_group, current_builder

            current_builder['current_doc'].append(doc_page_num)

            # Sanity checks
            if page_total != None and page_total != current_builder['page_limit']:
                logger.critical(f'New page had limit {page_total} and current doc had limit {current_builder["page_limit"]}')
                raise Exception('Received pages in unknown order')
            
            if page_num != None and page_num != len(current_builder['current_doc']):
                logger.critical(f'New page has number {page_num} and current doc has {len(current_builder["current_doc"])} pages')
                raise Exception('Received pages out of order')

            return_group = __check_at_page_limit(return_group, current_builder)

    if is_last_page and len(current_builder['current_doc']) > 0:
        return_group.append(current_builder['current_doc'])
        current_builder['current_doc'] = []
        current_builder['DOCUMENT_STATE'] = doc_state.waiting_for_new
        current_builder['page_limit'] = -1

    return return_group, current_builder


def __handle_core_log(page_total: int | None,
                      return_obj: list[list[int]],
                      page_index: int,
                      current_builder: Page_Group_Builder
                      ) -> list[list[int]]:
    """
    Returns
    `new state`, `new ret`, `new current doc`, `new page limit`
    """

    logger.debug('Found a page 1 while building a document')
    logger.debug('Assuming that the previous document led to rock coring log')

    return_state: doc_state
    return_document: list[int]
    return_limit: int

    # Add in old document
    return_obj.append(current_builder['current_doc'])
    
    # Does the new document end immediately?
    if page_total == 1:
        logger.debug('Creating a new document of length 1')
        return_obj.append([page_index])
        return_state = doc_state.waiting_for_new
        return_document = []
        return_limit = -1
        
    else:
        logger.debug('Creating a new document')
        return_document = [page_index]

        if page_total == None:
            logger.debug('"page total" field is missing')
            return_limit = -1
            return_state = doc_state.building_but_no_limit
        else:
            logger.debug(f'Page total is {page_total}')
            return_limit = page_total
            return_state = doc_state.building_with_limit

    current_builder['DOCUMENT_STATE'] = return_state
    current_builder['current_doc'] = return_document
    current_builder['page_limit'] = return_limit

    return return_obj

def __check_at_page_limit(return_obj: list[list[int]],
                          current_builder: Page_Group_Builder,
                          ) -> list[list[int]]:
    
    return_state: doc_state = current_builder['DOCUMENT_STATE']
    return_document: list[int] = current_builder['current_doc']
    return_limit: int = current_builder['page_limit']

    if len(current_builder['current_doc']) == current_builder['page_limit']:
        logger.debug(f'Document length met page limit. Result: {current_builder["current_doc"]}')
        return_obj.append(current_builder['current_doc'])
        return_limit = -1
        return_document = []
        return_state = doc_state.waiting_for_new


    current_builder['DOCUMENT_STATE'] = return_state
    current_builder['current_doc'] = return_document
    current_builder['page_limit'] = return_limit
    return return_obj