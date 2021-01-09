import math
import numpy as np
from PIL import Image, ImageTk
from tkinter import Canvas, Frame, Menu, Tk, ALL, filedialog

from utilities import find_coords
from get_shapes import get_circle, get_ellipse, get_roi


class Annotator(Frame):
    def __init__(self, master, load_image=True, height=500, width=500):
        self.master = master
        self.load_image = load_image

        self.canvas = Canvas(self.master, height=height, width=width, bg="black")
        self.canvas.pack()

        self.mode = "roi"
        self.do_polygon = False
        self.image_id = None

        self.annotations_dict = {}

        self.delete_ids = []
        self.move_id = None

        self.motion_id = None
        self.anno_coords = []

        self.temp_polygon_points = []
        self.temp_polygon_point_ids = []
        self.move_polygon_points = []

        if self.load_image:
            self.image = Image.open(filedialog.askopenfilename())
            self.imscale = 1.0
            self.delta = 0.75
            width, height = self.image.size

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
        self.master.bind("<Double-Button-1>", self.save_polygons)

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
        if self.load_image:
            self.show_image(self.image_id)

    def set_shape(self, mode):
        """" Set shape of the annotations (circle, ellipse, roi or polygon)"""
        self.mode = mode

    def create_annotation(self, event):
        """ Creates annotations using the coordinates of left mouse clicks"""
        if self.mode == "polygon":
            self.draw_polygon(event)
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
                x0, y0, x1, y1, fill="", outline="green", width=3
            )
        elif mode == "circle":
            x0, y0, x1, y1 = get_circle(coord1, coord2)
            temp_id = self.canvas.create_oval(
                x0, y0, x1, y1, fill="", outline="green", width=3
            )
        elif mode == "roi":
            x0, y0, x1, y1 = get_roi(coord1, coord2)
            temp_id = self.canvas.create_rectangle(
                x0, y0, x1, y1, fill="green", outline="green", width=3, stipple="gray12"
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
        """ Selects/deselects the closest annotation and adds/removes 'DELETE' tag"""
        widget_id = event.widget.find_closest(event.x, event.y, halo=2)
        if len(widget_id) and widget_id[0] != self.image_id:
            if widget_id[0] in self.delete_ids:
                fill = (
                    "green"
                    if self.annotations_dict[str(widget_id[0])][1] in ["polygon", "roi"]
                    else ""
                )
                self.canvas.itemconfigure(widget_id, outline="green", fill=fill)
                self.delete_ids.pop(self.delete_ids.index(widget_id[0]))

            elif widget_id[0] != self.move_id:
                fill = (
                    "red"
                    if self.annotations_dict[str(widget_id[0])][1] in ["polygon", "roi"]
                    else ""
                )
                self.canvas.itemconfigure(
                    widget_id,
                    tags="DELETE",
                    outline="red",
                    fill=fill,
                )
                self.delete_ids.append(widget_id[0])

    def select_move(self, event):
        """ Selects/deselects the closest annotation and adds/removes 'MOVE' tag"""
        widget_id = self.canvas.find_withtag("current")

        if len(widget_id) and widget_id[0] != self.image_id:
            if widget_id[0] == self.move_id:
                fill = (
                    "green"
                    if self.annotations_dict[str(widget_id[0])][1] in ["polygon", "roi"]
                    else ""
                )
                self.canvas.itemconfigure(widget_id, outline="green", fill=fill)
                self.move_id = None
                self.move_polygon_points = []

            elif widget_id[0] not in self.delete_ids:
                if not self.move_id:
                    fill = (
                        "blue"
                        if self.annotations_dict[str(widget_id[0])][1]
                        in ["polygon", "roi"]
                        else ""
                    )
                    self.canvas.itemconfigure(
                        widget_id, tags=("MOVE"), outline="blue", fill=fill
                    )
                    self.move_id = widget_id[0]

    def move_annotation(self, event):
        """ Moves annotations with tag 'MOVE' by presing the wheelmouse button and moving the mouse"""
        if self.move_id:
            coords, mode = self.annotations_dict[str(self.move_id)]

            if mode == "polygon":
                self.move_polygon(event)
            else:
                # Image dimensions
                xdim = abs(coords[0][0] - coords[1][0])
                ydim = abs(coords[0][1] - coords[1][1])

                # Create new annotations at new location
                new_coord1, new_coord2 = find_coords((event.x, event.y), xdim, ydim)
                new_id = self.create_annotation_func(new_coord1, new_coord2, mode)

                self.canvas.delete(self.move_id)
                fill = (
                    "blue"
                    if self.annotations_dict[str(self.move_id)][1] in ["polygon", "roi"]
                    else ""
                )
                self.canvas.itemconfigure(
                    new_id, tags="MOVE", outline="blue", fill=fill
                )

                self.annotations_dict[f"{new_id}"] = (
                    [new_coord1, new_coord2],
                    mode,
                )
                del self.annotations_dict[str(self.move_id)]
                self.move_id = new_id

    def delete_annotation(self, event):
        """ Deletes all canvas objects with the tag 'DELETE'"""
        for idx in self.canvas.find_withtag("DELETE"):
            self.canvas.delete(idx)

    def draw_polygon(self, event):
        """ Draws polygons"""
        self.delete_polygons()

        center_x, center_y = event.x, event.y
        self.temp_polygon_points.append((center_x, center_y))

        dots = self.draw_points(self.temp_polygon_points)
        self.temp_polygon_point_ids.extend(dots)

        self.draw_polygon_func(self.temp_polygon_points, True)

    def draw_points(self, centers, color="green"):
        """ Draws points at all points of polygons"""
        points = []
        for pt in centers:
            x, y = pt
            x1, y1 = (x - 1), (y - 1)
            x2, y2 = (x + 1), (y + 1)
            dot_id = self.canvas.create_oval(
                x1, y1, x2, y2, fill="green", outline=color, width=5
            )

            points.append(dot_id)

        return points

    def draw_polygon_func(self, centers, do_temp=False):
        """ Function to draw polygon"""
        n_points = len(centers)
        temp_id = 0
        if n_points > 2:
            temp_id = self.canvas.create_polygon(
                centers, fill="green", outline="green", width=3, stipple="gray12"
            )
        elif n_points == 2:
            temp_id = self.canvas.create_line(centers, fill="green", width=3)

        self.temp_polygon_point_ids.append(temp_id)
        return temp_id

    def move_polygon(self, event):
        """ Moves polygon annotations"""
        if not len(self.move_polygon_points):
            self.move_polygon_points, _ = self.annotations_dict[str(self.move_id)]

        dots_array = np.array(self.move_polygon_points)
        center = np.average(dots_array, 0)
        move = np.array([event.x, event.y]) - center
        dots_centers = [
            [x[0] + move[0], x[1] + move[1]] for x in self.move_polygon_points
        ]
        new_poly_id = self.canvas.create_polygon(
            dots_centers,
            fill="blue",
            tags="MOVE",
            outline="blue",
            width=3,
            stipple="gray12",
        )

        self.canvas.delete(self.move_id)
        del self.annotations_dict[str(self.move_id)]

        self.annotations_dict[str(new_poly_id)] = (dots_centers, "polygon")
        self.move_id = new_poly_id

    def save_polygons(self, event):
        """ Saves current polygon, after this a new polygon can be saved"""
        self.delete_polygons()
        poly_id = self.draw_polygon_func(self.temp_polygon_points, False)
        self.annotations_dict[f"{poly_id}"] = (self.temp_polygon_points, "polygon")
        self.temp_polygon_point_ids = []
        self.temp_polygon_points = []

    def delete_polygons(self):
        """ Deletes all widged ids of temp_polygon"""
        if len(self.temp_polygon_point_ids):
            for idx in self.temp_polygon_point_ids:
                self.canvas.delete(idx)

    def show_image(self, image_id):
        """ Show image on the Canvas """
        if image_id:
            self.canvas.delete(image_id)
            image_id = None
            self.canvas.imagetk = None  # delete previous image from the canvas
        width, height = self.image.size
        new_size = int(self.imscale * width), int(self.imscale * height)
        imagetk = ImageTk.PhotoImage(self.image.resize(new_size))
        # Use self.text object to set proper coordinates
        self.image_id = self.canvas.create_image((0, 0), anchor="nw", image=imagetk)
        self.canvas.lower(self.image_id)  # set it into background
        self.canvas.imagetk = (
            imagetk  # keep an extra reference to prevent garbage-collection
        )


# Main function
if __name__ == "__main__":
    root = Tk()
    anno = Annotator(root)
    root.mainloop()