import numpy as np
import cv2
from PIL import Image, ImageTk
from tkinter import filedialog


def img_dim(arr, showChannels=False):
    """ This function gives the image dimensions and optional channel of a numpy array."""
    s = np.shape(arr)

    if showChannels:
        if len(s) > 2:
            return s[1], s[0], s[2]
        else:
            return s[1], s[0], 1
    else:
        return s[1], s[0]


def scale_image(image, scale):
    img_width, img_height = img_dim(image)
    if type(image) is np.ndarray:
        image = Image.fromarray(image)

    new_size = int(scale * img_width), int(scale * img_height)
    imagetk = ImageTk.PhotoImage(image.resize(new_size))

    return imagetk


def get_image(scale, return_numpy=False):
    image_path = filedialog.askopenfilename()
    image = cv2.imread(image_path)

    if return_numpy:
        return image
    return scale_image(image, scale)
