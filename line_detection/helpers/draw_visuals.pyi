from typing import overload, Literal
import numpy as np
from xplorer_tools.segment_operations import Segment
from PIL import Image

@overload
def draw_on_image(image: np.ndarray,
                  horizontals: list[Segment],
                  verticals: list[Segment],
                  return_as_array: Literal[False] = False,
                  draw_text=True,
                  font_size=40,
                  horizontal_segment_color: tuple[int, int, int]=(0, 255, 0),
                  vertical_segment_color: tuple[int, int, int]=(255, 0, 0)
                ) -> Image.Image: ...

@overload
def draw_on_image(image: np.ndarray,
                  horizontals: list[Segment],
                  verticals: list[Segment],
                  return_as_array: Literal[True] = True,
                  draw_text=True,
                  font_size=40,
                  horizontal_segment_color: tuple[int, int, int]=(0, 255, 0),
                  vertical_segment_color: tuple[int, int, int]=(255, 0, 0)
                ) -> np.ndarray: ...

def draw_segment_on_image(image: np.ndarray,
                          segment: Segment,
                          color: tuple[int, int, int],
                          text='',
                          font_size=40) -> np.ndarray: ...

def draw_raw_visuals(shape,
                     horizontals: list[Segment],
                     verticals: list[Segment]) -> np.ndarray: ...

def draw_segment_visuals(shape,
                         horizontals: list[Segment],
                         verticals: list[Segment],
                         draw_text=True,
                         font_size=40) -> np.ndarray: ...