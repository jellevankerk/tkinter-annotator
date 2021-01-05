import math

# change to tkinter for python3
from tkinter import *
import numpy as np

# TODO improve delete
# TODO move annotations
# TODO replace id


class Draw(Frame):
    def __init__(self, master, height=1000, width=1000):
        self.master = master
        self.canvas = Canvas(self.master, height=height, width=width, bg="black")
        self.canvas.pack()

        self.mode = "roi"  # "circle"  # "ellipse"

        self.n_anno = 0
        self.annotations = {}
        self.temp_annotations = []
        self.temp_centers = []
        self.temp_ids = []
        self.selected = []
        self.selected2 = []
        self.select_dots = {}
        self.selected_dots = []

        self.centers = []
        self.motionid = None

        # Bind keys
        self.canvas.bind("<ButtonPress-1>", self.draw_shape)
        self.canvas.bind("<Motion>", self.motion)
        # self.canvas.bind("<Button 1>", self.draw_polygons)
        self.canvas.bind("<Button 2>", self.select2)
        self.canvas.bind("<Button 3>", self.select)
        self.master.bind("<Return>", self.save_polygons)
        self.master.bind("<Delete>", self.delete_annotation)
        self.canvas.bind("<B2-Motion>", self.move2)

        self.menubar = Menu(self.master)
        self.options = Menu(self.menubar, tearoff=0)
        self.shape = Menu(self.options, tearoff=0)
        self.options.add_cascade(label="Shape options", menu=self.shape)
        self.menubar.add_cascade(label="Options", menu=self.options)
        self.master.config(menu=self.menubar)

        # Load and save file functions
        self.shape.add_command(
            label="Circle",
            command=lambda: self.set_shape(mode="circle"),
        )
        self.shape.add_command(
            label="Ellipse",
            command=lambda: self.set_shape(mode="ellipse"),
        )
        self.shape.add_command(
            label="Roi",
            command=lambda: self.set_shape(mode="roi"),
        )

    def set_shape(self, mode):
        self.mode = mode

    def motion(self, event):
        """ Track mouse position over the canvas """
        x = self.canvas.canvasx(event.x)  # get coordinates of the event on the canvas
        y = self.canvas.canvasy(event.y)
        if self.motionid:
            self.canvas.delete(self.motionid)
        if len(self.centers) == 1:
            self.motionid = self.draw_shape_func(self.centers[0], (x, y))

        # elif len(self.centers) ==2

    def draw_shape_func(self, coord1, coord2, mode=None):
        if not mode:
            mode = self.mode
        if mode == "ellipse":
            temp = self.draw_ellipse(coord1, coord2)
        elif mode == "circle":
            # radius = math.sqrt(
            #     math.pow(coord1 - coord2[0], 2) + math.pow(coord1 - coord2[1], 2)
            # )
            temp = self.draw_circle(coord1, coord2)
        elif mode == "roi":
            temp = self.draw_roi(coord1, coord2)

        return temp

    def delete_annotation(self, event):
        for idx in self.canvas.find_withtag("DELETE"):
            # del self.annotations[idx]
            self.canvas.delete(idx)

    def draw_ellipse(self, center, edge):
        # x0 y0 leftop x1, y1 right down
        if edge[0] > center[0]:
            x0 = center[0] - (edge[0] - center[0])
            x1 = edge[0]
        elif edge[0] < center[0]:
            x0 = edge[0]
            x1 = center[0] - (edge[0] - center[0])
        else:
            x0 = center[0]
            x1 = center[0]

        if edge[1] > center[1]:
            y0 = center[1] - (edge[1] - center[1])
            y1 = edge[1]
        elif edge[1] < center[1]:
            y0 = edge[1]
            y1 = center[1] - (edge[1] - center[1])
        else:
            y0 = center[1]
            y1 = center[1]

        temp_id = self.canvas.create_oval(
            x0, y0, x1, y1, fill="", outline="green", width=2
        )
        return temp_id

    def draw_circle(self, coord1, coord2):
        radius = math.sqrt(
            math.pow(coord1[0] - coord2[0], 2) + math.pow(coord1[1] - coord2[1], 2)
        )
        x0, x1 = coord1[0] + radius, coord1[0] - radius
        y0, y1 = coord1[1] - radius, coord1[1] + radius
        temp_id = self.canvas.create_oval(
            x0, y0, x1, y1, fill="", outline="green", width=2
        )
        return temp_id

    def draw_roi(self, first_corner, second_corner):
        if first_corner[0] > second_corner[0]:
            x0 = first_corner[0]
            x1 = second_corner[0]
        elif first_corner[0] < second_corner[0]:
            x0 = second_corner[0]
            x1 = first_corner[0]
        else:
            x0 = 0
            x1 = 0

        if first_corner[1] > second_corner[1]:
            y0 = first_corner[1]
            y1 = second_corner[1]
        elif first_corner[1] < second_corner[1]:
            y0 = second_corner[1]
            y1 = first_corner[1]
        else:
            y0 = 0
            y1 = 0

        temp_id = self.canvas.create_rectangle(
            x0, y0, x1, y1, fill="", outline="green", width=2
        )
        return temp_id

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

        self.temp_ids.append(temp_id)
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

    def draw_shape(self, event):
        center_x, center_y = event.x, event.y
        self.centers.append([center_x, center_y])

        if len(self.centers) == 2:
            tempid = self.draw_shape_func(self.centers[0], self.centers[1])
            self.annotations[f"{tempid}"] = (self.centers, self.mode)
            self.centers = []

            return tempid

    def draw_polygons(self, event):
        self.delete_temp_ids()

        center_x, center_y = event.x, event.y
        self.temp_centers.append((center_x, center_y))

        dots = self.draw_dots(self.temp_centers)
        self.temp_ids.extend(dots)

        self.draw_annotations(self.temp_centers, True)

    def save_polygons(self, event):
        self.delete_temp_ids()
        poly_id = self.draw_annotations(self.temp_centers, False)
        self.annotations[f"{poly_id}"] = self.temp_centers
        self.temp_ids = []
        self.temp_centers = []

    def delete_all_polygons(self, event):
        self.canvas.delete(ALL)
        self.temp = []
        self.annotations = []

    def select(self, event):

        widget_id = event.widget.find_closest(event.x, event.y, halo=2)
        if len(widget_id):
            if widget_id[0] in self.selected:
                self.canvas.itemconfigure(widget_id, outline="green")
                self.selected.pop(self.selected.index(widget_id[0]))
                # if widget_id[0] in self.select_dots:
                #     for idx in self.select_dots[widget_id[0]]:
                #         self.canvas.delete(idx)

            elif widget_id[0] not in self.selected2:
                # dots_centers = self.annotations[str(widget_id[0])]
                # self.select_dots = {widget_id[0]: self.draw_dots(dots_centers, "red")}
                self.canvas.itemconfigure(widget_id, tags="DELETE", outline="red")
                self.selected.append(widget_id[0])

    def select2(self, event):
        widget_id = event.widget.find_closest(event.x, event.y, halo=5)
        if len(widget_id):
            if widget_id[0] in self.selected2:
                self.canvas.itemconfigure(widget_id, outline="green")
                self.selected2 = []
                self.selected_dots = []

            elif widget_id[0] not in self.selected:
                if not len(self.selected2):
                    self.canvas.itemconfigure(widget_id, tags="SELECT", outline="blue")
                    self.selected2.append(widget_id[0])

    def move(self, event):
        print(event.x, event.y)
        widget_id = event.widget.find_closest(event.x, event.y)
        if widget_id[0] in self.selected2:
            if not len(self.selected_dots):
                self.selected_dots = self.annotations[str(widget_id[0])]
            dots_array = np.array(self.selected_dots)
            center = np.average(dots_array, 0)
            move = np.array([event.x, event.y]) - center
            dots_centers = [
                [x[0] + move[0], x[1] + move[1]] for x in self.selected_dots
            ]
            new_poly_id = self.canvas.create_polygon(
                dots_centers, fill="", tags="SELECT", outline="blue", width=2
            )
            self.selected2.append(new_poly_id)
            self.selected2.pop(self.selected2.index(widget_id[0]))
            self.canvas.delete(widget_id[0])
            del self.annotations[str(widget_id[0])]
            self.annotations[str(new_poly_id)] = dots_centers

    def move2(self, event):
        widget_id = event.widget.find_closest(event.x, event.y)
        if widget_id[0] in self.selected2:
            coords, mode = self.annotations[str(widget_id[0])]
            # center = [coords[0][0] - coords[1][0], coords[0][1] - coords[1][1]]
            xdim = abs(coords[0][0] - coords[1][0])
            ydim = abs(coords[0][1] - coords[1][1])
            new_coord1, new_coord2 = self.find_coords((event.x, event.y), xdim, ydim)
            new_id = self.draw_shape_func(new_coord1, new_coord2, mode)
            self.selected2.append(new_id)
            self.selected2.pop(self.selected2.index(widget_id[0]))
            self.canvas.delete(widget_id[0])
            self.canvas.itemconfigure(new_id, tags="SELECT", outline="blue")
            self.annotations[f"{new_id}"] = ([new_coord1, new_coord2], mode)
            del self.annotations[str(widget_id[0])]

    def find_coords(self, center, xdim, ydim):
        x0 = center[0] - int(xdim / 2)
        x1 = center[0] + int(xdim / 2)

        y0 = center[1] - int(ydim / 2)
        y1 = center[1] + int(ydim / 2)
        return (x0, y0), (x1, y1)

    def delete_temp_ids(self):
        if len(self.temp_ids):
            for idx in self.temp_ids:
                self.canvas.delete(idx)


# Main function
if __name__ == "__main__":
    root = Tk()
    anno = Draw(root)
    root.mainloop()