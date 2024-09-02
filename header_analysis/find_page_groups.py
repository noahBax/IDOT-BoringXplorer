from copy import deepcopy
import logging
from math import ceil, floor
import os
from enum import Enum, auto
import numpy as np
from paddleocr import PaddleOCR
from skimage.io import imsave
from tools.types import *
from header_analysis.analyze_waters import Water_Obj, analyze_water
from header_analysis.analyze_header import Header_Obj, analyze_header
from detect_structure.helpers.table_structure.table_structure import Table_Structure
from detect_structure.helpers.draw_ocr_text_bounds import draw_ocr_text_bounds
from detect_structure.helpers.table_structure.table_structure_half import Table_Structure_Half

logger = logging.getLogger(__name__)

class doc_state(Enum):
    waiting_for_new = auto()
    building_but_no_limit = auto()
    building_with_limit = auto()

def find_page_groups(log_locations: list[int],
                     structure_dict: dict[int, Table_Structure_Half|Table_Structure],
                     image_dict: dict[int, tuple[np.ndarray, np.ndarray]],
                     ocr_cls_false: PaddleOCR,
                     draw_visuals=False,
                     visuals_folder='visuals'
                     ) -> tuple[dict[int, Header_Obj], dict[int, Water_Obj]]:
    """
    Right now it's just a hacky way that looks like it should work a majority of
    the time. It assumes that
     1) The pages of a singular report are added in order
     2) All pages of a singular report are included

    If you wanted to make this more robust, the Header_Obj type contains all of
    the fields that are present in the header of each soil boring log page.
    Compare them and make sure that only pages that have similarity in certain
    fields get put into the same document.
    """

    header_dict: dict[int, Header_Obj] = {}
    water_dict: dict[int, Water_Obj] = {}
    # ret: list[list[int]] = []
    # current_doc: list[int] = []

    # DOCUMENT_STATE: doc_state
    # DOCUMENT_STATE = doc_state.waiting_for_new
    
    # page_limit: int = -1

    for index, loc in enumerate(log_locations):

        # structure_dict[loc].draw_structure()
        header = __get_header_info(structure_dict[loc],
                                   image_dict[loc][1],
                                   ocr_cls_false,
                                   index,
                                   len(log_locations),
                                   draw_visuals=draw_visuals,
                                   visuals_folder=visuals_folder)
        water = __get_water_info(structure_dict[loc],
                                 image_dict[loc][1],
                                 ocr_cls_false,
                                 draw_visuals=draw_visuals,
                                 visuals_folder=visuals_folder)
        header_dict[loc] = header
        water_dict[loc] = water
        logger.debug(f'Found header: {header}')

    #     match DOCUMENT_STATE:
    #         case doc_state.waiting_for_new:

    #             # Sanity check to make sure pages are not out of order
    #             if header['page_num'] != None and header['page_num'] > 1:
    #                 logger.critical(f'New page listed as page {header["page_num"]}')
    #                 raise Exception('Received pages out of order')

    #             if header['page_total'] == 1:
    #                 logger.debug('Creating a new document of length 1')
    #                 ret.append([loc])
                    
    #             else:
    #                 logger.debug('Creating a new document')
    #                 current_doc = [loc]

    #                 if header['page_total'] == None:
    #                     logger.debug('"page total" field is missing')
    #                     DOCUMENT_STATE = doc_state.building_but_no_limit
    #                 else:
    #                     logger.debug(f'Page total is {header["page_total"]}')
    #                     page_limit = header["page_total"]
    #                     DOCUMENT_STATE = doc_state.building_with_limit

    #         case doc_state.building_but_no_limit:
                
    #             # See if document isn't continued later by a rock core log
    #             if header['page_num'] != None and header['page_num'] == 1:

    #                 DOCUMENT_STATE, ret, current_doc, page_limit = __handle_core_log(header, ret, loc, current_doc)
    #                 continue

    #             current_doc.append(loc)

    #             # Check to see if we can update that limit
    #             if header['page_total'] != None:
    #                 page_limit = header['page_total']

    #                 # Is the page limit valid?
    #                 if page_limit < len(current_doc):
    #                     logger.critical(f'Updated page limit to {page_limit} while length of current document is {len(current_doc)}')
    #                     raise Exception('Received pages in unknown order')

    #                 logger.debug('Found a page limit')
    #                 DOCUMENT_STATE = doc_state.building_with_limit

    #                 # Sanity check
    #                 if header['page_num'] != None and header['page_num'] != len(current_doc):
    #                     logger.critical(f'New page has number {header["page_num"]} and current doc has {len(current_doc)} pages')
    #                     raise Exception('Received pages out of order')

    #                 DOCUMENT_STATE, ret, current_doc, page_limit = __check_at_page_limit(ret, current_doc, page_limit, DOCUMENT_STATE)

    #         case doc_state.building_with_limit:

    #             # See if document isn't continued later by a rock core log
    #             if header['page_num'] != None and header['page_num'] == 1:
                    
    #                 DOCUMENT_STATE, ret, current_doc, page_limit = __handle_core_log(header, ret, loc, current_doc)
    #                 continue

    #             current_doc.append(loc)

    #             # Sanity checks
    #             if header['page_total'] != None and header['page_total'] != page_limit:
    #                 logger.critical(f'New page had limit {header["page_total"]} and current doc had limit {page_limit}')
    #                 raise Exception('Received pages in unknown order')
                
    #             if header['page_num'] != None and header['page_num'] != len(current_doc):
    #                 logger.critical(f'New page has number {header["page_num"]} and current doc has {len(current_doc)} pages')
    #                 raise Exception('Received pages out of order')

    #             DOCUMENT_STATE, ret, current_doc, page_limit = __check_at_page_limit(ret, current_doc, page_limit, DOCUMENT_STATE)

    
    # if len(current_doc) > 0:
    #     logger.warning('Ending last document prematurely; no remaining pages')
    #     ret.append(current_doc)

    return header_dict, water_dict


