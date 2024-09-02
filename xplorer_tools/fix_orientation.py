from math import degrees
from xplorer_tools.guess_page_orientation import guess_page_orientation
from PIL import Image

def fix_orientation(grayscale_image: Image.Image, color_image: Image.Image, assess_count=3) -> tuple[Image.Image, Image.Image]:
    """
    The theory is that we can correct the image first and then try to work on it
    from there. This will specifically make things like drawing boxes a lot
    easier and not having to draw trapezoids.

    The grayscale image should NOT be inverted.

    The one modifiable arg I'm allowing is assess_count. What it does it lets
    you adjust the amount of times that guess_page_orientation runs a hough
    transformation. It's simply a way to reduce variance in the results. Just
    doing some testing on a few images, 5 seems to only vary in maybe ~3-5
    hundredths of a degree from run to run, but 3 seems to only vary by around
    0.5-1 degree.
    """

    initial_orientation = guess_page_orientation(grayscale_image, assess_count)

    # The guess_page_orientation will always return a negative value
    rotate_by = 90.0 + degrees(initial_orientation)

    r1 = grayscale_image.rotate(rotate_by, fillcolor=255)
    r2 = color_image.rotate(rotate_by, fillcolor=(255, 255, 255))

    return r1, r2