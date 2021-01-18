import json
import uuid
import numpy as np
from copy import deepcopy  # dont know if this is the correct operation for this


class AnnotationsTkinter:
    def __init__(self):
        self.annotations_tkinter = {}

    def __len__(self):
        return len(self.annotations_tkinter)

    def __getitem__(self, index):
        idx = list(self.annotations_tkinter.keys())[
            index
        ]  # python 3.6+ dicts are ordered
        return self.annotations_tkinter[idx], idx

    def load_annotations(self, path):
        with open(path, "r") as f:
            annotations = json.load(f)
        self.__convert2tkinter_format(annotations)

    def add_annotation(self, coord_norm, shape, canvas_id, idx):
        if shape == "polygon":
            self.annotations_tkinter[idx] = AnnotationTkinter(
                coord_norm, canvas_id=canvas_id
            )
        elif shape == "ellipse" or shape == "circle":
            self.annotations_tkinter[idx] = EllipseTkinter(
                coord_norm, shape, canvas_id=canvas_id
            )
        elif shape == "rectangle":
            self.annotations_tkinter[idx] = RectangleTkinter(
                coord_norm, canvas_id=canvas_id
            )

    def delete_annotation(self, idx):
        del self.annotations_tkinter[idx]

    def __convert2tkinter_format(self, annotations):
        copy_annotations = deepcopy(annotations)
        for annotation in copy_annotations:
            if "id" in annotation:
                idx = annotation["id"]
            else:
                idx = str(uuid.uuid4())

            if annotation["type"] == "ellipse" or annotation["type"] == "circle":

                self.annotations_tkinter[idx] = self.__ellipse2tkinter(
                    annotation, annotation["type"]
                )

            elif annotation["type"] == "polygon":
                self.annotations_tkinter[idx] = self.__polygon2tkinter(annotation)

            elif annotation["type"] == "rectangle":
                self.annotations_tkinter[idx] = self.__rectangle2tkinter(annotation)
            else:
                raise ValueError(f" Mode {annotation['type']} is not supported")

    @staticmethod
    def __ellipse2tkinter(data, shape):
        radius_x, radius_y = data["radiusX"], data["radiusY"]

        center_x, center_y = (
            data["center"]["x"],
            data["center"]["y"],
        )

        if "area" in data:
            area = data["area"]
        else:
            area = None

        if "accuracy" in data:
            accuracy = data["accuracy"]
        else:
            accuracy = None

        coords = ((center_x, center_y), (center_x + radius_x, center_y + radius_y))
        annotation = EllipseTkinter(
            coords,
            shape,
            area=area,
            accuracy=accuracy,
            radius_x=radius_x,
            radius_y=radius_y,
        )
        return annotation

    @staticmethod
    def __polygon2tkinter(data):
        points = [(point["x"], point["y"]) for point in data["points"]]

        if "area" in data:
            area = data["area"]
        else:
            area = None

        if "accuracy" in data:
            accuracy = data["accuracy"]
        else:
            accuracy = None

        annotation = AnnotationTkinter(
            points,
            area=area,
            accuracy=accuracy,
        )
        return annotation

    @staticmethod
    def __rectangle2tkinter(data):
        x_coord, y_coord = data["coords"]
        width = data["width"]
        height = data["height"]

        if "area" in data:
            area = data["area"]
        else:
            area = None

        if "accuracy" in data:
            accuracy = data["accuracy"]
        else:
            accuracy = None
        coord = ((x_coord, y_coord), (x_coord + width, y_coord + height))
        annotation = RectangleTkinter(
            coord, area=area, accuracy=accuracy, width=width, height=height
        )

        return annotation

    @staticmethod
    def __convert2json_format(annotation):
        pass

    @staticmethod
    def __ellipse2json(data):
        pass

    @staticmethod
    def __polygon2json(data):
        pass


class AnnotationTkinter:
    def __init__(
        self,
        coords_norm,
        shape="polygon",
        canvas_id=None,
        area=None,
        accuracy=None,
    ):
        self.coords_norm = coords_norm
        self.shape = shape
        self.canvas_id = canvas_id
        self.area = area
        self.accuracy = accuracy

    def edit_annotation(self, coord_norm, canvas_id):
        self.coords_norm = coord_norm
        self.canvas_id = canvas_id


class EllipseTkinter(AnnotationTkinter):
    def __init__(
        self,
        coords_norm,
        shape,
        canvas_id=None,
        area=None,
        accuracy=None,
        radius_x=None,
        radius_y=None,
        angle=None,
    ):
        super().__init__(coords_norm, shape, canvas_id=None, area=None, accuracy=None)

        self.radius_x = radius_x
        self.radius_y = radius_y
        self.angle = angle

    def get_mean_radius(self):
        return (self.radius_y + self.radius_x) / 2

    def get_mean_diameter(self):
        return (2 * self.radius_y + 2 * self.radius_x) / 2


class RectangleTkinter(AnnotationTkinter):
    def __init__(
        self,
        coords_norm,
        canvas_id=None,
        area=None,
        accuracy=None,
        width=None,
        height=None,
    ):
        super().__init__(
            coords_norm,
            shape="rectangle",
            canvas_id=None,
            area=None,
            accuracy=None,
        )

        self.width = width
        self.height = height


def convert2json(data):
    annotation = data.coords_norm
    mode = data.shape

    if mode == "ellipse" or mode == "circle":
        json_annotation = ellipse2json(annotation, mode)
    elif mode == "polygon":
        json_annotation = polygon2json(annotation)
    elif mode == "rectangle":
        json_annotation = rectangle2json(annotation)
    else:
        raise ValueError(f"Mode {mode} is not supported")

    return json_annotation


def ellipse2json(annotation, annotation_type):
    json_annotation = {}
    json_annotation["type"] = annotation_type
    json_annotation["angleOfRotation"] = 0

    coord1, coord2 = annotation
    x0, y0 = coord1
    x1, y1 = coord2

    radius_x = int(np.floor(np.abs((x1 - x0))))
    radius_y = int(np.floor(np.abs((y1 - y0))))
    json_annotation["radiusX"] = radius_x
    json_annotation["radiusY"] = radius_y

    json_annotation["center"] = {}
    json_annotation["center"]["x"] = x0
    json_annotation["center"]["y"] = y0

    return json_annotation


def polygon2json(annotation):
    json_annotation = {}
    json_annotation["type"] = "polygon"

    points = []
    for point in annotation:
        json_point = {}
        json_point["x"] = point[0]
        json_point["y"] = point[1]
        points.append(json_point)

    json_annotation["points"] = points

    return json_annotation


def rectangle2json(annotation):
    json_annotation = {}
    json_annotation["type"] = "rectangle"

    coord1, coord2 = annotation

    json_annotation["coords"] = coord1
    json_annotation["width"] = coord2[0] - coord1[0]
    json_annotation["height"] = coord2[1] - coord1[1]
    return json_annotation
