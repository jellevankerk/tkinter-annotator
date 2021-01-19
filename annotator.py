import math
import uuid
import cv2
import json
import numpy as np
from shapely.geometry import Polygon
from shapely.ops import unary_union
from PIL import Image, ImageTk
from tkinter import Canvas, Frame, Menu, Tk, ALL, filedialog

from utilities import find_coords
from get_shapes import get_circle, get_ellipse, get_rectangle, oval2poly
from data import AnnotationsTkinter, convert2json


class Annotator(Frame):
    def __init__(self, master, height=1000, width=1000):
        self.master = master
        self.canvas = Canvas(self.master, height=height, width=width, bg="black")
        self.canvas.pack()

        self.shape = "circle"
        self.do_polygon = False

        self.annotations_dict = {}
        self.Data = AnnotationsTkinter()

        self.delete_ids = []
        self.combine_ids = []
        self.move_id = None

        self.motion_id = None
        self.temp_coords = []
        self.temp_coords_norm = []

        self.temp_polygon_points = []
        self.temp_polygon_points_norm = []
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
        self.menubar.add_cascade(
            label="Combine", command=lambda: self.set_canvas_mode(mode="combine")
        )
        self.menubar.add_cascade(label="Options", menu=self.shape_options)
        self.master.config(menu=self.menubar)

        # Shape options
        self.shape_options.add_command(
            label="Circle",
            command=lambda: self.set_shape(shape="circle"),
        )
        self.shape_options.add_command(
            label="Ellipse",
            command=lambda: self.set_shape(shape="ellipse"),
        )
        self.shape_options.add_command(
            label="Rectangle",
            command=lambda: self.set_shape(shape="rectangle"),
        )
        self.shape_options.add_command(
            label="Polygon",
            command=lambda: self.set_shape(shape="polygon"),
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
            self.canvas.bind("<Motion>", self.move_annotation)
        elif mode == "delete":
            self.canvas.bind("<ButtonPress-1>", self.select_delete)
            self.canvas.bind("<ButtonPress-3>", self.delete_annotation)
        elif mode == "combine":
            self.canvas.bind("<ButtonPress-1>", self.select_combine)
            self.canvas.bind("<ButtonPress-3>", self.combine_annotation)

    def unbind(self):
        """ Unbind keys"""
        self.canvas.unbind("<ButtonPress-1>")
        self.canvas.unbind("<Motion>")
        self.canvas.unbind("<ButtonPress 3>")

    def set_shape(self, shape):
        """ Set shape of the annotations (circle, ellipse, rectangle or polygon)"""
        if len(self.temp_polygon_point_ids):
            self.save_polygons(None)
        self.shape = shape

    def create_annotation(self, event):
        """ Creates annotations using the coordinates of left mouse clicks"""
        unique_id = str(uuid.uuid4())
        if self.shape == "polygon":
            self.draw_polygon(event)
        else:
            # Get normalized coordinates
            x_norm, y_norm = self.get_coords(event)
            self.temp_coords_norm.append([x_norm, y_norm])

            # Get scaled coordinates
            x_canvas = self.canvas.canvasx(event.x)
            y_canvas = self.canvas.canvasy(event.y)
            self.temp_coords.append([x_canvas, y_canvas])

            if len(self.temp_coords) >= 2:
                # Draw annotation on canvas
                canvas_id = self.create_annotation_func(
                    unique_id,
                    self.temp_coords[0],
                    self.temp_coords[1],
                )

                # Save annotation information
                self.Data.add_annotation(
                    unique_id,
                    canvas_id,
                    self.temp_coords_norm,
                    self.shape,
                )

                # Reset annotations creation
                self.temp_coords = []
                self.temp_coords_norm = []

                return canvas_id

    def create_annotation_func(self, unique_id, coord1, coord2, shape=None):
        """ Depending on the shape of the functions draws a circle, ellipse, rectangle or polygon """
        if not shape:
            shape = self.shape

        if shape == "ellipse":
            x0, y0, x1, y1 = get_ellipse(coord1, coord2)
            point_list = oval2poly(x0, y0, x1, y1)
            canvas_id = self.canvas.create_polygon(
                point_list,
                fill="green",
                outline="green",
                width=3,
                stipple="gray12",
                tags=unique_id,
            )
        elif shape == "circle":
            x0, y0, x1, y1 = get_circle(coord1, coord2)
            point_list = oval2poly(x0, y0, x1, y1)
            canvas_id = self.canvas.create_polygon(
                point_list,
                fill="green",
                outline="green",
                width=3,
                stipple="gray12",
                tags=unique_id,
            )
        elif shape == "rectangle":
            x0, y0, x1, y1 = get_rectangle(coord1, coord2)
            canvas_id = self.canvas.create_rectangle(
                x0,
                y0,
                x1,
                y1,
                fill="green",
                outline="green",
                width=3,
                stipple="gray12",
                tags=unique_id,
            )

        return canvas_id

    def motion_create_annotation(self, event):
        """ Track mouse position over the canvas """
        x_canvas = self.canvas.canvasx(event.x)
        y_canvas = self.canvas.canvasy(event.y)

        if self.motion_id:
            self.canvas.delete(self.motion_id)
        if len(self.temp_coords) == 1 and not self.do_polygon:
            self.motion_id = self.create_annotation_func(
                "CREATE",
                self.temp_coords[0],
                (x_canvas, y_canvas),
            )

    def select_delete(self, event):
        """ Selects/deselects the closest annotation and adds/removes 'DELETE' tag"""
        x_canvas = self.canvas.canvasx(event.x)
        y_canvas = self.canvas.canvasy(event.y)
        delete_canvas_id = event.widget.find_closest(x_canvas, y_canvas, halo=2)[0]

        if delete_canvas_id != self.image_id:
            if delete_canvas_id in self.delete_ids:
                self.canvas.itemconfigure(
                    delete_canvas_id, outline="green", fill="green"
                )
                self.canvas.dtag(delete_canvas_id, "DELETE")
                self.delete_ids.pop(self.delete_ids.index(delete_canvas_id))

            elif (
                delete_canvas_id != self.move_id
                and delete_canvas_id not in self.combine_ids
            ):
                self.canvas.itemconfigure(
                    delete_canvas_id,
                    outline="red",
                    fill="red",
                )
                self.canvas.addtag_withtag("DELETE", delete_canvas_id)
                self.delete_ids.append(delete_canvas_id)

    def select_move(self, event):
        """ Selects/deselects the closest annotation and adds/removes 'MOVE' tag"""
        move_canvas_id = self.canvas.find_withtag("current")[0]

        if move_canvas_id != self.image_id:
            if move_canvas_id == self.move_id:
                self.canvas.itemconfigure(move_canvas_id, outline="green", fill="green")
                self.canvas.dtag(move_canvas_id, "MOVE")
                self.move_id = None
                self.move_polygon_points = []

            elif (
                move_canvas_id not in self.delete_ids
                and move_canvas_id not in self.combine_ids
            ):
                if not self.move_id:
                    self.canvas.itemconfigure(
                        move_canvas_id, outline="blue", fill="blue"
                    )
                    self.canvas.addtag_withtag("MOVE", move_canvas_id)
                    self.move_id = move_canvas_id

    def select_combine(self, event=None, canvas_id=None):
        """ Selects/deselects the closest annotation and adds/removes 'COMBINE' tag"""
        if event:
            x = self.canvas.canvasx(event.x)
            y = self.canvas.canvasy(event.y)
            combine_canvas_id = event.widget.find_closest(x, y, halo=2)[0]
        if canvas_id:
            combine_canvas_id = canvas_id

        if combine_canvas_id != self.image_id:
            if combine_canvas_id in self.combine_ids:
                fill = "green"
                self.canvas.itemconfigure(combine_canvas_id, outline="green", fill=fill)
                self.canvas.dtag(combine_canvas_id, "COMBINE")
                self.combine_ids.pop(self.combine_ids.index(combine_canvas_id))

            elif (
                combine_canvas_id != self.move_id
                and combine_canvas_id not in self.delete_ids
            ):
                self.canvas.itemconfigure(
                    combine_canvas_id,
                    outline="yellow",
                    fill="yellow",
                )
                self.canvas.addtag_withtag("COMBINE", combine_canvas_id)
                self.combine_ids.append(combine_canvas_id)

    def move_annotation(self, event):
        """ Moves annotations with tag 'MOVE' by presing the wheelmouse button and moving the mouse"""
        if self.move_id:
            unique_id = self.canvas.gettags(self.move_id)[0]
            coords, shape = self.Data.get_coords_from_unique_id(unique_id)

            if shape == "polygon":
                self.move_polygon(event)
            else:
                # Image dimensions
                x_dim = abs(coords[0][0] - coords[1][0])
                y_dim = abs(coords[0][1] - coords[1][1])

                # Create new annotations at new location
                x_norm, y_norm = self.get_coords(event)
                coord1_norm, coord2_norm = find_coords((x_norm, y_norm), x_dim, y_dim)

                x_canvas = self.canvas.canvasx(event.x)
                y_canvas = self.canvas.canvasy(event.y)
                coord1_scaled, coord2_scaled = find_coords(
                    (x_canvas, y_canvas),
                    x_dim * self.imscale,
                    y_dim * self.imscale,
                )

                canvas_id = self.create_annotation_func(
                    unique_id, coord1_scaled, coord2_scaled, shape
                )

                self.canvas.delete(self.move_id)
                self.canvas.itemconfigure(
                    canvas_id, tags=(unique_id, "MOVE"), outline="blue", fill="blue"
                )
                self.Data.edit_annotation(
                    unique_id,
                    canvas_id,
                    [coord1_norm, coord2_norm],
                )

                self.move_id = canvas_id

    def delete_annotation(self, event):
        """ Deletes all canvas objects with the tag 'DELETE'"""
        for canvas_id in self.canvas.find_withtag("DELETE"):
            unique_id = self.canvas.gettags(canvas_id)[0]
            self.canvas.delete(canvas_id)
            self.Data.delete_annotation(unique_id)

    def combine_annotation(self, event):
        """ Combines annotations together"""
        # TODO annotations when created start on the wrong place
        # TODO something goes wrong when combining combined annotations
        polygon_list = []
        index_tags = []
        index_canvas = []
        for idx in self.canvas.find_withtag("COMBINE"):
            idx_tag = self.canvas.gettags(idx)[0]
            index_canvas.append(idx)
            index_tags.append(idx_tag)

            data = self.Data.annotations_tkinter[idx_tag]
            coords_norm = data.coords_norm
            shape = data.shape
            if shape == "ellipse":
                coord1, coord2 = coords_norm
                x0, y0, x1, y1 = get_ellipse(coord1, coord2)
                point_list = oval2poly(x0, y0, x1, y1)
                point_list = [
                    (x, y) for x, y in zip(point_list[0::2], point_list[1::2])
                ]
                polygon = Polygon(point_list)
            elif shape == "circle":
                coord1, coord2 = coords_norm
                x0, y0, x1, y1 = get_circle(coord1, coord2)
                point_list = oval2poly(x0, y0, x1, y1)
                point_list = [
                    (x, y) for x, y in zip(point_list[0::2], point_list[1::2])
                ]
                polygon = Polygon(point_list)
            else:
                polygon = Polygon(coords_norm)
            polygon_list.append(polygon)

        union_polygon = unary_union(polygon_list)
        if hasattr(union_polygon, "exterior"):
            union_polygon = [tuple(x) for x in np.array(union_polygon.exterior)]
            union_polygon_scale = [
                (x[0] * self.imscale, x[1] * self.imscale) for x in union_polygon
            ]
            idx = str(uuid.uuid4())
            poly_id = self.draw_polygon_func(union_polygon_scale, False, idx=idx)
            self.Data.add_annotation(union_polygon, "polygon", poly_id, idx)
            for idx, idx_tag in zip(index_canvas, index_tags):
                self.canvas.delete(idx)
                self.Data.delete_annotation(idx_tag)
        else:
            for idx in index_canvas:
                self.select_combine(event=None, canvas_id=[idx])

    def draw_polygon(self, event):
        """ Draws polygons"""
        self.delete_polygons()
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        norm_x, norm_y = self.get_coords(event)
        self.temp_polygon_points.append((x, y))
        self.temp_polygon_points_norm.append((norm_x, norm_y))

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

    def draw_polygon_func(self, centers, do_temp=False, idx=None):
        """ Function to draw polygon"""
        n_points = len(centers)
        temp_id = 0
        if n_points > 2:
            temp_id = self.canvas.create_polygon(
                centers,
                fill="green",
                outline="green",
                width=3,
                stipple="gray12",
                tags=idx,
            )
        elif n_points == 2:
            temp_id = self.canvas.create_line(centers, fill="green", width=3, tags=idx)

        if do_temp:
            self.temp_polygon_point_ids.append(temp_id)
        return temp_id

    def move_polygon(self, event):
        """ Moves polygon annotations"""
        idx = self.canvas.gettags(self.move_id)[0]
        if not len(self.move_polygon_points):
            self.move_polygon_points = self.Data.annotations_tkinter[idx].coords_norm

        dots_array = np.array(self.move_polygon_points)
        center = np.average(dots_array, 0)
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        norm_x, norm_y = self.get_coords(event)

        move_scaled = np.array([x, y]) - center * self.imscale
        scaled_centers = [
            [x[0] * self.imscale + move_scaled[0], x[1] * self.imscale + move_scaled[1]]
            for x in self.move_polygon_points
        ]

        move = np.array([norm_x, norm_y]) - center
        dots_centers = [
            [x[0] + move[0], x[1] + move[1]] for x in self.move_polygon_points
        ]

        new_poly_id = self.canvas.create_polygon(
            scaled_centers,
            fill="blue",
            tags=(idx, "MOVE"),
            outline="blue",
            width=3,
            stipple="gray12",
        )

        self.canvas.delete(self.move_id)
        self.Data.annotations_tkinter[idx].edit_annotation(dots_centers, new_poly_id)
        self.move_id = new_poly_id

    def save_polygons(self, event):
        """ Saves current polygon, after this a new polygon can be saved"""
        if len(self.temp_polygon_point_ids):
            idx = str(uuid.uuid4())
            self.delete_polygons()
            poly_id = self.draw_polygon_func(self.temp_polygon_points, False, idx=idx)
            self.Data.add_annotation(
                self.temp_polygon_points_norm, "polygon", poly_id, idx
            )
            self.temp_polygon_point_ids = []
            self.temp_polygon_points = []
            self.temp_polygon_points_norm = []

    def delete_polygons(self):
        """ Deletes all widged ids of temp_polygon"""
        if len(self.temp_polygon_point_ids):
            for idx in self.temp_polygon_point_ids:
                self.canvas.delete(idx)

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
        self.Data.load_annotations(path=path)

        for annotation, idx in self.Data:
            self.load_annotation(annotation, idx)

    def load_annotation(self, data, idx):

        annotation = data.coords_norm
        shape = data.shape

        x, y = self.canvas.coords(self.text)
        annotation_scale = [
            (x + i[0] * self.imscale, y + i[1] * self.imscale) for i in annotation
        ]

        if shape == "polygon":
            temp_id = self.draw_polygon_func(annotation_scale, do_temp=False, idx=idx)

        else:
            coord1, coord2 = annotation_scale
            temp_id = self.create_annotation_func(idx, coord1, coord2, shape=shape)

        data.coords = annotation
        data.canvas_id = temp_id

    def save_annotations(self):
        save_path = filedialog.asksaveasfilename(defaultextension=".json")
        annotations_json = []
        for annotation, _ in self.Data:
            annotation = convert2json(annotation)
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

    def get_coords(self, event):
        """ Get coordinates of the mouse click event on the image """
        x1 = self.canvas.canvasx(event.x)  # get coordinates of the event on the canvas
        y1 = self.canvas.canvasy(event.y)
        xy = self.canvas.coords(
            self.image_id
        )  # get coords of image's upper left corner
        x2 = round(
            (x1 - xy[0]) / self.imscale
        )  # get real (x,y) on the image without zoom
        y2 = round((y1 - xy[1]) / self.imscale)
        if 0 <= x2 <= self.image.size[0] and 0 <= y2 <= self.image.size[1]:
            return (x2, y2)
        else:
            print("Outside of the image")


# Main function
if __name__ == "__main__":
    root = Tk()
    anno = Annotator(root)
    root.mainloop()