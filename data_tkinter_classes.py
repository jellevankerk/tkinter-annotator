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
        return self.__convert2tkinter_format(annotations)

    def save_annotations(self, path):
        annotations_json = self.__convert2json_format()

        with open(path, "w") as f:
            json.dump(annotations_json, f)

    def add_annotation(
        self,
        unique_id,
        canvas_id,
        coord_norm,
        shape,
    ):
        if shape == "polygon":
            self.annotations_tkinter[unique_id] = AnnotationTkinter(
                coord_norm, canvas_id=canvas_id
            )
        elif shape == "ellipse" or shape == "circle":
            self.annotations_tkinter[unique_id] = EllipseTkinter(
                coord_norm, shape, canvas_id=canvas_id
            )
        elif shape == "rectangle":
            self.annotations_tkinter[unique_id] = RectangleTkinter(
                coord_norm, canvas_id=canvas_id
            )

    def edit_annotation(
        self,
        unique_id,
        canvas_id,
        coord_norm,
    ):
        self.annotations_tkinter[unique_id].edit_annotation(coord_norm, canvas_id)

    def delete_annotation(self, unique_id):
        del self.annotations_tkinter[unique_id]

    def get_coords_from_unique_id(self, unique_id):
        return (
            self.annotations_tkinter[unique_id].coords_norm,
            self.annotations_tkinter[unique_id].shape,
        )

    def __convert2tkinter_format(self, annotations):
        tkinter_annotations = []
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
            tkinter_annotations.append((self.annotations_tkinter[idx], idx))
        return tkinter_annotations

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

    def __convert2json_format(self):
        annotations_json = []
        for unique_id in list(self.annotations_tkinter.keys()):
            annotation, shape = self.get_coords_from_unique_id(unique_id)

            if shape == "ellipse" or shape == "circle":
                json_annotation = self.__ellipse2json(annotation, shape)
            elif shape == "polygon":
                json_annotation = self.__polygon2json(annotation)
            elif shape == "rectangle":
                json_annotation = self.__rectangle2json(annotation)
            else:
                raise ValueError(f"shape {shape} is not supported")

            annotations_json.append(json_annotation)

        return annotations_json

    @staticmethod
    def __ellipse2json(data, shape):
        json_annotation = {}
        json_annotation["type"] = shape
        json_annotation["angleOfRotation"] = 0

        coord1, coord2 = data
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

    @staticmethod
    def __polygon2json(data):
        json_annotation = {}
        json_annotation["type"] = "polygon"

        points = []
        for point in data:
            json_point = {}
            json_point["x"] = point[0]
            json_point["y"] = point[1]
            points.append(json_point)

        json_annotation["points"] = points

        return json_annotation

    @staticmethod
    def __rectangle2json(data):
        json_annotation = {}
        json_annotation["type"] = "rectangle"

        coord1, coord2 = data

        json_annotation["coords"] = coord1
        json_annotation["width"] = coord2[0] - coord1[0]
        json_annotation["height"] = coord2[1] - coord1[1]
        return json_annotation


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
