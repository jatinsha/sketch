################################################################################
# This file contains the source code for the notebook where actual sketches are
# drawn using blocks and links.
################################################################################

import os
import glob
import tkinter as tk
from tkinter import ttk
from os import path
from tkinter import scrolledtext
from tkinter import *

from Log import *

class Notebook(tk.Frame):
    def __init__(self, master, sync, state, clipboard):
        tk.Frame.__init__(self, master)
        self.tabControl = ttk.Notebook(master)
        self.state = state
        self.clipboard = clipboard
        self.fullCount = 0
        self.selected_tab = None
        self.hoverwindow = None
        self.openTabs = {}
        self.openList = []
        self.tabControl.pack(expand=1, fill='both')
        # binds for hover text
        # Bindings for open tabs
        self.tabControl.bind('<Enter>', lambda event: self.after(400,self.create_popup(event)))
        self.tabControl.bind('<Leave>', self.remove_popup)
        self.tabControl.bind('<Button-1>', lambda e: self.press_tab(e))
        self.tabControl.bind('<B1-Motion>', lambda e: self.drag_tab(e))
        self.tabControl.bind('<ButtonRelease-1>', lambda e: self.release_tab(e))
        self.tabControl.bind('<Button-3><ButtonRelease-3>', self.tab_right_click_menu)
        self.tabControl.bind("<Control-w>", self.clicked_close)
        self.tabControl.bind("<Control-s>", self.clicked_save)
        self.tabControl.bind("<Control-Shift-S>", self.clicked_saveas)
        self.sync = sync
        state = self.load_state()
        if not state:
            tab_new = self.open_tab(start=True)

    def __str__(self):
        return str(self.openTabs)

    def press_tab(self, event):
        x, y, widget = event.x, event.y, event.widget
        elem = widget.identify(x, y)
        tab = self.tabControl.tk.call(self.tabControl._w, "identify", "tab", x, y)
        if tab == '':
            return
        self.selected_tab = tab
        try:
            self.tabControl.select(tab)
            if 'close' in elem:
                widget.state(['pressed'])
                widget.pressed_index = tab
        except:
            pass

    def drag_tab(self, event):
        x, y, widget = event.x, event.y, event.widget
        tab = self.tabControl.tk.call(self.tabControl._w, "identify", "tab", x, y)
        if self.selected_tab == None:
            return
        elif tab != self.selected_tab:
            widget.state(['!pressed'])
            widget.pressed_index = None
            if tab == '':
                if x <= 0:
                    self.tabControl.insert(0, self.selected_tab)
                    self.selected_tab = 0
                else:
                    self.tabControl.insert('end', self.selected_tab)
                    self.selected_tab = len(self.tabControl.tabs())-1
            elif tab > self.selected_tab:
                self.tabControl.insert(tab, self.selected_tab)
                self.selected_tab += 1
            elif tab < self.selected_tab:
                self.tabControl.insert(self.selected_tab, tab)
                self.selected_tab -= 1

    def release_tab(self, event):
        x, y, widget = event.x, event.y, event.widget
        try:
            elem = widget.identify(x, y)
            tab = self.tabControl.tk.call(self.tabControl._w, "identify", "tab", x, y)
            if 'close' in elem and widget.pressed_index == tab:
                self.clicked_close()
            else:
                self.create_refresh_popup(event)
            widget.state(['!pressed'])
            widget.pressed_index = None
        except:
            pass
        self.selected_tab = None

    def open_tab(self, tab_full = None, new_file=False, load_content=None, state=False, start=False, canvas=None):
        if tab_full == None or tab_full == '' :
            tab_full = self.state.dom['cwd'] + '/Untitled.txt'
        tab_name = tab_full.split('/')[-1]
        content = load_content
        if tab_full not in self.openList:
            tab = ttk.Frame(self.tabControl)
            self.tabControl.add(tab, text=tab_name)
            if load_content or start:
                textbox = self.add_scrollbox(tab, content)
            else:
                textbox = self.add_scrollbox(tab, self.file_content(tab_full, new_file))
            # add page struct here to keep all info
            if not state:
                log(tab_full + ' (new)')
        else:
            if new_file:
                self.fullCount += 1
                filename = self.state.dom['cwd'] + '/Untitled ('+str(self.fullCount)+').txt'
                self.open_tab(tab_full=filename, new_file=True, load_content=content, canvas=canvas)
            else:
                log(tab_full + ' (existing)')
            return

        # focus on open
        self.tabControl.select(tab)
        self.openTabs.update({self.getCurrentTabId():{'name':tab_name, 'full_loc':tab_full, 'object':textbox, 'duplicate':False}})
        self.openList.append(tab_full)
        # add to sync if from compile
        if canvas:
            self.sync.add_sync(canvas, self.getCurrentTabId())
        textbox.bind('<Enter>', self.remove_popup)
        textbox.bind('<Leave>', self.create_refresh_popup)
        return tab

    def open_duplicate(self, event=None):
        tab_full = self.openTabs[self.getCurrentTabId()]['full_loc']
        tab_name = tab_full.split('/')[-1]
        current_tab = self.openTabs[self.getCurrentTabId()]['object']
        content = current_tab.get('1.0', 'end-1c')

        tab = ttk.Frame(self.tabControl)
        self.tabControl.add(tab, text=tab_name)
        textbox = self.add_scrollbox(tab, content)
        # add page struct here to keep all info
        log(tab_full + ' (new)')

        # focus on open
        self.tabControl.select(tab)
        self.openTabs.update({self.getCurrentTabId():{'name':tab_name, 'full_loc':tab_full, 'object':textbox, 'duplicate':True}})
        self.openList.append(tab_full+str(self.getCurrentTabId()))
        textbox.bind('<Enter>', self.remove_popup)
        textbox.bind('<Leave>', self.create_refresh_popup)
        return tab

    def file_content(self, filepath, new_file=False):
        if path.isfile(filepath) and not new_file:
            file_new = open(filepath, "r+")
            try:
                content = file_new.read()
            except:
                content = 'File load error!'
            file_new.close()
        else:
            content = None
        return content

    def add_scrollbox(self, tab, content=None):
        txt_new = scrolledtext.ScrolledText(tab)
        txt_new.pack(expand=True, fill='both')
        txt_new.bind("<Control-s>", self.clicked_save)
        if content:
            txt_new.insert(INSERT, content)
        else:
            # empty file content into the scrollable/editable text region
            txt_new.insert(INSERT,'<----- Your sketch goes here ----->\n')
        return txt_new

    def getCurrentTabId(self):
        tab_id = self.tabControl.select()
        return tab_id

    def getTabFile(self, tab_id):
        tab_file = self.openTabs[tab_id]['full_loc']
        return tab_file

    def file_open(self, filepath):
        tab_new = self.open_tab(filepath)

    def clicked_new(self):
        tab_new = self.open_tab(new_file=True)

    def clicked_open(self):
        filepath = filedialog.askopenfilename(filetypes = (("Text files","*.txt"), ("All Files","*.*") ))
        log(filepath)
        self.file_open(filepath)

    def clicked_close(self, event=None, tab=None, unredo=False):
        if not tab:
            tab = self.getCurrentTabId()
        tab_file = self.getTabFile(tab)
        duplicate = self.openTabs[tab]['duplicate']
        if duplicate:
            self.openList.remove(tab_file+tab)
        else:
            self.openList.remove(tab_file)
        del self.openTabs[tab]
        self.sync.remove_sync(tab)
        self.tabControl.forget(tab)
        if not unredo:
            log(tab_file)
        if len(self.openList) == 0 and not unredo:
            self.fullCount = 0
            filename = self.state.dom['cwd'] + '/Untitled.txt'
            self.open_tab(tab_full=filename, new_file=True)

    def close_sync(self, remove_list):
        for tab in remove_list:
            self.clicked_close(tab=tab)

    def clicked_saveas(self, event=None):
        filepath = filedialog.asksaveasfilename(filetypes = (("All Files","*.*"), ))
        if not filepath:
            return
        filepath = filepath.replace('\\', '/')
        tab = self.getCurrentTabId()
        tab_file = self.getTabFile(tab)
        if filepath != tab_file:
            orig_duplicate = self.openTabs[tab]['duplicate']
            orig_textbox = self.openTabs[tab]['object']
            if orig_duplicate:
                self.openList.remove(tab_file+tab)
            else:
                self.openList.remove(tab_file)
            new_tab_name = filepath.split('/')[-1]
            duplicate = any(filepath in item for item in self.openList)
            self.openTabs.update({self.getCurrentTabId():{'name':new_tab_name, 'full_loc':filepath, 'object':orig_textbox, 'duplicate':duplicate}})
            if duplicate:
                self.openList.append(filepath+str(self.getCurrentTabId()))
            else:
                self.openList.append(filepath)
            self.tabControl.tab(self.getCurrentTabId(), text=new_tab_name)
        log(filepath)
        self.clicked_save()

    def clicked_save(self, event=None):
        tab_file = self.getTabFile(self.getCurrentTabId())
        log(tab_file)
        tab = self.openTabs[self.getCurrentTabId()]['object']
        content = tab.get('1.0', 'end-1c')
        file_new = open(tab_file, "w+")
        file_new.write(content)
        file_new.close()

    def update_state(self):
        state_dict = {}
        count = 0
        for tab in self.tabControl.tabs():
            count += 1
            tab_full = self.getTabFile(tab)
            current_tab = self.openTabs[tab]['object']
            content = current_tab.get('1.0', 'end-1c')
            save_obj = Save(tab_full, content)
            state_dict[count] = save_obj
        self.state.update('notebook', state_dict)
        self.state.update('notebooktab', int(self.tabControl.index(self.tabControl.select())))

    def load_state(self, unredo=False, state_dom=None):
        if unredo:
            self.state.dom = state_dom
        if 'notebook' not in self.state.dom:
            return False
        if self.state.dom['notebook'] == '':
            return False
        if unredo:
            for i in list(self.openList):
                self.clicked_close(unredo=True)
        key_list = []
        for key in self.state.dom['notebook']:
            key_list.append(int(key))
        key_list = sorted(key_list)
        for key in key_list:
            state_obj = self.state.dom['notebook'][key]
            tab_full = state_obj.tab_full
            content = state_obj.content
            self.open_tab(tab_full=tab_full, load_content=content, state=True)
        if not unredo:
            self.tabControl.select(self.tabControl.tabs()[0])
        else:
            self.tabControl.select(self.state.dom['notebooktab'])
        return True

    def create_popup(self, event):
        if self.hoverwindow:
            self.remove_popup(event)
        try:
            tab = self.tabControl.tk.call(self.tabControl._w, "identify", "tab", event.x, event.y)
            active_tab = self.tabControl.index(self.tabControl.select())
            if tab != active_tab:
                self.create_refresh_popup()
                return
            tab_full = self.openTabs[self.getCurrentTabId()]['full_loc']
            x = event.x_root
            y = event.y_root-20
        except:
            self.hoverwindow = None
            return
        try:
            self.hoverwindow = tk.Toplevel(tab)
        except:
            self.hoverwindow = tk.Toplevel(event.widget.winfo_containing(event.x_root, event.y_root))
        self.hoverwindow.wm_overrideredirect(True)
        self.hoverwindow.wm_geometry('+%d+%d' % (x, y))
        hoverlabel = tk.Label(self.hoverwindow, text=tab_full, justify=LEFT, bg='#FFFFFF', relief='solid', borderwidth=1)
        hoverlabel.pack(ipadx=1)

    def create_refresh_popup(self, event):
        if self.hoverwindow:
            self.remove_popup(event)
        try: # prevents rare warning
            self.hoverwindow = tk.Toplevel(event.widget.winfo_containing(event.x_root, event.y_root))
            self.hoverwindow.wm_overrideredirect(True)
            self.hoverwindow.wm_geometry('+%d+%d' % (event.x_root, event.y_root))
            hoverlabel = tk.Label(self.hoverwindow, text='', justify=LEFT, bg='#d9d9d9', borderwidth=0)
            hoverlabel.pack(ipadx=1)
        except:
            pass

    def remove_popup(self, event):
        if self.hoverwindow:
            self.hoverwindow.destroy()
            self.hoverwindow = None

    def tab_right_click_menu(self, event):
        tab = self.tabControl.tk.call(self.tabControl._w, "identify", "tab", event.x, event.y)
        active_tab = self.tabControl.index(self.tabControl.select())
        if tab == '':
            tab = active_tab
        elif tab != active_tab:
            self.tabControl.select(tab)
        menu_popup = tk.Menu(self.tabControl, tearoff=0)
        menu_popup.add_command(label='   New Tab  ', command=self.clicked_new)
        menu_popup.add_command(label='   Open  ', command=self.clicked_open)
        menu_popup.add_command(label='   Save  ', command=self.clicked_save)
        menu_popup.add_command(label='   Save As  ', command=self.clicked_saveas)
        menu_popup.add_command(label='   Duplicate  ', command=self.open_duplicate)
        menu_popup.add_command(label='   Close Tab  ', command=self.clicked_close)
        menu_popup.tk.call('tk_popup', menu_popup, event.x_root, event.y_root)

class NotebookSync(object):
    def __init__(self):
        self.sync_dict = {}
        self.tab_dict = {}

    def add_obj(self, canvasObj):
        self.sync_dict[canvasObj] = []

    def add_sync(self, canvasObj, tab):
        self.sync_dict[canvasObj].append(tab)
        self.tab_dict[tab] = canvasObj

    def remove_sync(self, tab):
        if tab in self.tab_dict:
            if self.tab_dict[tab] in self.sync_dict:
                self.sync_dict[self.tab_dict[tab]].remove(tab)

    def remove_obj(self, canvasObj):
        delete_list = list(self.sync_dict[canvasObj])
        del self.sync_dict[canvasObj]
        return delete_list # to be deleted by Notebook, passed through Toolbox, close specified tab (see clicked_close)

class Save(object):
    def __init__(self, tab_full, content):
        self.tab_full = tab_full
        self.content = content

