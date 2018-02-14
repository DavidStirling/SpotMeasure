# MigraMeasure - A tool for quantifying how far into a region fluorescent objects have migrated.
# Copyright(C) 2018 David Stirling

"""This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>."""

import os
import threading
import tkinter as tk
import tkinter.filedialog as tkfiledialog
from tkinter import ttk

import numpy as np
from PIL import Image
from PIL import ImageTk

import measurescript as ms

# Global Variables
version = "0.4 Beta"
regionfiles = []
spotfiles = []
regionshortnames = []
spotshortnames = []
firstrun = True  # Do we need to write headers to the output file?


# Get path for unpacked Pyinstaller exe (MEIPASS), else default to current dir.
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# Core UI
class CoreWindow:
    # Core tabbed GUI
    def __init__(self, master):
        self.master = master
        self.master.wm_title("MigraMeasure")
        self.master.iconbitmap(resource_path('resources/mmicon.ico'))
        self.master.resizable(width=False, height=True)
        self.height = self.master.winfo_screenheight()
        self.width = 740
        self.desiredheight = 825
        if self.height < self.desiredheight:
            self.master.geometry('%sx%s' % (self.width, self.height - 50))
        else:
            self.master.geometry('%sx%s' % (self.width, self.desiredheight))

        # Top Bar
        self.header = tk.Frame()
        self.title = tk.Label(self.header, text="MigraMeasure", font=("Arial", 25), justify=tk.CENTER)
        self.title.grid(column=2, columnspan=1, row=1, sticky=tk.E + tk.W)

        self.buttontype = ttk.Style()
        self.buttontype.configure('MM.TButton', foreground='blue')
        self.aboutbutton = ttk.Button(self.header, text="About", command=self.about_window, style='MM.TButton')
        self.aboutbutton.grid(column=4, row=1, rowspan=1, sticky=tk.E + tk.W, padx=25)
        self.header.grid_columnconfigure(1, weight=1)
        self.header.grid_columnconfigure(5, weight=1)
        self.header.pack(fill=tk.BOTH)

        # Tab Control
        self.tabControl = ttk.Notebook()
        self.tabControl.pack(pady=(10, 0), padx=5, fill=tk.BOTH, expand=True)
        self.tab1 = ttk.Frame(self.tabControl)  # Input page
        self.tab2 = ttk.Frame(self.tabControl)  # region segmentation page
        self.tab3 = ttk.Frame(self.tabControl)  # spot segmentation page
        self.tab4 = ttk.Frame(self.tabControl)  # Output page

        self.tabControl.add(self.tab1, text='Input')
        self.tabControl.add(self.tab2, text='Region Detection', sticky=tk.W + tk.E + tk.N + tk.S)
        self.tabControl.add(self.tab3, text='Spot Detection')
        self.tabControl.add(self.tab4, text='Output')

        # Construct tab contents
        self.input = InputTab(self.tab1)
        self.regionconfig = ImageViewer(self.tab2, "regions")
        self.spotconfig = ImageViewer(self.tab3, "spots")
        self.logconfig = OutputTab(self.tab4)
        self.tabControl.bind('<Button-1>', self.on_click)

        #  Hold empty
        self.about_window = None
        self.app = None

    def on_click(self, event):
        global regionfiles, regionshortnames, spotfiles, spotshortnames
        activated_tab = self.tabControl.tk.call(self.tabControl._w, "identify", "tab", event.x, event.y)
        if activated_tab == 1:
            self.regionconfig.activate_tab(regionfiles, regionshortnames)
        elif activated_tab == 2:
            self.spotconfig.activate_tab(spotfiles, spotshortnames)

    def about_window(self):
        x = self.master.winfo_rootx()
        y = self.master.winfo_rooty()
        x += self.master.winfo_width()
        self.about_window = tk.Toplevel(self.master)
        self.app = AboutWindow(self.about_window)
        self.about_window.title("About")
        self.about_window.wm_attributes('-toolwindow', 1)
        self.about_window.focus_set()
        self.about_window.grab_set()
        self.about_window.update_idletasks()
        self.about_window.geometry(
            '%dx%d+%d+%d' % (self.about_window.winfo_width(), self.about_window.winfo_height(), x, y))
        self.about_window.resizable(width=False, height=False)


class AboutWindow:
    # Simple about window frame
    def __init__(self, master):
        self.master = master
        x = self.master.winfo_rootx()
        x += self.master.winfo_width()
        self.aboutwindow = tk.Frame(self.master)
        self.logo = Image.open(resource_path("resources/logo.png"))
        self.logoimg = ImageTk.PhotoImage(self.logo)
        self.logoimage = tk.Label(self.aboutwindow, image=self.logoimg)
        self.logoimage.pack(pady=(15, 0))
        self.heading = tk.Label(self.aboutwindow, text="MigraMeasure", font=("Arial", 18), justify=tk.CENTER)
        self.heading.pack()
        self.line2 = tk.Label(self.aboutwindow, text="Version " + version, font=("Consolas", 10), justify=tk.CENTER)
        self.line2.pack(pady=(0, 5))
        self.line3 = tk.Label(self.aboutwindow, text="David Stirling, 2018", font=("Arial", 10), justify=tk.CENTER)
        self.line3.pack()
        self.line4 = tk.Label(self.aboutwindow, text="@DavidRStirling", font=("Arial", 10), justify=tk.CENTER)
        self.line4.pack(pady=(0, 15))
        self.aboutwindow.pack()


def customtoggle(kwd, target):
    if kwd == "Custom":
        target.config(state=tk.NORMAL)
        target.delete(0, tk.END)
    else:
        target.config(state=tk.DISABLED)


