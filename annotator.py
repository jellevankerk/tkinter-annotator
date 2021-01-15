import math
import cv2
import json
import numpy as np
from PIL import Image, ImageTk
from tkinter import Canvas, Frame, Menu, Tk, ALL, filedialog

from utilities import find_coords
from get_shapes import get_circle, get_ellipse, get_roi, oval2poly
from data import Annotations, convert2json


class Annotator(Frame):
    def __init__(self, master, height=1000, width=1000):
        self.master = master
        self.canvas = Canvas(self.master, height=height, width=width, bg="black")
        self.canvas.pack()

        self.mode = "ellipse"
        self.do_polygon = False

        self.annotations_dict = {}

        self.delete_ids = []
        self.move_id = None

        self.motion_id = None
        self.anno_coords = []

        self.temp_polygon_points = []
        self.temp_polygon_point_ids = []
        self.move_polygon_points = []

        # Bind events to the Canvas
        self.canvas.bind("<ButtonPress-2>", self.move_from)
        self.canvas.bind("<B2-Motion>", self.move_to)
        self.canvas.bind("<MouseWheel>", self.wheel)

        self.image = Image.open(filedialog.askopenfilename())
        self.image_id = None
        self.imscale = 1.0
        self.delta = 0.75
        width, height = self.image.size
        minsize, maxsize = 5, 20

        # Menu options
        self.menubar = Menu(self.master)
        self.shape_options = Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(
            label="Create", command=lambda: self.set_canvas_mode(mode="create")
        )
        self.menubar.add_cascade(
            label="Move", command=lambda: self.set_canvas_mode(mode="move")
        )
        self.menubar.add_cascade(
            label="Delete", command=lambda: self.set_canvas_mode(mode="delete")
        )
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
        self.menubar.add_cascade(
            label="Load annotations", command=self.load_annotations
        )
        self.menubar.add_cascade(
            label="Save annotations", command=self.save_annotations
        )
        self.text = self.canvas.create_text(0, 0)
        self.show_image()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.set_canvas_mode("create")

    def set_canvas_mode(self, mode, event=None):
        self.unbind()
        self.canvas_mode = mode
        if len(self.temp_polygon_point_ids):
            self.save_polygons(None)
        if mode == "create":
            # Create annotations
            self.canvas.bind("<ButtonPress-1>", self.create_annotation)
            self.canvas.bind("<Motion>", self.motion_create_annotation)
            self.canvas.bind("<ButtonPress-3>", self.save_polygons)
        elif mode == "move":
            self.canvas.bind("<ButtonPress-1>", self.select_move)
            # self.canvas.bind("<B2-Motion>", self.rotated_ellipse)
            self.canvas.bind("<Motion>", self.move_annotation)
        elif mode == "delete":
            self.canvas.bind("<ButtonPress-1>", self.select_delete)
            self.canvas.bind("<ButtonPress-3>", self.delete_annotation)

    def unbind(self):
        self.canvas.unbind("<ButtonPress-1>")
        # self.canvas.unbind("<B2-Motion>")
        self.canvas.unbind("<Motion>")
        self.canvas.unbind("<ButtonPress 3>")

    def set_shape(self, mode):
        """" Set shape of the annotations (circle, ellipse, roi or polygon)"""
        if len(self.temp_polygon_point_ids):
            self.save_polygons(None)
        self.mode = mode

    def create_annotation(self, event):
        """ Creates annotations using the coordinates of left mouse clicks"""
        if self.mode == "polygon":
            self.draw_polygon(event)
        else:
            x = self.canvas.canvasx(event.x)
            y = self.canvas.canvasy(event.y)
            self.anno_coords.append([x, y])

            if len(self.anno_coords) >= 2:
                temp_id = self.create_annotation_func(
                    self.anno_coords[0], self.anno_coords[1]
                )

                coords = [
                    (x[0] / self.imscale, x[1] / self.imscale) for x in self.anno_coords
                ]
                self.annotations_dict[f"{temp_id}"] = (coords, self.mode)
                self.anno_coords = []

                return temp_id

    def create_annotation_func(
        self, coord1, coord2, mode=None, start_from_center=False
    ):
        """ Depending on the mode of the functions draws a circle, ellipse, roi or polygon """
        if not mode:
            mode = self.mode
        if mode == "ellipse":
            if start_from_center:
                x0, y0, x1, y1 = get_ellipse(coord1, coord2)
            else:
                x0, y0 = coord1
                x1, y1 = coord2

            point_list = oval2poly(x0, y0, x1, y1)
            temp_id = self.canvas.create_polygon(
                point_list, fill="green", outline="green", width=3, stipple="gray12"
            )
        elif mode == "circle":
            if start_from_center:
                x0, y0, x1, y1 = get_circle(coord1, coord2)
            else:
                x0, y0 = coord1
                x1, y1 = coord2
            point_list = oval2poly(x0, y0, x1, y1)
            temp_id = self.canvas.create_polygon(
                point_list, fill="green", outline="green", width=3, stipple="gray12"
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
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        widget_id = event.widget.find_closest(x, y, halo=2)
        if len(widget_id) and widget_id[0] != self.image_id:
            if widget_id[0] in self.delete_ids:
                fill = "green"
                self.canvas.itemconfigure(widget_id, outline="green", fill=fill)
                self.delete_ids.pop(self.delete_ids.index(widget_id[0]))

            elif widget_id[0] != self.move_id:
                fill = "red"
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
                fill = "green"
                self.canvas.itemconfigure(widget_id, outline="green", fill=fill)
                self.move_id = None
                self.move_polygon_points = []

            elif widget_id[0] not in self.delete_ids:
                if not self.move_id:
                    fill = "blue"
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
                x = self.canvas.canvasx(event.x)
                y = self.canvas.canvasy(event.y)
                new_coord1, new_coord2 = find_coords((x, y), xdim, ydim)
                scaled_coord1, scaled_coord2 = find_coords(
                    (x, y),
                    xdim * self.imscale,
                    ydim * self.imscale,
                )

                new_id = self.create_annotation_func(scaled_coord1, scaled_coord2, mode)

                self.canvas.delete(self.move_id)
                fill = "blue"
                self.canvas.itemconfigure(
                    new_id, tags="MOVE", outline="blue", fill=fill
                )

                self.annotations_dict[f"{new_id}"] = (
                    [new_coord1, new_coord2],
                    mode,
                )
                del self.annotations_dict[str(self.move_id)]
                self.move_id = new_id

    def rotated_ellipse(self, event):
        if self.move_id:
            coords, mode = self.annotations_dict[str(self.move_id)]
            if mode == "ellipse":
                (x0, y0), (x1, y1) = coords
                center_x = x1 - x0
                center_y = y1 - y0

                rotate_x = event.x
                rotate_y = event.y

                diff_x = rotate_x - center_x
                diff_y = rotate_y - center_y
                theta = math.atan((diff_y / diff_x)) * (180 / math.pi)
                print(theta)

                x0_n, y0_n, x1_n, y1_n = get_ellipse((x0, y0), (x1, y1))
                point_list = oval2poly(x0_n, y0_n, x1_n, y1_n, rotation=theta)
                new_id = self.canvas.create_polygon(
                    point_list, fill="green", outline="green", width=3, stipple="gray12"
                )

                self.canvas.delete(self.move_id)
                fill = "blue"
                self.canvas.itemconfigure(
                    new_id, tags="MOVE", outline="blue", fill=fill
                )

                self.annotations_dict[f"{new_id}"] = (
                    [(x0, y0), (x1, y1)],
                    mode,
                )
                del self.annotations_dict[str(self.move_id)]
                self.move_id = new_id

    def delete_annotation(self, event):
        """ Deletes all canvas objects with the tag 'DELETE'"""
        for idx in self.canvas.find_withtag("DELETE"):
            self.canvas.delete(idx)
            del self.annotations_dict[str(idx)]

    def draw_polygon(self, event):
        """ Draws polygons"""
        self.delete_polygons()
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        center_x, center_y = x, y
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

        if do_temp:
            self.temp_polygon_point_ids.append(temp_id)
        return temp_id

    def move_polygon(self, event):
        """ Moves polygon annotations"""
        if not len(self.move_polygon_points):
            self.move_polygon_points, _ = self.annotations_dict[str(self.move_id)]

        dots_array = np.array(self.move_polygon_points)
        center = np.average(dots_array, 0)
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)

        move_scaled = np.array([x, y]) - center * self.imscale
        scaled_centers = [
            [x[0] * self.imscale + move_scaled[0], x[1] * self.imscale + move_scaled[1]]
            for x in self.move_polygon_points
        ]

        move = np.array([x, y]) - center
        dots_centers = [
            [x[0] + move[0], x[1] + move[1]] for x in self.move_polygon_points
        ]

        new_poly_id = self.canvas.create_polygon(
            scaled_centers,
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
        if len(self.temp_polygon_point_ids):
            self.delete_polygons()
            poly_id = self.draw_polygon_func(self.temp_polygon_points, False)
            coords = [
                (x[0] / self.imscale, x[1] / self.imscale)
                for x in self.temp_polygon_points
            ]
            self.annotations_dict[f"{poly_id}"] = (coords, "polygon")
            self.temp_polygon_point_ids = []
            self.temp_polygon_points = []

    def delete_polygons(self):
        """ Deletes all widged ids of temp_polygon"""
        if len(self.temp_polygon_point_ids):
            for idx in self.temp_polygon_point_ids:
                self.canvas.delete(idx)
                del self.annotations_dict[str(idx)]

    def show_image(self):
        """ Show image on the Canvas """
        if self.image_id:
            self.canvas.delete(self.image_id)
            self.image_id = None
            self.canvas.imagetk = None  # delete previous image from the canvas
        width, height = self.image.size
        new_size = int(self.imscale * width), int(self.imscale * height)
        imagetk = ImageTk.PhotoImage(self.image.resize(new_size))
        self.image_id = self.canvas.create_image(
            self.canvas.coords(self.text), anchor="nw", image=imagetk
        )
        self.canvas.lower(self.image_id)  # set it into background
        self.canvas.imagetk = (
            imagetk  # keep an extra reference to prevent garbage-collection
        )

    def load_annotations(self):
        path = filedialog.askopenfilename()
        annotations = Annotations(path)

        for annotation in annotations:
            self.load_annotation(annotation)

    def load_annotation(self, data):

        annotation, mode = data
        x, y = self.canvas.coords(self.text)
        annotation_scale = [
            (x + i[0] * self.imscale, y + i[1] * self.imscale) for i in annotation
        ]

        if mode == "polygon":
            temp_id = self.draw_polygon_func(annotation_scale, do_temp=False)

            self.annotations_dict[f"{temp_id}"] = (annotation, mode)

        elif mode == "ellipse":
            coord1, coord2 = annotation_scale
            temp_id = self.create_annotation_func(coord1, coord2, mode=mode)
            coord1, coord2 = annotation

            self.annotations_dict[f"{temp_id}"] = ((coord1, coord2), mode)

    def save_annotations(self):
        save_path = filedialog.asksaveasfilename(defaultextension=".json")
        annotations_json = []
        for i in self.annotations_dict:
            annotation = convert2json(self.annotations_dict[i])
            annotations_json.append(annotation)

        with open(save_path, "w") as f:
            json.dump(annotations_json, f)

    def move_from(self, event):
        """ Remember previous coordinates for scrolling with the mouse """
        self.canvas.scan_mark(event.x, event.y)

    def move_to(self, event):
        """ Drag (move) canvas to the new position """
        self.canvas.scan_dragto(event.x, event.y, gain=1)

    def wheel(self, event):
        """ Zoom with mouse wheel """
        scale = 1.0

        if event.delta == -120:
            scale *= self.delta
            self.imscale *= self.delta
        if event.delta == 120:
            scale /= self.delta
            self.imscale /= self.delta
        # Rescale all canvas objects
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        self.canvas.scale("all", x, y, scale, scale)
        self.show_image()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))


# Main function
if __name__ == "__main__":
    root = Tk()
    anno = Annotator(root)
    root.mainloop()