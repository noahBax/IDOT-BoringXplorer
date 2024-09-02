from copy import deepcopy
from typing import Any, Literal, overload
from numpy import ndarray
from PIL import Image, ImageDraw
from skimage.draw import line
from skimage.color import gray2rgb
from tools.segment_operations import int_ify_segment, Segment
from tools.stringify_types import str_segment
import numpy as np

def __line_rr_cc(segment: Segment):
    int_segment = int_ify_segment(segment)

    y1, x1 = int_segment.pt_1['y'], int_segment.pt_1['x']
    y2, x2 = int_segment.pt_2['y'], int_segment.pt_2['x']

    return line(y1, x1, y2, x2)

def draw_raw_visuals(shape, horizontals: list[Segment], verticals: list[Segment]) -> np.ndarray:

    blank_image = np.zeros(shape, dtype=np.uint8)
    for segment in horizontals:
        rr, cc = __line_rr_cc(segment)
        blank_image[rr, cc] = (0, 255, 0)

    for segment in verticals:
        rr, cc = __line_rr_cc(segment)
        blank_image[rr, cc] = (255, 0, 0)

    return blank_image

def draw_segment_visuals(shape, horizontals: list[Segment], verticals: list[Segment], draw_text=True, font_size=40) -> np.ndarray:
    blank_image = np.zeros(shape, dtype=np.uint8)
    for segment in horizontals:
        rr, cc = __line_rr_cc(segment)
        blank_image[rr, cc] = (0, 255, 0)

    for segment in verticals:
        rr, cc = __line_rr_cc(segment)
        blank_image[rr, cc] = (255, 0, 0)

    
    if draw_text:
        image = Image.fromarray(blank_image)
        draw_me = ImageDraw.Draw(image)

        for index, segment in enumerate(horizontals):
            rr, cc = __line_rr_cc(segment)
            draw_me.text((cc[0] - 10, rr[0]), str(index), fill=(0, 255, 0), font_size=font_size)
            draw_me.text((cc[-1] - 10, rr[-1]), str(index), fill=(0, 255, 0), font_size=font_size)

        for index, segment in enumerate(verticals):
            rr, cc = __line_rr_cc(segment)
            draw_me.text((cc[0] - 10, rr[0]), str(index), fill=(255, 0, 0), font_size=font_size)
            draw_me.text((cc[-1] - 10, rr[-1]), str(index), fill=(255, 0, 0), font_size=font_size)

        return np.array(image, dtype=np.uint8)
    else:
        return blank_image


def draw_on_image(image: ndarray[Any, np.dtype[Any]],
                  horizontals: list[Segment],
                  verticals: list[Segment],
                  create_copy=True,
                  draw_text=True,
                  font_size=40,
                  return_as_array=False,
                  horizontal_segment_color: tuple[int, int, int]=(0, 255, 0),
                  vertical_segment_color: tuple[int, int, int]=(255, 0, 0)
                ) -> np.ndarray | Image.Image:
                
    if create_copy:
        color_me = deepcopy(image)
    else:
        color_me = image
    for segment in horizontals:
        rr, cc = __line_rr_cc(segment)
        color_me[rr, cc] = horizontal_segment_color

    for segment in verticals:
        rr, cc = __line_rr_cc(segment)
        color_me[rr, cc] = vertical_segment_color

    colorful_image = Image.fromarray(color_me)

    if draw_text:
        draw_me = ImageDraw.Draw(colorful_image)
        for index, segment in enumerate(horizontals):
            rr, cc = __line_rr_cc(segment)

            draw_me.text((cc[0] - 10, rr[0]), str(index), fill=horizontal_segment_color, font_size=font_size)
            draw_me.text((cc[-1] - 10, rr[-1]), str(index), fill=horizontal_segment_color, font_size=font_size)

        for index, segment in enumerate(verticals):
            rr, cc = __line_rr_cc(segment)

            draw_me.text((cc[0] - 10, rr[0]), str(index), fill=vertical_segment_color, font_size=font_size)
            draw_me.text((cc[-1] - 10, rr[-1]), str(index), fill=vertical_segment_color, font_size=font_size)

    if return_as_array:
        return np.array(colorful_image, dtype=np.uint8)
    else:
        return colorful_image

def draw_segment_on_image(image: np.ndarray,
                          segment: Segment,
                          color: tuple[int, int, int],
                          text='',
                          font_size=40) -> np.ndarray:

    rr, cc = __line_rr_cc(segment)

    image[rr, cc] = color

    if text:

        pre_text = Image.fromarray(image)
        draw_text = ImageDraw.Draw(pre_text)
        
        start_text = int_ify_segment(segment).leftmost_point
        draw_text.text((start_text['x'] - 10, start_text['y']), text, fill=color, font_size=font_size)

        image = np.array(pre_text, dtype=np.uint8)
    
    return image

def colorize_array(gray_image: ndarray) -> ndarray:
    c = gray2rgb(gray_image)
    return c