class InputTab(tk.Frame):
    # A tab for choosing files
    def __init__(self, target):
        tk.Frame.__init__(self)
        self.inputframe = ttk.Frame(target)
        self.inputframe.pack()
        self.loaddir = tk.StringVar()
        self.loaddir.set('Select a directory to process')
        self.dirselect = ttk.Button(self.inputframe, text="Select Directory", command=self.select_directory)
        self.dirselect.grid(column=11, row=1, rowspan=1, padx=5, sticky=tk.E + tk.W)
        self.currdir = ttk.Entry(self.inputframe, textvariable=self.loaddir)
        self.currdir.grid(column=1, columnspan=10, ipadx=150, padx=5, pady=5, row=1, sticky=tk.E + tk.W)
        self.currdir.bind("<Button-1>", self.select_directory)
        self.subdiron = tk.BooleanVar()
        self.subdiron.set(True)
        self.subdircheck = ttk.Checkbutton(self.inputframe, text="Include Subdirectories", variable=self.subdiron,
                                           onvalue=True, offvalue=False)
        self.subdircheck.grid(column=7, row=2, columnspan=4, sticky=tk.E)

        # Region Colour Select Box
        self.region_keyword = tk.StringVar()
        self.region_keyword.set("Blue")
        self.region_custom_text = tk.StringVar()
        self.region_custom_text.set('Enter Keyword')
        self.region_colour = ttk.LabelFrame(self.inputframe, text="Region Filename Keyword:")
        self.region_colour.grid(column=1, columnspan=5, row=4, sticky=tk.W + tk.E + tk.N + tk.S, padx=5, pady=5)
        self.custom = ttk.Entry(self.region_colour, textvariable=self.region_custom_text)
        self.custom.grid(column=3, columnspan=2, row=4, pady=3, sticky=tk.W)
        self.custom.config(state=tk.DISABLED)
        self.opt1 = ttk.Radiobutton(self.region_colour, text="Blue", variable=self.region_keyword, value="Blue",
                                    command=lambda: customtoggle("Blue", self.custom))
        self.opt1.grid(column=1, columnspan=2, row=2, sticky=tk.W)
        self.opt2 = ttk.Radiobutton(self.region_colour, text="Green", variable=self.region_keyword, value="Green",
                                    command=lambda: customtoggle("Green", self.custom))
        self.opt2.grid(column=3, columnspan=2, row=2, sticky=tk.W)
        self.opt3 = ttk.Radiobutton(self.region_colour, text="Red", variable=self.region_keyword, value="Red",
                                    command=lambda: customtoggle("Red", self.custom))
        self.opt3.grid(column=1, columnspan=2, row=3, sticky=tk.W)
        self.opt4 = ttk.Radiobutton(self.region_colour, text="FarRed", variable=self.region_keyword, value="FarRed",
                                    command=lambda: customtoggle("FarRed", self.custom))
        self.opt4.grid(column=3, columnspan=2, row=3, sticky=tk.W)
        self.opt5 = ttk.Radiobutton(self.region_colour, text="Custom:", variable=self.region_keyword, value="Custom",
                                    command=lambda: customtoggle("Custom", self.custom))
        self.opt5.grid(column=1, columnspan=2, row=4, sticky=tk.W)

        # Spot Colour Select Box
        self.spot_keyword = tk.StringVar()
        self.spot_keyword.set("_Red")
        self.spot_custom_text = tk.StringVar()
        self.spot_custom_text.set('Enter Keyword')
        self.spot_colour = ttk.LabelFrame(self.inputframe, text="Spot Filename Keyword:")
        self.spot_colour.grid(column=6, columnspan=5, row=4, sticky=tk.W + tk.E + tk.N + tk.S, padx=5, pady=5)
        self.custom2 = ttk.Entry(self.spot_colour, textvariable=self.spot_custom_text)
        self.custom2.grid(column=3, columnspan=2, row=4, pady=3, sticky=tk.W)
        self.custom2.config(state=tk.DISABLED)
        self.opt6 = ttk.Radiobutton(self.spot_colour, text="Blue", variable=self.spot_keyword, value="Blue",
                                    command=lambda: customtoggle("Blue", self.custom2))
        self.opt6.grid(column=1, columnspan=2, row=2, sticky=tk.W)
        self.opt7 = ttk.Radiobutton(self.spot_colour, text="Green", variable=self.spot_keyword, value="Green",
                                    command=lambda: customtoggle("Green", self.custom2))
        self.opt7.grid(column=3, columnspan=2, row=2, sticky=tk.W)
        self.opt8 = ttk.Radiobutton(self.spot_colour, text="Red", variable=self.spot_keyword, value="_Red",
                                    command=lambda: customtoggle("Red", self.custom2))
        self.opt8.grid(column=1, columnspan=2, row=3, sticky=tk.W)
        self.opt9 = ttk.Radiobutton(self.spot_colour, text="FarRed", variable=self.spot_keyword, value="FarRed",
                                    command=lambda: customtoggle("FarRed", self.custom2))
        self.opt9.grid(column=3, columnspan=2, row=3, sticky=tk.W)
        self.opt10 = ttk.Radiobutton(self.spot_colour, text="Custom:", variable=self.spot_keyword, value="Custom",
                                     command=lambda: customtoggle("Custom", self.custom2))
        self.opt10.grid(column=1, columnspan=2, row=4, sticky=tk.W)

        # Keyword Search Type Chooser
        self.searchtype = tk.IntVar()
        self.searchtype.set(0)
        self.search_type_box = ttk.LabelFrame(self.inputframe, text="Find Keyword In:")
        self.search_type_box.grid(column=11, columnspan=1, row=4, padx=5, sticky=tk.W + tk.E + tk.N + tk.S, pady=5)
        self.checkname = ttk.Radiobutton(self.search_type_box, text="File Name", variable=self.searchtype, value=0)
        self.checkname.grid(column=1, row=2, sticky=tk.W)
        self.checksubd = ttk.Radiobutton(self.search_type_box, text="Subdirectory", variable=self.searchtype, value=1)
        self.checksubd.grid(column=1, row=3, sticky=tk.W)
        self.checkpath = ttk.Radiobutton(self.search_type_box, text="Full Path", variable=self.searchtype, value=2)
        self.checkpath.grid(column=1, row=4, sticky=tk.W)

        # File List Generator
        self.gen_filelist = ttk.Button(target, text="Generate File List", command=self.populate_file_list)
        self.gen_filelist.pack(fill=tk.X, padx=20, pady=10)

        # List Box Frame
        self.file_list_box = ttk.Frame(target, border=2, relief=tk.GROOVE)
        self.file_list_box.pack(expand=True, fill=tk.Y)
        self.scrollbar = ttk.Scrollbar(self.file_list_box, orient=tk.VERTICAL)
        self.regionbox = tk.Listbox(self.file_list_box, width=52, yscrollcommand=self.scrollbar.set, activestyle="none")
        self.regionbox.grid(column=1, row=1, rowspan=10, sticky=tk.W + tk.E + tk.N + tk.S)
        self.spotbox = tk.Listbox(self.file_list_box, width=52, yscrollcommand=self.scrollbar.set, activestyle="none")
        self.spotbox.grid(column=4, row=1, rowspan=10, sticky=tk.W + tk.E + tk.N + tk.S)
        self.scrollbar.config(command=self.scroll_listboxes)
        self.scrollbar.grid(column=5, row=1, rowspan=10, sticky=tk.W + tk.E + tk.N + tk.S)
        self.regionbox.bind("<MouseWheel>", self.mousewheel_listboxes)
        self.spotbox.bind("<MouseWheel>", self.mousewheel_listboxes)
        self.file_list_box.grid_rowconfigure(1, weight=1)
        self.file_list_box.grid_rowconfigure(10, weight=1)

        # Control Buttons
        self.move_item_up = ttk.Button(self.file_list_box, text="Up", command=lambda: self.move_list_item("up"))
        self.upphoto = tk.PhotoImage(file="resources/Up.png")
        self.move_item_up.config(image=self.upphoto)
        self.move_item_down = ttk.Button(self.file_list_box, text="Down", command=lambda: self.move_list_item("down"))
        self.dnphoto = tk.PhotoImage(file="resources/Down.png")
        self.move_item_down.config(image=self.dnphoto)
        self.add_item = ttk.Button(self.file_list_box, text="Add", command=self.add_list_item)
        self.addphoto = tk.PhotoImage(file="resources/Add.png")
        self.add_item.config(image=self.addphoto)
        self.remove_item = ttk.Button(self.file_list_box, text="Remove", command=self.remove_list_item)
        self.delphoto = tk.PhotoImage(file="resources/Remove.png")
        self.remove_item.config(image=self.delphoto)
        self.move_item_up.grid(column=3, row=2, padx=2, pady=5, sticky=tk.E + tk.W)
        self.move_item_down.grid(column=3, row=3, padx=2, pady=5, sticky=tk.E + tk.W)
        self.add_item.grid(column=3, row=4, padx=2, pady=5, sticky=tk.E + tk.W)
        self.remove_item.grid(column=3, row=5, padx=2, pady=5, sticky=tk.E + tk.W)

    def get_selected(self):
        if self.regionbox.curselection():
            return "regions", self.regionbox.curselection()[0]
        elif self.spotbox.curselection():
            return "spots", self.spotbox.curselection()[0]
        else:
            return "none", 0

    def remove_list_item(self):
        global regionfiles, spotfiles, regionshortnames, spotshortnames
        target, selected = self.get_selected()
        if target == "regions":
            if spotfiles[selected] == "<No File Found>":
                del spotfiles[selected]
                del spotshortnames[selected]
            elif spotfiles[-1] == "<No File Found>":
                del spotfiles[-1]
                del spotshortnames[-1]
            del regionfiles[selected]
            del regionshortnames[selected]
        elif target == "spots":
            if regionfiles[selected] == "<No File Found>":
                del regionfiles[selected]
                del regionshortnames[selected]
            elif regionfiles[-1] == "<No File Found>":
                del regionfiles[-1]
                del regionshortnames[-1]
            del spotfiles[selected]
            del spotshortnames[selected]
        else:
            return
        self.update_file_list()

    def add_list_item(self):
        global regionfiles, spotfiles, regionshortnames, spotshortnames
        maxlen = 50
        newfile = tkfiledialog.askopenfilename(title="Choose an image to add", initialdir=self.loaddir,
                                               filetypes=[('Tiff file', '*.tif')])
        if newfile:
            target, selected = self.get_selected()
            if target == "regions":
                if regionfiles[selected] == "<No File Found>":
                    del regionfiles[selected]
                    del regionshortnames[selected]
                regionfiles.insert(selected, newfile)
                regionshortnames.insert(selected, (('..' + newfile[-maxlen:]) if len(newfile) > maxlen else newfile))
            if target == "spots":
                if spotfiles[selected] == "<No File Found>":
                    del spotfiles[selected]
                    del spotshortnames[selected]
                spotfiles.insert(selected, newfile)
                spotshortnames.insert(selected, ('..' + (newfile[-maxlen:]) if len(newfile) > maxlen else newfile))
            else:
                regionfiles.insert(-1, newfile)
                regionshortnames.insert(-1, ('..' + (newfile[-maxlen:]) if len(newfile) > maxlen else newfile))
            self.update_file_list()
        return

    def move_list_item(self, direction):
        global regionfiles, spotfiles, regionshortnames, spotshortnames
        target, selected = self.get_selected()
        if target == "none":
            return
        if direction == "up":
            newindex = selected - 1
        else:
            newindex = selected + 1
        if target == "regions":
            regionfiles.insert(newindex, regionfiles.pop(selected))
            regionshortnames.insert(newindex, regionshortnames.pop(selected))
            self.update_file_list()
            self.regionbox.selection_set(newindex)
        elif target == "spots":
            spotfiles.insert(newindex, spotfiles.pop(selected))
            spotshortnames.insert(newindex, spotshortnames.pop(selected))
            self.update_file_list()
            self.spotbox.selection_set(newindex)

    def scroll_listboxes(self, *args):
        self.regionbox.yview(*args)
        self.spotbox.yview(*args)

    def mousewheel_listboxes(self, event):
        direction = 0
        if event.delta == -120:
            direction = 1
        if event.delta == 120:
            direction = -1
        self.regionbox.yview_scroll(direction, "units")
        self.spotbox.yview_scroll(direction, "units")
        return "break"  # Prevent default bindings from activating and trying to scroll twice

    def select_directory(self, *args):
        tryloaddir = tkfiledialog.askdirectory(title='Choose directory')
        if tryloaddir:
            self.loaddir.set(tryloaddir)
            app.logconfig.logevent("Images will be read from: " + tryloaddir)
            return
        app.logconfig.logevent("Directory not selected")

    def populate_file_list(self):
        global regionfiles, spotfiles, regionshortnames, spotshortnames
        if self.region_keyword.get() == "Custom":
            regionkwd = self.region_custom_text.get()
        else:
            regionkwd = self.region_keyword.get()
        if self.spot_keyword.get() == "Custom":
            spotkwd = self.spot_custom_text.get()
        else:
            spotkwd = self.spot_keyword.get()
        self.regionbox.delete(0, tk.END)
        self.spotbox.delete(0, tk.END)
        regionfiles, spotfiles, regionshortnames, spotshortnames = ms.genfilelist(self.loaddir.get(),
                                                                                  self.subdiron.get(), regionkwd,
                                                                                  spotkwd, self.searchtype.get())
        # FILL MISSING FILES
        if len(regionshortnames) < len(spotshortnames):
            regionfiles += ["<No File Found>"] * (len(spotfiles) - len(regionfiles))
            regionshortnames += ["<No File Found>"] * (len(spotshortnames) - len(regionshortnames))
        if len(regionshortnames) > len(spotshortnames):
            spotfiles += ["<No File Found>"] * (len(regionfiles) - len(spotfiles))
            spotshortnames += ["<No File Found>"] * (len(regionshortnames) - len(spotshortnames))
        for file in regionshortnames:
            self.regionbox.insert(tk.END, file)
        for file in spotshortnames:
            self.spotbox.insert(tk.END, file)
        app.regionconfig.firstview = True
        app.spotconfig.firstview = True

    def update_file_list(self):
        global regionfiles, spotfiles, regionshortnames, spotshortnames
        self.regionbox.delete(0, tk.END)
        self.spotbox.delete(0, tk.END)
        # FILL MISSING FILES
        if len(regionshortnames) < len(spotshortnames):
            regionfiles += ["<No File Found>"] * (len(spotfiles) - len(regionfiles))
            regionshortnames += ["<No File Found>"] * (len(spotshortnames) - len(regionshortnames))
        if len(regionshortnames) > len(spotshortnames):
            spotfiles += ["<No File Found>"] * (len(regionfiles) - len(spotfiles))
            spotshortnames += ["<No File Found>"] * (len(regionshortnames) - len(spotshortnames))
        for file in regionshortnames:
            self.regionbox.insert(tk.END, file)
        for file in spotshortnames:
            self.spotbox.insert(tk.END, file)
        app.regionconfig.firstview = True
        app.spotconfig.firstview = True


