from PIL import Image
import fitz

def get_image_from_page(file_path: str, page_num=0, dpi=300) -> tuple[Image.Image, Image.Image]:
    
    gray_pixmap: fitz.Pixmap
    colo_pixmap: fitz.Pixmap
    with fitz.open(file_path) as pdf:
        page = pdf.load_page(page_num)
        gray_pixmap = page.get_pixmap(dpi=dpi, colorspace='GRAY')
        colo_pixmap = page.get_pixmap(dpi=dpi)
        
    gray_image = Image.frombytes('L', size=(gray_pixmap.width, gray_pixmap.height), data=gray_pixmap.samples)
    colo_image = Image.frombytes('RGB', size=(colo_pixmap.width, colo_pixmap.height), data=colo_pixmap.samples)

    if gray_image.width > gray_image.height:
        gray_image = gray_image.crop((0, 0, 2500, gray_image.height))
        colo_image = colo_image.crop((0, 0, 2500, colo_image.height))

    return gray_image, colo_image