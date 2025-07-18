import matplotlib.pyplot as plt
import fitz 
from PIL import Image
import io
import numpy as np

def convert_pdf_to_image(pdf_data):
    zoom_x = 15.0
    zoom_y = 15.0
    mat = fitz.Matrix(zoom_x, zoom_y)

    doc = fitz.open(stream=pdf_data, filetype="pdf")
    page = doc.load_page(0)
    pix = page.get_pixmap(matrix=mat, colorspace='gray')

    img_data = pix.tobytes("png")
    image = Image.open(io.BytesIO(img_data))

    return np.array(image)

path = r"C:\\Users\\Haroon\\OneDrive\Desktop\\Custom_Arabic_OCR\\Custom_Arabic_OCR\\VAT Invoice2.pdf"

with open(path, 'rb') as f:
    pdf_data = f.read()

image = convert_pdf_to_image(pdf_data)

plt.imshow(image, cmap='gray')
plt.axis('off')
plt.show()