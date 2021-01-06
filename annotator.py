import math
import numpy as np
from tkinter import Canvas, Frame, Menu, Tk, ALL

from utilities import find_coords
from get_shapes import get_circle, get_ellipse, get_roi


class Annotator(Frame):
    def __init__(self, master, height=1000, width=1000):
        self.master = master

        self.canvas = Canvas(self.master, height=height, width=width, bg="black")
        self.canvas.pack()

        self.mode = "polygon"
        self.start = None
        self.do_polygon = False

        self.annotations_dict = {}

        self.delete_ids = []
        self.move_ids = []

        self.motion_id = None
        self.anno_coords = []

        self.temp_polygon_points = []
        self.temp_polygon_point_ids = []
        self.move_polygon_points = []

        # Create annotations
        self.canvas.bind("<ButtonPress-1>", self.create_annotation)
        self.canvas.bind("<Motion>", self.motion_create_annotation)

        # Select annotations
        self.canvas.bind("<Button 2>", self.select_move)
        self.canvas.bind("<Button 3>", self.select_delete)

        # Actions annotations
        self.canvas.bind("<B2-Motion>", self.move_annotation)
        self.master.bind("<Delete>", self.delete_annotation)

        # Polygon commands
        self.master.bind("<Return>", self.save_polygons)

        # Menu options
        self.menubar = Menu(self.master)
        self.shape_options = Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Options", menu=self.shape_options)
        self.master.config(menu=self.menubar)

        # Shape options
        self.shape_options.add_command(
            label="Circle",
            command=lambda: self.set_shape(mode="circle"),
        )
        self.shape_options.add_command(
            label="Ellipse",
            command=lambda: self.set_shape(mode="ellipse"),
        )
        self.shape_options.add_command(
            label="Roi",
            command=lambda: self.set_shape(mode="roi"),
        )
        self.shape_options.add_command(
            label="Polygon",
            command=lambda: self.set_shape(mode="polygon"),
        )

    def set_shape(self, mode):
        """" Set shape of the annotations (circle, ellipse, roi or polygon)"""
        self.mode = mode

    def create_annotation(self, event):
        """ Creates annotations using the coordinates of left mouse clicks"""
        if self.mode == "polygon":
            self.draw_polygons(event)
        else:
            center_x, center_y = event.x, event.y
            self.anno_coords.append([center_x, center_y])

            if len(self.anno_coords) >= 2:
                temp_id = self.create_annotation_func(
                    self.anno_coords[0], self.anno_coords[1]
                )

                self.annotations_dict[f"{temp_id}"] = (self.anno_coords, self.mode)
                self.anno_coords = []

                return temp_id

    def create_annotation_func(self, coord1, coord2, mode=None):
        """ Depending on the mode of the functions draws a circle, ellipse, roi or polygon """
        if not mode:
            mode = self.mode
        if mode == "ellipse":
            x0, y0, x1, y1 = get_ellipse(coord1, coord2)
            temp_id = self.canvas.create_oval(
                x0, y0, x1, y1, fill="", outline="green", width=2
            )
        elif mode == "circle":
            x0, y0, x1, y1 = get_circle(coord1, coord2)
            temp_id = self.canvas.create_oval(
                x0, y0, x1, y1, fill="", outline="green", width=2
            )
        elif mode == "roi":
            x0, y0, x1, y1 = get_roi(coord1, coord2)
            temp_id = self.canvas.create_rectangle(
                x0, y0, x1, y1, fill="", outline="green", width=2
            )
        return temp_id

    def motion_create_annotation(self, event):
        """ Track mouse position over the canvas """
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        if self.motion_id:
            self.canvas.delete(self.motion_id)
        if len(self.anno_coords) == 1 and not self.do_polygon:
            self.motion_id = self.create_annotation_func(self.anno_coords[0], (x, y))

    def select_delete(self, event):

        widget_id = event.widget.find_closest(event.x, event.y, halo=2)
        if len(widget_id):
            if widget_id[0] in self.delete_ids:
                self.canvas.itemconfigure(widget_id, outline="green")
                self.delete_ids.pop(self.delete_ids.index(widget_id[0]))

            elif widget_id[0] not in self.move_ids:
                self.canvas.itemconfigure(widget_id, tags="DELETE", outline="red")
                self.delete_ids.append(widget_id[0])

    def select_move(self, event):
        widget_id = event.widget.find_closest(event.x, event.y, halo=5)
        if len(widget_id):
            if widget_id[0] in self.move_ids:
                self.canvas.itemconfigure(widget_id, outline="green")
                self.move_ids = []
                self.move_polygon_points = []

            elif widget_id[0] not in self.delete_ids:
                if not len(self.move_ids):
                    self.canvas.itemconfigure(widget_id, tags="SELECT", outline="blue")
                    self.move_ids.append(widget_id[0])

    def delete_annotation(self, event):
        for idx in self.canvas.find_withtag("DELETE"):
            # del self.annotations_dict[idx]
            self.canvas.delete(idx)

    # Polygon functions
    def draw_annotations(self, centers, do_temp=False):
        # Draw polygon
        n_points = len(centers)
        temp_id = 0
        if n_points > 2:
            temp_id = self.canvas.create_polygon(
                centers, fill="", outline="green", width=2
            )
        elif n_points == 2:
            temp_id = self.canvas.create_line(centers)

        self.temp_polygon_point_ids.append(temp_id)
        return temp_id

    def draw_dots(self, centers, color="green"):
        dots = []
        for pt in centers:
            x, y = pt
            # draw dot over position which is clicked
            x1, y1 = (x - 1), (y - 1)
            x2, y2 = (x + 1), (y + 1)
            dot_id = self.canvas.create_oval(
                x1, y1, x2, y2, fill="green", outline=color, width=5
            )

            dots.append(dot_id)

        return dots

    def draw_polygons(self, event):
        self.delete_temp_ids()

        center_x, center_y = event.x, event.y
        self.temp_polygon_points.append((center_x, center_y))

        dots = self.draw_dots(self.temp_polygon_points)
        self.temp_polygon_point_ids.extend(dots)

        self.draw_annotations(self.temp_polygon_points, True)

    def save_polygons(self, event):
        self.delete_temp_ids()
        poly_id = self.draw_annotations(self.temp_polygon_points, False)
        self.annotations_dict[f"{poly_id}"] = (self.temp_polygon_points, "polygon")
        self.temp_polygon_point_ids = []
        self.temp_polygon_points = []

    def move_annotation(self, event):

        widget_id = event.widget.find_closest(event.x, event.y)
        if widget_id[0] in self.move_ids:
            coords, mode = self.annotations_dict[str(widget_id[0])]
            if mode == "polygon":
                self.move(event, widget_id)
            else:
                xdim = abs(coords[0][0] - coords[1][0])
                ydim = abs(coords[0][1] - coords[1][1])
                new_coord1, new_coord2 = find_coords((event.x, event.y), xdim, ydim)
                new_id = self.create_annotation_func(new_coord1, new_coord2, mode)
                self.move_ids.append(new_id)
                self.move_ids.pop(self.move_ids.index(widget_id[0]))
                self.canvas.delete(widget_id[0])
                self.canvas.itemconfigure(new_id, tags="SELECT", outline="blue")
                self.annotations_dict[f"{new_id}"] = ([new_coord1, new_coord2], mode)
                del self.annotations_dict[str(widget_id[0])]

    def delete_all_polygons(self, event):
        self.canvas.delete(ALL)
        self.temp = []
        self.annotations_dict = []

    def move(self, event, widget_id):

        # widget_id = event.widget.find_closest(event.x, event.y)
        if widget_id[0] in self.move_ids:
            if not len(self.move_polygon_points):
                self.move_polygon_points, _ = self.annotations_dict[str(widget_id[0])]
            dots_array = np.array(self.move_polygon_points)
            center = np.average(dots_array, 0)
            move = np.array([event.x, event.y]) - center
            dots_centers = [
                [x[0] + move[0], x[1] + move[1]] for x in self.move_polygon_points
            ]
            new_poly_id = self.canvas.create_polygon(
                dots_centers, fill="", tags="SELECT", outline="blue", width=2
            )
            self.move_ids.append(new_poly_id)
            self.move_ids.pop(self.move_ids.index(widget_id[0]))
            self.canvas.delete(widget_id[0])
            del self.annotations_dict[str(widget_id[0])]
            self.annotations_dict[str(new_poly_id)] = (dots_centers, "polygon")

    def delete_temp_ids(self):
        if len(self.temp_polygon_point_ids):
            for idx in self.temp_polygon_point_ids:
                self.canvas.delete(idx)


# Main function
if __name__ == "__main__":
    root = Tk()
    anno = Annotator(root)
    root.mainloop()