"""A directory browser using Ttk Treeview.
Based on the demo found in Tk 8.5 library/demos/browse
"""
import os
import re
import glob
import tkinter as tk
from tkinter import ttk

class DirectoryTree(tk.Frame):
    def __init__(self, master, nodeTb, notebookTb, canvas):
        tk.Frame.__init__(self, master)
        self.tree = ttk.Treeview(self, columns=("fullpath", "type", "size"), displaycolumns="size")
        ysb = tk.Scrollbar(self, orient='vertical', command=self.tree.yview)
        #xsb = ttk.Scrollbar(self, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscroll=ysb.set)#, xscroll=xsb.set)

        self.tree.heading("#0", text="Directory Structure", anchor='w')
        self.tree.heading("size", text="File Size", anchor='w')
        self.tree.column("size", stretch=1, width=100)

        self.populate_roots()
        self.tree.bind('<<TreeviewOpen>>', self.update_tree)
        self.tree.bind('<Double-Button-1>', self.change_dir)
        self.tree.bind("<<TreeviewSelect>>", self.itemClick)
        self.tree.bind("<<TreeviewClose>>", self.itemClick)
        self.tree.bind('<Button-3><ButtonRelease-3>', self.right_click_menu)

        self.tree.pack(expand=1, fill='both', side='left')
        ysb.pack(fill='y', side='right')
        #xsb.pack(fill='x') # will not work with pack, needs grid, more complicated to implement for little gain, have columns anyway
        self.pack(expand=1, fill='both')

        self.selectedFile = None

        self.nodeTb = nodeTb
        self.notebookTb = notebookTb
        self.canvas = canvas

    def populate_tree(self, node):
        if self.tree.set(node, "type") != 'directory':
            return

        path = self.tree.set(node, "fullpath")
        # * is important don't remove that
        self.tree.delete(*self.tree.get_children(node))

        parent = self.tree.parent(node)
        special_dirs = [] if parent else glob.glob('.') + glob.glob('..')
        item_list = self.true_sort(os.listdir(path))
        dir_list = [i for i in item_list if os.path.isdir(os.path.join(path, i).replace('\\', '/'))]
        file_list = [i for i in item_list if os.path.isfile(os.path.join(path, i).replace('\\', '/'))]
        for p in special_dirs + dir_list + file_list:
            # optional, change if necessary
            if p == '.':   # removes redundancy
                continue
            elif '~' in p: # remove temp from list
                continue
            ptype = None
            p = os.path.join(path, p).replace('\\', '/')
            if os.path.isdir(p):
                ptype = "directory"
            elif os.path.isfile(p):
                ptype = "file"
            fname = os.path.split(p)[1]

            id = self.tree.insert(node, "end", text=fname, values=[p, ptype])

            if ptype == 'directory':
                if fname not in ('.', '..'):
                    self.tree.insert(id, 0, text="dummy")
                    self.tree.item(id, text=fname)
            elif ptype == 'file':
                size = os.stat(p).st_size
                self.tree.set(id, "size", "%d bytes" % size)

    def populate_roots(self):
        dir = os.path.abspath('.').replace('\\', '/')
        node = self.tree.insert('', 'end', text=dir, values=[dir, "directory"])
        self.populate_tree(node)

    def update_tree(self, event):
        self.tree = event.widget
        self.populate_tree(self.tree.focus())

    def change_dir(self, event):
        self.tree = event.widget
        node = self.tree.focus()
        if self.tree.parent(node):
            path = os.path.abspath(self.tree.set(node, "fullpath"))
            if os.path.isdir(path):
                os.chdir(path)
                self.tree.delete(self.tree.get_children(''))
                self.populate_roots()
            elif os.path.isfile(path):
                self.selectedFile = path
                if self.selectedFile.endswith(('.sav', '.net', '.pth')):
                    self.send_canvas()
                else:
                    self.send_notebookTb()

    def autoscroll(self, sbar, first, last):
        """Hide and show scrollbar as needed."""
        first, last = float(first), float(last)
        if first <= 0 and last >= 1:
            sbar.grid_remove()
        else:
            sbar.grid()
        sbar.set(first, last)

    def itemClick(self, event):
        id = self.tree.selection()
        values = self.tree.item(id, 'values')
        if len(values) < 2:
            self.selectedFile = None
        if values[1] == 'directory':
            self.selectedFile = None
        else:
            self.selectedFile = values[0]

    def right_click_menu(self, event): # right click popup
        rowId = self.tree.identify('item', event.x, event.y)
        if not rowId:
            return
        self.tree.selection_set(rowId)
        self.tree.focus_set()
        self.tree.focus(rowId)
        self.itemClick(self)
        if self.selectedFile == None:
            return
        menu_popup = tk.Menu(self.tree, tearoff=0)
        if self.selectedFile.endswith(('.sav', '.net', '.pth')):
            menu_popup.add_command(label='   Import Model  ', command=self.send_canvas)
        menu_popup.add_command(label='   Import Node  ', command=self.send_nodeTb)
        menu_popup.add_command(label='   Import Sketch  ', command=self.send_notebookTb)
        menu_popup.tk.call('tk_popup', menu_popup, event.x_root, event.y_root)

    def send_nodeTb(self):
        if not self.nodeTb.chosenId:
            print('Must select Node to edit first!')
            return
        try:
            with open(self.selectedFile, 'rb') as fp:
                contents = fp.read()
            self.nodeTb.textbox.delete('1.0', tk.END)
            self.nodeTb.textbox.insert('1.0', contents)
        except:
            self.nodeTb.textbox.delete('1.0', tk.END)
            self.nodeTb.textbox.insert('1.0', 'File load error!')

    def send_notebookTb(self):
        self.notebookTb.open_tab(tab_full=self.selectedFile)

    def send_canvas(self):
        self.canvas.import_model(filename=self.selectedFile)

    def true_sort(self, item_list):
        convert = lambda filename: int(filename) if filename.isdigit() else filename.lower()
        sort_key = lambda key: [convert(filename) for filename in re.split('([0-9]+)', key)]
        return sorted(item_list, key = sort_key)
