import json
import numpy as np
from copy import deepcopy  # dont know if this is the correct operation for this


class Annotations:
    def __init__(self, json_path):
        self.annotations_json = self.__load_annotations(json_path)
        self.annotations = self.__convert2tkinter_format(self.annotations_json)

    def __len__(self):
        return len(self.annotations)

    def __getitem__(self, index):
        return self.annotations[index]

    def __load_annotations(self, path):
        with open(path, "r") as f:
            annotations = json.load(f)
        return annotations

    def __convert2tkinter_format(self, annotations):
        tkinter_annotations = []
        copy_annotations = deepcopy(annotations)
        for annotation in copy_annotations:
            if annotation["type"] == "ellipse" or annotation["type"] == "circle":
                tkinter_annotations.append(
                    self.__ellipse2tkinter(annotation, annotation["type"])
                )

            elif annotation["type"] == "polygon":
                tkinter_annotations.append(self.__polygon2tkinter(annotation))

            elif annotation["type"] == "rectangle":
                tkinter_annotations.append(self.__rectangle2tkinter(annotation))
            else:
                raise ValueError(f" Mode {annotation['type']} is not supported")

        return tkinter_annotations

    @staticmethod
    def __ellipse2tkinter(data, mode):
        radius_x, radius_y = data["radiusX"], data["radiusY"]

        center_x, center_y = (
            data["center"]["x"],
            data["center"]["y"],
        )

        return (
            ((center_x, center_y), (center_x + radius_x, center_y + radius_y)),
            mode,
        )

    @staticmethod
    def __polygon2tkinter(data):
        points = [(point["x"], point["y"]) for point in data["points"]]

        return (points, "polygon")

    @staticmethod
    def __rectangle2tkinter(data):
        x_coord, y_coord = data["coords"]
        width = data["width"]
        height = data["height"]

        return (((x_coord, y_coord), (x_coord + width, y_coord + height)), "rectangle")

    def add_annotation(self, annotation):
        pass

    def delete_annotation(self, index):
        pass

    @staticmethod
    def __convert2json_format(annotation):
        pass

    @staticmethod
    def __ellipse2json(data):
        pass

    @staticmethod
    def __polygon2json(data):
        pass


def convert2json(data):
    annotation, mode = data

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
