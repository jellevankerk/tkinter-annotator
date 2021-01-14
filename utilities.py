import numpy as np
import cv2
from PIL import Image, ImageTk


def find_coords(center, xdim, ydim):
    """
    Finds the coordinates of the topleft
    and bottomright corners of a region of interest (roi).
    It uses the center and the roi dimension.
    """
    x0 = center[0] - int(xdim / 2)
    x1 = center[0] + int(xdim / 2)

    y0 = center[1] - int(ydim / 2)
    y1 = center[1] + int(ydim / 2)
    return (x0, y0), (x1, y1)


def img_dim(arr):
    s = np.shape(arr)
    return s[1], s[0]