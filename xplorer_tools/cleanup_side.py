import logging
from xplorer_tools.flatten_ndarray_3_to_1 import flatten_ndarray_3_to_1
from typing import Literal
import numpy as np

logger = logging.getLogger(__name__)

def clean_side(image: np.ndarray, side: Literal[0,1,2,3,4]=0, ratio=0.6, leeway=2) -> np.ndarray:
    """
    Takes a 2D image and attempts to remove any lines that outline the image.
    This function assumes the color is white (so do a 255-ndarray before)

    The side specifies which side to clean
     - 0 - all
     - 1 - top
     - 2 - right
     - 3 - bottom
     - 4 - left

    `ratio` is the ratio of white pixels to black. By default this is 6/10. So
    if there are 20 total pixels and if more than 12 of them are NOT black, then
    the side will be cleaned.
    """
    
    ret: np.ndarray = image.copy()
    if len(image.shape) == 3:
        analyze_this = flatten_ndarray_3_to_1(image)
    elif len(image.shape) == 2:
        analyze_this = image.copy()
    else:
        raise Exception('clean_side must be called with a 2 or 3 dimensional array')
    
    match side:
        case 0:
            top, found = remove_top(analyze_this, ret.shape[0], leeway, 0, ratio)
            if found:
                ret[:top] = 0

            low, found = remove_bottom(analyze_this, ret.shape[0], leeway, 0, ratio)
            if found:
                ret[(ret.shape[0]-low-1):] = 0

            left, found = remove_left(analyze_this, ret.shape[1], leeway, 0, ratio)
            if found:
                ret[:, :left] = 0

            right, found = remove_right(analyze_this, ret.shape[1], leeway, 0, ratio)
            if found:
                ret[:, (ret.shape[1]-right-1):] = 0

        case 1:
            top, found = remove_top(analyze_this, ret.shape[0], leeway, 0, ratio)
            if found:
                ret[:top] = 0
        case 2:
            right, found = remove_right(analyze_this, ret.shape[1], leeway, 0, ratio)
            if found:
                ret[:, (ret.shape[1]-right-1):] = 0
        case 3:
            low, found = remove_bottom(analyze_this, ret.shape[0], leeway, 0, ratio)
            if found:
                ret[(ret.shape[0]-low-1):] = 0
        case 4:
            left, found = remove_left(analyze_this, ret.shape[1], leeway, 0, ratio)
            if found:
                ret[:, :left] = 0
    
    return ret

def check_majority_not_black(pixels: np.ndarray, ratio: float) -> bool:
    return np.count_nonzero(pixels) > len(pixels) * ratio

def remove_left(reference: np.ndarray, limit: int, remaining: int, offset: int, ratio: float, found=False) -> tuple[int, bool]:

    if remaining == 0 and offset != limit:
        return offset, found
    elif remaining == 0 or offset == limit:
        return offset-1, found

    if check_majority_not_black(reference[:, offset], ratio):
        # return_val[:,offset] = 0
        return remove_left(reference, limit, 1, offset+1, ratio, found=True)
    else:
        return remove_left(reference, limit, remaining-1, offset+1, ratio, found)


def remove_bottom(reference: np.ndarray, limit: int, remaining: int, offset: int, ratio: float, found=False) -> tuple[int, bool]:

    if remaining == 0 and offset != limit:
        return offset, found
    elif remaining == 0 or offset == limit:
        return offset-1, found

    current_level = reference.shape[0] - offset - 1
    if check_majority_not_black(reference[current_level], ratio):
        # return_val[current_level] = 0
        
        return remove_bottom(reference, limit, 1, offset+1, ratio, found=True)
    else:
        return remove_bottom(reference, limit, remaining-1, offset+1, ratio, found)

def remove_right(reference: np.ndarray, limit: int, remaining: int, offset: int, ratio: float, found=False) -> tuple[int, bool]:

    if remaining == 0 and offset != limit:
        return offset, found
    elif remaining == 0 or offset == limit:
        return offset-1, found

    current_level = reference.shape[1] - offset - 1
    if check_majority_not_black(reference[:, current_level], ratio):
        # return_val[:, current_level] = 0
        
        return remove_right(reference, limit, 1, offset+1, ratio, found=True)
    else:
        return remove_right(reference, limit, remaining-1, offset+1, ratio, found)

def remove_top(reference: np.ndarray, limit: int, remaining: int, offset: int, ratio: float, found=False) -> tuple[int, bool]:

    if remaining == 0 and offset != limit:
        return offset, found
    elif remaining == 0 or offset == limit:
        return offset-1, found

    if check_majority_not_black(reference[offset], ratio):
        # return_val[offset] = 0
        
        return remove_top(reference, limit, 1, offset+1, ratio, found=True)
    else:
        return remove_top(reference, limit, remaining-1, offset+1, ratio, found)

# if side == 0 or side == 2:  # right
#     rope = leeway
#     while rope > 0:
#         while check_majority_not_black(analyze_this[:, (right_level-1)]) and right_level > left_level:
#             right_level -= 1
#             rope = 0
#         rope -= 1
#     ret[:, right_level:] = 0