def __get_water_info(structure: Table_Structure|Table_Structure_Half,
                     color_image: np.ndarray,
                     ocr_water_info: PaddleOCR,
                     draw_visuals=False,
                     visuals_folder='visuals') -> Water_Obj:

    logger.debug('Finding water')

    # Cut down the header to just the area that contains water info
    if draw_visuals:
        structure.draw_structure(color_image, visuals_folder=visuals_folder) # type: ignore

    top_y = ceil(structure.header_top.average_y)+3
    low_y = floor(structure.table_top.average_y)-2
    left_x = ceil(structure.left_half['moisture'][1].average_x)+2
    if isinstance(structure, Table_Structure_Half):
        right_x = floor(structure.table_top.rightmost_point['x']) - 20
        logger.debug('Is half a table')
    else:
        right_x = floor(structure.right_half['ruler'][0].average_x)-5
        logger.debug('Is a full table')

    logger.debug(f'Cropping water table to {[top_y, low_y, left_x, right_x]}')

    water_color = color_image[top_y:low_y, left_x:right_x]
    
    texts = ocr_water_info.ocr(water_color, cls=False)[0]
    if texts == None or len(texts) == 0:
        raise Exception('OCR could not find any text in the water section')
    
    # Convert these to the much nicer ocr_analysis
    blocks: list[ocr_analysis] = [
        {
            'coords_group': text[0],
            'confidence': text[1][1],
            'page_offset': { 'x': 0, 'y': 0 },
            'text': text[1][0].replace('_', '')
        }
        for text in texts
    ]

    logger.debug('-- Found these texts --')
    for b in blocks:
        logger.debug(f'"{b["text"]}" : {b["confidence"]}')

    if draw_visuals:
        with_text = draw_ocr_text_bounds(texts, water_color)
        imsave(os.path.join(visuals_folder, 'water_hedaer.png'), with_text)

    water_obj = analyze_water(blocks)
    return water_obj

def __get_header_info(structure: Table_Structure|Table_Structure_Half,
                      color_image: np.ndarray,
                      ocr_header_info: PaddleOCR,
                      known_page: int | None,
                      known_page_limit: int | None,
                      draw_visuals=False,
                      visuals_folder='visuals') -> Header_Obj:

    logger.debug('Finding header')
    
    # Now need to cut down header to just text we are interested in
    header_bottom = floor(structure.table_top.average_y) - 3
    header_left = floor(structure.left_half['full_description'][0].average_x)

    header_color = deepcopy(color_image[:header_bottom, header_left:])

    cut_top = floor(structure.header_top.average_y) - 3
    cut_left = floor(structure.left_half['ruler'][0].average_x) - header_left - 2

    header_color[cut_top:, cut_left:] = 255

    texts = ocr_header_info.ocr(header_color, cls=False)[0]
    if texts == None or len(texts) == 0:
        raise Exception('OCR could not find any text in the header')

    # Convert these to the much nicer ocr_analysis
    blocks: list[ocr_analysis] = [
        {
            'coords_group': text[0],
            'confidence': text[1][1],
            'page_offset': { 'x': 0, 'y': 0 },
            'text': text[1][0].replace('_', '')
        }
        for text in texts
    ]

    logger.debug('-- Found these texts --')
    for b in blocks:
        logger.debug(f'"{b["text"]}" : {b["confidence"]}')

    if draw_visuals:
        with_text = draw_ocr_text_bounds(texts, header_color)
        imsave(os.path.join(visuals_folder, 'head_test.png'), with_text)

    header_obj = analyze_header(blocks, known_page, known_page_limit)
    return header_obj


def __check_at_page_limit(return_obj: list[list[int]],
                          old_doc: list[int],
                          current_limit: int,
                          current_state: doc_state
                          ) -> tuple[doc_state, list[list[int]], list[int], int]:
    """
    Returns
    `new state`, `new ret`, `new current doc`, `new page limit`
    """
    
    return_state: doc_state = current_state
    return_document: list[int] = old_doc
    return_limit: int = current_limit

    if len(old_doc) == current_limit:
        logger.debug(f'Document length met page limit. Result: {old_doc}')
        return_obj.append(old_doc)
        return_limit = -1
        return_document = []
        return_state = doc_state.waiting_for_new

    return return_state, return_obj, return_document, return_limit


def __handle_core_log(header: Header_Obj,
                      return_obj: list[list[int]],
                      page_index: int,
                      old_doc: list[int]
                      ) -> tuple[doc_state, list[list[int]], list[int], int]:
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
    return_obj.append(old_doc)
    
    # Does the new document end immediately?
    if header['page_total'] == 1:
        logger.debug('Creating a new document of length 1')
        return_obj.append([page_index])
        return_state = doc_state.waiting_for_new
        return_document = []
        return_limit = -1
        
    else:
        logger.debug('Creating a new document')
        return_document = [page_index]

        if header['page_total'] == None:
            logger.debug('"page total" field is missing')
            return_limit = -1
            return_state = doc_state.building_but_no_limit
        else:
            logger.debug(f'Page total is {header["page_total"]}')
            return_limit = header["page_total"]
            return_state = doc_state.building_with_limit

    return return_state, return_obj, return_document, return_limit
