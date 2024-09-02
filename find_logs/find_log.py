import logging
from math import floor
import os
from pathlib import Path
import numpy as np
from tools.types import *
from skimage.io import imsave
from paddleocr import PaddleOCR
from labeled_sets import bbs_137_rev_8_99, page_dict
from detect_structure.helpers.find_descriptions.block_operations import join_horizontal_blocks, join_vertical_blocks
from detect_structure.helpers.draw_ocr_text_bounds import draw_ocr_text_bounds
from PIL import Image
from difflib import SequenceMatcher
import fitz

logger = logging.getLogger(__name__)


# Identification information should be in the top 30%
def find_bbs_137_rev_8_99_log_pages(file_path: str,
                              ocr_bbs_texts: PaddleOCR,
                              draw_visuals=False,
                              visuals_folder='visuals',
                            ) -> list[int]:
    """
    Look at all the pages of a document and look for all soil boring logs. Some
    documents contain more than one boring log so return a list of a list of all
    the pages in an individual log.
    """

    
    if draw_visuals:
        Path(os.path.join(visuals_folder, 'page_heads')).mkdir(parents=True, exist_ok=True)
    
    ret: list[int] = []
    
    # Look at text in the top of each page. Combine text that needs to be
    # combined and then look for "soil boring log"
    logger.info('Searching through page heads')

    with fitz.open(file_path) as pdf:

        logger.info(f'There are {pdf.page_count} pages in document')
        
        for page_num in range(pdf.page_count):
            page = pdf.load_page(page_num)
            colo_pixmap = page.get_pixmap(dpi=150)
            page = None

            color_image = Image.frombytes('RGB', size=(colo_pixmap.width, floor(colo_pixmap.height*0.13)), data=colo_pixmap.samples)
            colo_pixmap = None

            if color_image.width > color_image.height:
                color_image = color_image.crop((0, 0, 2500, color_image.height))

            is_soil_log_page: bool = __test_page_for_log(np.array(color_image),
                                                         ocr_bbs_texts,
                                                         page_num,
                                                         create_copy_of_image=False,
                                                         draw_visuals=draw_visuals,
                                                         visuals_folder=visuals_folder,)

            color_image = None

            if is_soil_log_page:
                ret.append(page_num)

            fitz.TOOLS.store_shrink(100)

    logger.info(f'File has {len(ret)} BBS_137_REV_8_99 soil boring logs')
    return ret
    
    # For testing purposes, just return the pre-labeled stuff
    # return page_dict[file_path]

def similar(a: str, b: str):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def __test_page_for_log(color_img: np.ndarray,
                        ocr_bbs_texts: PaddleOCR,
                        index: int,
                        create_copy_of_image=False,
                        draw_visuals=False,
                        visuals_folder='visuals') -> bool:

    texts = ocr_bbs_texts.ocr(color_img, cls=False)[0]
    if texts == None or len(texts) == 0:
        return False

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
        path = os.path.join(visuals_folder, 'page_heads', f'page_{index}.png')
        with_text = draw_ocr_text_bounds(texts, color_img, in_place=(not create_copy_of_image))
        imsave(path, with_text)


    logger.debug('Sequence matching')
    for b in blocks:
        sim = similar(b['text'], 'soil boring log')
        logger.debug(f'"{b["text"]}": {sim}')

        if sim >= 0.95:
            return True

    return False