import math


def get_ellipse(coord1, coord2):
    """
    Returns the coordinates of rectangle defined by the coordinates (x0, y0) of the top left corner
    and the coordinates (x1, y1) of a point just outside of the bottom right corner.
    An circle will coincide with the top and left-hand lines of this box, but will fit just inside the bottom and right-hand sides.
    """

    if coord2[0] > coord1[0]:
        x0 = coord1[0] - (coord2[0] - coord1[0])
        x1 = coord2[0]
    elif coord2[0] < coord1[0]:
        x0 = coord2[0]
        x1 = coord1[0] - (coord2[0] - coord1[0])
    else:
        x0 = coord1[0]
        x1 = coord1[0]

    if coord2[1] > coord1[1]:
        y0 = coord1[1] - (coord2[1] - coord1[1])
        y1 = coord2[1]
    elif coord2[1] < coord1[1]:
        y0 = coord2[1]
        y1 = coord1[1] - (coord2[1] - coord1[1])
    else:
        y0 = coord1[1]
        y1 = coord1[1]

    return x0, y0, x1, y1


def get_circle(coord1, coord2):
    """
    Returns the coordinates of rectangle defined by the coordinates (x0, y0) of the top left corner
    and the coordinates (x1, y1) of a point just outside of the bottom right corner.
    An circle will coincide with the top and left-hand lines of this box, but will fit just inside the bottom and right-hand sides.
    """
    radius = math.sqrt(
        math.pow(coord1[0] - coord2[0], 2) + math.pow(coord1[1] - coord2[1], 2)
    )
    x0, x1 = coord1[0] + radius, coord1[0] - radius
    y0, y1 = coord1[1] - radius, coord1[1] + radius

    return x0, y0, x1, y1


def get_roi(coord1, coord2):
    """
    Returns the topleft (x0, y0) and bottomright (x1, y1) coordinates of a region of interest (rectangle)
    For example, the rectangle specified by top left corner (100,100) and bottom right corner (102,102)
    is a square two pixels by two pixels, including pixel (101,101) but not including (102,102)
    """

    if coord1[0] > coord2[0]:
        x0 = coord1[0]
        x1 = coord2[0]
    elif coord1[0] < coord2[0]:
        x0 = coord2[0]
        x1 = coord1[0]
    else:
        x0 = 0
        x1 = 0

    if coord1[1] > coord2[1]:
        y0 = coord1[1]
        y1 = coord2[1]
    elif coord1[1] < coord2[1]:
        y0 = coord2[1]
        y1 = coord1[1]
    else:
        y0 = 0
        y1 = 0

    return x0, y0, x1, y1


def oval2poly(x0, y0, x1, y1, steps=20, rotation=0):
    """
    Return an oval as coordinates suitable for create_polygon.
    Credits to Stephen D Evans. https://mail.python.org/pipermail/python-list/2000-December/022013.html

    """

    # x0,y0,x1,y1 are as create_oval

    # rotation is in degrees anti-clockwise, convert to radians
    rotation = rotation * math.pi / 180.0

    # major and minor axes
    a = (x1 - x0) / 2.0
    b = (y1 - y0) / 2.0

    # center
    xc = x0 + a
    yc = y0 + b

    point_list = []

    # create the oval as a list of points
    for i in range(steps):

        # Calculate the angle for this step
        # 360 degrees == 2 pi radians
        theta = (math.pi * 2) * (float(i) / steps)

        x1 = a * math.cos(theta)
        y1 = b * math.sin(theta)

        # rotate x, y
        x = (x1 * math.cos(rotation)) + (y1 * math.sin(rotation))
        y = (y1 * math.cos(rotation)) - (x1 * math.sin(rotation))

        point_list.append(round(x + xc))
        point_list.append(round(y + yc))

    return point_list