class ImageViewer(tk.Frame):
    # A previewing pane for displaying images from a directory alongside controls to cycle through files
    def __init__(self, target, viewertype):
        tk.Frame.__init__(self)
        self.firstview = True
        self.type = viewertype
        self.fileid = 0
        if self.type == "regions":
            global regionfiles, regionshortnames
            self.imagepool = regionfiles
            self.imagenamepool = regionshortnames
            self.default_smoothing = 10
            self.default_minsize = 1000
            self.default_thresh = 4096
        elif self.type == "spots":
            global spotfiles, spotshortnames
            self.imagepool = spotfiles
            self.imagenamepool = spotshortnames
            self.default_smoothing = 1
            self.default_minsize = 10
            self.default_thresh = 8192
        self.ivcanvas = tk.Canvas(target, highlightthickness=0)
        self.ivframe = ttk.Frame(self.ivcanvas)
        self.ivscrollbar = ttk.Scrollbar(target, command=self.ivcanvas.yview)
        self.ivcanvas.configure(yscrollcommand=self.ivscrollbar.set)

        self.ivscrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.ivcanvas.pack(fill=tk.BOTH, expand=True, ipadx=10)
        self.ivcanvas.create_window((0, 0), window=self.ivframe, anchor="nw")
        self.ivframe.bind("<Configure>", self.config_canvas)
        # Reserve essential variables
        self.previewfile = None
        self.previewfiletitle = ""
        self.image = None
        self.im = None
        self.im2 = None
        self.numplanes = 0
        self.planeid = 1
        self.temppreview = None
        self.preview = None

        # Image Frame Constructor
        self.previewframe = ttk.Frame(self.ivframe, width=696, height=520)
        self.previewpane = tk.Label(self.previewframe)
        self.previewpane.pack()
        self.previewpane.bind("<MouseWheel>", self.mouse_wheel)

        # Frame of plane controls
        self.imgcontrols = ttk.LabelFrame(self.ivframe, text="File Controls:",
                                          relief=tk.GROOVE)  # Frame for preview controls.
        self.imgcontrols.pack(expand=1, fill=tk.BOTH, padx=5, pady=5)
        self.imgcontrols.grid_columnconfigure(10, weight=1)
        self.imgcontrols.grid_columnconfigure(1, weight=1)
        self.previewtitle = ttk.Label(self.imgcontrols, text=("..." + self.previewfiletitle[-60:]))
        self.previewtitle.grid(row=1, column=2, columnspan=6, padx=20)

        self.prevpreviewbutton = ttk.Button(self.imgcontrols, text="Previous File")
        self.prevpreviewbutton.grid(column=2, row=2, padx=(3, 0), pady=5, ipadx=10)
        self.prevpreviewbutton.config(state=tk.DISABLED)
        self.nextpreviewbutton = ttk.Button(self.imgcontrols, text="Next File")
        self.nextpreviewbutton.grid(column=3, row=2, padx=(0, 3), pady=5, ipadx=10)
        self.changepreviewbutton = ttk.Button(self.imgcontrols, text="Select File", )
        self.changepreviewbutton.grid(column=4, row=2, padx=3, ipadx=10)

        self.prevplanebutton = ttk.Button(self.imgcontrols, text="Previous", state=tk.DISABLED)
        self.prevphoto = tk.PhotoImage(file="resources/Left.png")
        self.prevplanebutton.config(image=self.prevphoto)
        self.prevplanebutton.grid(column=5, row=2, padx=1, pady=2)
        self.planenumber = ttk.Label(self.imgcontrols, text=(
                "Plane " + str("%02d" % self.planeid) + " of " + str("%02d" % self.numplanes)))
        self.planenumber.grid(column=6, row=2)
        self.nextplanebutton = ttk.Button(self.imgcontrols, text="Next", state=tk.DISABLED)
        self.nextphoto = tk.PhotoImage(file="resources/Right.png")
        self.nextplanebutton.config(image=self.nextphoto)
        self.nextplanebutton.grid(column=7, row=2, padx=1, pady=2)

        self.changepreviewbutton.config(command=lambda: self.update_file("new"))
        self.prevpreviewbutton.config(command=lambda: self.update_file("rev"))
        self.nextpreviewbutton.config(command=lambda: self.update_file("fwd"))
        self.prevplanebutton.config(command=lambda: self.update_plane("rev"))
        self.nextplanebutton.config(command=lambda: self.update_plane("fwd"))

        self.previewframe.pack(padx=5, fill=tk.Y)

        # Image Segmentation Controls
        self.segcontrols = ttk.LabelFrame(self.ivframe, text="Detection Options",
                                          relief=tk.GROOVE)  # Frame for preview controls.
        self.segcontrols.pack()
        self.segcontrols.grid_columnconfigure(10, weight=1)
        self.segcontrols.grid_columnconfigure(1, weight=1)
        self.seglabel = ttk.Label(self.segcontrols, text="Segmentation Mode:")
        self.seglabel.grid(column=2, row=1, columnspan=2)
        self.segtype = tk.BooleanVar()

        self.autoseg = ttk.Radiobutton(self.segcontrols, text="Automatic", variable=self.segtype, value=True,
                                       command=lambda: self.threshold_mode(True))
        self.autoseg.grid(column=2, row=2)
        self.manualseg = ttk.Radiobutton(self.segcontrols, text="Manual", variable=self.segtype, value=False,
                                         command=lambda: self.threshold_mode(False))
        self.manualseg.grid(column=3, row=2)

        # Regen Preview and Overlay Buttons
        self.regenprev = ttk.Button(self.segcontrols, text="Refresh Preview")
        self.regenprev.grid(column=4, row=1, padx=5, rowspan=2, sticky=tk.NSEW)
        self.toggleoverlay = ttk.Button(self.segcontrols, text="Show/Hide Overlay")
        self.toggleoverlay.grid(column=5, row=1, padx=5, rowspan=2, sticky=tk.NSEW)
        self.overlaysave = ttk.Button(self.segcontrols, text="Save Preview")
        self.overlaysave.grid(column=6, row=1, rowspan=2, padx=5, sticky=tk.NSEW)

        # Preview Progress
        self.progress_var = tk.IntVar()
        self.progress_var.set(0)
        self.previewprogress = ttk.Progressbar(self.segcontrols, mode='determinate', variable=self.progress_var,
                                               length=100, orient=tk.HORIZONTAL)
        self.previewprogress.grid(column=7, row=1, rowspan=2, pady=5, sticky=tk.E, padx=20)

        # Manual Segmentation Sliders
        self.sliderframe = ttk.Frame(self.segcontrols)
        self.sliderframe.grid(column=1, row=3, columnspan=50, padx=5, pady=5, sticky=tk.NSEW)
        self.sliderframe.grid_columnconfigure(1, weight=1)
        self.sliderframe.grid_columnconfigure(3, weight=1)

        # Threshold
        self.thresh = tk.IntVar()
        self.thresh.set(50)
        self.thresholdlabel = ttk.LabelFrame(self.sliderframe, text="Threshold:")
        self.thresholdlabel.grid(column=1, row=4, padx=5)
        self.threshold_max = 65000
        self.threshold = ttk.Scale(self.thresholdlabel, from_=0, to=self.threshold_max, length=200,
                                   variable=self.thresh, command=lambda s: self.thresh.set('%0.0f' % float(s)))
        self.threshold.grid(column=1, columnspan=1, row=1, padx=5)
        self.setthr = ttk.Entry(self.thresholdlabel, textvariable=self.thresh, justify=tk.CENTER, )
        self.setthr.grid(column=1, row=2, sticky=tk.S)

        # Smoothing
        self.smooth = tk.IntVar()
        self.smooth.set(10)
        self.smoothlabel = ttk.LabelFrame(self.sliderframe, text="Smoothing")
        self.smoothlabel.grid(column=2, row=4, padx=5)
        self.smoothscale = ttk.Scale(self.smoothlabel, from_=0, to=50, length=200, variable=self.smooth,
                                     command=lambda s: self.smooth.set('%0.1f' % float(s)))
        self.smoothscale.grid(column=1, row=1, padx=5)
        self.setsmooth = ttk.Entry(self.smoothlabel, textvariable=self.smooth, justify=tk.CENTER)
        self.setsmooth.grid(column=1, row=2, sticky=tk.S)

        # Min Size
        self.minsize = tk.IntVar()
        self.minsize.set(100)
        self.minsizelabel = ttk.LabelFrame(self.sliderframe, text="Minimum Object Size")
        self.minsizelabel.grid(column=3, row=4, padx=5)
        self.minsizescale = ttk.Scale(self.minsizelabel, from_=0, to=1000, length=200, variable=self.minsize,
                                      command=lambda s: self.minsize.set('%0.0f' % float(s)))
        self.minsizescale.grid(column=1, row=1, padx=5)
        self.setminsize = ttk.Entry(self.minsizelabel, textvariable=self.minsize, justify=tk.CENTER, )
        self.setminsize.grid(column=1, row=2, sticky=tk.S)
        self.threshold_mode(True)
        self.regenprev.config(command=self.initiate_overlay)
        self.toggleoverlay.config(command=self.toggle_overlay)
        # Setup variables for overlay control
        self.overlayon = False
        self.overlaymade = False
        self.segoverlay = None
        self.overlaypreview = None
        self.runningstatus = False

        for child in self.ivframe.children.values():
            child.bind("<MouseWheel>", self.mouse_wheel)

    def activate_tab(self, imagepool, imagenamepool):
        if self.firstview is False:
            return
        self.imagepool = imagepool
        self.imagenamepool = imagenamepool
        self.fileid = 0
        if len(self.imagepool) <= 1:
            self.nextpreviewbutton.config(state=tk.DISABLED)
            self.prevpreviewbutton.config(state=tk.DISABLED)
        if self.imagepool:
            self.previewfile = self.imagepool[self.fileid]
            self.previewfiletitle = self.imagenamepool[self.fileid]
        else:
            self.previewfiletitle = "<No File Selected>"
            self.previewframe.config(height=520)
            self.previewframe.pack_propagate(False)
            self.previewpane.config(image='', text="No Image")
            self.planenumber.config(text=("Plane " + str(00) + " of " + str(00)))
            self.previewtitle.config(text=self.previewfiletitle)
            self.prevplanebutton.config(state=tk.DISABLED)
            self.nextplanebutton.config(state=tk.DISABLED)
            return
        self.planeid = 1
        if self.previewfile != "<No File Found>":
            self.image = Image.open(self.previewfile)
        self.regen_preview()
        self.update_file("none")
        self.firstview = False

    def regen_preview(self):
        if len(self.previewfiletitle) > 150:
            self.previewtitle.config(text=("..." + self.previewfiletitle[-60:]))
        else:
            self.previewtitle.config(text=self.previewfiletitle)
        if self.previewfile == "<No File Found>":
            self.previewpane.config(image='', text="No Image File")
            self.planenumber.config(text=("Plane " + str(00) + " of " + str(00)))
            self.previewframe.config(height=520)
            self.previewframe.pack_propagate(False)
            self.overlayon = False
            self.toggleoverlay.state(['!pressed'])
        else:
            if self.image.mode == 'I;8' or self.image.mode == 'L':
                self.threshold_max = 256
            elif self.image.mode == 'I;16':
                self.threshold_max = 65000
            else:
                self.previewpane.config(image='', text="Invalid Image File Format")
                self.planenumber.config(text=("Plane " + str(00) + " of " + str(00)))
                self.previewframe.config(height=520)
                self.previewframe.pack_propagate(False)
                self.overlayon = False
                self.toggleoverlay.state(['!pressed'])
                return
            self.threshold.config(from_=0, to=self.threshold_max)
            self.im = np.array(self.image)
            self.im2 = (self.im / 256).astype('uint8')
            self.im2 = self.im2[::2, ::2]
            self.temppreview = Image.fromarray(self.im2)
            self.preview = ImageTk.PhotoImage(self.temppreview)
            self.previewpane.config(image=self.preview)

    def update_plane(self, direction):
        self.numplanes = self.image.n_frames
        if direction == "fwd":
            self.planeid += 1
            self.image.seek(self.planeid - 1)
            self.regen_preview()

        elif direction == "rev":
            self.planeid -= 1
            self.image.seek(self.planeid - 1)
            self.regen_preview()
        elif self.previewfile == "<No File Found>":
            self.planenumber.config(text="Plane 00 of 00")
            self.prevplanebutton.config(state=tk.DISABLED)
            self.nextplanebutton.config(state=tk.DISABLED)
            self.overlaymade = False
            self.progress_var.set(0)
            return
        self.planenumber.config(text=("Plane " + str("%02d" % self.planeid) + " of " + str("%02d" % self.numplanes)))
        self.prevplanebutton.config(state=tk.DISABLED)
        self.nextplanebutton.config(state=tk.DISABLED)
        if self.planeid > 1:
            self.prevplanebutton.config(state=tk.NORMAL)
        if self.planeid < self.numplanes:
            self.nextplanebutton.config(state=tk.NORMAL)
        self.overlaymade = False
        if self.overlayon is True:
            self.initiate_overlay()
        else:
            self.progress_var.set(0)

    def update_file(self, changetype):
        self.nextpreviewbutton.config(state=tk.DISABLED)
        self.prevpreviewbutton.config(state=tk.DISABLED)

        if changetype == "fwd":
            self.fileid += 1
            self.previewfile = self.imagepool[self.fileid]
            self.previewfiletitle = self.imagenamepool[self.fileid]
            if self.previewfile != "<No File Found>":
                self.image = Image.open(self.previewfile)
            self.regen_preview()

        elif changetype == "rev":
            self.fileid -= 1
            self.previewfile = self.imagepool[self.fileid]
            self.previewfiletitle = self.imagenamepool[self.fileid]
            if self.previewfile != "<No File Found>":
                self.image = Image.open(self.previewfile)
            self.regen_preview()

        elif changetype == "new":
            self.previewfile = tkfiledialog.askopenfilename(filetypes=[('Tiff file', '*.tif')])

            if self.previewfile:
                self.previewfiletitle = self.previewfile
                self.image = Image.open(self.previewfile)
            self.regen_preview()

        if self.fileid > 0:
            self.prevpreviewbutton.config(state=tk.NORMAL)
        if self.fileid + 1 < len(self.imagepool):
            self.nextpreviewbutton.config(state=tk.NORMAL)

        self.planeid = 1
        self.update_plane("none")

    def segmentation_preview(self):
        self.progress_var.set(0)
        self.previewprogress.start(10)
        self.runningstatus = True
        if self.im is None:  # Don't try to overlay if there is no image set
            self.overlayon = False
            self.overlaymade = False
            self.toggleoverlay.state(['!pressed'])
            self.previewprogress.stop()
            self.progress_var.set(0)
            return
        # Return 8 bit array for display
        labelled = ms.seg_preview(self.im, self.segtype.get(), self.thresh.get(), self.smooth.get(),
                                  self.minsize.get(), self.type)
        miniseg = labelled[::2, ::2]
        self.segoverlay = Image.fromarray(miniseg)
        if self.overlayon is False:  # Abandon overlaying if mode already changed
            return
        self.overlaypreview = ImageTk.PhotoImage(self.segoverlay)
        self.previewpane.config(image=self.overlaypreview)
        self.runningstatus = False
        self.overlaymade = True
        self.previewprogress.stop()
        self.progress_var.set(100)

    def initiate_overlay(self):
        global overlay_thread
        if 'overlay_thread' in globals() and overlay_thread.isAlive():  # Disable overlays if img changing too fast.
            self.previewpane.config(image=self.preview)
            self.overlayon = False
            self.overlaymade = False
            self.toggleoverlay.state(['!pressed'])
            self.previewprogress.stop()
            self.progress_var.set(0)
            return
        overlay_thread = threading.Thread(target=self.segmentation_preview)
        overlay_thread.setDaemon(True)
        overlay_thread.start()
        self.overlayon = True
        self.toggleoverlay.state(['pressed'])

    def toggle_overlay(self):
        if self.overlayon is True:
            self.previewpane.config(image=self.preview)
            self.overlayon = False
            self.toggleoverlay.state(['!pressed'])
        elif self.overlaymade is False:
            self.initiate_overlay()
        else:
            self.previewpane.config(image=self.overlaypreview)
            self.overlayon = True
            self.toggleoverlay.state(['pressed'])

    def config_canvas(self, *args):
        self.ivcanvas.configure(scrollregion=self.ivcanvas.bbox("all"))  # Need to remove delta on OSX

    def mouse_wheel(self, event):
        """ Mouse wheel as scroll bar """
        direction = 0
        # Respond to Linux or Windows wheel event
        if event.delta == -120:
            direction = 1
        if event.delta == 120:
            direction = -1
        self.ivcanvas.yview_scroll(direction, "units")

    def threshold_mode(self, autostatus):
        if autostatus is True:
            stateset = 'disabled'
            self.segtype.set(True)
            self.smooth.set(self.default_smoothing)
            self.minsize.set(self.default_minsize)
            self.thresh.set(self.default_thresh)
        else:
            stateset = '!disabled'
            self.segtype.set(False)
        for widget in self.sliderframe.winfo_children():
            for subwidget in widget.winfo_children():
                subwidget.state([stateset])
            widget.state([stateset])


