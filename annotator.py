import math
import uuid
import numpy as np
import warnings
from shapely.geometry import Polygon, LineString
from shapely.ops import unary_union, split
from PIL import Image, ImageTk
from tkinter import Canvas, Frame, Menu, Tk, ALL, filedialog

from utilities import find_coords
from get_shapes import get_circle, get_ellipse, get_rectangle, oval2poly, rec2poly
from data_tkinter_classes import AnnotationsTkinter


class Annotator(Frame):
    def __init__(self, master, height=1000, width=1000):
        self.master = master
        self.canvas = Canvas(self.master, height=height, width=width, bg="black")
        self.canvas.pack()

        self.shape = "circle"
        self.state = False
        self.do_polygon = False

        self.annotations_dict = {}
        self.Data = AnnotationsTkinter()

        self.delete_ids = []
        self.combine_ids = []
        self.move_id = None

        self.motion_id = None
        self.cut_points = []
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

        # Shortcuts
        self.master.bind("c", lambda v: self.set_canvas_mode(mode="create"))
        self.master.bind("m", lambda v: self.set_canvas_mode(mode="move"))
        self.master.bind("d", lambda v: self.set_canvas_mode(mode="delete"))
        self.master.bind("f", lambda v: self.set_canvas_mode(mode="combine"))
        self.master.bind("t", self.hide_annotations)
        self.master.bind("e", lambda v: self.set_shape(shape="ellipse"))
        self.master.bind("i", lambda v: self.set_shape(shape="circle"))
        self.master.bind("p", lambda v: self.set_shape(shape="polygon"))
        self.master.bind("r", lambda v: self.set_shape(shape="rectangle"))

        self.path = filedialog.askopenfilename()
        self.image_id = None
        self.imscale = 1.0
        self.delta = 0.75
        self.__filter = Image.ANTIALIAS

        Image.MAX_IMAGE_PIXELS = (
            1000000000  # suppress DecompressionBombError for big image
        )
        with warnings.catch_warnings():  # suppress DecompressionBombWarning for big image
            warnings.simplefilter("ignore")
            self.image = Image.open(self.path)
        self.imwidth, self.imheight = self.image.size
        # Create image pyramid
        self.__pyramid = [Image.open(self.path)]
        self.__ratio = 1.0
        self.__curr_img = 0  # current image from the pyramid
        self.__scale = self.imscale * self.__ratio  # image pyramide scale
        self.__reduction = 2  # reduction degree of image pyramid
        (w, h), m, j = self.__pyramid[-1].size, 512, 0
        n = (
            math.ceil(math.log(min(w, h) / m, self.__reduction)) + 1
        )  # image pyramid length
        while w > m and h > m:  # top pyramid image is around 512 pixels in size
            j += 1
            print("\rCreating image pyramid: {j} from {n}".format(j=j, n=n), end="")
            w /= self.__reduction  # divide on reduction degree
            h /= self.__reduction  # divide on reduction degree
            self.__pyramid.append(
                self.__pyramid[-1].resize((int(w), int(h)), self.__filter)
            )
        print("\r" + (40 * " ") + "\r", end="")  # hide printed string
        # Put image into container rectangle and use it to set proper coordinates to the image
        self.container = self.canvas.create_text(0, 0, width=0)

        # Menu options
        self.menubar = Menu(self.master)
        self.shape_options = Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(
            label="Create (c)", command=lambda: self.set_canvas_mode(mode="create")
        )
        self.menubar.add_cascade(
            label="Move (m)", command=lambda: self.set_canvas_mode(mode="move")
        )
        self.menubar.add_cascade(
            label="Delete (d)", command=lambda: self.set_canvas_mode(mode="delete")
        )
        self.menubar.add_cascade(
            label="Combine (f)", command=lambda: self.set_canvas_mode(mode="combine")
        )
        self.menubar.add_cascade(
            label="Cut (u)", command=lambda: self.set_canvas_mode(mode="cut")
        )
        self.menubar.add_cascade(
            label="Toggle (t)", command=lambda: self.hide_annotations(None)
        )
        self.menubar.add_cascade(label="Options", menu=self.shape_options)
        self.master.config(menu=self.menubar)

        # Shape options
        self.shape_options.add_command(
            label="Circle (i)",
            command=lambda: self.set_shape(shape="circle"),
        )
        self.shape_options.add_command(
            label="Ellipse (e)",
            command=lambda: self.set_shape(shape="ellipse"),
        )
        self.shape_options.add_command(
            label="Rectangle (r)",
            command=lambda: self.set_shape(shape="rectangle"),
        )
        self.shape_options.add_command(
            label="Polygon (p)",
            command=lambda: self.set_shape(shape="polygon"),
        )
        self.menubar.add_cascade(
            label="Load annotations", command=self.load_annotations
        )
        self.menubar.add_cascade(
            label="Save annotations", command=self.save_annotations
        )
        self.__show_image()
        self.canvas.focus_set()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.set_canvas_mode("create")

    def set_canvas_mode(self, mode, event=None):
        """ Set canvas mode to create, move, delete or combine"""
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
            self.canvas.bind("<B1-Motion>", self.move_annotation)
        elif mode == "delete":
            self.canvas.bind("<ButtonPress-1>", self.select_delete)
            self.canvas.bind("<ButtonPress-3>", self.delete_annotation)
        elif mode == "combine":
            self.canvas.bind("<ButtonPress-1>", self.select_combine)
            self.canvas.bind("<ButtonPress-3>", self.combine_annotation)
        elif mode == "cut":
            self.canvas.bind("<ButtonPress-1>", self.create_cut)

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

    def hide_annotations(self, event):
        """ Toggles on/off annotations"""
        if self.state:
            state = "normal"
        else:
            state = "hidden"

        for _, unique_id in self.Data:
            canvas_id = self.canvas.find_withtag(unique_id)
            self.canvas.itemconfig(canvas_id, state=state)

        self.state = not self.state

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
        delete_canvas_id = self.canvas.find_withtag("current")[0]

        if delete_canvas_id != self.image_id and delete_canvas_id != self.container:
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

        if move_canvas_id != self.image_id and move_canvas_id != self.container:
            if move_canvas_id == self.move_id:
                self.canvas.itemconfigure(move_canvas_id, outline="green", fill="green")
                self.canvas.dtag(move_canvas_id, "MOVE")
                self.move_id = None
                self.move_polygon_points = []
                self.canvas.delete("POINTS")

            elif (
                move_canvas_id not in self.delete_ids
                and move_canvas_id not in self.combine_ids
            ):  # TODO ADD points when you select
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

        if combine_canvas_id != self.image_id and combine_canvas_id != self.container:
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

                if shape == "ellipse":
                    x0, y0, x1, y1 = get_ellipse(coord1_scaled, coord2_scaled)
                    point_list = oval2poly(x0, y0, x1, y1)

                elif shape == "circle":
                    x0, y0, x1, y1 = get_circle(coord1_scaled, coord2_scaled)
                    point_list = oval2poly(x0, y0, x1, y1)

                elif shape == "rectangle":
                    x0, y0, x1, y1 = get_rectangle(coord1_scaled, coord2_scaled)
                    point_list = [x0, y0, x1, y1]

                self.canvas.delete("POINTS")
                self.draw_points(
                    [(x, y) for x, y in zip(point_list[0::2], point_list[1::2])],
                    color="blue",
                    tags=("POINTS"),
                )

                self.canvas.coords(self.move_id, point_list)
                self.Data.edit_annotation(
                    unique_id,
                    self.move_id,
                    [coord1_norm, coord2_norm],
                )

    def delete_annotation(self, event):
        """ Deletes all canvas objects with the tag 'DELETE'"""
        for canvas_id in self.canvas.find_withtag("DELETE"):
            unique_id = self.canvas.gettags(canvas_id)[0]
            self.canvas.delete(canvas_id)
            self.Data.delete_annotation(unique_id)

    def combine_annotation(self, event):
        """ Combines annotations together"""
        polygon_list = []
        index_tags = []
        index_canvas = []

        for canvas_id in self.canvas.find_withtag("COMBINE"):
            unique_id = self.canvas.gettags(canvas_id)[0]
            index_canvas.append(canvas_id)
            index_tags.append(unique_id)

            coords_norm, shape = self.Data.get_coords_from_unique_id(unique_id)
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
            elif shape == "rectangle":
                coord1, coord2 = coords_norm
                x0, y0, x1, y1 = get_rectangle(coord1, coord2)
                point_list = rec2poly(x0, y0, x1, y1)
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
            x_text, y_text = self.canvas.coords(self.text)
            union_polygon_scale = [
                (x_text + x[0] * self.imscale, y_text + x[1] * self.imscale)
                for x in union_polygon
            ]
            unique_id = str(uuid.uuid4())
            canvas_id = self.draw_polygon_func(
                union_polygon_scale, False, unique_id=unique_id
            )
            self.Data.add_annotation(unique_id, canvas_id, union_polygon, "polygon")
            for canvas_id, unique_id in zip(index_canvas, index_tags):
                self.canvas.delete(canvas_id)
                self.Data.delete_annotation(unique_id)
        else:
            for canvas_id in index_canvas:
                self.select_combine(event=None, canvas_id=canvas_id)

    def create_cut(self, event):
        # Get scaled coordinates
        x_canvas = self.canvas.canvasx(event.x)
        y_canvas = self.canvas.canvasy(event.y)
        self.cut_points.extend([x_canvas, y_canvas])

        self.draw_points([(x_canvas, y_canvas)], "yellow", "CUT")
        if len(self.cut_points) == 4:
            self.canvas.create_line(self.cut_points, fill="yellow", tags=("CUT"))
            self.cut_annotations(event, self.cut_points)
            self.canvas.delete("CUT")
            self.cut_points = []

    def cut_annotations(self, event, cut_line):
        unique_id = self.canvas.find_withtag("current")[0]
        coords_norm, shape = self.Data.get_coords_from_unique_id(unique_id)
        if shape == "ellipse":
            coord1, coord2 = coords_norm
            x0, y0, x1, y1 = get_ellipse(coord1, coord2)
            point_list = oval2poly(x0, y0, x1, y1)
            point_list = [(x, y) for x, y in zip(point_list[0::2], point_list[1::2])]
            polygon = Polygon(point_list)
        elif shape == "circle":
            coord1, coord2 = coords_norm
            x0, y0, x1, y1 = get_circle(coord1, coord2)
            point_list = oval2poly(x0, y0, x1, y1)
            point_list = [(x, y) for x, y in zip(point_list[0::2], point_list[1::2])]
            polygon = Polygon(point_list)
        elif shape == "rectangle":
            coord1, coord2 = coords_norm
            x0, y0, x1, y1 = get_rectangle(coord1, coord2)
            point_list = rec2poly(x0, y0, x1, y1)
            point_list = [(x, y) for x, y in zip(point_list[0::2], point_list[1::2])]
            polygon = Polygon(point_list)
        else:
            polygon = Polygon(coords_norm)
        cut_line = LineString([(x, y) for x, y in zip(cut_line[0::2], cut_line[1::2])])
        split_polygons = split(polygon, cut_line)
        for split_polygon in split_polygons:
            split_polygon = [tuple(x) for x in np.array(split_polygon.exterior)]
            x_text, y_text = self.canvas.coords(self.text)
            split_polygon_scale = [
                (x_text + x[0] * self.imscale, y_text + x[1] * self.imscale)
                for x in split_polygon
            ]
            unique_id = str(uuid.uuid4())
            canvas_id = self.draw_polygon_func(
                split_polygon_scale, False, unique_id=unique_id
            )
            self.Data.add_annotation(unique_id, canvas_id, split_polygon, "polygon")
            self.canvas.delete(canvas_id)
            self.Data.delete_annotation(unique_id)

    def draw_polygon(self, event):
        """ Draws polygons"""
        self.delete_polygons()

        norm_x, norm_y = self.get_coords(event)
        self.temp_polygon_points_norm.append((norm_x, norm_y))

        x_canvas = self.canvas.canvasx(event.x)
        y_canvas = self.canvas.canvasy(event.y)
        self.temp_polygon_points.append((x_canvas, y_canvas))

        points = self.draw_points(self.temp_polygon_points)
        self.temp_polygon_point_ids.extend(points)

        self.draw_polygon_func(self.temp_polygon_points, True)

    def draw_points(self, centers, color="green", tags=()):
        """ Draws points at all points of polygons"""
        points = []
        for pt in centers:
            x, y = pt
            x1, y1 = (x - 1), (y - 1)
            x2, y2 = (x + 1), (y + 1)
            dot_id = self.canvas.create_oval(
                x1, y1, x2, y2, fill=color, outline=color, width=5, tags=tags
            )

            points.append(dot_id)

        return points

    def draw_polygon_func(self, centers, do_temp=False, unique_id=None):
        """ Function to draw polygon"""
        n_points = len(centers)
        canvas_id = 0
        if n_points > 2:
            canvas_id = self.canvas.create_polygon(
                centers,
                fill="green",
                outline="green",
                width=3,
                stipple="gray12",
                tags=unique_id,
            )
        elif n_points == 2:
            canvas_id = self.canvas.create_line(
                centers, fill="green", width=3, tags=unique_id
            )

        if do_temp:
            self.temp_polygon_point_ids.append(canvas_id)
        return canvas_id

    def move_polygon(self, event):
        """ Moves polygon annotations"""
        unique_id = self.canvas.gettags(self.move_id)[0]
        if not len(self.move_polygon_points):
            self.move_polygon_points = self.Data.annotations_tkinter[
                unique_id
            ].coords_norm

        points_array = np.array(self.move_polygon_points)
        center = np.average(points_array, 0)

        norm_x, norm_y = self.get_coords(event)
        move = np.array([norm_x, norm_y]) - center
        point_centers = [
            [x[0] + move[0], x[1] + move[1]] for x in self.move_polygon_points
        ]

        x_canvas = self.canvas.canvasx(event.x)
        y_canvas = self.canvas.canvasy(event.y)

        move_scaled = np.array([x_canvas, y_canvas]) - center * self.imscale
        scaled_centers = [
            [x[0] * self.imscale + move_scaled[0], x[1] * self.imscale + move_scaled[1]]
            for x in self.move_polygon_points
        ]
        self.canvas.delete("POINTS")
        self.draw_points(scaled_centers, color="blue", tags=("POINTS"))
        self.canvas.coords(
            self.move_id, [item for sublist in scaled_centers for item in sublist]
        )

        self.Data.edit_annotation(unique_id, self.move_id, point_centers)

    def save_polygons(self, event):
        """ Saves current polygon, after this a new polygon can be saved"""
        if len(self.temp_polygon_point_ids):
            unique_id = str(uuid.uuid4())
            self.delete_polygons()
            canvas_id = self.draw_polygon_func(
                self.temp_polygon_points, False, unique_id=unique_id
            )
            self.Data.add_annotation(
                unique_id,
                canvas_id,
                self.temp_polygon_points_norm,
                "polygon",
            )
            self.temp_polygon_point_ids = []
            self.temp_polygon_points = []
            self.temp_polygon_points_norm = []

    def delete_polygons(self):
        """ Deletes all widged ids of temp_polygon"""
        if len(self.temp_polygon_point_ids):
            for canvas_id in self.temp_polygon_point_ids:
                self.canvas.delete(canvas_id)

    def __show_image(self):
        """ Show image on the Canvas. Implements correct image zoom almost like in Google Maps """
        if self.image_id:
            self.canvas.delete(self.image_id)
            self.image_id = None
            self.canvas.imagetk = None
        x, y = self.canvas.coords(self.container)
        x2, y2 = self.imwidth * self.__scale + x, self.imheight * self.__scale + y
        box_image = (x, y, x2, y2)  # get image area
        box_canvas = (
            self.canvas.canvasx(0),  # get visible area of the canvas
            self.canvas.canvasy(0),
            self.canvas.canvasx(self.canvas.winfo_width()),
            self.canvas.canvasy(self.canvas.winfo_height()),
        )
        box_img_int = tuple(map(int, box_image))

        # convert to integer or it will not work properly
        # Get scroll region box
        box_scroll = [
            min(box_img_int[0], box_canvas[0]),
            min(box_img_int[1], box_canvas[1]),
            max(box_img_int[2], box_canvas[2]),
            max(box_img_int[3], box_canvas[3]),
        ]
        # Horizontal part of the image is in the visible area
        if box_scroll[0] == box_canvas[0] and box_scroll[2] == box_canvas[2]:
            box_scroll[0] = box_img_int[0]
            box_scroll[2] = box_img_int[2]
        # Vertical part of the image is in the visible area
        if box_scroll[1] == box_canvas[1] and box_scroll[3] == box_canvas[3]:
            box_scroll[1] = box_img_int[1]
            box_scroll[3] = box_img_int[3]
        # Convert scroll region to tuple and to integer
        self.canvas.configure(
            scrollregion=tuple(map(int, box_scroll))
        )  # set scroll region
        x1 = max(
            box_canvas[0] - box_image[0], 0
        )  # get coordinates (x1,y1,x2,y2) of the image tile
        y1 = max(box_canvas[1] - box_image[1], 0)
        x2 = min(box_canvas[2], box_image[2]) - box_image[0]
        y2 = min(box_canvas[3], box_image[3]) - box_image[1]
        if (
            int(x2 - x1) > 0 and int(y2 - y1) > 0
        ):  # show image if it in the visible area

            image = self.__pyramid[
                max(0, self.__curr_img)
            ].crop(  # crop current img from pyramid
                (
                    int(x1 / self.__scale),
                    int(y1 / self.__scale),
                    int(x2 / self.__scale),
                    int(y2 / self.__scale),
                )
            )
            #
            imagetk = ImageTk.PhotoImage(
                image.resize((int(x2 - x1), int(y2 - y1)), self.__filter)
            )
            self.image_id = self.canvas.create_image(
                max(box_canvas[0], box_img_int[0]),
                max(box_canvas[1], box_img_int[1]),
                anchor="nw",
                image=imagetk,
            )
            self.canvas.lower(self.image_id)  # set image into background
            self.canvas.imagetk = (
                imagetk  # keep an extra reference to prevent garbage-collection
            )

    def load_annotations(self):
        """ Load annotations"""
        path = filedialog.askopenfilename()
        loaded_annotations = self.Data.load_annotations(path=path)

        for annotation, unique_id in loaded_annotations:
            self.load_annotation(annotation, unique_id)

    def load_annotation(self, data, unique_id):

        coords_norm = data.coords_norm
        shape = data.shape

        x, y = self.canvas.coords(self.container)
        coords_scale = [
            (x + i[0] * self.imscale, y + i[1] * self.imscale) for i in coords_norm
        ]

        if shape == "polygon":
            canvas_id = self.draw_polygon_func(
                coords_scale, do_temp=False, unique_id=unique_id
            )

        else:
            coord1, coord2 = coords_scale
            canvas_id = self.create_annotation_func(
                unique_id, coord1, coord2, shape=shape
            )

        data.canvas_id = canvas_id

    def save_annotations(self):
        """ Saves annotations as json"""
        save_path = filedialog.asksaveasfilename(defaultextension=".json")
        self.Data.save_annotations(save_path)

    def move_from(self, event):
        """ Remember previous coordinates for scrolling with the mouse """
        self.canvas.scan_mark(event.x, event.y)

    def move_to(self, event):
        """ Drag (move) canvas to the new position """
        self.canvas.scan_dragto(event.x, event.y, gain=1)
        self.__show_image()

    def wheel(self, event):
        """ Zoom with mouse wheel """
        x = self.canvas.canvasx(event.x)  # get coordinates of the event on the canvas
        y = self.canvas.canvasy(event.y)
        scale = 1.0

        if event.delta == -120:
            scale *= self.delta
            self.imscale *= self.delta
        if event.delta == 120:
            scale /= self.delta
            self.imscale /= self.delta

        k = self.imscale * self.__ratio  # temporary coefficient
        self.__curr_img = min(
            (-1) * int(math.log(k, self.__reduction)), len(self.__pyramid) - 1
        )
        self.__scale = k * math.pow(self.__reduction, max(0, self.__curr_img))
        #
        self.canvas.scale("all", x, y, scale, scale)  # rescale all objects
        # Redraw some figures before showing image on the screen
        self.redraw_figures()  # method for child classes
        self.__show_image()

    def redraw_figures(self):
        pass

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