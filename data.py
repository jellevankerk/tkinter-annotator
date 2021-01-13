import json
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
            if annotation["type"] == "ellipse":
                tkinter_annotations.append(self.__ellipse2tkinter(annotation))

            elif annotation["type"] == "polygon":
                tkinter_annotations.append(self.__polygon2tkinter(annotation))

            else:
                # These types are not yet implemented
                continue

        return tkinter_annotations

    @staticmethod
    def __ellipse2tkinter(data):
        radius_x, radius_y = data["radiusX"], data["radiusY"]

        center_x, center_y = (
            data["center"]["x"],
            data["center"]["y"],
        )

        coord1 = (center_x - radius_x, center_y + radius_y)
        coord2 = (center_x + radius_x, center_y - radius_y)
        return ((coord1, coord2), "ellipse")

    @staticmethod
    def __polygon2tkinter(data):
        points = [(point["x"], point["y"]) for point in data["points"]]

        return (points, "polygon")

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


# if __name__ == "__main__":
#     from tkinter import filedialog

#     path = filedialog.askopenfilename()
#     A = Annotations(path)
#     print(1)
