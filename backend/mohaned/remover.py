import numpy as np
from rembg import remove
from PIL import Image

img = Image.open("input/green.png").convert("RGBA")

# remove background → already PIL Image
img = remove(img).convert("RGBA")

data = np.array(img)

green_mask = (
    (data[...,0] < 100) &
    (data[...,1] > 120) &
    (data[...,2] < 100) &
    (data[...,3] > 0)
)

data[green_mask] = [255, 255, 255, 255]

Image.fromarray(data).save("output/output.png")
