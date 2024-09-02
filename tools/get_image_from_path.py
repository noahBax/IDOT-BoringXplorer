from PIL import Image

def get_image_from_path(path: str):
    image = Image.open(path)
    color_image = image
    gray_image = image.convert('L')
    return gray_image, color_image