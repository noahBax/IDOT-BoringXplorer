from skimage.transform import probabilistic_hough_line
from line_detection.helpers.create_segments import create_segments
from xplorer_tools.segment_operations import zero_segment
from xplorer_tools.vector_operations import vector_flip
from math import atan2
import numpy as np
from PIL import Image

def guess_page_orientation(grayscale_image: Image.Image, assess_count=1) -> float:
    """
    Guess the orientation of the page by getting long vertical lines running
    around vertical and average their slope.

    The grayscale image should NOT be inverted!

    A note: this method only works because we know something about the page: it
    has lines running up and down it.

    Theory for this comes from: https://www.themathdoctors.org/averaging-angles/
    """

    grayscale_array = np.array(grayscale_image, dtype=np.uint8)
    grayscale_array = (255 - grayscale_array)

    # Perform a quick scan to get all vertical lines
    verticals = np.linspace(-np.pi / 8, np.pi / 8, 120, endpoint=False)

    raw_segments: list[tuple[tuple[float, float], tuple[float, float]]] = []
    
    for _ in range(assess_count):
        t: list[tuple[tuple[float, float], tuple[float, float]]] = probabilistic_hough_line(grayscale_array, line_length=1500, theta=verticals)
        raw_segments = t + raw_segments
    
    segments = create_segments(raw_segments)

    sines = 0
    cosines = 0
    for segment in segments:
        zero, _ = zero_segment(segment)

        # Make sure all lines are pointing DOWN
        if zero['y'] > 0:
            zero = vector_flip(zero)

        sines += zero['y']
        cosines += zero['x']

    guess = atan2(sines, cosines)

    return guess
