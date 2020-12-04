################################################################################
# This file implements the bulk of the actions (drag/drop, undo/redo)
################################################################################

import tkinter as tk
from tkinter import *
from PIL import Image, ImageTk
import math
import re
import os
import pickle
from copy import copy, deepcopy
from statistics import mean

from Graph import Graph, Node, Edge, Save
from Defaults import ChoiceDefaults

from Binder import *

class Toolbox(object):
    def __init__(self, window, parent, groupParent, state, nodeTb, notebookTb, sync, clipboard, sketchobj):
        self.sketchobj = sketchobj
        self.window = window
        self.parent = parent
        self.group_parent = groupParent
        self.state = state
        self.canvas_dict = {}
        self.arrow_dict = {}
        self.command_lock = None
        self.new_obj = None
        self.start_obj = None
        self.count = 0
        self.start_x = None
        self.start_y = None
        self.selected_tab = None
        self.selected_obj = None
        self.selected_text = None
        self.selected_arrows_start = None
        self.selected_arrows_end = None
        self.selected_links_start = None
        self.selected_links_end = None
        self.selected_label = None
        self.new_text = None
        self.default_node_height = 45
        self.default_node_width = 165
        self.default_widget_height = 2
        self.default_widget_width = 20
        self.canvas_tabs = None
        self.canvas_tab_dict = {}
        self.defaults_dict = {}
        self.defaults_list = []
        self.geometry_dict = {}
        self.group_canvas_dict = {}
        self.event_list = []
        self.hover_obj = None
        self.start_tab = None
        self.select_canvas = None
        self.start_widget = None
        self.select_node_set = set()
        self.select_edge_set = set()
        self.current_widget = None
        self.last_canvas = None
        self.dummy_object = None
        self.dummy_text = None
        self.group_canvas = None
        self.original_group_save = None
        self.selected_group_obj = None
        self.savetoggle = 1

        self.nodeTb = nodeTb
        self.notebookTb = notebookTb
        self.sync = sync
        self.clipboard = clipboard
        self.graph_dict = {} # list of initialized Graph objects
        self.save_dict = {} # stores save file loc for canvas when load or save as
        self.root = Frame(parent)
        self.group_root = Frame(groupParent, bg='white')
        self.create_toolbox(parent, groupParent)
        self.load_state()

    def true_sort(self, item_list, model=False):
        convert = lambda item: int(item) if item.isdigit() else item.lower()
        sort_key = lambda key: [convert(item) for item in re.split('([0-9]+)', str(key))]
        if not model:
            return sorted(item_list, key = sort_key)
        else:
            change_set = set([item.split('_')[0] for item in item_list if '_' in item])
            edited_list = []
            for item in item_list:
                if item in change_set:
                    item = item+'_Z'
                edited_list.append(item)
            item_list = sorted(edited_list, key = sort_key)
            return [item.replace('_Z', '') for item in item_list]

    def create_choice(self, choice_cell):
        if self.command_lock != None:
            return

        self.count += 1
        new_choice = Label(self.choice_frame, text = 'Untitled ('+str(self.count)+')', height=self.default_widget_height, width=self.default_widget_width)
        new_choice.base_value = '{}'
        new_choice.grid(padx=10, pady=5, sticky=NSEW)
        new_choice.optiontag = 1
        new_choice.image = None
        new_choice.file = None
        self.defaults_dict[new_choice['text']] = {'value':new_choice.base_value, 'image':None}
        self.defaults_list.append(new_choice['text'])
        self.notebookTb.update_state()
        self.update_state()
        self.clipboard.add(self.state.export())

    def delete_choice(self, event):
        if self.command_lock != None:
            return
        if not hasattr(event.widget, 'optiontag'):
            return
        del self.defaults_dict[event.widget['text']]
        self.defaults_list.remove(event.widget['text'])
        event.widget.base_value = 'NULL'+str(event.widget)
        event.widget.destroy()
        self.notebookTb.update_state()
        self.update_state()
        self.clipboard.add(self.state.export())

    def command_release(self, command):
        if self.command_lock == command:
            self.command_lock = None

    def edit_choice_value(self, event):
        if not hasattr(event.widget, 'optiontag'):
            return
        obj_id = event.widget
        value = obj_id.base_value
        label_text = obj_id['text']
        self.nodeTb.loadDefaultText(obj_id, label_text, value, self.defaults_dict)

    def edit_node_value(self, event, code_canvas):
        if code_canvas == self.group_canvas:
            tab = self.group_canvas
        else:
            tab = self.canvas_tabs.select()
        obj_id = self.canvas_dict[tab][code_canvas.find_withtag(CURRENT)[0]]['object_id']

        if self.canvas_dict[tab][obj_id]['group_obj'] != None: # prevents editing group obj, open canvas instead
            self.reset_selected(event)
            save_obj = self.canvas_dict[tab][obj_id]['group_obj']
            self.load_group(save_obj, obj_id)
            return

        if code_canvas == self.group_canvas:
            self.nodeTb.loadNodeText(obj_id, self.canvas_dict[tab], self.graph_dict[tab], tab_dict=None, tab=tab, full_dict=self.canvas_dict)
        else:
            self.nodeTb.loadNodeText(obj_id, self.canvas_dict[tab], self.graph_dict[tab], tab_dict=self.canvas_tab_dict, tab=tab, full_dict=self.canvas_dict)

    def change_choice_label(self, event, choice_cell):
        if not hasattr(event.widget, 'optiontag'):
            return
        obj_id = event.widget
        label_text = obj_id['text']
        if label_text.isspace():
            label_text = 'None'

        choice_root = Toplevel(self.root)
        choice_root.title('Choice Menu')
        choice_root.resizable(False, False)

        Label(choice_root, text='Choice Text: '+label_text).pack(fill=X)
        Label(choice_root, text='New Text:').pack(fill=X)
        choice_textbox = Entry(choice_root)
        choice_textbox.pack(fill=X)

        Button(choice_root, text='Submit', command = lambda: self.choice_submit(choice_root, obj_id, choice_textbox)).pack(fill=X)
        choice_root.bind('<Return>', lambda e: self.choice_submit(choice_root, obj_id, choice_textbox))

        choice_root.transient(self.root)
        choice_root.wait_visibility()
        choice_root.grab_set()
        self.window.config(menu = self.sketchobj.menu)

    def choice_submit(self, choice_root, obj_id, choice_textbox):
        choice_text = choice_textbox.get()
        if not choice_text:
            print('Cancelled')
            choice_root.destroy()
            return
        elif choice_text in self.defaults_dict:
            print('Label name already exists! Choose another.')
            choice_root.destroy()
            return

        value = self.defaults_dict[obj_id['text']]
        self.defaults_list.remove(obj_id['text'])
        del self.defaults_dict[obj_id['text']]
        choice_text = choice_text.strip()
        obj_id.config(text = str(choice_text))
        self.defaults_list.append(obj_id['text'])
        self.defaults_dict[obj_id['text']] = value
        choice_root.destroy()
        self.notebookTb.update_state()
        self.update_state()
        self.clipboard.add(self.state.export())

    ####### Drag n Drop #######
    def drag_new(self, event, command):
        if self.command_lock != None and self.command_lock != 'new':
            return

        if not hasattr(event.widget, 'optiontag'):
            return

        if self.command_lock == None:
            self.current_widget = None
            self.last_canvas = None

        try:
            self.current_widget = event.widget.winfo_containing(event.x_root, event.y_root)
        except:
            pass # skip updating if issue
        if self.last_canvas == None:
            if hasattr(self.current_widget, 'group_sandbox'):
                self.last_canvas = self.group_canvas
            elif hasattr(self.current_widget, 'sandbox'):
                self.last_canvas = self.canvas_tab_dict[self.canvas_tabs.select()]['object']

        if command == 'new-drag':
            if not self.new_obj:
                try:
                    #self.current_widget = event.widget.winfo_containing(event.x_root, event.y_root)
                    if not hasattr(self.current_widget, 'sandbox') and not hasattr(self.current_widget, 'group_sandbox'):
                        return
                    elif self.current_widget.active == 0:
                        return
                    elif hasattr(self.current_widget, 'group_sandbox') and 'subgraph' in self.selected_label.base_value: # no group in group
                        return
                except:
                    return
                if self.current_widget != self.last_canvas:
                    if self.current_widget.active == 1:
                        self.last_canvas = self.current_widget
                try: #prevents NoneType error if dragged after doubleclick
                    label_offset_x, label_offset_y = self.selected_label.winfo_rootx()-self.root.winfo_rootx(), \
                                                     self.selected_label.winfo_rooty()-self.root.winfo_rooty()
                    canvas_offset_x, canvas_offset_y = self.last_canvas.winfo_rootx()-self.root.winfo_rootx(), \
                                                       self.last_canvas.winfo_rooty()-self.root.winfo_rooty()
                    canvas_relative_x, canvas_relative_y = event.x+label_offset_x-canvas_offset_x, event.y+label_offset_y-canvas_offset_y
                except:
                    return
                if canvas_relative_x <= 0:
                    canvas_relative_x = 1
                if canvas_relative_y <= 0:
                    canvas_relative_y = 1
                if canvas_relative_x >= self.last_canvas.winfo_width()-self.selected_label.winfo_width():
                    canvas_relative_x = self.last_canvas.winfo_width()-self.selected_label.winfo_width()
                if canvas_relative_y >= self.last_canvas.winfo_height()-self.selected_label.winfo_height():
                    canvas_relative_y = self.last_canvas.winfo_height()-self.selected_label.winfo_height()
                if 'subgraph' in self.selected_label.base_value:
                    fill='gold'
                else:
                    fill=self.selected_label['bg']
                self.new_obj = self.last_canvas.create_rectangle(canvas_relative_x, canvas_relative_y, self.default_node_width+canvas_relative_x,
                                                            self.default_node_height+canvas_relative_y, fill=fill, tags=('node',))
                self.new_text = self.last_canvas.create_text(((self.default_node_width+canvas_relative_x*2)//2),
                                                          ((self.default_node_height+canvas_relative_y*2)//2),
                                                          text=self.selected_label['text'], fill=self.selected_label['fg'], tags=('node',))
            else:
                if self.current_widget != self.last_canvas:
                    if (hasattr(self.current_widget, 'group_sandbox') or hasattr(self.current_widget, 'sandbox')) \
                         and self.current_widget.active == 1 and 'subgraph' not in self.selected_label.base_value: # no group in group
                        self.last_canvas.delete(self.new_obj)
                        self.last_canvas.delete(self.new_text)
                        self.new_obj = None
                        self.new_text = None
                        self.last_canvas = self.current_widget
                        try: #prevents NoneType error if dragged after doubleclick
                            label_offset_x, label_offset_y = self.selected_label.winfo_rootx()-self.root.winfo_rootx(), \
                                                                self.selected_label.winfo_rooty()-self.root.winfo_rooty()
                            canvas_offset_x, canvas_offset_y = self.last_canvas.winfo_rootx()-self.root.winfo_rootx(), \
                                                                self.last_canvas.winfo_rooty()-self.root.winfo_rooty()
                            canvas_relative_x, canvas_relative_y = event.x+label_offset_x-canvas_offset_x, event.y+label_offset_y-canvas_offset_y
                        except:
                            return
                        if canvas_relative_x <= 0:
                            canvas_relative_x = 1
                        if canvas_relative_y <= 0:
                            canvas_relative_y = 1
                        if canvas_relative_x >= self.last_canvas.winfo_width()-self.selected_label.winfo_width():
                            canvas_relative_x = self.last_canvas.winfo_width()-self.selected_label.winfo_width()
                        if canvas_relative_y >= self.last_canvas.winfo_height()-self.selected_label.winfo_height():
                            canvas_relative_y = self.last_canvas.winfo_height()-self.selected_label.winfo_height()
                        self.new_obj = self.last_canvas.create_rectangle(canvas_relative_x, canvas_relative_y,
                                                                    self.default_node_width+canvas_relative_x,
                                                                    self.default_node_height+canvas_relative_y,
                                                                    fill=self.selected_label['bg'], tags=('node',))
                        self.new_text = self.last_canvas.create_text(((self.default_node_width+canvas_relative_x*2)//2),
                                                                  ((self.default_node_height+canvas_relative_y*2)//2),
                                                                  text=self.selected_label['text'], fill=self.selected_label['fg'], tags=('node',))
                try: #prevents NoneType error if dragged after doubleclick
                    label_offset_x, label_offset_y = self.selected_label.winfo_rootx()-self.root.winfo_rootx(), self.selected_label.winfo_rooty()-self.root.winfo_rooty()
                    canvas_offset_x, canvas_offset_y = self.last_canvas.winfo_rootx()-self.root.winfo_rootx(), self.last_canvas.winfo_rooty()-self.root.winfo_rooty()
                    canvas_relative_x, canvas_relative_y = event.x+label_offset_x-canvas_offset_x, event.y+label_offset_y-canvas_offset_y
                except:
                    return
                if canvas_relative_x <= 0:
                    canvas_relative_x = 1
                if canvas_relative_y <= 0:
                    canvas_relative_y = 1
                if canvas_relative_x >= self.last_canvas.winfo_width()-self.default_node_width:
                    canvas_relative_x = self.last_canvas.winfo_width()-self.default_node_width
                if canvas_relative_y >= self.last_canvas.winfo_height()-self.default_node_height:
                    canvas_relative_y = self.last_canvas.winfo_height()-self.default_node_height
                #self.current_widget = event.widget.winfo_containing(event.x_root, event.y_root)
                self.last_canvas.coords(self.new_obj, canvas_relative_x, canvas_relative_y, self.default_node_width+canvas_relative_x,
                                   self.default_node_height+canvas_relative_y)
                self.last_canvas.coords(self.new_text, ((self.default_node_width+canvas_relative_x*2)//2), ((self.default_node_height+canvas_relative_y*2)//2))
        elif command == 'new-start':
            self.command_lock = 'new'
            self.selected_label = event.widget
        elif command == 'new-drop':
            if self.new_obj:
                if self.last_canvas == self.canvas_tab_dict[self.canvas_tabs.select()]['object']:
                    x1, y1, x2, y2 = self.last_canvas.bbox(self.new_obj)
                    self.canvas_dict[self.canvas_tabs.select()][self.new_obj] = {'object_id':self.new_obj, 'text_id':self.new_text,
                                                                        'text':self.selected_label['text'], 'value':self.selected_label.base_value,
                                                                        'pair_dict_start':{}, 'pair_dict_end':{}, 'arrow_ids_start':[], 'arrow_ids_end':[],
                                                                        'dimensions':[x1, y1, x2, y2], 'canvas':self.canvas_tabs.select(), 'group_obj':None}
                    x1, y1 = self.last_canvas.coords(self.new_text)
                    self.canvas_dict[self.canvas_tabs.select()][self.new_text] = {'object_id':self.new_obj, 'text_id':self.new_text,
                                                                                  'dimensions':[int(x1), int(y1)]}
                    self.graph_dict[self.canvas_tabs.select()].addNode(Node(self.new_obj, type=self.selected_label['text'],
                                                                             params=self.selected_label.base_value))
                else:
                    x1, y1, x2, y2 = self.last_canvas.bbox(self.new_obj)
                    self.canvas_dict[self.group_canvas][self.new_obj] = {'object_id':self.new_obj, 'text_id':self.new_text,
                                                                         'text':self.selected_label['text'], 'value':self.selected_label.base_value,
                                                                         'pair_dict_start':{}, 'pair_dict_end':{}, 'arrow_ids_start':[], 'arrow_ids_end':[],
                                                                         'dimensions':[x1, y1, x2, y2], 'canvas':str(self.group_canvas), 'group_obj':None}
                    x1, y1 = self.last_canvas.coords(self.new_text)
                    self.canvas_dict[self.group_canvas][self.new_text] = {'object_id':self.new_obj, 'text_id':self.new_text, 'dimensions':[int(x1), int(y1)]}
                    self.graph_dict[self.group_canvas].addNode(Node(self.new_obj, type=self.selected_label['text'], params=self.selected_label.base_value))

                if 'subgraph' in self.selected_label.base_value: # create group canvas
                    self.create_group_canvas(clipboard=True)
                    self.group_canvas.active = 1
                    canvas_name = self.canvas_tab_dict[self.canvas_tabs.select()]['name']
                    node_name = self.selected_label['text']
                    self.group_label.config(text='Group Canvas: '+node_name+' ('+canvas_name+')')
                    tab_text = 'Group Canvas: '+node_name+' ('+canvas_name+')'
                    saved_canvas = dict(self.canvas_dict[self.group_canvas])
                    saved_arrows = dict(self.arrow_dict[self.group_canvas])
                    saved_graph_active_edge = dict(self.graph_dict[self.group_canvas].activeEdgeList)
                    saved_graph_nodes = dict(self.graph_dict[self.group_canvas].nodes)
                    saved_graph_obj = self.graph_dict[self.group_canvas]
                    save_obj = Save(tab_text, saved_canvas, saved_arrows, saved_graph_active_edge, saved_graph_nodes, saved_graph_obj) #sets up initial save obj
                    self.canvas_dict[self.canvas_tabs.select()][self.new_obj]['group_obj'] = save_obj
                    self.graph_dict[self.canvas_tabs.select()].editNode(self.new_obj, params={'subgraph':deepcopy(saved_graph_obj)}, group=True)
            self.command_release('new')
            self.selected_label = None
            self.new_obj = None
            self.new_text = None
            self.current_widget = None
            self.last_canvas = None
            self.notebookTb.update_state()
            self.update_state()
            self.clipboard.add(self.state.export())

    def drag_select(self, event, code_canvas, command):
        if self.command_lock != None and self.command_lock != 'dragselect':
            return

        if code_canvas == self.group_canvas:
            tab = self.group_canvas
        else:
            tab = self.canvas_tabs.select()

        tags = code_canvas.itemcget(code_canvas.find_withtag(CURRENT), 'tags')
        if 'arrow' in tags or 'node' in tags:
            return

        if event.widget.active == 0:
            return

        if command == 'current-drag':
            if self.dummy_object == None:
                self.command_lock = 'dragselect'
                self.start_x, self.start_y = event.x, event.y
                self.dummy_object = code_canvas.create_rectangle(self.start_x, self.start_y, event.x+1, event.y+1, outline='#3399FF', width=3, dash=(4, 8))
                self.dummy_text = code_canvas.create_text(1, 1, text=' ', fill='white', font=('Arial', 2))
                code_canvas.tag_raise(self.dummy_object)
            code_canvas.coords(self.dummy_object, self.start_x, self.start_y, event.x, event.y)
        elif command == 'current-drop':
            if self.command_lock != 'dragselect':
                return
            self.command_release('dragselect')
            if self.dummy_object != None:
                code_canvas.delete(self.dummy_object)
                code_canvas.delete(self.dummy_text)
            overlap_list = code_canvas.find_overlapping(self.start_x, self.start_y, event.x, event.y)
            if self.dummy_object in overlap_list:
                overlap_list.remove(self.dummy_object)
            if self.dummy_text in overlap_list:
                overlap_list.remove(self.dummy_text)
            overlap_set = set()
            for item in overlap_list:
                obj = self.canvas_dict[tab][item]['object_id']
                overlap_set.add(obj)
            for item in overlap_set:
                self.select_object(event, code_canvas, obj=item)
            self.dummy_object = None
            self.dummy_text = None
            self.current_widget = None

    def drag_current(self, event, command):
        if event.widget == self.group_canvas:
            code_canvas = self.group_canvas
        else:
            code_canvas = self.canvas_tab_dict[self.canvas_tabs.select()]['object']

        if self.command_lock != None and self.command_lock != 'current' and self.command_lock != 'link':
            return
        #elif len(code_canvas.find_withtag(CURRENT)) == 0:
        #    self.command_release('current')
        #    return

        if self.command_lock == None:
            self.current_widget = None
            self.last_canvas = None

        if self.command_lock == 'link':
            if code_canvas == self.group_canvas:
                tab = self.group_canvas
            else:
                tab = self.canvas_tabs.select()
            if command == 'current-drag':
                if self.selected_obj == None:
                    self.selected_obj = self.start_obj
                    self.event_list = []

                    x1, y1, x2, y2 = code_canvas.bbox(self.selected_obj)
                    width = x2-x1
                    height = y2-y1
                    if height > width:
                        arrow_width = width//3
                    else:
                        arrow_width = height//3
                    self.start_x = (x1+x2)//2
                    self.start_y = (y1+y2)//2
                    line_length = int(math.hypot(event.x - self.start_x, event.y - self.start_y))
                    self.dummy_object = code_canvas.create_line(self.start_x, self.start_y, event.x, event.y, arrow='last',
                                                                arrowshape=[line_length,line_length,arrow_width], fill='lime', tags=('arrow',))
                    self.dummy_text = code_canvas.create_text(1, 1, text=' ', fill='white', font=('Arial', 2))
                    code_canvas.tag_lower(self.dummy_object)
                x1, y1, x2, y2 = code_canvas.bbox(self.selected_obj)
                width = x2-x1
                height = y2-y1
                if height > width:
                    arrow_width = width//3
                else:
                    arrow_width = height//3
                line_length = int(math.hypot(event.x - self.start_x, event.y - self.start_y))
                code_canvas.coords(self.dummy_object, self.start_x, self.start_y, event.x, event.y)
                code_canvas.itemconfig(self.dummy_object, arrowshape=[line_length, line_length, arrow_width])
                self.event_list.append(0)
            elif command == 'current-drop':
                if self.dummy_object != None:
                    code_canvas.delete(self.dummy_object)
                    code_canvas.delete(self.dummy_text)
                #if len(self.event_list) != 0: # allows click to make edge
                closest = code_canvas.find_closest(event.x, event.y)[0]
                overlap_list = code_canvas.find_overlapping(event.x-10, event.y-10, event.x+10, event.y+10)
                if closest in overlap_list:
                    end_obj = self.canvas_dict[tab][closest]['object_id']
                    tags = code_canvas.itemcget(end_obj, 'tags')
                    if 'node' in tags:
                        self.link_objects(event, code_canvas, end_obj=end_obj)
                    else:
                        self.link_objects(event, code_canvas, end_obj=self.start_obj) # force a reset, landed on edge
                else:
                    self.link_objects(event, code_canvas, end_obj=self.start_obj) # force a reset, landed on empty
                if len(self.event_list) <= 5: # determine if node should be selected
                    self.select_object(event, code_canvas)
                self.dummy_object = None
                self.dummy_text = None
                self.selected_obj = None
                self.event_list = []

        else:
            try:
                self.current_widget = event.widget.winfo_containing(event.x_root, event.y_root)
            except:
                return
            if self.last_canvas == None:
                if hasattr(self.current_widget, 'group_sandbox'):
                    self.last_canvas = self.group_canvas
                elif hasattr(self.current_widget, 'sandbox'):
                    self.last_canvas = self.canvas_tab_dict[self.canvas_tabs.select()]['object']
                else:
                    if self.command_lock == None:
                        return
            if self.last_canvas == self.group_canvas:
                tab = self.group_canvas
            else:
                tab = self.canvas_tabs.select()
            if command == 'current-start':
                self.event_list = []
                try:
                    self.selected_obj = self.canvas_dict[tab][self.last_canvas.find_withtag(CURRENT)[0]]['object_id']
                except:   # prevents rare bug, self.last_canvas did not update
                    self.last_canvas = self.current_widget
                    self.selected_obj = self.canvas_dict[tab][self.last_canvas.find_withtag(CURRENT)[0]]['object_id']
                    if self.last_canvas == self.group_canvas:
                        tab = self.group_canvas
                    else:
                        tab = self.canvas_tabs.select()
                self.selected_text = self.canvas_dict[tab][self.selected_obj]['text_id']
                self.selected_arrows_start = self.canvas_dict[tab][self.selected_obj]['arrow_ids_start']
                self.selected_arrows_end = self.canvas_dict[tab][self.selected_obj]['arrow_ids_end']
                self.selected_links_start = self.canvas_dict[tab][self.selected_obj]['pair_dict_start']
                self.selected_links_end = self.canvas_dict[tab][self.selected_obj]['pair_dict_end']
                self.last_canvas.tag_raise(self.selected_obj)
                self.last_canvas.tag_raise(self.selected_text)
                self.start_x = event.x
                self.start_y = event.y
                self.start_widget = self.last_canvas
                self.command_lock = 'current'
            elif command == 'current-drag':
                if self.command_lock != 'current':
                    return
                self.event_list.append(0)
                if self.current_widget != self.last_canvas:
                    if (hasattr(self.current_widget, 'group_sandbox') or hasattr(self.current_widget, 'sandbox')) and self.current_widget.active == 1:
                        if (self.canvas_dict[tab][self.selected_obj]['group_obj'] == None) \
                               or 'subgraph' not in self.graph_dict[tab].nodes.get(self.selected_obj).params: # prevents group objects from changing canvas
                            x1, y1, x2, y2 = self.last_canvas.bbox(self.selected_obj)
                            color = self.last_canvas.itemcget(self.selected_obj, "fill")
                            node = self.graph_dict[tab].nodes.get(self.selected_obj)
                            type = node.type
                            params = node.params
                            learned_params = node.learned_params
                            prior_group_obj = self.canvas_dict[tab][self.selected_obj]['group_obj']
                            self.delete_current(event, self.last_canvas, id=self.selected_obj, clipboard=False, bypass=True)
                            self.start_x = event.x
                            self.start_y = event.y
                            self.selected_obj = None
                            self.selected_text = None
                            self.selected_arrows_start = []
                            self.selected_arrows_end = []
                            self.selected_links_start = {}
                            self.selected_links_end = {}
                            self.last_canvas = self.current_widget
                            if hasattr(self.current_widget, 'group_sandbox'):
                                canvas_relative_x = self.window.winfo_rootx()
                                canvas_relative_y = 0
                            else:
                                canvas_relative_x = self.window.winfo_rootx()-(self.canvas_tabs.winfo_rootx()-self.window.winfo_rootx())
                                canvas_relative_y = 1000000
                            '''label_offset_x, label_offset_y = x1-self.root.winfo_rootx(), \
                                                                y1-self.root.winfo_rooty()
                            canvas_offset_x, canvas_offset_y = self.last_canvas.winfo_rootx()-self.root.winfo_rootx(), \
                                                                self.last_canvas.winfo_rooty()-self.root.winfo_rooty()
                            canvas_relative_x, canvas_relative_y = event.x+label_offset_x-canvas_offset_x, event.y+label_offset_y-canvas_offset_y'''
                            if canvas_relative_x <= 0:
                                canvas_relative_x = 1
                            if canvas_relative_y <= 0:
                                canvas_relative_y = 1
                            if canvas_relative_x >= self.last_canvas.winfo_width()-(x2-x1):
                                canvas_relative_x = self.last_canvas.winfo_width()-(x2-x1)
                            if canvas_relative_y >= self.last_canvas.winfo_height()-(y2-y1):
                                canvas_relative_y = self.last_canvas.winfo_height()-(y2-y1)

                            self.selected_obj = self.last_canvas.create_rectangle(canvas_relative_x+1, canvas_relative_y+1,
                                                                        (x2-x1)+canvas_relative_x-1,
                                                                        (y2-y1)+canvas_relative_y-1,
                                                                        fill=color, tags=('node',))
                            self.selected_text = self.last_canvas.create_text((((x2-x1)+canvas_relative_x*2)//2),
                                                                      (((y2-y1)+canvas_relative_y*2)//2),
                                                                      text=type, fill='black', tags=('node',))
                            if self.last_canvas == self.canvas_tab_dict[self.canvas_tabs.select()]['object']:
                                tab = self.canvas_tabs.select()
                            else:
                                tab = self.group_canvas
                            x1, y1, x2, y2 = self.last_canvas.bbox(self.selected_obj)
                            self.canvas_dict[tab][self.selected_obj] = {'object_id':self.selected_obj, 'text_id':self.selected_text,
                                                                        'text':type, 'value':params,
                                                                        'pair_dict_start':{}, 'pair_dict_end':{}, 'arrow_ids_start':[], 'arrow_ids_end':[],
                                                                        'dimensions':[x1, y1, x2, y2], 'canvas':str(tab), 'group_obj':prior_group_obj}
                            x1, y1 = self.last_canvas.coords(self.selected_text)
                            self.canvas_dict[tab][self.selected_text] = {'object_id':self.selected_obj, 'text_id':self.selected_text,
                                                                              'dimensions':[int(x1), int(y1)]}
                            # WILL NEED TO EDIT IN FUTURE: text separate from type, params change/addition
                            self.graph_dict[tab].addNode(Node(self.selected_obj, type=type, params=params, learned_params=learned_params))
                            self.graph_dict[tab].editNode(self.selected_obj, status='setactive')
                            self.last_canvas.itemconfig(self.selected_obj, fill='#d9d9d9')

                x_move, y_move = event.x-self.start_x, event.y-self.start_y
                x1, y1, x2, y2 = self.last_canvas.bbox(self.selected_obj)
                if x1+x_move < 0:
                    x_move = 0
                if y1+y_move < 0:
                    y_move = 0
                if x2+x_move > self.last_canvas.winfo_width():
                    x_move = self.last_canvas.winfo_width()-(x2+x_move)
                if y2+y_move > self.last_canvas.winfo_height():
                    y_move = self.last_canvas.winfo_height()-(y2+y_move)
                self.last_canvas.move(self.selected_obj, x_move, y_move)
                self.last_canvas.move(self.selected_text, x_move, y_move)
                for selected_arrow_start in self.selected_arrows_start:
                    line_coords = [int(i) for i in self.last_canvas.coords(selected_arrow_start)]
                    arrow_width = self.last_canvas.itemcget(selected_arrow_start, 'arrowshape').split(' ')[-1]
                    x1, y1, x2, y2 = self.last_canvas.bbox(self.selected_links_start[selected_arrow_start][0])
                    center_x1 = (x1+x2)//2
                    center_y1 = (y1+y2)//2
                    x1, y1, x2, y2 = self.last_canvas.bbox(self.selected_links_start[selected_arrow_start][1])
                    center_x2 = (x1+x2)//2
                    center_y2 = (y1+y2)//2
                    line_length = int(math.hypot(center_x2 - center_x1, center_y2 - center_y1))
                    self.last_canvas.coords(selected_arrow_start, line_coords[0]+x_move, line_coords[1]+y_move, line_coords[2], line_coords[3])
                    arrow = self.arrow_dict[tab][str(self.selected_links_start[selected_arrow_start][0])+'|'+str(self.selected_links_start[selected_arrow_start][1])]
                    midpoint_x, midpoint_y = (center_x2+center_x1)//2, (center_y2+center_y1)//2
                    self.last_canvas.coords(self.canvas_dict[tab][arrow]['text_id'], midpoint_x, midpoint_y)
                    self.last_canvas.itemconfig(selected_arrow_start, arrowshape=[line_length, line_length, arrow_width])
                for selected_arrow_end in self.selected_arrows_end:
                    line_coords = [int(i) for i in self.last_canvas.coords(selected_arrow_end)]
                    arrow_width = self.last_canvas.itemcget(selected_arrow_end, 'arrowshape').split(' ')[-1]
                    x1, y1, x2, y2 = self.last_canvas.bbox(self.selected_links_end[selected_arrow_end][0])
                    center_x1 = (x1+x2)//2
                    center_y1 = (y1+y2)//2
                    x1, y1, x2, y2 = self.last_canvas.bbox(self.selected_links_end[selected_arrow_end][1])
                    center_x2 = (x1+x2)//2
                    center_y2 = (y1+y2)//2
                    line_length = int(math.hypot(center_x2 - center_x1, center_y2 - center_y1))
                    self.last_canvas.coords(selected_arrow_end, line_coords[0], line_coords[1], line_coords[2]+x_move, line_coords[3]+y_move)
                    arrow = self.arrow_dict[tab][str(self.selected_links_end[selected_arrow_end][0])+'|'+str(self.selected_links_end[selected_arrow_end][1])]
                    midpoint_x, midpoint_y = (center_x2+center_x1)//2, (center_y2+center_y1)//2
                    self.last_canvas.coords(self.canvas_dict[tab][arrow]['text_id'], midpoint_x, midpoint_y)
                    self.last_canvas.itemconfig(selected_arrow_end, arrowshape=[line_length, line_length, arrow_width])
                self.start_x = event.x
                self.start_y = event.y
            elif command == 'current-drop':
                if self.command_lock != 'current':
                    return
                self.command_release('current')
                try:
                    self.canvas_dict[tab][self.selected_obj]['dimensions'] = list(self.last_canvas.bbox(self.selected_obj)) # catches drag from canvas space bug
                    x1, y1 = self.last_canvas.coords(self.selected_text)
                    self.canvas_dict[tab][self.selected_text]['dimensions'] = [int(x1), int(y1)]
                except:
                    pass

                if len(self.event_list) <= 10: # determine if node should be selected
                    self.select_object(event, self.last_canvas)
                self.event_list = []
                self.start_x = None
                self.start_y = None
                self.selected_obj = None
                self.selected_text = None
                self.last_canvas = None
                self.current_widget = None
                if self.savetoggle == 1:
                    self.notebookTb.update_state()
                    self.update_state()
                    self.clipboard.add(self.state.export())


        '''else: #old
            if command == 'current-drag':
                if self.command_lock != 'current':
                    return
                self.event_list.append(0)
                x_move, y_move = event.x-self.start_x, event.y-self.start_y
                x1, y1, x2, y2 = code_canvas.bbox(self.selected_obj)
                if x1+x_move < 0:
                    x_move = 0
                if y1+y_move < 0:
                    y_move = 0
                if x2+x_move > code_canvas.winfo_width():
                    x_move = code_canvas.winfo_width()-(x2+x_move)
                if y2+y_move > code_canvas.winfo_height():
                    y_move = code_canvas.winfo_height()-(y2+y_move)
                code_canvas.move(self.selected_obj, x_move, y_move)
                code_canvas.move(self.selected_text, x_move, y_move)
                for selected_arrow_start in self.selected_arrows_start:
                    line_coords = [int(i) for i in code_canvas.coords(selected_arrow_start)]
                    arrow_width = code_canvas.itemcget(selected_arrow_start, 'arrowshape').split(' ')[-1]
                    x1, y1, x2, y2 = code_canvas.bbox(self.selected_links_start[selected_arrow_start][0])
                    center_x1 = (x1+x2)//2
                    center_y1 = (y1+y2)//2
                    x1, y1, x2, y2 = code_canvas.bbox(self.selected_links_start[selected_arrow_start][1])
                    center_x2 = (x1+x2)//2
                    center_y2 = (y1+y2)//2
                    line_length = int(math.hypot(center_x2 - center_x1, center_y2 - center_y1))
                    code_canvas.coords(selected_arrow_start, line_coords[0]+x_move, line_coords[1]+y_move, line_coords[2], line_coords[3])
                    arrow = self.arrow_dict[tab][str(self.selected_links_start[selected_arrow_start][0])+'|'+str(self.selected_links_start[selected_arrow_start][1])]
                    midpoint_x, midpoint_y = (center_x2+center_x1)//2, (center_y2+center_y1)//2
                    code_canvas.coords(self.canvas_dict[tab][arrow]['text_id'], midpoint_x, midpoint_y)
                    code_canvas.itemconfig(selected_arrow_start, arrowshape=[line_length, line_length, arrow_width])
                for selected_arrow_end in self.selected_arrows_end:
                    line_coords = [int(i) for i in code_canvas.coords(selected_arrow_end)]
                    arrow_width = code_canvas.itemcget(selected_arrow_end, 'arrowshape').split(' ')[-1]
                    x1, y1, x2, y2 = code_canvas.bbox(self.selected_links_end[selected_arrow_end][0])
                    center_x1 = (x1+x2)//2
                    center_y1 = (y1+y2)//2
                    x1, y1, x2, y2 = code_canvas.bbox(self.selected_links_end[selected_arrow_end][1])
                    center_x2 = (x1+x2)//2
                    center_y2 = (y1+y2)//2
                    line_length = int(math.hypot(center_x2 - center_x1, center_y2 - center_y1))
                    code_canvas.coords(selected_arrow_end, line_coords[0], line_coords[1], line_coords[2]+x_move, line_coords[3]+y_move)
                    arrow = self.arrow_dict[tab][str(self.selected_links_end[selected_arrow_end][0])+'|'+str(self.selected_links_end[selected_arrow_end][1])]
                    midpoint_x, midpoint_y = (center_x2+center_x1)//2, (center_y2+center_y1)//2
                    code_canvas.coords(self.canvas_dict[tab][arrow]['text_id'], midpoint_x, midpoint_y)
                    code_canvas.itemconfig(selected_arrow_end, arrowshape=[line_length, line_length, arrow_width])
                self.start_x = event.x
                self.start_y = event.y
            elif command == 'current-start':
                self.event_list = []
                self.command_lock = 'current'
                self.selected_obj = self.canvas_dict[tab][code_canvas.find_withtag(CURRENT)[0]]['object_id']
                self.selected_text = self.canvas_dict[tab][self.selected_obj]['text_id']
                self.selected_arrows_start = self.canvas_dict[tab][self.selected_obj]['arrow_ids_start']
                self.selected_arrows_end = self.canvas_dict[tab][self.selected_obj]['arrow_ids_end']
                self.selected_links_start = self.canvas_dict[tab][self.selected_obj]['pair_dict_start']
                self.selected_links_end = self.canvas_dict[tab][self.selected_obj]['pair_dict_end']
                code_canvas.tag_raise(self.selected_obj)
                code_canvas.tag_raise(self.selected_text)
                self.start_x = event.x
                self.start_y = event.y
            elif command == 'current-drop':
                if self.command_lock != 'current':
                    return
                self.command_release('current')
                try:
                    self.canvas_dict[tab][self.selected_obj]['dimensions'] = code_canvas.bbox(self.selected_obj) # catches drag from canvas space bug
                    x1, y1 = code_canvas.coords(self.selected_text)
                    self.canvas_dict[tab][self.selected_text]['dimensions'] = [int(x1), int(y1)]
                except:
                    pass

                if len(self.event_list) <= 10: # determine if node should be selected
                    self.select_object(event, code_canvas)
                self.event_list = []
                self.start_x = None
                self.start_y = None
                self.selected_obj = None
                self.selected_text = None

                self.notebookTb.update_state() # in future: toggle this
                self.update_state()
                self.clipboard.add(self.state.export()) '''

    def delete_current(self, event, code_canvas, id=None, clipboard=True, bypass=False):
        if self.command_lock != None and not bypass:
            return

        if not id:
            if len(code_canvas.find_withtag(CURRENT)) == 0:
                return
            id = code_canvas.find_withtag(CURRENT)[0]

        if code_canvas == self.group_canvas:
            tab = self.group_canvas
        else:
            tab = self.canvas_tabs.select()

        tags = code_canvas.itemcget(id, 'tags')
        if 'arrow' in tags:
            found_obj = self.canvas_dict[tab][id]['object_id']
            found_text = self.canvas_dict[tab][found_obj]['text_id']
            partner_id_start, partner_id_end = self.canvas_dict[tab][found_obj]['pair']
            del self.canvas_dict[tab][partner_id_start]['pair_dict_start'][found_obj]
            del self.canvas_dict[tab][partner_id_end]['pair_dict_end'][found_obj]
            self.canvas_dict[tab][partner_id_start]['arrow_ids_start'].remove(found_obj)
            self.canvas_dict[tab][partner_id_end]['arrow_ids_end'].remove(found_obj)
            del self.arrow_dict[tab][str(partner_id_start)+'|'+str(partner_id_end)]
            self.graph_dict[tab].deleteEdge(partner_id_start, partner_id_end)
            if found_obj in self.select_edge_set:
                self.select_edge_set.remove(found_obj)
        elif 'node' in tags:
            found_obj = self.canvas_dict[tab][id]['object_id']
            found_text = self.canvas_dict[tab][found_obj]['text_id']
            self.graph_dict[tab].deleteNode(found_obj)
            if found_obj in self.select_node_set:
                self.select_node_set.remove(found_obj)
            for arrow in self.canvas_dict[tab][found_obj]['arrow_ids_start']:
                code_canvas.delete(arrow)
                text = self.canvas_dict[tab][arrow]['text_id']
                code_canvas.delete(self.canvas_dict[tab][arrow]['text_id'])
                partner_id = self.canvas_dict[tab][found_obj]['pair_dict_start'][arrow][1]
                self.graph_dict[tab].deleteEdge(found_obj, partner_id)
                del self.canvas_dict[tab][partner_id]['pair_dict_end'][arrow]
                self.canvas_dict[tab][partner_id]['arrow_ids_end'].remove(arrow)
                del self.arrow_dict[tab][str(self.canvas_dict[tab][found_obj]['pair_dict_start'][arrow][0])+'|'+str(self.canvas_dict[tab][found_obj]['pair_dict_start'][arrow][1])]
                del self.canvas_dict[tab][arrow]
                del self.canvas_dict[tab][text]
                if arrow in self.select_edge_set:
                    self.select_edge_set.remove(arrow)
            for arrow in self.canvas_dict[tab][found_obj]['arrow_ids_end']:
                code_canvas.delete(arrow)
                text = self.canvas_dict[tab][arrow]['text_id']
                code_canvas.delete(self.canvas_dict[tab][arrow]['text_id'])
                partner_id = self.canvas_dict[tab][found_obj]['pair_dict_end'][arrow][0]
                self.graph_dict[tab].deleteEdge(partner_id, found_obj)
                del self.canvas_dict[tab][partner_id]['pair_dict_start'][arrow]
                self.canvas_dict[tab][partner_id]['arrow_ids_start'].remove(arrow)
                del self.arrow_dict[tab][str(self.canvas_dict[tab][found_obj]['pair_dict_end'][arrow][0])+'|'+str(self.canvas_dict[tab][found_obj]['pair_dict_end'][arrow][1])]
                del self.canvas_dict[tab][arrow]
                del self.canvas_dict[tab][text]
                if arrow in self.select_edge_set:
                    self.select_edge_set.remove(arrow)
        code_canvas.delete(found_obj)
        code_canvas.delete(found_text)
        del self.canvas_dict[tab][found_obj]
        del self.canvas_dict[tab][found_text]
        if found_obj == self.selected_group_obj and code_canvas != self.group_canvas:
            self.create_group_canvas()
        if clipboard:
            self.notebookTb.update_state()
            self.update_state()
            self.clipboard.add(self.state.export())

    def link_objects(self, event, code_canvas, end_obj=None):
        if self.command_lock != None and self.command_lock != 'link':
            return
        elif len(code_canvas.find_withtag(CURRENT)) == 0 and end_obj == None:
            return
        '''tags = code_canvas.itemcget(code_canvas.find_withtag(CURRENT), 'tags')
        if 'arrow' in tags:
            return'''

        if code_canvas == self.group_canvas:
            tab = self.group_canvas
        else:
            tab = self.canvas_tabs.select()

        if not self.start_obj:
            self.command_lock = 'link'
            self.start_obj = self.canvas_dict[tab][code_canvas.find_withtag(CURRENT)[0]]['object_id']
            self.start_canvas = tab
            code_canvas.itemconfig(self.start_obj, outline='#3399FF', width=3, dash=(4, 8))
        else:
            if not end_obj:
                end_obj = self.canvas_dict[tab][code_canvas.find_withtag(CURRENT)[0]]['object_id']
            link_pair = [self.start_obj,end_obj]
            if self.start_canvas != tab:
                self.canvas_tabs.select(self.start_canvas)
                code_canvas = self.canvas_tab_dict[tab]['object']
                code_canvas.itemconfig(self.start_obj, outline='black', width=1, dash=())
                self.command_release('link')
                print("Can't link across canvases!")
                self.start_obj = None
                self.start_canvas = None
                return
            elif link_pair[0] == link_pair[1]:
                code_canvas.itemconfig(self.start_obj, outline='black', width=1, dash=())
                self.command_release('link')
                self.start_obj = None
                self.start_canvas = None
                self.set_hover(event, code_canvas, 'enter')
                return
            elif str(link_pair[0])+'|'+str(link_pair[1]) in self.arrow_dict[tab]:
                code_canvas.itemconfig(self.start_obj, outline='black', width=1, dash=())
                self.command_release('link')
                print('Link already present!')
                self.start_obj = None
                self.start_canvas = None
                return
            prior_arrow_text = None
            if str(link_pair[1])+'|'+str(link_pair[0]) in self.arrow_dict[tab]:
                old_arrow = self.arrow_dict[tab][str(link_pair[1])+'|'+str(link_pair[0])]
                old_text = self.canvas_dict[tab][old_arrow]['text_id']
                prior_arrow_text = self.canvas_dict[tab][old_arrow]['text']
                del self.arrow_dict[tab][str(link_pair[1])+'|'+str(link_pair[0])]
                code_canvas.delete(old_arrow)
                code_canvas.delete(self.canvas_dict[tab][old_arrow]['text_id'])
                del self.canvas_dict[tab][self.start_obj]['pair_dict_end'][old_arrow]
                self.canvas_dict[tab][self.start_obj]['arrow_ids_end'].remove(old_arrow)
                del self.canvas_dict[tab][end_obj]['pair_dict_start'][old_arrow]
                self.canvas_dict[tab][end_obj]['arrow_ids_start'].remove(old_arrow)
                del self.canvas_dict[tab][old_arrow]
                del self.canvas_dict[tab][old_text]
                self.graph_dict[tab].deleteEdge(link_pair[1], link_pair[0])
            code_canvas.itemconfig(self.start_obj, outline='black', width=1, dash=())
            x1, y1, x2, y2 = code_canvas.bbox(self.start_obj)
            width = x2-x1
            height = y2-y1
            if height > width:
                arrow_width = width//3
            else:
                arrow_width = height//3
            center_x1 = (x1+x2)//2
            center_y1 = (y1+y2)//2
            x1, y1, x2, y2 = code_canvas.bbox(end_obj)
            center_x2 = (x1+x2)//2
            center_y2 = (y1+y2)//2
            line_length = int(math.hypot(center_x2 - center_x1, center_y2 - center_y1))
            if prior_arrow_text:
                arrow_text = str(prior_arrow_text)
            else:
                arrow_text = ' '
            self.new_text = code_canvas.create_text((center_x2+center_x1)//2, (center_y2+center_y1)//2, text=str(arrow_text), fill='black', font=('Arial', 16))
            code_canvas.itemconfig(self.new_text, tags=('arrow',))
            code_canvas.tag_raise(self.new_text)
            new_arrow = code_canvas.create_line(center_x1, center_y1, center_x2, center_y2, arrow='last', arrowshape=[line_length,line_length,arrow_width],
                                                  fill='green', tags=('arrow',))
            code_canvas.tag_lower(new_arrow)
            self.arrow_dict[tab][str(link_pair[0])+'|'+str(link_pair[1])] = new_arrow
            self.canvas_dict[tab][self.start_obj]['pair_dict_start'][new_arrow] = list(link_pair)
            self.canvas_dict[tab][end_obj]['pair_dict_end'][new_arrow] = list(link_pair)
            self.canvas_dict[tab][self.start_obj]['arrow_ids_start'].append(new_arrow)
            self.canvas_dict[tab][end_obj]['arrow_ids_end'].append(new_arrow)
            self.canvas_dict[tab][new_arrow] = {'object_id':new_arrow, 'text_id':self.new_text, 'pair':[self.start_obj,end_obj], 'text':arrow_text} #'order':code_canvas.itemcget(self.new_text, 'text')}
            self.canvas_dict[tab][self.new_text] = {'object_id':new_arrow, 'text_id':self.new_text}
            self.graph_dict[tab].addEdge(Edge(link_pair[0], link_pair[1]))
            source_status = self.graph_dict[tab].nodes.get(link_pair[0]).status
            sink_status = self.graph_dict[tab].nodes.get(link_pair[1]).status
            if not source_status or not sink_status:
                self.graph_dict[tab].editEdge(Edge(link_pair[0], link_pair[1]), activity=True)
                code_canvas.itemconfig(new_arrow, fill='red')
            self.command_release('link')
            self.start_obj = None
            self.start_canvas = None
            self.notebookTb.update_state()
            self.update_state()
            self.clipboard.add(self.state.export())

    def change_arrow_label(self, event, code_canvas):
        if code_canvas == self.group_canvas:
            tab = self.group_canvas
        else:
            tab = self.canvas_tabs.select()
        arrow = code_canvas.find_withtag(CURRENT)[0]
        arrow_id = self.canvas_dict[tab][arrow]['object_id']
        text_id = self.canvas_dict[tab][arrow]['text_id']
        label_text = self.canvas_dict[tab][arrow_id]['text']

        arrow_root = Toplevel(self.root)
        arrow_root.title('Arrow Menu')
        arrow_root.resizable(False, False)

        Label(arrow_root, text='Arrow Text: '+label_text).pack(fill=X)
        Label(arrow_root, text='New Text:').pack(fill=X)
        arrow_textbox = Entry(arrow_root)
        arrow_textbox.pack(fill=X)

        Button(arrow_root, text='Submit', command = lambda: self.arrow_submit(arrow_root, code_canvas, arrow, arrow_id, text_id, arrow_textbox, tab)).pack(fill=X)
        arrow_root.bind('<Return>', lambda e: self.arrow_submit(arrow_root, code_canvas, arrow, arrow_id, text_id, arrow_textbox, tab))

        arrow_root.transient(self.root)
        arrow_root.wait_visibility()
        arrow_root.grab_set()
        self.window.config(menu = self.sketchobj.menu)

    def arrow_submit(self, arrow_root, code_canvas, arrow, arrow_id, text_id, arrow_textbox, tab):
        arrow_text = arrow_textbox.get()
        if not arrow_text:
            print('Cancelled')
            arrow_root.destroy()
            return

        arrow_text = arrow_text.strip()
        code_canvas.itemconfig(text_id, text=str(arrow_text))
        self.canvas_dict[tab][arrow_id]['text'] = str(arrow_text)

        arrow_root.destroy()

        self.notebookTb.update_state()
        self.update_state()
        self.clipboard.add(self.state.export())

    def change_box_label(self, event, code_canvas):
        if code_canvas == self.group_canvas:
            tab = self.group_canvas
        else:
            tab = self.canvas_tabs.select()

        obj_id =  self.canvas_dict[tab][code_canvas.find_withtag(CURRENT)[0]]['object_id']
        text_id = self.canvas_dict[tab][obj_id]['text_id']
        label_text = self.canvas_dict[tab][obj_id]['text']
        if label_text.isspace():
            label_text = 'None'

        box_root = Toplevel(self.root)
        box_root.title('Box Menu')
        box_root.resizable(False, False)

        Label(box_root, text='Box Text: '+label_text).pack(fill=X)
        Label(box_root, text='New Text:').pack(fill=X)
        box_textbox = Entry(box_root)
        box_textbox.pack(fill=X)

        Button(box_root, text='Submit', command = lambda: self.box_submit(box_root, code_canvas, obj_id, text_id, box_textbox, tab)).pack(fill=X)
        box_root.bind('<Return>', lambda e: self.box_submit(box_root, code_canvas, obj_id, text_id, box_textbox, tab))

        box_root.transient(self.root)
        box_root.wait_visibility()
        box_root.grab_set()
        self.window.config(menu = self.sketchobj.menu)

    def box_submit(self, box_root, code_canvas, obj_id, text_id, box_textbox, tab):
        box_text = box_textbox.get()
        if not box_text:
            print('Cancelled')
            box_root.destroy()
            return
        box_text = box_text.strip()
        code_canvas.itemconfig(text_id, text=box_text)
        self.canvas_dict[tab][obj_id]['text'] = box_text
        self.graph_dict[tab].editNode(obj_id, type=box_text)
        box_root.destroy()

        self.notebookTb.update_state()
        self.update_state()
        self.clipboard.add(self.state.export())

    def change_tab_label(self):
        label_text = self.canvas_tab_dict[self.canvas_tabs.select()]['name']
        if label_text.isspace():
            label_text = 'None'

        tab_root = Toplevel(self.root)
        tab_root.title('Canvas Tab Menu')
        tab_root.resizable(False, False)

        Label(tab_root, text='Tab Text: '+label_text).pack(fill=X)
        Label(tab_root, text='New Text:').pack(fill=X)
        tab_textbox = Entry(tab_root)
        tab_textbox.pack(fill=X)

        Button(tab_root, text='Submit', command = lambda: self.tab_submit(tab_root, tab_textbox)).pack(fill=X)
        tab_root.bind('<Return>', lambda e: self.tab_submit(tab_root, tab_textbox))

        tab_root.transient(self.root)
        tab_root.wait_visibility()
        tab_root.grab_set()
        self.window.config(menu = self.sketchobj.menu)

    def tab_submit(self, tab_root, tab_textbox):
        tab_text = tab_textbox.get()
        if not tab_text:
            print('Cancelled')
            tab_root.destroy()
            return
        elif tab_text.isspace():
            tab_text = 'Canvas'
        tab_text = tab_text.strip()
        self.canvas_tabs.tab(self.canvas_tabs.select(), text=tab_text)
        self.canvas_tab_dict[self.canvas_tabs.select()]['name'] = tab_text
        tab_root.destroy()
        self.notebookTb.update_state()
        self.update_state()
        self.clipboard.add(self.state.export())

    def set_active_arrow(self, event, code_canvas, arrow=None, tab=None, forceactivity=None):
        if not tab:
            if code_canvas == self.group_canvas:
                tab = self.group_canvas
            else:
                tab = self.canvas_tabs.select()
        if not arrow:
            arrow = code_canvas.find_withtag(CURRENT)[0]
        if arrow in self.select_edge_set:
            self.select_edge_set.remove(arrow)

        arrow_id = self.canvas_dict[tab][arrow]['object_id']
        text_id = self.canvas_dict[tab][arrow_id]['text_id']
        source, sink = self.canvas_dict[tab][arrow_id]['pair']

        if (sink in self.graph_dict[tab].activeEdgeList[source] and forceactivity == None) or forceactivity == 'setinactive':
            self.graph_dict[tab].editEdge(Edge(source, sink), activity=True)
            code_canvas.itemconfig(arrow_id, fill='red')
        else:
            source_status = self.graph_dict[tab].nodes.get(source).status
            sink_status = self.graph_dict[tab].nodes.get(sink).status
            if not source_status or not sink_status:
                code_canvas.itemconfig(arrow_id, fill='red')
                return
            self.graph_dict[tab].editEdge(Edge(source, sink), activity=False)
            code_canvas.itemconfig(arrow_id, fill='green')

    def set_active_node(self, event, code_canvas, node=None, tab=None, refresh=False, forceactivity=None):
        if not node:
            node = code_canvas.find_withtag(CURRENT)[0]
        if not tab:
            if code_canvas == self.group_canvas:
                tab = self.group_canvas
            else:
                tab = self.canvas_tabs.select()

        node_id = self.canvas_dict[tab][node]['object_id']

        if (self.graph_dict[tab].nodes.get(node_id).status == True and forceactivity == None) or forceactivity == 'setinactive':
            self.graph_dict[tab].editNode(node_id, status='setinactive')
            code_canvas.itemconfig(node_id, fill='#EEA4A4')
            if not refresh: # prevents edge from changing status when switching selection
                for arrow_id in self.canvas_dict[tab][node_id]['arrow_ids_start']:
                    code_canvas.itemconfig(arrow_id, fill='red')
                    partner_id = self.canvas_dict[tab][node_id]['pair_dict_start'][arrow_id][1]
                    self.graph_dict[tab].editEdge(Edge(node_id, partner_id), activity=True)
                for arrow_id in self.canvas_dict[tab][node_id]['arrow_ids_end']:
                    code_canvas.itemconfig(arrow_id, fill='red')
                    partner_id = self.canvas_dict[tab][node_id]['pair_dict_end'][arrow_id][0]
                    self.graph_dict[tab].editEdge(Edge(partner_id, node_id), activity=True)
        else:
            self.graph_dict[tab].editNode(node_id, status='setactive')
            if self.canvas_dict[tab][node_id]['group_obj'] == None:
                code_canvas.itemconfig(node_id, fill='#d9d9d9')
            else:
                code_canvas.itemconfig(node_id, fill='gold')
        if node_id in self.select_node_set:
            self.select_node_set.remove(node_id)

    ###### Compile Canvas and Save #####
    def compile_objects(self):
        # choose file
        self.command_lock = 'compile'
        filename = filedialog.asksaveasfilename(title = 'Save binary output as...', filetypes = (("all files","*.*"), ))
        if not filename:
            print('Cancelled')
            self.command_release('compile')
            return
        self.command_release('compile')
        if self.state.kernel == 'ONNX':
            print(self.state.kernel)
            # check graph object for group nodes (ONNX unpack code)
            group_node_list = []
            prior_canvas = deepcopy(self.canvas_dict[self.canvas_tabs.select()])
            prior_arrow_dict = deepcopy(self.arrow_dict[self.canvas_tabs.select()])
            prior_graph_nodes = deepcopy(self.graph_dict[self.canvas_tabs.select()].nodes)
            prior_graph_adjacency = deepcopy(self.graph_dict[self.canvas_tabs.select()].adjacencyList)
            prior_graph_active_list = deepcopy(self.graph_dict[self.canvas_tabs.select()].activeEdgeList)
            for node in prior_graph_nodes:
                if (prior_graph_nodes[node].status == True) and (prior_graph_nodes[node].group == True or 'subgraph' in prior_graph_nodes[node].params):
                    group_node_list.append(prior_graph_nodes[node].id)
            if len(group_node_list) > 0:
                group_node_list = sorted(group_node_list)
                graph_obj = Graph(graph=self.graph_dict[self.canvas_tabs.select()])
                try:
                    new_id = max([key for key in prior_canvas]) # last id before new added
                except:
                    new_id = 0
                for group_node in group_node_list:
                    old_new_id_ref = {}
                    node_graph_obj = prior_canvas[group_node]['group_obj']
                    node_prior_canvas = node_graph_obj.saved_canvas
                    node_prior_graph_nodes = node_graph_obj.saved_graph_nodes
                    node_prior_graph_obj = node_graph_obj.saved_graph_obj
                    # check if node is empty
                    if len(node_prior_canvas) == 0:
                        prior_canvas[group_node]['text'] = 'PASS'
                        prior_canvas[group_node]['group_obj'] = None
                        graph_obj.editNode(group_node, params={}, group=False, type='PASS')
                        continue
                    # for first/last, even if starts at high number, normalized later on (1, 3, etc)
                    first_sub_node = int(new_id+1) #new sink
                    topo_sort, expanded_topo_sort = node_prior_graph_obj.topologicalSort() # must determine order for source/sink
                    for sub_node in topo_sort:
                        node_obj = node_prior_graph_nodes[sub_node]
                        type = node_obj.type
                        status = node_obj.status
                        params = node_obj.params
                        learned_params = node_obj.learned_params
                        new_id += 1 # node
                        old_new_id_ref[sub_node] = new_id
                        graph_obj.addNode(Node(new_id, type=type, params=params, learned_params=learned_params, status=status))
                        prior_canvas[new_id] = {'text':type}
                        new_id += 1 # text
                    last_sub_node = int(new_id-1) #new source
                    for source in node_prior_graph_obj.adjacencyList:
                        sink_list = node_prior_graph_obj.adjacencyList[source]
                        if source not in node_prior_graph_obj.activeEdgeList:
                            continue
                        for sink in sink_list:
                            if sink not in node_prior_graph_obj.activeEdgeList[source]:
                                continue
                            new_id += 1 # text
                            new_id += 1 # node
                            graph_obj.addEdge(Edge(old_new_id_ref[source], old_new_id_ref[sink]))
                    # delete group node from list, go through prior_arrow_dict and delete edges with id as source or sink
                    graph_obj.deleteNode(group_node)
                    for pair in dict(prior_arrow_dict):
                        source, sink = pair.split('|')
                        source = int(source)
                        sink = int(sink)
                        if source in prior_graph_active_list:
                            if sink not in prior_graph_active_list[source]:
                                continue
                        else:
                            continue
                        if sink == group_node: # lead into group node, replace with first sub
                            graph_obj.addEdge(Edge(source, first_sub_node))
                            graph_obj.deleteEdge(source, sink)
                            del prior_arrow_dict[pair]
                            new_pair = '|'.join([str(source), str(first_sub_node)])
                            prior_arrow_dict[new_pair] = 0 # dummy edge, source/sink used as reference for next group node if group nodes link later
                        if source == group_node: # from group node, replace with last sub
                            graph_obj.addEdge(Edge(last_sub_node, sink))
                            graph_obj.deleteEdge(source, sink)
                            del prior_arrow_dict[pair]
                            new_pair = '|'.join([str(last_sub_node), str(sink)])
                            prior_arrow_dict[new_pair] = 0 # dummy edge, source/sink used as reference for next group node if group nodes link later
            else:
                graph_obj = self.graph_dict[self.canvas_tabs.select()]
        else:
            graph_obj = self.graph_dict[self.canvas_tabs.select()] # standardized since sequential nodes will unpack automatically

        #normalize ids in graph object
        graph_obj = Graph(graph=graph_obj).normalize()

        # display
        graph_obj.display()
        order, expanded_order = graph_obj.topologicalSort()
        print(order)
        value_order = [graph_obj.nodes.get(i).type for i in order]
        print(value_order)
        print(expanded_order)

        # compile
        binder = Binder(self.state.kernel)
        model_text = binder.exportModel(graph_obj, filename)

        # push to notebook
        self.notebookTb.open_tab(new_file=True, load_content=model_text, canvas=self.canvas_tabs.select())

    def save_canvas(self, event=None):
        if self.canvas_tabs.select() in self.save_dict:
            filename = self.save_dict[self.canvas_tabs.select()]
        else:
            filename = None
        self.save_as_canvas(filename=filename)

    def save_as_canvas(self, event=None, filename=None, rearrange=False):
        self.command_lock = 'compile'
        if not filename and not rearrange:
            filename = filedialog.asksaveasfilename(title = 'Save current canvas as...', filetypes = (("Sketch Files","*.sk"), ))
        if not filename and not rearrange:
            print('Cancelled')
            self.command_release('compile')
            return
        self.command_release('compile')
        tab_text = str(self.canvas_tab_dict[self.canvas_tabs.select()]['name'])
        saved_canvas = self.canvas_dict[self.canvas_tabs.select()]
        saved_arrows = self.arrow_dict[self.canvas_tabs.select()]
        saved_graph_active_edge = self.graph_dict[self.canvas_tabs.select()].activeEdgeList
        saved_graph_nodes = self.graph_dict[self.canvas_tabs.select()].nodes
        saved_graph_obj = self.graph_dict[self.canvas_tabs.select()]
        save_obj = Save(tab_text, saved_canvas, saved_arrows, saved_graph_active_edge, saved_graph_nodes, saved_graph_obj)
        if rearrange:
            self.load_canvas(rearrange=True, state_obj=save_obj)
        else:
            with open(filename, 'wb') as save_file:
                pickle.dump(save_obj, save_file)
            self.save_dict[self.canvas_tabs.select()] = filename

    def update_state(self):
        tab = self.group_canvas
        tab_text = self.group_label['text']
        saved_canvas = dict(self.canvas_dict[tab])
        saved_arrows = dict(self.arrow_dict[tab])
        saved_graph_active_edge = dict(self.graph_dict[tab].activeEdgeList)
        saved_graph_nodes = dict(self.graph_dict[tab].nodes)
        saved_graph_obj = self.graph_dict[tab]
        save_obj = Save(tab_text, saved_canvas, saved_arrows, saved_graph_active_edge, saved_graph_nodes, saved_graph_obj)
        self.state.update('groupcanvas', save_obj)
        if self.selected_group_obj:
            self.canvas_dict[self.canvas_tabs.select()][self.selected_group_obj]['group_obj'] = save_obj
            self.graph_dict[self.canvas_tabs.select()].editNode(self.selected_group_obj, params={'subgraph':deepcopy(saved_graph_obj)})

        state_dict = {}
        count = 0
        for tab in self.canvas_tabs.tabs():
            count += 1
            tab_text = str(self.canvas_tab_dict[tab]['name'])
            saved_canvas = dict(self.canvas_dict[tab])
            saved_arrows = dict(self.arrow_dict[tab])
            saved_graph_active_edge = dict(self.graph_dict[tab].activeEdgeList)
            saved_graph_nodes = dict(self.graph_dict[tab].nodes)
            saved_graph_obj = self.graph_dict[tab]
            save_obj = Save(tab_text, saved_canvas, saved_arrows, saved_graph_active_edge, saved_graph_nodes, saved_graph_obj)
            state_dict[count] = save_obj
        self.state.update('canvas', dict(state_dict))
        self.state.update('canvastab', int(self.canvas_tabs.index(self.canvas_tabs.select())))

        ChoiceDefaults().save(self.defaults_list, self.defaults_dict, self.geometry_dict)

    def load_state(self, unredo=False, state_dom=None):
        if unredo:
            self.state.dom = dict(state_dom)
        if 'canvas' not in self.state.dom:
            return
        if self.state.dom['canvas'] == '':
            return
        if unredo:
            for i in range(0, len(self.canvas_tabs.tabs())):
                self.delete_canvas(state=True)
        else:
            self.delete_canvas(state=True)
        key_list = []
        for key in self.state.dom['canvas']:
            key_list.append(int(key))
        key_list = sorted(key_list)
        for key in key_list:
            state_obj = self.state.dom['canvas'][key]
            self.load_canvas(state=True, state_obj=state_obj)
        #self.load_canvas(state=True, state_obj=self.state.dom['groupcanvas'], groupcanvas=True) # disabled undo/redo showing group canvas, only reloads obj.
                                                                       # Requires selected_group_obj to remain consistent to work properly.
        if not unredo:
            self.canvas_tabs.select(self.canvas_tabs.tabs()[0])
        else:
            self.canvas_tabs.select(self.state.dom['canvastab'])

    def load_canvas(self, duplicate=False, state=False, rearrange=False, state_obj=None, clipboard=False, groupcanvas=False):
        if duplicate:
            tab_text = str(self.canvas_tab_dict[self.canvas_tabs.select()]['name'])+' (dup)'
            prior_canvas = self.canvas_dict[self.canvas_tabs.select()]
            prior_arrows = self.arrow_dict[self.canvas_tabs.select()]
            prior_graph_active_edge = self.graph_dict[self.canvas_tabs.select()].activeEdgeList
            prior_graph_nodes = self.graph_dict[self.canvas_tabs.select()].nodes
            prior_graph = self.graph_dict[self.canvas_tabs.select()].saved_graph_obj
            clipboard = True
        elif state:
            save_obj = state_obj
            tab_text = save_obj.tab_text
            prior_canvas = save_obj.saved_canvas
            prior_arrows = save_obj.saved_arrows
            prior_graph_active_edge = save_obj.saved_graph_active_edge
            prior_graph_nodes = save_obj.saved_graph_nodes
            prior_graph = save_obj.saved_graph_obj
        elif rearrange:
            save_obj = state_obj
            tab_text = save_obj.tab_text
            prior_canvas = save_obj.saved_canvas
            prior_arrows = save_obj.saved_arrows
            prior_graph_active_edge = save_obj.saved_graph_active_edge
            prior_graph_nodes = save_obj.saved_graph_nodes
            prior_graph = save_obj.saved_graph_obj
            tab_position = self.canvas_tabs.index(self.canvas_tabs.select())
            specified_tab = self.canvas_tabs.select()
            clipboard = True
        else:
            self.command_lock = 'compile'
            filename = filedialog.askopenfilename(title = 'Open prior saved canvas...', filetypes = (("Sketch Files","*.sk"), ))
            if not filename:
                print('Cancelled')
                self.command_release('compile')
                return
            self.command_release('compile')
            with open(filename, 'rb') as save_file:
                save_obj = pickle.load(save_file)
                tab_text = save_obj.tab_text
                prior_canvas = save_obj.saved_canvas
                prior_arrows = save_obj.saved_arrows
                prior_graph_active_edge = save_obj.saved_graph_active_edge
                prior_graph_nodes = save_obj.saved_graph_nodes
                prior_graph = save_obj.saved_graph_obj

        if not groupcanvas:
            self.create_canvas()
            tab = self.canvas_tabs.select()
            graph = self.graph_dict[tab]
            self.canvas_tabs.tab(tab, text=tab_text)
            self.canvas_tab_dict[tab]['name'] = tab_text
            code_canvas = self.canvas_tab_dict[tab]['object']
        else:
            self.create_group_canvas()
            tab = self.group_canvas
            graph = self.graph_dict[tab]
            code_canvas = self.group_canvas

        if rearrange:
            self.delete_canvas(tab=specified_tab)
            self.canvas_tabs.insert(tab_position, tab)

        group_trip = 0
        group_node_list = []
        try:
            new_id = max([key for key in prior_canvas]) # last id before new added
        except:
            new_id = 0
        if groupcanvas:
            for node in prior_graph_nodes:
                if prior_canvas[node]['group_obj'] != None:
                    group_trip = 1
                    group_node_list.append(node)
            if group_trip == 1:
                rearrange = True
                for group_node in group_node_list:
                    old_new_group_ids = {}
                    node_graph_obj = prior_canvas[group_node]['group_obj']
                    node_prior_canvas = node_graph_obj.saved_canvas
                    node_prior_arrows = node_graph_obj.saved_arrows
                    node_prior_graph_active_edge = node_graph_obj.saved_graph_active_edge
                    node_prior_graph_nodes = node_graph_obj.saved_graph_nodes
                    node_prior_graph_obj = node_graph_obj.saved_graph_obj
                    # check if node is empty
                    if len(node_prior_canvas) == 0:
                        prior_canvas[group_node]['text'] = 'PASS'
                        prior_canvas[group_node]['group_obj'] = None
                        prior_canvas[group_node]['value'] = {}
                        prior_graph_nodes.get(group_node).params = {}
                        prior_graph_nodes.get(group_node).group = False
                        prior_graph_nodes.get(group_node).type = 'PASS'
                        continue
                    # for first/last, even if starts at high number, normalized later on (1, 3, etc)
                    first_sub_node = int(new_id+1) #new source
                    topo_sort, expanded_topo_sort = node_prior_graph_obj.topologicalSort() # must determine order for source/sink
                    for sub_node in topo_sort:
                        new_id += 1 # node
                        old_new_group_ids[sub_node] = new_id
                        new_id += 1 # text
                        old_new_group_ids[sub_node+1] = new_id
                    last_sub_node = int(new_id-1) #new sink
                    for sub_arrow in node_prior_arrows:
                        new_id += 1 # text
                        old_new_group_ids[node_prior_arrows[sub_arrow]-1] = new_id
                        new_id += 1 # node
                        old_new_group_ids[node_prior_arrows[sub_arrow]] = new_id
                    # convert prior dictionaries to set up for 1st and last group nodes
                    for id in prior_graph_nodes: # convert prior_canvas sources and sinks
                        for edge in prior_canvas[id]['arrow_ids_start']:
                            source, sink = prior_canvas[id]['pair_dict_start'][edge]
                            if source == group_node: # only case is for group node itself
                                source = last_sub_node
                            if sink == group_node:
                                sink = first_sub_node
                            prior_canvas[id]['pair_dict_start'][edge] = [source, sink]
                        for edge in prior_canvas[id]['arrow_ids_end']:
                            source, sink = prior_canvas[id]['pair_dict_end'][edge]
                            if source == group_node:
                                source = last_sub_node
                            if sink == group_node: # only case is for group node itself
                                sink = first_sub_node
                            prior_canvas[id]['pair_dict_end'][edge] = [source, sink]
                    for pair in prior_arrows:
                        arrow_obj = prior_arrows[pair]
                        source, sink = pair.split('|')
                        if source == str(group_node):
                            source = str(last_sub_node)
                        if sink == str(group_node):
                            sink = str(first_sub_node)
                        newpair = '|'.join([source, sink])
                        prior_canvas[arrow_obj]['pair'] = [int(source), int(sink)]
                        prior_arrows[newpair] = prior_arrows.pop(pair)
                    for id in dict(prior_graph_active_edge):
                        link_list = prior_graph_active_edge[id]
                        new_link_list = []
                        for sink in link_list:
                            if sink == group_node:
                                sink = first_sub_node
                            new_link_list.append(sink)
                        prior_graph_active_edge[id] = list(new_link_list)
                        if id == group_node: # add last node if group node is in active edges
                            prior_graph_active_edge[last_sub_node] = list(new_link_list)
                    # convert every value in node_prior_canvas, node_prior_arrows, node_prior_graph_active_edge, and node_prior_graph_nodes using old_new_group_ids
                    for id in node_prior_graph_nodes: # convert node_prior_canvas sources and sinks
                        text_id = id+1
                        new_edges = []
                        for edge in node_prior_canvas[id]['arrow_ids_start']:
                            source, sink = node_prior_canvas[id]['pair_dict_start'][edge]
                            new_source = old_new_group_ids[source]
                            new_sink = old_new_group_ids[sink]
                            node_prior_canvas[id]['pair_dict_start'][edge] = [new_source, new_sink]
                            new_edges.append(old_new_group_ids[edge])
                        node_prior_canvas[id]['arrow_ids_start'] = list(new_edges)
                        new_edges = []
                        for edge in node_prior_canvas[id]['arrow_ids_end']:
                            source, sink = node_prior_canvas[id]['pair_dict_end'][edge]
                            new_source = old_new_group_ids[source]
                            new_sink = old_new_group_ids[sink]
                            node_prior_canvas[id]['pair_dict_end'][edge] = [new_source, new_sink]
                            new_edges.append(old_new_group_ids[edge])
                        new_pair_dict_start = {}
                        new_pair_dict_end = {}
                        for old_edge in node_prior_canvas[id]['pair_dict_start']:
                            new_pair_dict_start[old_new_group_ids[old_edge]] = list(node_prior_canvas[id]['pair_dict_start'][old_edge])
                        node_prior_canvas[id]['pair_dict_start'] = {}
                        node_prior_canvas[id]['pair_dict_start'] = dict(new_pair_dict_start)
                        for old_edge in node_prior_canvas[id]['pair_dict_end']:
                            new_pair_dict_end[old_new_group_ids[old_edge]] = list(node_prior_canvas[id]['pair_dict_end'][old_edge])
                        node_prior_canvas[id]['pair_dict_end'] = {}
                        node_prior_canvas[id]['pair_dict_end'] = dict(new_pair_dict_end)
                        node_prior_canvas[id]['arrow_ids_end'] = list(new_edges)
                        node_prior_canvas[id]['object_id'] = old_new_group_ids[node_prior_canvas[id]['object_id']]
                        node_prior_canvas[id]['text_id'] = old_new_group_ids[node_prior_canvas[id]['text_id']]
                        node_prior_canvas[text_id]['object_id'] = old_new_group_ids[node_prior_canvas[text_id]['object_id']]
                        node_prior_canvas[text_id]['text_id'] = old_new_group_ids[node_prior_canvas[text_id]['text_id']]
                    for pair in node_prior_arrows:
                        arrow_id = node_prior_arrows[pair]
                        text_id = arrow_id-1
                        node_prior_canvas[text_id]['object_id'] = old_new_group_ids[node_prior_canvas[text_id]['object_id']]
                        node_prior_canvas[text_id]['text_id'] = old_new_group_ids[node_prior_canvas[text_id]['text_id']]
                        node_prior_canvas[arrow_id]['object_id'] = old_new_group_ids[node_prior_canvas[arrow_id]['object_id']]
                        node_prior_canvas[arrow_id]['text_id'] = old_new_group_ids[node_prior_canvas[arrow_id]['text_id']]
                        source, sink = node_prior_canvas[arrow_id]['pair']
                        new_source = old_new_group_ids[source]
                        new_sink = old_new_group_ids[sink]
                        node_prior_canvas[arrow_id]['pair'] = [new_source, new_sink]
                        node_prior_arrows[pair] = old_new_group_ids[node_prior_arrows[pair]]
                    for id in node_prior_graph_active_edge:
                        sink_list = node_prior_graph_active_edge[id]
                        new_sink_list = []
                        for sink in sink_list:
                            new_sink_list.append(old_new_group_ids[sink])
                        node_prior_graph_active_edge[id] = list(new_sink_list)
                    # convert every key in node_prior_canvas, node_prior_arrows, node_prior_graph_active_edge, and node_prior_graph_nodes using old_new_group_ids
                    new_node_prior_canvas = {}
                    new_node_prior_graph_active_edge = {}
                    new_node_prior_graph_nodes = {}
                    new_node_prior_arrows = {}
                    for key in dict(node_prior_canvas):
                        new_node_prior_canvas[old_new_group_ids[key]] = node_prior_canvas[key]
                    for key in dict(node_prior_graph_active_edge):
                        new_node_prior_graph_active_edge[old_new_group_ids[key]] = node_prior_graph_active_edge[key]
                    for key in dict(node_prior_graph_nodes):
                        new_node_prior_graph_nodes[old_new_group_ids[key]] = node_prior_graph_nodes[key]
                    for pair in dict(node_prior_arrows):
                        source, sink = pair.split('|')
                        new_source = old_new_group_ids[int(source)]
                        new_sink = old_new_group_ids[int(sink)]
                        new_pair = '|'.join([str(new_source), str(new_sink)])
                        new_node_prior_arrows[new_pair] = node_prior_arrows[pair]
                    node_prior_canvas = dict(new_node_prior_canvas)
                    node_prior_graph_active_edge = dict(new_node_prior_graph_active_edge)
                    node_prior_graph_nodes = dict(new_node_prior_graph_nodes)
                    node_prior_arrows = dict(new_node_prior_arrows)
                    # in node_prior_canvas, add converted sinks to first sub node and sources to last sub node in node_prior_canvas from group_node in prior_canvas
                    node_prior_canvas[last_sub_node]['arrow_ids_start'] = list(prior_canvas[group_node]['arrow_ids_start'])
                    node_prior_canvas[last_sub_node]['pair_dict_start'] = dict(prior_canvas[group_node]['pair_dict_start'])
                    node_prior_canvas[first_sub_node]['arrow_ids_end'] = list(prior_canvas[group_node]['arrow_ids_end'])
                    node_prior_canvas[first_sub_node]['pair_dict_end'] = dict(prior_canvas[group_node]['pair_dict_end'])
                    # delete group_node from prior_canvas, prior_graph_nodes, prior_graph_active_edge (if present)
                    del prior_canvas[group_node]
                    del prior_canvas[group_node+1] # get rid of text
                    del prior_graph_nodes[group_node]
                    if group_node in prior_graph_active_edge:
                        del prior_graph_active_edge[group_node]
                    # merge all node_prior dictionaries to original prior dictionaries
                    prior_canvas.update(node_prior_canvas)
                    prior_arrows.update(node_prior_arrows)
                    prior_graph_active_edge.update(node_prior_graph_active_edge)
                    prior_graph_nodes.update(node_prior_graph_nodes)

        prior_arrow_ids = []
        prior_arrow_txt_ids = []
        for key in prior_arrows:
            prior_arrow_ids.append(prior_arrows[key])
            prior_arrow_txt_ids.append(prior_arrows[key]-1)
        prior_node_ids = []
        prior_node_txt_ids = []
        for key in prior_canvas:
            if (key in prior_arrow_ids) or (key in prior_arrow_txt_ids):
                continue
            if key % 2 == 0:
                prior_node_txt_ids.append(key)
            else:
                prior_node_ids.append(key)
        prior_arrow_ids = sorted(prior_arrow_ids)
        prior_arrow_txt_ids = sorted(prior_arrow_txt_ids)
        prior_node_ids = sorted(prior_node_ids)
        prior_node_txt_ids = sorted(prior_node_txt_ids)
        new_node_ids = []
        new_node_txt_ids = []
        new_arrow_ids = []
        new_arrow_txt_ids = []
        offset = 0
        for i in range(1, len(prior_node_ids)+1):
            new_node_ids.append(i+offset)
            new_node_txt_ids.append(i+offset+1)
            offset += 1
        offset = len(new_node_ids)*2
        for i in range(1, len(prior_arrow_ids)+1):
            new_arrow_txt_ids.append(i+offset)
            new_arrow_ids.append(i+offset+1)
            offset += 1

        old_new_ref = {}
        for i in range(0, len(prior_arrow_ids)):
            old_new_ref[prior_arrow_ids[i]] = new_arrow_ids[i]
        for i in range(0, len(prior_arrow_txt_ids)):
            old_new_ref[prior_arrow_txt_ids[i]] = new_arrow_txt_ids[i]
        for i in range(0, len(prior_node_ids)):
            old_new_ref[prior_node_ids[i]] = new_node_ids[i]
        for i in range(0, len(prior_node_txt_ids)):
            old_new_ref[prior_node_txt_ids[i]] = new_node_txt_ids[i]

        new_canvas = {}
        new_arrows = {}
        for key in prior_arrows:
            source, sink = key.split('|')
            arrow = prior_arrows[key]
            new_source = old_new_ref[int(source)]
            new_sink = old_new_ref[int(sink)]
            new_arrow = old_new_ref[arrow]
            new_key = str(new_source)+'|'+str(new_sink)
            new_arrows[new_key] = new_arrow

        if not state and not groupcanvas and not rearrange:
            self.root.update_idletasks() # allows geometry check later, only after start

        for i in prior_arrow_ids:
            id_dict = prior_canvas[i]
            source, sink = id_dict['pair']
            obj_id = id_dict['object_id']
            text = id_dict['text']
            txt_id = id_dict['text_id']
            new_key = old_new_ref[i]
            new_source = old_new_ref[source]
            new_sink = old_new_ref[sink]
            new_obj_id = old_new_ref[obj_id]
            new_txt_id = old_new_ref[txt_id]
            new_canvas[new_key] = {'object_id':new_obj_id, 'text_id':new_txt_id, 'pair':[new_source, new_sink], 'text':text}
        for i in prior_arrow_txt_ids:
            id_dict = prior_canvas[i]
            obj_id = id_dict['object_id']
            txt_id = id_dict['text_id']
            new_key = old_new_ref[i]
            new_obj_id = old_new_ref[obj_id]
            new_txt_id = old_new_ref[txt_id]
            new_canvas[new_key] = {'object_id':new_obj_id, 'text_id':new_txt_id}
        for i in prior_node_txt_ids:
            id_dict = prior_canvas[i]
            obj_id = id_dict['object_id']
            txt_id = id_dict['text_id']
            new_key = old_new_ref[i]
            new_obj_id = old_new_ref[obj_id]
            new_txt_id = old_new_ref[txt_id]
            dimensions = id_dict['dimensions']
            new_canvas[new_key] = {'object_id':new_obj_id, 'text_id':new_txt_id, 'dimensions':dimensions}
        for i in prior_node_ids:
            id_dict = prior_canvas[i]
            obj_id = id_dict['object_id']
            txt_id = id_dict['text_id']
            arrows_start = id_dict['arrow_ids_start']
            arrows_end = id_dict['arrow_ids_end']
            new_arrows_start = []
            new_arrows_end = []
            if len(arrows_start) > 0:
                for item in arrows_start:
                    new_item = old_new_ref[item]
                    new_arrows_start.append(new_item)
            if len(arrows_end) > 0:
                for item in arrows_end:
                    new_item = old_new_ref[item]
                    new_arrows_end.append(new_item)
            start_pair_dict = id_dict['pair_dict_start']
            end_pair_dict = id_dict['pair_dict_end']
            new_start_pair_dict = {}
            new_end_pair_dict = {}
            if len(start_pair_dict) > 0:
                for key in start_pair_dict:
                    source, sink = start_pair_dict[key]
                    new_key = old_new_ref[key]
                    new_source = old_new_ref[source]
                    new_sink = old_new_ref[sink]
                    new_start_pair_dict[new_key] = [new_source, new_sink]
            if len(end_pair_dict) > 0:
                for key in end_pair_dict:
                    source, sink = end_pair_dict[key]
                    new_key = old_new_ref[key]
                    new_source = old_new_ref[source]
                    new_sink = old_new_ref[sink]
                    new_end_pair_dict[new_key] = [new_source, new_sink]
            new_key = old_new_ref[i]
            new_obj_id = old_new_ref[obj_id]
            new_txt_id = old_new_ref[txt_id]
            text = id_dict['text']
            value = id_dict['value']
            dimensions = list(id_dict['dimensions'])
            if not rearrange and not groupcanvas and not state:
                if dimensions[2] > self.canvas_tab_dict[tab]['object'].winfo_width() or dimensions[3] > self.canvas_tab_dict[tab]['object'].winfo_height():
                    rearrange = True
                    print('Canvas too small to load as planned. Automatically rearranging nodes.')
            group_obj = id_dict['group_obj']
            new_canvas[new_key] = {'object_id':new_obj_id, 'text_id':new_txt_id, 'text':text, 'value':value, 'dimensions':dimensions,
                                   'arrow_ids_start':new_arrows_start, 'arrow_ids_end':new_arrows_end, 'pair_dict_start':new_start_pair_dict,
                                   'pair_dict_end':new_end_pair_dict, 'canvas':str(tab), 'group_obj':group_obj}

        new_graph_active_edge = {}
        for key in prior_graph_active_edge:
            new_key = old_new_ref[key]
            new_list = []
            for item in prior_graph_active_edge[key]:
                new_item = old_new_ref[item]
                new_list.append(new_item)
            new_graph_active_edge[new_key] = new_list

        active_nodes = []
        for key in prior_graph_nodes:
            new_key = old_new_ref[key]
            old_node = prior_graph_nodes.get(key)
            type = old_node.type
            params = old_node.params
            learned_params = old_node.learned_params
            status = old_node.status
            group = old_node.group
            self.graph_dict[tab].addNode(Node(new_key, type=type, params=params, learned_params=learned_params, status=status, group=group))
            if status == True:
                active_nodes.append(new_key)

        active_edges = []
        for key in new_graph_active_edge:
            edge_list = new_graph_active_edge[key]
            if len(edge_list) == 0:
                continue
            for item in edge_list:
                pair = str(key)+'|'+str(item)
                arrow_id = new_arrows[pair]
                active_edges.append(arrow_id)

        self.canvas_dict[tab] = new_canvas
        self.arrow_dict[tab] = new_arrows

        for arrow_txt_id in new_arrow_txt_ids:
            arrow_id = self.canvas_dict[tab][arrow_txt_id]['object_id']
            source, sink = self.canvas_dict[tab][arrow_id]['pair']
            self.graph_dict[tab].addEdge(Edge(source, sink))

        if rearrange or groupcanvas:
            orphaned_nodes = []
            x1_s, y1_s, x2_s, y2_s = [10, 10, self.default_node_width+10, self.default_node_height+10]
            self.root.update_idletasks() # allows geometry
            x2_limit = int(code_canvas.winfo_width())
            y2_limit = int(code_canvas.winfo_height())
            topo_sort, expanded_topo_sort = self.graph_dict[tab].topologicalSort()
            for i in topo_sort:
                if len(expanded_topo_sort[i]['next']) == 0 and len(expanded_topo_sort[i]['prior']) == 0:
                    orphaned_nodes.append(i)
                else:
                    node_key = i
                    text_key = i+1
                    node_dimensions = [x1_s, y1_s, x2_s, y2_s]
                    text_dimensions = [int((x1_s+x2_s)//2), int((y1_s+y2_s)//2)]
                    new_canvas[node_key]['dimensions'] = list(node_dimensions)
                    new_canvas[text_key]['dimensions'] = list(text_dimensions)
                    if y2_s+65 > y2_limit:
                        x1_s, y1_s, x2_s, y2_s = [x1_s+(x2_s-x1_s)+10, 10, x2_s+(x2_s-x1_s)+10, 55]
                    else:
                        x1_s += 0
                        y1_s += 65
                        x2_s += 0
                        y2_s += 65
            for i in orphaned_nodes:
                node_key = i
                text_key = i+1
                node_dimensions = [x1_s, y1_s, x2_s, y2_s]
                text_dimensions = [int((x1_s+x2_s)//2), int((y1_s+y2_s)//2)]
                new_canvas[node_key]['dimensions'] = list(node_dimensions)
                new_canvas[text_key]['dimensions'] = list(text_dimensions)
                if y2_s+65 > y2_limit:
                    x1_s, y1_s, x2_s, y2_s = [x1_s+(x2_s-x1_s)+10, 10, x2_s+(x2_s-x1_s)+10, 55]
                else:
                    x1_s += 0
                    y1_s += 65
                    x2_s += 0
                    y2_s += 65

        self.populate_new_canvas(new_node_ids, new_node_txt_ids, new_arrow_txt_ids, new_arrow_ids, active_nodes, active_edges, tab, clipboard, code_canvas)

    def populate_new_canvas(self, new_node_ids, new_node_txt_ids, new_arrow_txt_ids, new_arrow_ids, active_nodes, active_edges, tab, clipboard, code_canvas):

        for obj_id in new_node_ids:
            x1, y1, x2, y2 = self.canvas_dict[tab][obj_id]['dimensions']
            text = self.canvas_dict[tab][obj_id]['text']
            text_id = self.canvas_dict[tab][obj_id]['text_id']
            if obj_id not in active_nodes:
                fill = '#EEA4A4'
            elif 'subgraph' in self.graph_dict[tab].nodes.get(obj_id).params: # allows group in group, can't be moved out
                fill = 'gold'
            elif self.canvas_dict[tab][obj_id]['group_obj'] == None:
                fill = '#d9d9d9'
            else:
                fill = 'gold'
            new_obj = code_canvas.create_rectangle(x1+1, y1+1, x2-1, y2-1, fill=fill, tags=('node',))
            x1, y1 = self.canvas_dict[tab][text_id]['dimensions']
            new_text = code_canvas.create_text(x1, y1, text=text, fill='black', tags=('node',))

        for arrow_txt_id in new_arrow_txt_ids:
            arrow_id = self.canvas_dict[tab][arrow_txt_id]['object_id']
            arrow_text = self.canvas_dict[tab][arrow_id]['text']
            if arrow_id in active_edges:
                arrow_fill = 'green'
            else:
                arrow_fill = 'red'
            source, sink = self.canvas_dict[tab][arrow_id]['pair']
            x1, y1, x2, y2 = self.canvas_dict[tab][source]['dimensions']
            width = x2-x1
            height = y2-y1
            if height > width:
                arrow_width = width//3
            else:
                arrow_width = height//3
            center_x1 = (x1+x2)//2
            center_y1 = (y1+y2)//2
            x1, y1, x2, y2 = self.canvas_dict[tab][sink]['dimensions']
            center_x2 = (x1+x2)//2
            center_y2 = (y1+y2)//2
            line_length = int(math.hypot(center_x2 - center_x1, center_y2 - center_y1))
            new_text = code_canvas.create_text((center_x2+center_x1)//2, (center_y2+center_y1)//2, text=str(arrow_text), fill='black', font=('Arial', 16))
            code_canvas.itemconfig(new_text, tags=('arrow',))
            code_canvas.tag_raise(new_text)
            new_arrow = code_canvas.create_line(center_x1, center_y1, center_x2, center_y2, arrow='last', arrowshape=[line_length,line_length,arrow_width],
                                                  fill=arrow_fill, tags=('arrow',))
            code_canvas.tag_lower(new_arrow)
            #self.graph_dict[tab].addEdge(Edge(source, sink)) # moved to earlier
            if arrow_id not in active_edges:
                self.graph_dict[tab].editEdge(Edge(source, sink), activity=True)
        if clipboard:
            self.notebookTb.update_state()
            self.update_state()
            self.clipboard.add(self.state.export())

    def import_model(self, filename=None):
        if not filename:
            self.command_lock = 'compile'
            filename = filedialog.askopenfilename(title = 'Choose model for import...', filetypes = (("LuaTorch","*.net"), \
                                                    ("PyTorch Model", "*.pth"), ("ONNX model","*.onnx"), ("Sketch File","*.sk"), ))
        if not filename:
            print('Cancelled')
            self.command_release('compile')
            return
        self.command_release('compile')
        if filename.endswith('.sk'):
            with open(filename, 'rb') as save_file:
                graph = pickle.load(save_file)
            self.load_canvas(state=True, state_obj=graph) # reroutes to prevent attribute error
        else:
            if filename.endswith('.net'):
                binder = Binder("LuaTorch")
            elif filename.endswith('.pth'):
                binder = Binder("PyTorch")
            elif filename.endswith('.onnx'):
                binder = Binder("ONNX")
            graph = binder.importModel(filename)
            graph.display()
            self.import_from_model(graph, str(binder))

    def import_from_model(self, imported_graph_obj, binder=None):
        self.create_canvas()
        tab = self.canvas_tabs.select()
        graph = self.graph_dict[tab]
        tab_text = 'Imported Model'
        self.canvas_tabs.tab(tab, text=tab_text)
        self.canvas_tab_dict[tab]['name'] = tab_text
        code_canvas = self.canvas_tab_dict[tab]['object']
        code_canvas.update_idletasks() # allows geometry calls

        key_list = []                   # create new nodes
        prior_nodes = imported_graph_obj.nodes
        for key in prior_nodes:
            key_list.append(key)
        key_list = self.true_sort(key_list, model=True)
        old_new_ref = {}
        new_key_obj_ref = {}
        id_count = 1
        group_id_count = 1
        group_id_trip = 0
        group_id_max_list = []
        group_id_set = set()

        if binder == 'ONNX':
            for key in key_list:
                if '_' not in key:
                    if group_id_trip == 1:
                        group_id_set.add(key)
                        group_id_max_list.append(group_id_count-2)
                        group_id_count = 1
                    old_new_ref[key] = id_count
                    id_count += 2
                else:
                    group_id_trip = 1
                    old_new_ref[key] = group_id_count # add group ids to same ref
                    group_id_count += 2
        else:
            for key in key_list:
                old_new_ref[key] = id_count
                id_count += 2

        x1_s, y1_s, x2_s, y2_s = [10, 10, self.default_node_width+10, self.default_node_height+10]
        x2_limit = int(code_canvas.winfo_width())
        y2_limit = int(code_canvas.winfo_height())

        if binder == 'ONNX':
            # sets up necessary vars
            x1_s_node, y1_s_node, x2_s_node, y2_s_node = [10, 10, self.default_node_width+10, self.default_node_height+10]
            x2_limit_node = int(self.group_canvas.winfo_width())
            y2_limit_node = int(self.group_canvas.winfo_height())
            node_canvas_dict = {}
            node_canvas_arrows = {}
            node_graph_obj = Graph()
            internal_count = 0
            group_id_list = []
            for key in key_list:
                new_key = old_new_ref[key]
                if key not in group_id_set and '_' not in key:
                    fill = '#d9d9d9'
                    prior_node = prior_nodes.get(key)
                    type = prior_node.type
                    params = prior_node.params
                    learned_params = prior_node.learned_params
                    status = prior_node.status
                    value = prior_node.params
                    new_obj = code_canvas.create_rectangle(x1_s+1, y1_s+1, x2_s-1, y2_s-1, fill=fill, tags=('node',))
                    new_text = code_canvas.create_text(((x1_s+x2_s)//2), ((y1_s+y2_s)//2), text=str(type), fill='black', tags=('node',))
                    self.canvas_dict[tab][new_obj] = {'object_id':new_obj, 'text_id':new_text, 'text':str(type), 'value':value,
                                                      'pair_dict_start':{}, 'pair_dict_end':{}, 'arrow_ids_start':[], 'arrow_ids_end':[],
                                                      'dimensions':[x1_s, y1_s, x2_s, y2_s], 'canvas':tab, 'group_obj':None}
                    self.canvas_dict[tab][new_text] = {'object_id':new_obj, 'text_id':new_text, 'dimensions':[int((x1_s+x2_s)//2), int((y1_s+y2_s)//2)]}
                    self.graph_dict[tab].addNode(Node(new_key, type=type, params=params, learned_params=learned_params, status=status))
                    new_key_obj_ref[new_key] = new_obj
                    if y2_s+65 > y2_limit:
                        x1_s, y1_s, x2_s, y2_s = [x1_s+(x2_s-x1_s)+10, 10, x2_s+(x2_s-x1_s)+10, 55]
                    else:
                        x1_s += 0
                        y1_s += 65
                        x2_s += 0
                        y2_s += 65
                elif '_' in key:
                    prior_node = prior_nodes.get(key)
                    type = prior_node.type
                    params = prior_node.params
                    learned_params = prior_node.learned_params
                    status = prior_node.status
                    value = prior_node.params
                    node_canvas_dict[new_key] = {'object_id':new_key, 'text_id':new_key+1, 'text':str(type), 'value':value,
                                                 'pair_dict_start':{}, 'pair_dict_end':{}, 'arrow_ids_start':[], 'arrow_ids_end':[],
                                                 'dimensions':[x1_s_node, y1_s_node, x2_s_node, y2_s_node], 'canvas':None, 'group_obj':None}
                    node_canvas_dict[new_key+1] = {'object_id':new_key, 'text_id':new_key+1, 'dimensions':[int((x1_s_node+x2_s_node)//2),
                                                   int((y1_s_node+y2_s_node)//2)]}
                    node_graph_obj.addNode(Node(new_key, type=type, params=params, learned_params=learned_params, status=status))
                    if y2_s_node+65 > y2_limit_node:
                        x1_s_node, y1_s_node, x2_s_node, y2_s_node = [x1_s_node+(x2_s_node-x1_s_node)+10, 10, x2_s_node+(x2_s_node-x1_s_node)+10, 55]
                    else:
                        x1_s_node += 0
                        y1_s_node += 65
                        x2_s_node += 0
                        y2_s_node += 65
                    group_id_list.append(new_key)
                    internal_count += 2
                elif key in group_id_set: # packs the current group node set, resets for next set
                    internal_count += 1 # set up count for first arrow text (arrow id is internal_count+1)
                    node_arrow_list = []
                    arrow_pair_dict = {}
                    for key in group_id_list: # set up edge pairs
                        if key == group_id_list[-1]:
                            continue
                        source = str(key)
                        sink = str(key+2)
                        pair = '|'.join([source, sink])
                        node_canvas_arrows[pair] = int(internal_count+1)
                        node_arrow_list.append(int(internal_count+1))
                        arrow_pair_dict[int(internal_count+1)] = pair
                        internal_count += 2
                    for arrow_id in node_arrow_list: # add edge obj
                        text_id = arrow_id-1
                        source, sink =  arrow_pair_dict[arrow_id].split('|')
                        source = int(source)
                        sink = int(sink)
                        node_canvas_dict[text_id] = {'object_id':arrow_id, 'text_id':text_id} # add edge to canvas dict
                        node_canvas_dict[arrow_id] = {'object_id':arrow_id, 'text_id':text_id, 'pair':[source, sink], 'text':' '}
                        node_graph_obj.addEdge(Edge(source, sink)) # add edge to graph
                    for pair in node_canvas_arrows: # edit source/sink in node_canvas_dict
                        arrow_id = node_canvas_arrows[pair]
                        source, sink =  pair.split('|')
                        source = int(source)
                        sink = int(sink)
                        node_canvas_dict[source]['arrow_ids_start'].append(arrow_id)
                        node_canvas_dict[source]['pair_dict_start'][arrow_id] = [source, sink]
                        node_canvas_dict[sink]['arrow_ids_end'].append(arrow_id)
                        node_canvas_dict[sink]['pair_dict_end'][arrow_id] = [source, sink]
                    # compile save obj
                    node_graph_active_edge = dict(node_graph_obj.activeEdgeList)
                    node_graph_nodes = dict(node_graph_obj.nodes)
                    save_obj = Save('Sequential', dict(node_canvas_dict), dict(node_canvas_arrows), node_graph_active_edge, node_graph_nodes, node_graph_obj)
                    # add completed group node
                    fill = 'gold'
                    new_obj = code_canvas.create_rectangle(x1_s+1, y1_s+1, x2_s-1, y2_s-1, fill=fill, tags=('node',))
                    new_text = code_canvas.create_text(((x1_s+x2_s)//2), ((y1_s+y2_s)//2), text='Sequential', fill='black', tags=('node',))
                    self.canvas_dict[tab][new_obj] = {'object_id':new_obj, 'text_id':new_text, 'text':'Sequential', 'value':{},
                                                      'pair_dict_start':{}, 'pair_dict_end':{}, 'arrow_ids_start':[], 'arrow_ids_end':[],
                                                      'dimensions':[x1_s, y1_s, x2_s, y2_s], 'canvas':tab, 'group_obj':save_obj}
                    self.canvas_dict[tab][new_text] = {'object_id':new_obj, 'text_id':new_text, 'dimensions':[int((x1_s+x2_s)//2), int((y1_s+y2_s)//2)]}
                    self.graph_dict[tab].addNode(Node(new_key, type='Sequential', params={'subgraph':deepcopy(node_graph_obj)}, learned_params={}, status=True, group=True))
                    new_key_obj_ref[new_key] = new_obj
                    # resets start vars
                    x1_s_node, y1_s_node, x2_s_node, y2_s_node = [10, 10, self.default_node_width+10, self.default_node_height+10]
                    x2_limit_node = int(self.group_canvas.winfo_width())
                    y2_limit_node = int(self.group_canvas.winfo_height())
                    node_canvas_dict = {}
                    node_canvas_arrows = {}
                    node_graph_obj = Graph()
                    internal_count = 0
                    group_id_list = []
        else:        # look for sequentials for pytorch/lua on fly, make canvas obj at same time as adding node since no need to worry about outside edges
            for key in key_list:
                new_key = old_new_ref[key]
                prior_node = prior_nodes.get(key)
                type = prior_node.type
                params = prior_node.params
                if 'subgraph' in params:
                    fill = 'gold'
                else:
                    fill = '#d9d9d9'
                learned_params = prior_node.learned_params
                status = prior_node.status
                value = prior_node.params
                new_obj = code_canvas.create_rectangle(x1_s+1, y1_s+1, x2_s-1, y2_s-1, fill=fill, tags=('node',))
                new_text = code_canvas.create_text(((x1_s+x2_s)//2), ((y1_s+y2_s)//2), text=str(type), fill='black', tags=('node',))
                self.canvas_dict[tab][new_obj] = {'object_id':new_obj, 'text_id':new_text, 'text':str(type), 'value':value,
                                                  'pair_dict_start':{}, 'pair_dict_end':{}, 'arrow_ids_start':[], 'arrow_ids_end':[],
                                                  'dimensions':[x1_s, y1_s, x2_s, y2_s], 'canvas':tab, 'group_obj':None}
                self.canvas_dict[tab][new_text] = {'object_id':new_obj, 'text_id':new_text, 'dimensions':[int((x1_s+x2_s)//2), int((y1_s+y2_s)//2)]}
                self.graph_dict[tab].addNode(Node(new_key, type=type, params=params, learned_params=learned_params, status=status))
                new_key_obj_ref[new_key] = new_obj
                if y2_s+65 > y2_limit:
                    x1_s, y1_s, x2_s, y2_s = [x1_s+(x2_s-x1_s)+10, 10, x2_s+(x2_s-x1_s)+10, 55]
                else:
                    x1_s += 0
                    y1_s += 65
                    x2_s += 0
                    y2_s += 65
                if 'subgraph' in params:
                    # establishes start vars
                    x1_s_node, y1_s_node, x2_s_node, y2_s_node = [10, 10, self.default_node_width+10, self.default_node_height+10]
                    x2_limit_node = int(self.group_canvas.winfo_width())
                    y2_limit_node = int(self.group_canvas.winfo_height())
                    node_canvas_dict = {}
                    node_canvas_arrows = {}
                    node_old_new_ref = {}
                    node_graph_obj = Graph()
                    internal_count = 0
                    node_arrow_list = []
                    arrow_pair_dict = {}

                    graph_obj = params['subgraph']
                    node_prior_nodes = graph_obj.nodes
                    topo_sort, expanded_topo_sort = graph_obj.topologicalSort()
                    for id in topo_sort:                    # set up conversion dict
                        internal_count += 1
                        node_old_new_ref[id] = internal_count
                        internal_count += 1
                    internal_count += 1 # index for first arrow text
                    for id in topo_sort:
                        new_id = node_old_new_ref[id]
                        node_prior_node = node_prior_nodes.get(id)
                        type = node_prior_node.type
                        params = node_prior_node.params
                        learned_params = node_prior_node.learned_params
                        status = node_prior_node.status
                        value = node_prior_node.params
                        node_canvas_dict[new_id] = {'object_id':new_id, 'text_id':new_id+1, 'text':str(type), 'value':value,
                                                     'pair_dict_start':{}, 'pair_dict_end':{}, 'arrow_ids_start':[], 'arrow_ids_end':[],
                                                     'dimensions':[x1_s_node, y1_s_node, x2_s_node, y2_s_node], 'canvas':None, 'group_obj':None}
                        node_canvas_dict[new_id+1] = {'object_id':new_id, 'text_id':new_id+1, 'dimensions':[int((x1_s_node+x2_s_node)//2),
                                                       int((y1_s_node+y2_s_node)//2)]}
                        node_graph_obj.addNode(Node(new_id, type=type, params=params, learned_params=learned_params, status=status))
                        if y2_s_node+65 > y2_limit_node:
                            x1_s_node, y1_s_node, x2_s_node, y2_s_node = [x1_s_node+(x2_s_node-x1_s_node)+10, 10, x2_s_node+(x2_s_node-x1_s_node)+10, 55]
                        else:
                            x1_s_node += 0
                            y1_s_node += 65
                            x2_s_node += 0
                            y2_s_node += 65
                    for i in range(0, len(topo_sort)): # set up edge pairs
                        if i == len(topo_sort)-1:
                            continue
                        orig_source = topo_sort[i]
                        orig_sink = topo_sort[i+1]
                        new_source = node_old_new_ref[orig_source]
                        new_sink = node_old_new_ref[orig_sink]
                        pair = '|'.join([str(new_source), str(new_sink)])
                        node_canvas_arrows[pair] = int(internal_count+1)
                        node_arrow_list.append(int(internal_count+1))
                        arrow_pair_dict[int(internal_count+1)] = pair
                        internal_count += 2
                    for arrow_id in node_arrow_list: # add edge obj
                        text_id = arrow_id-1
                        source, sink =  arrow_pair_dict[arrow_id].split('|')
                        source = int(source)
                        sink = int(sink)
                        node_canvas_dict[text_id] = {'object_id':arrow_id, 'text_id':text_id} # add edge to canvas dict
                        node_canvas_dict[arrow_id] = {'object_id':arrow_id, 'text_id':text_id, 'pair':[source, sink], 'text':' '}
                        node_graph_obj.addEdge(Edge(source, sink)) # add edge to graph
                    for pair in node_canvas_arrows: # edit source/sink in node_canvas_dict
                        arrow_id = node_canvas_arrows[pair]
                        source, sink =  pair.split('|')
                        source = int(source)
                        sink = int(sink)
                        node_canvas_dict[source]['arrow_ids_start'].append(arrow_id)
                        node_canvas_dict[source]['pair_dict_start'][arrow_id] = [source, sink]
                        node_canvas_dict[sink]['arrow_ids_end'].append(arrow_id)
                        node_canvas_dict[sink]['pair_dict_end'][arrow_id] = [source, sink]
                    # compile save obj
                    node_graph_active_edge = dict(node_graph_obj.activeEdgeList)
                    node_graph_nodes = dict(node_graph_obj.nodes)
                    save_obj = Save('Sequential', dict(node_canvas_dict), dict(node_canvas_arrows), node_graph_active_edge, node_graph_nodes, node_graph_obj)
                    # edit group node
                    self.canvas_dict[tab][new_obj]['group_obj'] = save_obj
                    self.graph_dict[tab].editNode(new_obj, params={'subgraph':deepcopy(node_graph_obj)}, group=True)

        if x2_s > x2_limit:
            print('Nodes out of immediately visible boundary.\nSuggested expand workspace and re-import model.')

        code_canvas.update_idletasks()  # allows arrow geometry calls for edges
        prior_edges = imported_graph_obj.activeEdgeList  # determine edge ids
        new_edges = {}
        arrow_id_list = []

        # reroute any edges from internal nodes to parent group node (for ONNX), else make edges
        for key in prior_edges:
            if '_' in key and binder == 'ONNX':
                continue
            new_key = old_new_ref[key]
            new_list = []
            for item in prior_edges[key]:
                if '_' in item and binder == 'ONNX':
                    item = item.split('_')[0]
                new_item = old_new_ref[item]
                if new_item not in new_list:
                    new_list.append(new_item)
            new_edges[new_key] = new_list
        for key in new_edges:
            source = key
            sink_list = new_edges[key]
            for sink in sink_list:
                text_id = id_count
                arrow_id = id_count+1
                key_str = str(source)+'|'+str(sink)
                self.arrow_dict[tab][key_str] = arrow_id     # arrow dict updated
                arrow_id_list.append(arrow_id)
                self.canvas_dict[tab][new_key_obj_ref[source]]['arrow_ids_start'].append(arrow_id)     # linked objs updated
                self.canvas_dict[tab][new_key_obj_ref[source]]['pair_dict_start'][arrow_id] = [source, sink]
                self.canvas_dict[tab][new_key_obj_ref[sink]]['arrow_ids_end'].append(arrow_id)
                self.canvas_dict[tab][new_key_obj_ref[sink]]['pair_dict_end'][arrow_id] = [source, sink]
                # create arrow
                x1, y1, x2, y2 = code_canvas.bbox(source)
                width = x2-x1
                height = y2-y1
                if height > width:
                    arrow_width = width//3
                else:
                    arrow_width = height//3
                center_x1 = (x1+x2)//2
                center_y1 = (y1+y2)//2
                x1, y1, x2, y2 = code_canvas.bbox(sink)
                center_x2 = (x1+x2)//2
                center_y2 = (y1+y2)//2
                line_length = int(math.hypot(center_x2 - center_x1, center_y2 - center_y1))
                new_text = code_canvas.create_text((center_x2+center_x1)//2, (center_y2+center_y1)//2, text=' ', fill='black', font=('Arial', 16))
                code_canvas.itemconfig(new_text, tags=('arrow',))
                code_canvas.tag_raise(new_text)
                new_arrow = code_canvas.create_line(center_x1, center_y1, center_x2, center_y2, arrow='last', arrowshape=[line_length,line_length,arrow_width],
                                                     fill='green', tags=('arrow',))
                code_canvas.tag_lower(new_arrow)
                self.canvas_dict[tab][new_arrow] = {'object_id':new_arrow, 'text_id':new_text, 'pair':[source, sink], 'text':' '}
                self.canvas_dict[tab][new_text] = {'object_id':new_arrow, 'text_id':new_text}
                self.graph_dict[tab].addEdge(Edge(source, sink))
                id_count += 2

        # rearrange everything once done, just in case ids used cause issue
        self.save_as_canvas(rearrange=True)

        self.notebookTb.update_state()
        self.update_state()
        self.clipboard.add(self.state.export())

    def update_choices(self, event, choice_cell, choice_scroll):
        choice_cell.configure(scrollregion=choice_cell.bbox("all"))

    def mousewheel(self, event, choice_cell, direction):
        if not hasattr(event.widget, 'optiontag'):
            return
        x1, y1, x2, y2 = choice_cell.bbox("all")
        if int(y2) < int(choice_cell.winfo_height()):
            choice_cell.yview_moveto('0.0')
            return
        if direction == 'up':
            choice_cell.yview_scroll(-1, "units")
        else:
            choice_cell.yview_scroll(1, "units")

    def click_node(self, event):
        if event.widget == self.group_canvas:
            tab = self.group_canvas
            canvas = self.group_canvas
        else:
            tab = self.canvas_tabs.select()
            canvas = self.canvas_tab_dict[self.canvas_tabs.select()]['object']

        if self.command_lock == 'link':
            self.link_objects(event, canvas)
            return

        tags = canvas.itemcget(canvas.find_withtag(CURRENT), 'tags')
        if 'node' not in tags:
            return

        try:
            obj = self.canvas_dict[tab][canvas.find_withtag(CURRENT)[0]]['object_id']
        except:
            return
        x1, y1, x2, y2 = canvas.coords(obj)
        node_w = abs(x2)-abs(x1)
        node_h = abs(y2)-abs(y1)
        interior_w = float(int((1/10)*node_w))
        interior_h = float(int((1/5)*node_h))
        if (event.x <= x1+interior_w) or (event.x >= x2-interior_w) or (event.y <= y1+interior_h) or (event.y >= y2-interior_h):
            self.link_objects(event, canvas)
        else:
            self.drag_current(event, 'current-start')

    def select_object(self, event, canvas, obj=None):
        if canvas == self.group_canvas:
            tab = self.group_canvas
        else:
            tab = self.canvas_tabs.select()

        if self.select_tab != None:
            if self.select_tab != tab:
                if tab == self.group_canvas:
                    self.reset_selected(event, skipgroup=True)
                else:
                    self.reset_selected(event)

        self.select_tab = tab
        self.select_canvas = canvas
        if not obj:
            obj = self.canvas_dict[tab][canvas.find_withtag(CURRENT)[0]]['object_id']
        tags = canvas.itemcget(obj, 'tags')
        if 'node' in tags:
            if obj not in self.select_node_set:
                self.select_node_set.add(obj)
                canvas.itemconfig(obj, fill='#3399FF')
            else:
                self.set_active_node(event, canvas, node=obj, refresh=True) # calls twice to reset activity, removes from set
                self.set_active_node(event, canvas, node=obj, refresh=True)
        elif 'arrow' in tags:
            if obj not in self.select_edge_set:
                self.select_edge_set.add(obj)
                canvas.itemconfig(obj, fill='#99CCFF')
            else:
                self.set_active_arrow(event, canvas, arrow=obj) # calls twice to reset activity, removes from set
                self.set_active_arrow(event, canvas, arrow=obj)

        if len(self.select_node_set) == 0 and len(self.select_edge_set) == 0: # resets select_tab and select_canvas
            self.select_tab = None
            self.select_canvas = None

    def delete_selected(self, event):
        if self.select_canvas == None:
            return
        node_list = list(self.select_node_set)
        edge_list = list(self.select_edge_set)
        for obj in node_list:
            try:
                self.delete_current(event, self.select_canvas, id=obj, clipboard=False)
            except:
                pass
        for obj in edge_list:
            try:
                self.delete_current(event, self.select_canvas, id=obj, clipboard=False)
            except:
                pass
        self.select_canvas = None
        self.select_tab = None
        self.select_node_set = set()
        self.select_edge_set = set()
        self.notebookTb.update_state()
        self.update_state()
        self.clipboard.add(self.state.export())

    def group_selected(self, event):
        if self.command_lock != None:
            return

        if self.select_canvas == None:
            self.new_group()
            return
        elif self.select_canvas == self.group_canvas:
            print('Cannot group nodes inside a group.')
            self.reset_selected(event, skipgroup=False)
            return
        node_list = list(self.select_node_set)
        edge_list = list(self.select_edge_set)
        if len(node_list) == 0:
            return
        for node in node_list:
            if self.canvas_dict[self.canvas_tabs.select()][node]['group_obj'] != None:
                print('Group selected! Cannot add group nodes to group.')
                self.reset_selected(event, skipgroup=False)
                return

        temp_graph_obj = Graph()
        temp_saved_canvas = {}
        temp_saved_arrows = {}
        prior_arrows = self.arrow_dict[self.canvas_tabs.select()]
        prior_graph_nodes = self.graph_dict[self.canvas_tabs.select()].nodes
        coordinates_raw = []

        for node_key in node_list:
            node_dict = dict(self.canvas_dict[self.canvas_tabs.select()][node_key])
            text_key = node_dict['text_id']
            text_dict = dict(self.canvas_dict[self.canvas_tabs.select()][text_key])
            node_dict['arrow_ids_start'] = []
            node_dict['arrow_ids_end'] = []
            node_dict['pair_dict_start'] = {}
            node_dict['pair_dict_end'] = {}
            temp_saved_canvas[node_key] = dict(node_dict)
            temp_saved_canvas[text_key] = dict(text_dict)
            coordinates_raw.append(list(node_dict['dimensions']))
        for edge_pair in prior_arrows:
            source, sink = edge_pair.split('|')
            source = int(source)
            sink = int(sink)
            if source in temp_saved_canvas and sink in temp_saved_canvas:
                temp_saved_arrows[edge_pair] = prior_arrows[edge_pair]
                edge_key = prior_arrows[edge_pair]
                edge_dict = dict(self.canvas_dict[self.canvas_tabs.select()][edge_key])
                edge_text_key = edge_dict['text_id']
                edge_text_dict = dict(self.canvas_dict[self.canvas_tabs.select()][edge_text_key])
                temp_saved_canvas[edge_key] = dict(edge_dict)
                temp_saved_canvas[edge_text_key] = dict(edge_text_dict)
                temp_saved_canvas[source]['arrow_ids_start'].append(edge_key)
                temp_saved_canvas[sink]['arrow_ids_end'].append(edge_key)
                temp_saved_canvas[source]['pair_dict_start'][edge_key] = [source, sink]
                temp_saved_canvas[sink]['pair_dict_end'][edge_key] = [source, sink]

        for key in node_list:
            old_node = prior_graph_nodes.get(key)
            type = old_node.type
            params = old_node.params
            learned_params = old_node.learned_params
            status = old_node.status
            group = old_node.group
            temp_graph_obj.addNode(Node(key, type=type, params=params, learned_params=learned_params, status=status, group=group))
        for edge_pair in temp_saved_arrows:
            source, sink = edge_pair.split('|')
            temp_graph_obj.addEdge(Edge(int(source), int(sink)))

        coordinates = [int(i) for i in list(map(mean, zip(*coordinates_raw)))]
        self.new_group(coordinates)

        temp_tab_text = self.canvas_dict[self.canvas_tabs.select()][self.selected_group_obj]['group_obj'].tab_text
        temp_saved_graph_active_edge = temp_graph_obj.activeEdgeList
        temp_saved_graph_nodes = temp_graph_obj.nodes

        save_obj = Save(temp_tab_text, temp_saved_canvas, temp_saved_arrows, temp_saved_graph_active_edge, temp_saved_graph_nodes, temp_graph_obj)

        self.load_group(save_obj, self.selected_group_obj)
        self.canvas_dict[self.canvas_tabs.select()][self.selected_group_obj]['group_obj'] = save_obj
        self.graph_dict[self.canvas_tabs.select()].editNode(self.selected_group_obj, params={'subgraph':deepcopy(temp_graph_obj)})

        for obj in node_list:
            self.set_active_node(event, self.select_canvas, node=obj, tab=self.select_tab, refresh=True) # calls twice to reset activity
            self.set_active_node(event, self.select_canvas, node=obj, tab=self.select_tab, refresh=True)
        for obj in edge_list:
            self.set_active_arrow(event, self.select_canvas, arrow=obj, tab=self.select_tab) # calls twice to reset activity
            self.set_active_arrow(event, self.select_canvas, arrow=obj, tab=self.select_tab)

        self.select_node_set = list(node_list)
        self.delete_selected(event)

    def activity_selected(self, event, activity):
        if self.select_canvas != None:
            node_list = list(self.select_node_set)
            edge_list = list(self.select_edge_set)
            for obj in node_list:
                self.set_active_node(event, self.select_canvas, node=obj, tab=self.select_tab, forceactivity=activity)
            for obj in edge_list:
                self.set_active_arrow(event, self.select_canvas, arrow=obj, tab=self.select_tab, forceactivity=activity)
        self.select_canvas = None
        self.select_tab = None
        self.select_node_set = set()
        self.select_edge_set = set()

    def reset_selected(self, event, skipgroup=False):
        try:
            prior_group_canvas = self.group_canvas
            if not skipgroup:
                if self.group_label['text'] != 'Group Canvas (Inactive)':
                    self.create_group_canvas()
            if self.select_canvas != None:
                if (self.select_canvas != prior_group_canvas) or skipgroup:
                    node_list = list(self.select_node_set)
                    edge_list = list(self.select_edge_set)
                    for obj in node_list:
                        self.set_active_node(event, self.select_canvas, node=obj, tab=self.select_tab, refresh=True) # calls twice to reset activity
                        self.set_active_node(event, self.select_canvas, node=obj, tab=self.select_tab, refresh=True)
                    for obj in edge_list:
                        self.set_active_arrow(event, self.select_canvas, arrow=obj, tab=self.select_tab) # calls twice to reset activity
                        self.set_active_arrow(event, self.select_canvas, arrow=obj, tab=self.select_tab)
        except:
            print('WARNING: error deselecting some objects. Deselect manually.') # prevents race condition error
        self.select_canvas = None
        self.select_tab = None
        self.select_node_set = set()
        self.select_edge_set = set()

    def create_canvas(self, clipboard=False):
        try:
            if self.group_label['text'] != 'Group Canvas (Inactive)':
                self.create_group_canvas()
        except:
            pass
        new_canvas = Canvas(self.canvas_tabs, bg='white')
        new_canvas.sandbox = 1
        new_canvas.active = 1 # always active
        tab_name = 'Canvas '+str(len(self.canvas_tabs.tabs())+1)
        self.canvas_tabs.add(new_canvas, text=tab_name)
        self.canvas_tabs.select(new_canvas)
        self.canvas_tab_dict.update({self.canvas_tabs.select():{'name':tab_name, 'object':new_canvas}})
        self.canvas_dict[self.canvas_tabs.select()] = {}
        self.arrow_dict[self.canvas_tabs.select()] = {}
        self.graph_dict[self.canvas_tabs.select()] = Graph()
        new_canvas.bind('<Double-Button-2>', lambda e: self.delete_current(e, new_canvas))
        new_canvas.bind('<Button-1>', lambda event: self.drag_select(event, new_canvas, 'current-drag'))
        new_canvas.bind('<B1-Motion>', lambda event: self.drag_select(event, new_canvas, 'current-drag'))
        new_canvas.bind('<ButtonRelease-1>', lambda event: self.drag_select(event, new_canvas, 'current-drop'))
        #new_canvas.tag_bind('node', '<Button-1>', lambda e: self.click_node(e, new_canvas))
        #new_canvas.tag_bind('node', '<B1-Motion>', lambda e: self.drag_current(e, new_canvas, 'current-drag'))
        #new_canvas.tag_bind('node', '<ButtonRelease-1>', lambda e: self.drag_current(e, new_canvas, 'current-drop'))
        new_canvas.tag_bind('node', '<Button-3>', lambda e: self.edit_node_value(e, new_canvas))
        new_canvas.tag_bind('node', '<Double-Button-3>', lambda e: self.change_box_label(e, new_canvas))
        new_canvas.tag_bind('node', '<Button-2>', lambda e: self.set_active_node(e, new_canvas))
        new_canvas.tag_bind('node', '<Enter>', lambda e: self.set_hover(e, new_canvas, 'enter'))
        new_canvas.tag_bind('node', '<Leave>', lambda e: self.set_hover(e, new_canvas, 'exit'))
        new_canvas.tag_bind('arrow', '<Button-1>', lambda e: self.select_object(e, new_canvas))
        new_canvas.tag_bind('arrow', '<Button-2>', lambda e: self.set_active_arrow(e, new_canvas))
        new_canvas.tag_bind('arrow', '<Double-Button-3>', lambda e: self.change_arrow_label(e, new_canvas))
        new_canvas.tag_bind('arrow', '<Enter>', lambda e: self.set_hover(e, new_canvas, 'enter'))
        new_canvas.tag_bind('arrow', '<Leave>', lambda e: self.set_hover(e, new_canvas, 'exit'))
        self.sync.add_obj(self.canvas_tabs.select())
        if clipboard:
            self.notebookTb.update_state()
            self.update_state()
            self.clipboard.add(self.state.export())

    def create_group_canvas(self, clipboard=False):
        if self.group_canvas != None:
            del self.canvas_dict[self.group_canvas]
            del self.arrow_dict[self.group_canvas]
            del self.graph_dict[self.group_canvas]
            self.group_canvas.pack_forget()
            self.group_canvas = None
        self.original_group_save = None
        self.selected_group_obj = None
        self.group_label.config(text='Group Canvas (Inactive)')
        self.group_canvas = Canvas(self.group_root, bg='white')
        self.group_canvas.group_sandbox = 1
        self.group_canvas.active = 0        # can't use if nothing selected
        self.group_canvas.pack(expand=1, fill='both')
        self.canvas_dict[self.group_canvas] = {}
        self.arrow_dict[self.group_canvas] = {}
        self.graph_dict[self.group_canvas] = Graph()
        self.group_canvas.bind('<Double-Button-2>', lambda e: self.delete_current(e, self.group_canvas))
        self.group_canvas.bind('<Button-1>', lambda event: self.drag_select(event, self.group_canvas, 'current-drag'))
        self.group_canvas.bind('<B1-Motion>', lambda event: self.drag_select(event, self.group_canvas, 'current-drag'))
        self.group_canvas.bind('<ButtonRelease-1>', lambda event: self.drag_select(event, self.group_canvas, 'current-drop'))
        #self.group_canvas.tag_bind('node', '<Button-1>', lambda e: self.click_node(e, self.group_canvas))
        #self.group_canvas.tag_bind('node', '<B1-Motion>', lambda e: self.drag_current(e, self.group_canvas, 'current-drag'))
        #self.group_canvas.tag_bind('node', '<ButtonRelease-1>', lambda e: self.drag_current(e, self.group_canvas, 'current-drop'))
        self.group_canvas.tag_bind('node', '<Button-3>', lambda e: self.edit_node_value(e, self.group_canvas))
        self.group_canvas.tag_bind('node', '<Double-Button-3>', lambda e: self.change_box_label(e, self.group_canvas))
        self.group_canvas.tag_bind('node', '<Button-2>', lambda e: self.set_active_node(e, self.group_canvas))
        self.group_canvas.tag_bind('node', '<Enter>', lambda e: self.set_hover(e, self.group_canvas, 'enter'))
        self.group_canvas.tag_bind('node', '<Leave>', lambda e: self.set_hover(e, self.group_canvas, 'exit'))
        self.group_canvas.tag_bind('arrow', '<Button-1>', lambda e: self.select_object(e, self.group_canvas))
        self.group_canvas.tag_bind('arrow', '<Button-2>', lambda e: self.set_active_arrow(e, self.group_canvas))
        self.group_canvas.tag_bind('arrow', '<Double-Button-3>', lambda e: self.change_arrow_label(e, self.group_canvas))
        self.group_canvas.tag_bind('arrow', '<Enter>', lambda e: self.set_hover(e, self.group_canvas, 'enter'))
        self.group_canvas.tag_bind('arrow', '<Leave>', lambda e: self.set_hover(e, self.group_canvas, 'exit'))
        self.current_widget = None
        self.last_canvas = None # prevents rare bug on canvas change
        if clipboard:
            self.notebookTb.update_state()
            self.update_state()
            self.clipboard.add(self.state.export())

    def set_hover(self, event, canvas, status):
        if canvas == self.group_canvas:
            tab = self.group_canvas
        else:
            tab = self.canvas_tabs.select()
        try:
            self.hover_obj = self.canvas_dict[tab][canvas.find_withtag(CURRENT)[0]]['object_id']
        except:
            return
        if str(canvas.itemcget(self.hover_obj, 'width')) != '1.0':
            return
        tags = canvas.itemcget(canvas.find_withtag(CURRENT), 'tags')
        if 'node' in tags:
            if status == 'enter':
                canvas.itemconfig(self.hover_obj, outline='cyan')
            elif status == 'exit':
                canvas.itemconfig(self.hover_obj, outline='black')
        elif 'arrow' in tags:
            if status == 'enter':
                canvas.itemconfig(self.hover_obj, stipple='gray50')
            elif status == 'exit':
                canvas.itemconfig(self.hover_obj, stipple='')

    def delete_canvas(self, event=None, state=False, tab=None, clipboard=False):
        if self.command_lock != None:
            return

        self.reset_selected(event)
        if not tab:
            tab = self.canvas_tabs.select()
        self.canvas_tabs.forget(tab)
        del self.canvas_dict[tab]
        del self.arrow_dict[tab]
        del self.graph_dict[tab]
        del self.canvas_tab_dict[tab]
        remove_list = self.sync.remove_obj(tab)
        self.notebookTb.close_sync(remove_list)
        if tab in self.save_dict:
            del self.save_dict[tab]
        if int(len(self.canvas_tabs.tabs())) == 0 and not state:
            self.create_canvas()
        self.command_lock = None
        if clipboard:
            self.notebookTb.update_state()
            self.update_state()
            self.clipboard.add(self.state.export())

    def tab_right_click_menu(self, event):
        if self.command_lock != None:
            return
        tab = self.canvas_tabs.tk.call(self.canvas_tabs._w, "identify", "tab", event.x, event.y)
        active_tab = self.canvas_tabs.index(self.canvas_tabs.select())
        if tab == '': # clicked space after tabs
            tab = active_tab
        elif tab != active_tab:
            self.canvas_tabs.select(tab)
        menu_popup = tk.Menu(self.canvas_tabs, tearoff=0)
        menu_popup.add_command(label='   New Tab  ', command=lambda: self.create_canvas(clipboard=True))
        menu_popup.add_command(label='   Rearrange  ', command=lambda: self.save_as_canvas(rearrange=True))
        menu_popup.add_command(label='   Open  ', command=lambda: self.load_canvas(clipboard=True))
        menu_popup.add_command(label='   Save  ', command=self.save_canvas)
        menu_popup.add_command(label='   Save As  ', command=self.save_as_canvas)
        menu_popup.add_command(label='   Rename  ', command=self.change_tab_label)
        menu_popup.add_command(label='   Duplicate  ', command=lambda: self.load_canvas(duplicate=True))
        menu_popup.add_command(label='   Close Tab  ', command=lambda: self.delete_canvas(clipboard=True))
        menu_popup.tk.call('tk_popup', menu_popup, event.x_root, event.y_root)

    def open_config(self):
        if self.command_lock != None:
            return
        config_root = Toplevel(self.root)
        config_root.title('Config Menu')
        config_root.resizable(False, False)

        width_label = Label(config_root, text='Node Width (pixels):').pack(fill=X)
        width_textbox = Entry(config_root)
        width_textbox.pack(fill=X)
        width_textbox.insert(0, self.default_node_width)

        height_label = Label(config_root, text='Node Height (pixels):').pack(fill=X)
        height_textbox = Entry(config_root)
        height_textbox.pack(fill=X)
        height_textbox.insert(0, self.default_node_height)

        var = IntVar()
        var.set(self.savetoggle)
        button = Checkbutton(config_root, text='Undo/Redo Movement', variable=var, anchor=W)
        button.pack(fill=X)
        button.var = var

        submit_button = Button(config_root, command=lambda: self.config_submit(config_root, width_textbox, height_textbox, button), text='Submit').pack(fill=X)

        config_root.transient(self.root)
        config_root.wait_visibility()
        config_root.grab_set()
        self.window.config(menu = self.sketchobj.menu)

    def config_submit(self, config_root, width_textbox, height_textbox, button):
        if (not re.match('^[0-9]*$', width_textbox.get())) or (not re.match('^[0-9]*$', height_textbox.get())):
            print('Please only enter integers!')
            return

        if width_textbox.get() != '':
            self.geometry_dict['width'] = int(width_textbox.get())
        if height_textbox.get() != '':
            self.geometry_dict['height'] = int(height_textbox.get())
        self.default_node_height = self.geometry_dict['height']
        self.default_node_width = self.geometry_dict['width']
        self.default_widget_height = int(self.geometry_dict['height']/22.5)
        self.default_widget_width = int(self.geometry_dict['width']/8.25)

        self.savetoggle = int(button.var.get())

        config_root.destroy()

        self.choice_button.config(width=self.default_widget_width)
        self.compile_button.config(width=self.default_widget_width)
        self.load_default_nodes()

    def save_defaults(self):
        ChoiceDefaults().save(self.defaults_list, self.defaults_dict, self.geometry_dict)

    def load_default_geometry(self): # to do: menu from imagelabel script to change geometry
        defaults_obj = ChoiceDefaults().load()
        self.geometry_dict = defaults_obj.defGeo
        self.default_node_height = self.geometry_dict['height']
        self.default_node_width = self.geometry_dict['width']
        self.default_widget_height = int(self.geometry_dict['height']/22.5)
        self.default_widget_width = int(self.geometry_dict['width']/8.25)

    def load_default_nodes(self, revert=False):
        defaults_obj = ChoiceDefaults().load(revert=revert)
        if revert:
            self.geometry_dict = defaults_obj.defGeo
            self.default_node_height = self.geometry_dict['height']
            self.default_node_width = self.geometry_dict['width']
            self.default_widget_height = int(self.geometry_dict['height']/22.5)
            self.default_widget_width = int(self.geometry_dict['width']/8.25)
        self.defaults_dict = defaults_obj.defDict
        self.defaults_list = defaults_obj.defList
        for item in self.choice_frame.children.values():
            item.base_value = 'NULL'+str(item)
        for item in self.choice_frame.winfo_children():
            item.destroy()
        for key in self.defaults_list:
            value = self.defaults_dict[key]['value']
            img_file = self.defaults_dict[key]['image']
            if img_file and os.path.isfile(img_file):
                img = Image.open(img_file)
                if img.size[0] != self.default_widget_width*3.8:
                    rescale_factor = self.default_widget_width*3.8/float(img.size[0])
                    new_w = int(img.size[0]*rescale_factor)
                    new_h = int(img.size[1]*rescale_factor)
                    img = img.resize((new_w, new_h))
                img = ImageTk.PhotoImage(img)
                new_choice = Label(self.choice_frame, text = key, anchor=W, compound=LEFT, image=img,
                                   width=self.default_widget_width)#height=self.default_widget_height)
                new_choice.image = img
                new_choice.file = img_file
            else:
                new_choice = Label(self.choice_frame, text = key, height=self.default_widget_height, width=self.default_widget_width)
                new_choice.image = None
                new_choice.file = None
            if 'subgraph' in value:
                new_choice.configure(background='gold')
            new_choice.base_value = value
            new_choice.grid(padx=10, pady=5, sticky=NSEW)
            new_choice.optiontag = 1
        if revert:
            self.choice_button.config(width=self.default_widget_width)
            self.compile_button.config(width=self.default_widget_width)
            self.notebookTb.update_state()
            self.update_state()
            self.clipboard.add(self.state.export())

    def press_tab(self, event):
        x, y, widget = event.x, event.y, event.widget
        elem = widget.identify(x, y)
        tab = self.canvas_tabs.tk.call(self.canvas_tabs._w, "identify", "tab", x, y)
        if tab == '':
            return
        self.selected_tab = tab
        try:
            self.canvas_tabs.select(tab)
            if 'close' in elem:
                widget.state(['pressed'])
                widget.pressed_index = tab
        except:
            pass

    def drag_tab(self, event):
        x, y, widget = event.x, event.y, event.widget
        tab = self.canvas_tabs.tk.call(self.canvas_tabs._w, "identify", "tab", x, y)
        if self.selected_tab == None:
            return
        elif tab != self.selected_tab:
            widget.state(['!pressed'])
            widget.pressed_index = None
            if tab == '':
                if x <= 0:
                    self.canvas_tabs.insert(0, self.selected_tab)
                    self.selected_tab = 0
                else:
                    self.canvas_tabs.insert('end', self.selected_tab)
                    self.selected_tab = len(self.canvas_tabs.tabs())-1
            elif tab > self.selected_tab:
                self.canvas_tabs.insert(tab, self.selected_tab)
                self.selected_tab += 1
            elif tab < self.selected_tab:
                self.canvas_tabs.insert(self.selected_tab, tab)
                self.selected_tab -= 1

    def release_tab(self, event):
        x, y, widget = event.x, event.y, event.widget
        try:
            elem = widget.identify(x, y)
            tab = self.canvas_tabs.tk.call(self.canvas_tabs._w, "identify", "tab", x, y)
            if 'close' in elem and widget.pressed_index == tab:
                self.delete_canvas(clipboard=True)
            widget.state(['!pressed'])
            widget.pressed_index = None
        except:
            pass
        self.selected_tab = None

    def new_group(self, coordinates=None):
        self.create_group_canvas(clipboard=True)
        self.group_canvas.active = 1
        canvas_name = self.canvas_tab_dict[self.canvas_tabs.select()]['name']
        code_canvas = self.canvas_tab_dict[self.canvas_tabs.select()]['object']
        node_name = 'Sequential'
        self.group_label.config(text='Group Canvas: '+node_name+' ('+canvas_name+')')
        tab_text = 'Group Canvas: '+node_name+' ('+canvas_name+')'
        saved_canvas = dict(self.canvas_dict[self.group_canvas])
        saved_arrows = dict(self.arrow_dict[self.group_canvas])
        saved_graph_active_edge = dict(self.graph_dict[self.group_canvas].activeEdgeList)
        saved_graph_nodes = dict(self.graph_dict[self.group_canvas].nodes)
        saved_graph_obj = self.graph_dict[self.group_canvas]
        save_obj = Save(tab_text, saved_canvas, saved_arrows, saved_graph_active_edge, saved_graph_nodes, saved_graph_obj) #sets up initial save obj
        if coordinates:
            x1_s, y1_s, x2_s, y2_s = list(coordinates)
        else:
            x1_s, y1_s, x2_s, y2_s = [int(code_canvas.winfo_width())//2, int(code_canvas.winfo_height())//2,
                                      int(code_canvas.winfo_width())//2+self.default_node_width, int(code_canvas.winfo_height())//2+self.default_node_height]
        new_obj = code_canvas.create_rectangle(x1_s+1, y1_s+1, x2_s-1, y2_s-1, fill='gold', tags=('node',))
        new_text = code_canvas.create_text(((x1_s+x2_s)//2), ((y1_s+y2_s)//2), text=node_name, fill='black', tags=('node',))
        self.canvas_dict[self.canvas_tabs.select()][new_obj] = {'object_id':new_obj, 'text_id':new_text, 'text':node_name,
                                                                'value':{}, 'pair_dict_start':{}, 'pair_dict_end':{},
                                                                'arrow_ids_start':[], 'arrow_ids_end':[], 'dimensions':[x1_s, y1_s, x2_s, y2_s],
                                                                'canvas':self.canvas_tabs.select(), 'group_obj':save_obj}
        self.canvas_dict[self.canvas_tabs.select()][new_text] = {'object_id':new_obj, 'text_id':new_text, 'dimensions':[int((x1_s+x2_s)//2), int((y1_s+y2_s)//2)]}
        self.graph_dict[self.canvas_tabs.select()].addNode(Node(new_obj, type=node_name, params={'subgraph':deepcopy(saved_graph_obj)}, learned_params={}, status=True, group=True))
        self.original_group_save = save_obj
        self.selected_group_obj = new_obj

    def load_group(self, save_obj, obj_id):
        self.load_canvas(state=True, state_obj=save_obj, groupcanvas=True)
        self.group_canvas.active = 1
        node_name = self.canvas_dict[self.canvas_tabs.select()][obj_id]['text']
        canvas_name = self.canvas_tab_dict[self.canvas_tabs.select()]['name']
        self.group_label.config(text='Group Canvas: '+node_name+' ('+canvas_name+')')
        self.original_group_save = save_obj
        self.selected_group_obj = obj_id

    def set_group(self):
        if self.selected_group_obj:
            tab = self.group_canvas
            tab_text = self.canvas_dict[self.canvas_tabs.select()][self.selected_group_obj]['text']
            saved_canvas = dict(self.canvas_dict[tab])
            saved_arrows = dict(self.arrow_dict[tab])
            saved_graph_active_edge = dict(self.graph_dict[tab].activeEdgeList)
            saved_graph_nodes = dict(self.graph_dict[tab].nodes)
            saved_graph_obj = self.graph_dict[tab]
            save_obj = Save(tab_text, saved_canvas, saved_arrows, saved_graph_active_edge, saved_graph_nodes, saved_graph_obj)
            self.canvas_dict[self.canvas_tabs.select()][self.selected_group_obj]['group_obj'] = save_obj
            self.graph_dict[self.canvas_tabs.select()].editNode(self.selected_group_obj, params={'subgraph':deepcopy(saved_graph_obj)})

    def reload_group(self):
        if self.original_group_save != None:
            save_obj = self.original_group_save
            obj_id = self.selected_group_obj
            self.reset_selected(event=None)
            self.load_group(save_obj, obj_id)

    def clear_group(self):
        node_list = list(self.group_canvas.find_withtag('node'))
        node_set = set()
        if len(node_list) > 0:
            for id in node_list:
                node = self.canvas_dict[self.group_canvas][id]['object_id']
                node_set.add(node)
        for id in node_set:
            self.delete_current(event=None, code_canvas=self.group_canvas, id=id, clipboard=False)
        self.notebookTb.update_state()
        self.update_state()
        self.clipboard.add(self.state.export())

    def export_group(self):
        self.set_group()
        if self.group_label['text'] != 'Group Canvas (Inactive)':
            save_obj = self.canvas_dict[self.canvas_tabs.select()][self.selected_group_obj]['group_obj']
            self.command_lock = 'compile'
            filename = filedialog.asksaveasfilename(title = 'Save group canvas as...', filetypes = (("Sketch Files","*.sk"), ))
            if not filename:
                print('Cancelled')
                self.command_release('compile')
                return
            self.command_release('compile')
        with open(filename, 'wb') as save_file:
            pickle.dump(save_obj, save_file)

    def import_group(self):
        filename = filedialog.askopenfilename(title = 'Open prior saved canvas...', filetypes = (("Sketch Files","*.sk"), ))
        if not filename:
            print('Cancelled')
            self.command_release('compile')
            return
        self.command_release('compile')
        with open(filename, 'rb') as save_file:
            save_obj = pickle.load(save_file)
        if self.group_label['text'] == 'Group Canvas (Inactive)':
            self.new_group()
        else:
            group_obj = self.selected_group_obj
            label = self.group_label['text']
            self.create_group_canvas()
            self.group_canvas.active = 1
            self.selected_group_obj = group_obj
        self.original_group_save = save_obj
        self.load_group(save_obj, self.selected_group_obj)
        self.canvas_dict[self.canvas_tabs.select()][self.selected_group_obj]['group_obj'] = save_obj
        self.graph_dict[self.canvas_tabs.select()].editNode(self.selected_group_obj, params={'subgraph':deepcopy(save_obj.saved_graph_obj)})
        self.notebookTb.update_state()
        self.update_state()
        self.clipboard.add(self.state.export())

    def create_toolbox(self, parent, groupParent):
        self.load_default_geometry()

        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=10000)
        self.root.rowconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=10000)
        button_frame = Frame(self.root, bd=2, relief=RAISED, bg='white')
        button_frame.grid(row=0, column=0, sticky=NSEW)
        base_frame = Frame(self.root, bd=2, relief=RAISED, bg='white')
        base_frame.grid(row=1, column=0, sticky=NSEW)
        code_frame = Frame(self.root, bd=2, relief=SUNKEN, bg='white')
        code_frame.grid(row=0, column=1, rowspan=2, sticky=NSEW)

        self.canvas_tabs = ttk.Notebook(code_frame)
        self.canvas_tabs.pack(expand=True, fill=BOTH)
        self.canvas_tabs.bind("<<NotebookTabChanged>>", lambda e :self.reset_selected(e))
        self.canvas_tabs.bind('<Button-1>', lambda e: self.press_tab(e))
        self.canvas_tabs.bind('<B1-Motion>', lambda e: self.drag_tab(e))
        self.canvas_tabs.bind('<ButtonRelease-1>', lambda e: self.release_tab(e))
        self.canvas_tabs.bind('<Button-3><ButtonRelease-3>', lambda e: self.tab_right_click_menu(e))
        self.canvas_tabs.bind("<Control-w>", lambda e: self.delete_canvas(event=e, clipboard=True))
        self.canvas_tabs.bind("<Control-s>", lambda e: self.save_canvas(e))
        self.canvas_tabs.bind("<Control-Shift-S>", lambda e: self.save_as_canvas(event=e))
        self.create_canvas()

        self.group_button_frame = Frame(self.group_root)
        self.group_button_frame.columnconfigure(3, weight=1)
        self.group_button_frame.pack(expand=False, fill='both')
        self.new_group_button = Button(self.group_button_frame, text='New Group', command=self.new_group)
        self.import_group_button = Button(self.group_button_frame, text='Import', command=self.import_group)
        self.export_group_button = Button(self.group_button_frame, text='Export', command=self.export_group)
        self.group_label = Label(self.group_button_frame, text='Group Canvas (Inactive)')
        self.set_group_button = Button(self.group_button_frame, text='Set', command=self.set_group)
        self.reload_group_button = Button(self.group_button_frame, text='Reload', command=self.reload_group)
        self.clear_group_button = Button(self.group_button_frame, text='Clear', command=self.clear_group)
        self.new_group_button.grid(row=0, column=0, sticky=NSEW)
        self.import_group_button.grid(row=0, column=1, sticky=NSEW)
        self.export_group_button.grid(row=0, column=2, sticky=NSEW)
        self.group_label.grid(row=0, column=3, sticky=NSEW)
        self.set_group_button.grid(row=0, column=4, sticky=NSEW)
        self.reload_group_button.grid(row=0, column=5, sticky=NSEW)
        self.clear_group_button.grid(row=0, column=6, sticky=NSEW)
        self.create_group_canvas()

        self.choice_button = Button(button_frame, text='New Choice', command = lambda: self.create_choice(choice_cell), width=self.default_widget_width)
        self.choice_button.pack()
        self.compile_button = Button(button_frame, text='Compile', command = self.compile_objects, width=self.default_widget_width)
        self.compile_button.pack()
        self.choice_button.optiontag = 1
        self.compile_button.optiontag = 1

        base_frame.columnconfigure(0, weight=10000)
        base_frame.columnconfigure(1, weight=1)
        base_frame.rowconfigure(0, weight=1)
        choice_scroll = AutoHideScrollbar(base_frame, width=6)
        choice_scroll.grid(row=0, column=1, sticky=NSEW)
        choice_cell = Canvas(base_frame, bg='grey', width=1, yscrollcommand=choice_scroll.set)
        choice_cell.grid(row=0, column=0, sticky=NSEW)
        choice_cell.optiontag = 1
        choice_scroll.config(command=choice_cell.yview)

        self.choice_frame = Frame(choice_cell, bg='grey')
        self.choice_frame.optiontag = 1
        choice_cell.create_window((0,0),window=self.choice_frame,anchor='nw')
        self.choice_frame.bind("<Configure>", lambda event: self.update_choices(event, choice_cell, choice_scroll))
        self.choice_frame.bind('<Button-4>', lambda event: self.mousewheel(event, choice_cell, 'up'))
        self.choice_frame.bind('<Button-5>', lambda event: self.mousewheel(event, choice_cell, 'down'))

        self.load_default_nodes()

        self.choice_frame.bind_class('Label', '<Button-1>', lambda e: self.drag_new(e, 'new-start'))
        self.choice_frame.bind_class('Label', '<B1-Motion>', lambda e: self.drag_new(e, 'new-drag'))
        self.choice_frame.bind_class('Label', '<ButtonRelease-1>', lambda e: self.drag_new(e, 'new-drop'))
        self.choice_frame.bind_class('Label', '<Double-Button-1>', lambda e: self.edit_choice_value(e))
        self.choice_frame.bind_class('Label', '<Double-Button-2>', lambda e: self.delete_choice(e))
        self.choice_frame.bind_class('Label', '<Button-3>', lambda e: self.change_choice_label(e, choice_cell))
        self.choice_frame.bind_class('Label', '<Button-4>', lambda event: self.mousewheel(event, choice_cell, 'up'))
        self.choice_frame.bind_class('Label', '<Button-5>', lambda event: self.mousewheel(event, choice_cell, 'down'))

        base_frame.bind_class('Canvas', '<Button-1>', lambda e: self.click_node(e))
        base_frame.bind_class('Canvas', '<B1-Motion>', lambda e: self.drag_current(e, 'current-drag'))
        base_frame.bind_class('Canvas', '<ButtonRelease-1>', lambda e: self.drag_current(e, 'current-drop'))

        base_frame.bind_class('Canvas', '<Button-4>', lambda event: self.mousewheel(event, choice_cell, 'up'))
        base_frame.bind_class('Canvas', '<Button-5>', lambda event: self.mousewheel(event, choice_cell, 'down'))
        base_frame.bind_all('<Control-Delete>', lambda e: self.delete_selected(e))
        base_frame.bind_all('<Control-Insert>', lambda e: self.activity_selected(e, 'setactive'))
        base_frame.bind_all('<Control-Home>', lambda e: self.activity_selected(e, 'setinactive'))
        base_frame.bind_all('<Control-g>', lambda e: self.group_selected(e))

        self.root.pack(expand=1, fill='both')
        self.group_root.pack(expand=1, fill='both')


class AutoHideScrollbar(Scrollbar):
    def set(self, low, high):
        if float(low) <= 0.0 and float(high) >= 1.0:
            self.tk.call('grid', 'remove', self)
        else:
            self.grid()
        Scrollbar.set(self, low, high)