class OutputTab(tk.Frame):
    # A tab for setting up the data output and viewing the log
    def __init__(self, target):
        tk.Frame.__init__(self)

        self.savestatus = False
        self.previewdirstatus = False
        self.outputcontrols = ttk.Frame(target)
        self.outputcontrols.pack(pady=10)
        # Set Log File

        self.logtext = tk.StringVar()
        self.logtext.set("Create a data log file")
        self.logselect = ttk.Button(self.outputcontrols, text="Select Output File", command=self.save_file_set)
        self.logselect.grid(column=11, row=1, padx=5, sticky=tk.E + tk.W)
        self.currlog = ttk.Entry(self.outputcontrols, textvariable=self.logtext, takefocus=False)
        self.currlog.grid(column=1, columnspan=10, ipadx=150, padx=5, pady=5, row=1, sticky=tk.E + tk.W)

        # Set Preview Save Folder

        self.previewsavedir = tk.StringVar()
        self.previewsavedir.set("Select Preview Save Directory")
        self.prevsaveselect = ttk.Button(self.outputcontrols, text="Select Preview Save Directory",
                                         command=self.preview_directory_set)
        self.prevsaveselect.grid(column=11, row=2, rowspan=1, padx=5, sticky=tk.E + tk.W)
        self.prevdir = ttk.Entry(self.outputcontrols, textvariable=self.previewsavedir, takefocus=False)
        self.prevdir.grid(column=1, columnspan=10, row=2, ipadx=150, padx=5, pady=5, sticky=tk.E + tk.W)
        self.prevsavon = tk.BooleanVar()
        self.prevsavon.set(True)
        self.prevsavecheck = ttk.Checkbutton(self.outputcontrols, text="Save Previews", variable=self.prevsavon,
                                             onvalue=True, offvalue=False, command=self.toggle_preview_status)
        self.prevsavecheck.grid(column=7, row=3, columnspan=4, sticky=tk.E)

        self.one_per_cell = tk.BooleanVar()
        self.one_per_cell.set(False)
        self.singlespotcheck = ttk.Checkbutton(self.outputcontrols, text="Restrict analysis to cells with 1 spot",
                                               variable=self.one_per_cell, onvalue=True, offvalue=False)
        self.singlespotcheck.grid(column=1, row=3, columnspan=4, sticky=tk.E)

        self.startbutton = ttk.Button(target, text="Run!", command=self.sanity_check)
        self.startbutton.pack(expand=False, pady=10)

        self.controlframe = ttk.Frame(target)

        self.filelisttext = ttk.Label(self.controlframe, text="File Progress")
        self.filelisttext.pack()
        self.listprogressvar = tk.IntVar()
        self.listprogressvar.set(0)
        self.listprogress = ttk.Progressbar(self.controlframe, mode='determinate', length=400, orient=tk.HORIZONTAL,
                                            variable=self.listprogressvar)
        self.listprogress.pack(expand=False, pady=(0, 10), padx=20)

        self.planelisttext = ttk.Label(self.controlframe, text="Stack Progress")
        self.planelisttext.pack()
        self.planeprogressvar = tk.IntVar()
        self.planeprogressvar.set(0)
        self.planeprogress = ttk.Progressbar(self.controlframe, mode='determinate', length=400, orient=tk.HORIZONTAL,
                                             variable=self.planeprogressvar)
        self.planeprogress.pack(expand=False, pady=(0, 10), padx=20)

        self.celllisttext = ttk.Label(self.controlframe, text="Image Progress")
        self.celllisttext.pack()
        self.cellprogressvar = tk.IntVar()
        self.cellprogressvar.set(0)
        self.cellprogress = ttk.Progressbar(self.controlframe, mode='determinate', length=400, orient=tk.HORIZONTAL,
                                            variable=self.cellprogressvar)
        self.cellprogress.pack(expand=False, pady=(0, 10), padx=20)

        self.controlframe.pack()

        self.logframe = ttk.Frame(target)
        self.logscrollbar = ttk.Scrollbar(self.logframe)
        self.logbox = tk.Listbox(self.logframe, yscrollcommand=self.logscrollbar.set, activestyle="none")
        self.logbox.pack(expand=True, fill=tk.BOTH, side=tk.LEFT)
        self.logscrollbar.config(command=self.logbox.yview)
        self.logscrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.logbox.insert(tk.END, "Log:")
        self.logframe.pack(fill=tk.BOTH, expand=True, padx=20)

        self.currlog.bind("<Button-1>", self.save_file_set)
        self.prevdir.bind("<Button-1>", self.preview_directory_set)
        self.widgetslist = [self.logselect, self.currlog, self.prevsaveselect, self.prevdir, self.prevsavecheck,
                            self.singlespotcheck]
        self.filelimit = 0
        self.planelimit = 0
        self.celllimit = 0

    # Pushes message to log box.
    def logevent(self, text):
        self.logbox.insert(tk.END, str(text))
        self.logbox.see(tk.END)

    def save_file_set(self, *args):

        logfile = tkfiledialog.asksaveasfile(mode='w', defaultextension='.csv', initialfile='output.csv',
                                             title='Save output file')
        if logfile:
            logfile.close()
            self.logtext.set(logfile.name)
            self.savestatus = True
            self.logevent("Save file set successfully.")
        else:
            self.savestatus = False
            self.logtext.set("Create a data log file")
            self.logevent("Save file selection unsuccessful.")

    def preview_directory_set(self, *args):
        setprevdir = tkfiledialog.askdirectory(title='Choose directory in which to save preview images')
        if setprevdir:
            self.previewsavedir.set(setprevdir + '/')
            self.previewdirstatus = True
            self.logevent("Preview save directory set successfully.")
        else:
            self.previewdirstatus = False
            self.logevent("Preview directory selection unsuccessful.")

    def toggle_preview_status(self):
        if self.prevsavon.get() is True:
            self.prevsaveselect.state(['!disabled'])
            self.prevdir.state(['!disabled'])
        else:
            self.prevsaveselect.state(['disabled'])
            self.prevdir.state(['disabled'])
        return

    def sanity_check(self):
        global regionfiles, spotfiles, regionshortnames, spotshortnames
        if len(regionfiles) < 1 or len(spotfiles) < 1:
            self.logevent("Unable to run: No file list generated")
            return
        if os.path.exists(self.logtext.get()) is False:
            self.logevent("Unable to run: Log file not created")
            return
        if self.prevsavon.get():
            if os.path.isdir(self.previewsavedir.get()) is False:
                self.logevent("Unable to run: No preview directory set")
                return
        finalregionfiles = [file for index, file in enumerate(regionfiles) if
                            regionfiles[index] != "<No File Found>" and spotfiles[index] != "<No File Found>"]
        finalspotfiles = [file for index, file in enumerate(spotfiles) if
                          regionfiles[index] != "<No File Found>" and spotfiles[index] != "<No File Found>"]
        filesremoved = (len(regionfiles) - len(finalregionfiles))
        if filesremoved > 0:
            self.logevent(f"{filesremoved} unpaired files will be skipped")
        self.logevent("Pre-run checks complete. Initiating script")
        self.listprogress.config(maximum=len(regionfiles))
        self.listprogressvar.set(0)
        self.planeprogressvar.set(0)
        self.cellprogressvar.set(0)
        self.filelisttext.config(text='File Progress')
        self.planelisttext.config(text='Plane Progress')
        self.celllisttext.config(text='Cell Progress')
        self.startbutton.config(text="Stop", command=self.abort_analysis)
        self.widgetslist.append(app.tabControl)
        for widget in self.widgetslist:
            widget.state(['disabled'])
        self.currlog.unbind("<Button 1>")
        self.prevdir.unbind("<Button 1>")

        global process_stopper
        process_stopper = threading.Event()
        process_stopper.set()
        work_thread = threading.Thread(target=self.start_analysis,
                                       args=(process_stopper, finalregionfiles, finalspotfiles))
        work_thread.setDaemon(True)
        work_thread.start()

    def abort_analysis(self):
        try:
            process_stopper.clear()
            self.logevent("Aborted run")
            self.update_progress('finished', 0)
        except:
            self.logevent("Unable to stop")

    def start_analysis(self, stopper, regioninput, spotinput):

        previews = self.prevsavon.get()
        region_settings = (app.regionconfig.segtype.get(), app.regionconfig.thresh.get(), app.regionconfig.smooth.get(),
                           app.regionconfig.minsize.get())
        spot_settings = (app.spotconfig.segtype.get(), app.spotconfig.thresh.get(), app.spotconfig.smooth.get(),
                         app.spotconfig.minsize.get())
        ms.cyclefiles(regioninput, spotinput, region_settings, spot_settings, previews, self.logtext.get(),
                      self.previewsavedir.get(), self.one_per_cell.get(), stopper)

    def update_progress(self, updatetype, limit):
        if updatetype == "file":
            self.planelimit = limit
            self.planeprogress.config(maximum=self.planelimit)
            self.planeprogressvar.set(0)
            self.listprogressvar.set(self.listprogressvar.get() + 1)
            self.filelisttext.config(text=(
                    'File %(fileid)02d of %(totalfiles)02d' % {'fileid': self.listprogressvar.get(),
                                                               'totalfiles': self.filelimit}))
        elif updatetype == "plane":
            self.celllimit = limit
            self.cellprogress.config(maximum=self.celllimit)
            self.cellprogressvar.set(0)
            self.planeprogressvar.set(self.planeprogressvar.get() + 1)
            self.planelisttext.config(text=(
                    'Plane %(planeid)02d of %(totalplanes)02d' % {'planeid': self.planeprogressvar.get(),
                                                                  'totalplanes': self.planelimit}))
        elif updatetype == "cell":
            self.cellprogressvar.set(self.cellprogressvar.get() + 1)
            self.celllisttext.config(text=(
                    'Cell %(cellid)02d of %(totalcells)02d' % {'cellid': self.cellprogressvar.get(),
                                                               'totalcells': self.celllimit}))
        elif updatetype == "starting":
            self.filelimit = limit
            self.listprogress.config(maximum=self.filelimit)
            self.listprogressvar.set(0)
        else:  # Finished
            if limit != 0:
                self.listprogressvar.set(self.filelimit)
                self.planeprogressvar.set(self.planelimit)
                self.cellprogressvar.set(self.celllimit)
            self.startbutton.config(text="Run", command=self.sanity_check)
            for widget in self.widgetslist:
                widget.state(['!disabled'])
            if self.prevsavon.get() is False:
                self.prevsaveselect.state(['disabled'])
                self.prevdir.state(['disabled'])
            self.currlog.bind("<Button-1>", self.save_file_set)
            self.prevdir.bind("<Button-1>", self.preview_directory_set)


# UI Initialiser
def main():
    global app
    root = tk.Tk()

    app = CoreWindow(root)
    ms.logevent = app.logconfig.logevent
    ms.update_progress = app.logconfig.update_progress
    root.mainloop()


if __name__ == "__main__":
    main()

# TODO  - Error handling
# TODO  - Handle file format errors.
# TODO  - Full 8bit support
# TODO  - Further improve large object segmentation.
