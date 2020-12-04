################################################################################
# This file contains the source code for the main GUI and implements the basic
# over all structure and layout of various components
################################################################################

import os
import glob
from os import path
import tkinter as tk
from tkinter import *
from tkinter import ttk
from tkinter import filedialog
from tkinter import Menu
from tkinter import scrolledtext
from tkinter import messagebox
from PIL import Image, ImageTk

from DirectoryTree import *
from Notebook import *
from Log import *
from State import *
from Toolbox import *
from NodeTextbox import DefaultNodeTextbox
from Utils import *

class Sketch(object):
    def __init__(self):
        self.init_state()
        self.init_window()
        self.init_panedWindows()
        self.init_notebook()
        self.init_nodeTb()
        self.init_toolbox()
        self.init_menubar()         # dep: init_notebook
        self.init_directoryTree()
        self.init_dnd()
        self.clipboard_check()
        self.window.mainloop()      # dep: init_window

    def init_dnd(self):
        try:
            tk.BaseWidget.dnd_parser = self.dnd_parser
            self.window.tk.call('package', 'require', 'tkdnd')
            self.panedwin.tk.call('tkdnd::drop_target', 'register', self.panedwin._w, ('DND_Files',))
            drop_funct_id = self.panedwin._register(self.panedwin.dnd_parser)
            self.window.tk.call('bind', self.panedwin._w, '<<DropEnter>>', drop_funct_id+' %A %D %e %W')
            self.window.tk.call('bind', self.panedwin._w, '<<Drop>>', drop_funct_id+' %A %D %e %W')
        except:
            log("tkdnd package not found! Drag and drop disabled.")

    def dnd_parser(self, *args):
        if '<<DropEnter>>' in args:
            self.window.lift()
            if sys.platform.startswith('darwin'): # macOS
                self.window.attributes('-topmost', True)
                self.window.after_idle(root.attributes, '-topmost', False)
        else:
            paths = args[1].split(' ')
            for path in paths:
                if path.endswith('.sk') or path.endswith('.pth') or path.endswith('.net'):
                    self.toolbox.import_model(filename=path)
                else:
                    self.notebook.file_open(filepath=path)
            self.window.after(1, lambda: self.window.focus_force()) # brings focus back to window, repopulates menu
        return args

    def init_state(self):
        self.state = State()
        self.clipboard = Clipboard()

    def clipboard_check(self): # enables undo/redo on fresh install
        if self.state.dom['canvas'] == '':
            self.save_state()
        self.clipboard.add(self.state.export())

    def init_window(self):
        self.window = Tk()
        self.window.title("Sketch")
        iconPath = os.path.join(os.getcwd(), 'images/Linear.png') #placeholder icon
        self.window.tk.call('wm', 'iconphoto', self.window._w, tk.PhotoImage(file=iconPath))
        self.window.update_idletasks() # allows geometry calls prior to initialization
        #self.window.geometry('2000x1600') # wxh
        height = self.window.winfo_screenheight() // 5 * 3
        #width = self.window.winfo_screenwidth() // 5 * 3    # dynamic wxh
        width = 2*height
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)   # center of screen
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry('{}x{}+{}+{}'.format(width, height, x, y))
        self.window.columnconfigure(0, weight=1)  # 1 row, 1 column (0, 0) has all weight, allows stretching to border
        self.window.rowconfigure(0, weight=1)
        self.window.protocol("WM_DELETE_WINDOW", self.destroy_window)

        self.window.bind_class('Text', '<Button-3><ButtonRelease-3>', self.open_edit_menu) # allows right click and shortcuts in Textbox
        self.window.bind_class('Text', '<Control-a>', lambda e: e.widget.event_generate('<<SelectAll>>'))
        self.window.bind('<Escape>', self.destroy_window)
        self.window.bind('<Control-z>', self.undo_state)
        self.window.bind('<Control-Shift-Z>', self.redo_state)

        # Notebook tab style setup
        style = ttk.Style()
        self.images = (
            tk.PhotoImage("img_close", data='''
                R0lGODlhCAAIAMIBAAAAADs7O4+Pj9nZ2Ts7Ozs7Ozs7Ozs7OyH+EUNyZWF0ZWQg
                d2l0aCBHSU1QACH5BAEKAAQALAAAAAAIAAgAAAMVGDBEA0qNJyGw7AmxmuaZhWEU
                5kEJADs=
                '''),
            #tk.PhotoImage("img_closeactive", data='''
            #    R0lGODlhCAAIAMIEAAAAAP/SAP/bNNnZ2cbGxsbGxsbGxsbGxiH5BAEKAAQALAAA
            #    AAAIAAgAAAMVGDBEA0qNJyGw7AmxmuaZhWEU5kEJADs=
            #    '''),
            tk.PhotoImage("img_closepressed", data='''
                R0lGODlhCAAIAMIEAAAAAOUqKv9mZtnZ2Ts7Ozs7Ozs7Ozs7OyH+EUNyZWF0ZWQg
                d2l0aCBHSU1QACH5BAEKAAQALAAAAAAIAAgAAAMVGDBEA0qNJyGw7AmxmuaZhWEU
                5kEJADs=
                ''')
        )
        style.element_create("close", "image", "img_close",
                            ("active", "pressed", "!disabled", "img_closepressed"),
                            ("active", "!disabled", "img_close"), border=8, sticky='')
        style.layout("TNotebook", [("TNotebook.client", {"sticky": "nswe"})])
        style.layout("TNotebook.Tab", [
            ("TNotebook.tab", {
                "sticky": "nswe",
                "children": [
                    ("TNotebook.padding", {
                        "side": "top",
                        "sticky": "nswe",
                        "children": [
                            ("TNotebook.focus", {
                                "side": "top",
                                "sticky": "nswe",
                                "children": [
                                    ("TNotebook.label", {"side": "left", "sticky": ''}),
                                    ("TNotebook.close", {"side": "left", "sticky": ''}),
                                        ]
                                })
                            ]
                        })
                    ]
                })
            ])
        style.configure("TNotebook.Tab", background='#aaaaaa', foreground='#000000', lightcolor='#e9e9e9', borderwidth=1)

    def init_menubar(self):
        self.menu = Menu(self.window)
        item_file = Menu(self.menu, tearoff=0)
        item_tab = Menu(item_file, tearoff=0)
        item_file.add_cascade(menu=item_tab, label='Tab Options')
        #item_file.add_command(label='-----Tabs-----', command=None)
        item_tab.add_command(label='New Tab', command=lambda: self.toolbox.create_canvas(clipboard=True))
        item_tab.add_command(label='Rearrange', command=lambda: self.toolbox.save_as_canvas(rearrange=True))
        item_tab.add_command(label='Open', command=lambda: self.toolbox.load_canvas(clipboard=True))
        item_tab.add_command(label='Save', command=self.toolbox.save_canvas)
        item_tab.add_command(label='Save As', command=self.toolbox.save_as_canvas)
        item_tab.add_command(label='Rename', command=self.toolbox.change_tab_label)
        item_tab.add_command(label='Duplicate', command=lambda: self.toolbox.load_canvas(duplicate=True))
        item_tab.add_command(label='Close', command=lambda e: self.toolbox.delete_canvas(event=e, clipboard=True))
        item_file.add_separator()
        item_file.add_command(label='Save State', command=self.save_state)
        item_file.add_command(label='Exit', command=self.destroy_window)

        item_import = Menu(self.menu, tearoff=0)
        item_import.add_command(label='Import Model', command=self.toolbox.import_model)
        item_import.add_command(label='Import Text', command=self.notebook.clicked_open)

        item_defaults = Menu(self.menu, tearoff=0)
        item_defaults.add_command(label='Open Config', command=self.toolbox.open_config)
        item_defaults.add_command(label='Save Node Choices', command=self.toolbox.save_defaults)
        item_defaults.add_command(label='Restore Defaults', command=lambda: self.toolbox.load_default_nodes(revert=True))
        item_defaults.add_command(label='Keybind List', command=self.keybind_popup)

        item_run = Menu(self.menu, tearoff=0)
        item_run.add_command(label='Compile', command=self.toolbox.compile_objects)

        # setting kernel here
        kernelOptions = ["LuaTorch","PyTorch","ONNX"]
        self.kernelVar = StringVar(self.menu)
        self.state.kernel = kernelOptions[0]
        self.kernelVar.set(self.state.kernel) # default value
        item_kernel = Menu(self.menu, tearoff=0)
        for item in kernelOptions:
            item_kernel.add_radiobutton(label=item, value=item, variable=self.kernelVar, command=self.select_kernel)

        self.menu.add_cascade(label='File', menu=item_file)
        self.menu.add_cascade(label='Import', menu=item_import)
        self.menu.add_cascade(label='Config', menu=item_defaults)
        self.menu.add_cascade(label='Run', menu=item_run)
        self.menu.add_cascade(label='Kernel', menu=item_kernel)

        # icons
        icon_repo = os.path.join(os.getcwd(), 'images')
        self.menu.iconimages = []                      # keeps in memory
        icon_path = os.path.join(icon_repo, 'new.png') # placeholders
        img = Image.open(icon_path)
        img = ImageTk.PhotoImage(img)
        self.menu.add_command(image=img, compound='left', command=lambda: self.toolbox.create_canvas(clipboard=True))
        self.menu.iconimages.append(img)
        icon_path = os.path.join(icon_repo, 'open.png')
        img = Image.open(icon_path)
        img = ImageTk.PhotoImage(img)
        self.menu.add_command(image=img, compound='left', command=lambda: self.toolbox.load_canvas(clipboard=True))
        self.menu.iconimages.append(img)
        icon_path = os.path.join(icon_repo, 'save.png')
        img = Image.open(icon_path)
        img = ImageTk.PhotoImage(img)
        self.menu.add_command(image=img, compound='left', command=self.toolbox.save_canvas)
        self.menu.iconimages.append(img)

        self.window.config(menu = self.menu)

        # allows drag and drop to work
        self.window.bind("<FocusIn>", lambda e: self.handle_focusin(e))
        self.window.bind("<FocusOut>", lambda e: self.handle_focusout(e))

    def handle_focusin(self, event):
        self.window.config(menu = self.menu)

    def handle_focusout(self, event):
        try:
            if self.window.focus_get() == None:
                self.window.config(menu = "")
        except:
            pass

    def keybind_popup(self):
        if self.toolbox.command_lock != None:
            return

        keybind_root = Toplevel(self.window)
        keybind_root.title('Keybinds')
        keybind_root.resizable(False, False)

        keybind_root.columnconfigure(0, weight=1)
        keybind_root.columnconfigure(1, weight=1)
        Label(keybind_root, text='Window', font='Arial 12 bold').grid(row=0, column=0, columnspan=2)
        Label(keybind_root, text='Undo State:', anchor='w').grid(row=1, column=0, sticky=W)
        Label(keybind_root, text='Ctrl + Z', anchor='e').grid(row=1, column=1, sticky=E)
        Label(keybind_root, text='Redo State:', anchor='w').grid(row=2, column=0, sticky=W)
        Label(keybind_root, text='Ctrl + Shift + Z', anchor='e').grid(row=2, column=1, sticky=E)
        Label(keybind_root, text='Close selected tab:', anchor='w').grid(row=3, column=0, sticky=W)
        Label(keybind_root, text='Ctrl + W', anchor='e').grid(row=3, column=1, sticky=E)
        Label(keybind_root, text='Close:', anchor='w').grid(row=4, column=0, sticky=W)
        Label(keybind_root, text='Esc', anchor='e').grid(row=4, column=1, sticky=E)
        Label(keybind_root, text='').grid(row=5, column=0, columnspan=2)
        Label(keybind_root, text='Canvas', font='Arial 12 bold').grid(row=6, column=0, columnspan=2)
        Label(keybind_root, text='Set selected ACTIVE:', anchor='w').grid(row=7, column=0, sticky=W)
        Label(keybind_root, text='Ctrl + Insert', anchor='e').grid(row=7, column=1, sticky=E)
        Label(keybind_root, text='Set selected INACTIVE:', anchor='w').grid(row=8, column=0, sticky=W)
        Label(keybind_root, text='Ctrl + Home', anchor='e').grid(row=8, column=1, sticky=E)
        Label(keybind_root, text='DELETE selected:', anchor='w').grid(row=9, column=0, sticky=W)
        Label(keybind_root, text='Ctrl + Delete', anchor='e').grid(row=9, column=1, sticky=E)
        Label(keybind_root, text='GROUP selected:', anchor='w').grid(row=10, column=0, sticky=W)
        Label(keybind_root, text='Ctrl + G', anchor='e').grid(row=10, column=1, sticky=E)
        Label(keybind_root, text='').grid(row=11, column=0, columnspan=2)
        Label(keybind_root, text='Canvas Nodes', font='Arial 12 bold').grid(row=12, column=0, columnspan=2)
        Label(keybind_root, text='Select Node:', anchor='w').grid(row=13, column=0, sticky=W)
        Label(keybind_root, text='Left Click', anchor='e').grid(row=13, column=1, sticky=E)
        Label(keybind_root, text='Multi-select:', anchor='w').grid(row=14, column=0, sticky=W)
        Label(keybind_root, text='Left Click + Drag Canvas', anchor='e').grid(row=14, column=1, sticky=E)
        Label(keybind_root, text='Drag Node:', anchor='w').grid(row=15, column=0, sticky=W)
        Label(keybind_root, text='Left Click Node Center + Drag', anchor='e').grid(row=15, column=1, sticky=E)
        Label(keybind_root, text='Link Nodes:', anchor='w').grid(row=16, column=0, sticky=W)
        Label(keybind_root, text='Left Click Node Edge + Drag to Node', anchor='e').grid(row=16, column=1, sticky=E)
        Label(keybind_root, text='Set active/inactive:', anchor='w').grid(row=17, column=0, sticky=W)
        Label(keybind_root, text='Middle Click', anchor='e').grid(row=17, column=1, sticky=E)
        Label(keybind_root, text='Delete Node/Link:', anchor='w').grid(row=18, column=0, sticky=W)
        Label(keybind_root, text='Double Middle Click', anchor='e').grid(row=18, column=1, sticky=E)
        Label(keybind_root, text='Edit Node Value:', anchor='w').grid(row=19, column=0, sticky=W)
        Label(keybind_root, text='Right Click', anchor='e').grid(row=19, column=1, sticky=E)
        Label(keybind_root, text='Edit Node/Link Name:', anchor='w').grid(row=20, column=0, sticky=W)
        Label(keybind_root, text='Double Right Click', anchor='e').grid(row=20, column=1, sticky=E)
        Label(keybind_root, text='').grid(row=21, column=0, columnspan=2)
        Label(keybind_root, text='Choice Nodes', font='Arial 12 bold').grid(row=22, column=0, columnspan=2)
        Label(keybind_root, text='Edit Choice:', anchor='w').grid(row=23, column=0, sticky=W)
        Label(keybind_root, text='Double Left Click', anchor='e').grid(row=23, column=1, sticky=E)
        Label(keybind_root, text='Delete Choice: Double Middle Click', anchor='w').grid(row=24, column=0, sticky=W)
        Label(keybind_root, text='Double Middle Click', anchor='e').grid(row=24, column=1, sticky=E)
        Label(keybind_root, text='Edit Choice Name:', anchor='w').grid(row=25, column=0, sticky=W)
        Label(keybind_root, text='Right Click', anchor='e').grid(row=25, column=1, sticky=E)

        keybind_root.transient(self.window)
        keybind_root.wait_visibility()
        keybind_root.grab_set()
        self.window.config(menu = self.menu)

    def init_panedWindows(self):
        self.panedwin = PanedWindow(self.window, orient=VERTICAL)
        self.panedwin.grid(row=0, column=0, sticky=NSEW) # allows pane stretch

        topwin = PanedWindow(self.panedwin) # toolbox and notebook
        self.topleft = PanedWindow(topwin)
        topwin.add(self.topleft, stretch='always')
        self.topright = PanedWindow(topwin)
        topwin.add(self.topright, stretch='always')
        self.panedwin.add(topwin, stretch='always')

        bottomwin = PanedWindow(self.panedwin) # edits and directorytree
        self.bottomleft = PanedWindow(bottomwin)
        bottomwin.add(self.bottomleft, stretch='always')
        self.bottommiddle = PanedWindow(bottomwin)
        bottomwin.add(self.bottommiddle, stretch='always')
        self.bottomright = PanedWindow(bottomwin)
        bottomwin.add(self.bottomright, stretch='always')
        self.panedwin.add(bottomwin, stretch='always')


        self.window.update_idletasks()        # adds PanedWindow, allows gemoetry before root initialization
        self.panedwin.sash_place(0, 0, self.window.winfo_height()//5*3) # (index, x, y (vert y=0, horiz x=0))
        topwin.sash_place(0, self.window.winfo_width()//5*4, 0)
        bottomwin.sash_place(0, self.window.winfo_width()//10*5, 0)
        bottomwin.sash_place(1, self.window.winfo_width()//5*4, 0)


    def init_notebook(self):
        self.notebooksync = NotebookSync()
        self.notebook = Notebook(self.topright, self.notebooksync, self.state, self.clipboard)

    def init_nodeTb(self):
        self.nodeTb = DefaultNodeTextbox(self.bottommiddle, self.state)

    def init_toolbox(self):
        self.toolbox = Toolbox(self.window, self.topleft, self.bottomleft, self.state, self.nodeTb, self.notebook, self.notebooksync, self.clipboard, self)

    def init_directoryTree(self):
        self.dTree = DirectoryTree(self.bottomright, self.nodeTb, self.notebook, self.toolbox)

    def select_kernel(self):
        log("kernel:" + self.state.kernel + ' --> ' + self.kernelVar.get())
        self.state.kernel = self.kernelVar.get()

    def save_state(self):
        self.toolbox.update_state()
        self.notebook.update_state()
        self.state.save()

    def undo_state(self, event=None):
        if self.toolbox.command_lock != None:
            return
        self.clipboard.undo()
        state = dict(self.clipboard.get())
        self.state.dom = dict(state)
        self.toolbox.load_state(unredo=True, state_dom=state)
        self.notebook.load_state(unredo=True, state_dom=state)
        print('Undo')

    def redo_state(self, event=None):
        if self.toolbox.command_lock != None:
            return
        if self.clipboard.current == 0:
            return
        self.clipboard.redo()
        state = dict(self.clipboard.get())
        self.state.dom = dict(state)
        self.toolbox.load_state(unredo=True, state_dom=state)
        self.notebook.load_state(unredo=True, state_dom=state)
        print('Redo')

    def destroy_window(self, event=None):
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.save_state()
            self.window.destroy()
#             # Save current state and then close the window
#             if messagebox.askyesno("Save", "Do you want to save current state?"):
#                 self.save_state()
#             log('Window closed')
#             self.window.destroy()

    def open_edit_menu(self, event): # right click popup
        menu_popup = Menu(self.window, tearoff=0)
        menu_popup.add_command(label='   Cut  ', command=lambda: event.widget.event_generate('<<Cut>>'))
        menu_popup.add_command(label='   Copy  ', command=lambda: event.widget.event_generate('<<Copy>>'))
        menu_popup.add_command(label='   Paste  ', command=lambda: event.widget.event_generate('<<Paste>>'))
        menu_popup.tk.call('tk_popup', menu_popup, event.x_root, event.y_root)

