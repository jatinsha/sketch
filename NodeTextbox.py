################################################################################
# This file contains the source code for a single node's content
################################################################################

import os
import ast
import glob
import tkinter as tk
from tkinter import ttk
from os import path
from tkinter import scrolledtext
from tkinter import *

from Log import *

#from Toolbox import *
#from Graph import Graph, Node, Edge

class DefaultNodeTextbox(tk.Frame):
    def __init__(self, master, state):
        self.frame = tk.Frame(master)
        self.frame.pack(expand=1, fill='both')
        self.label = tk.Label(self.frame, text='Node and Default Edit', height=1)
        self.textbox = tk.Text(self.frame)
        self.scrollbar = tk.Scrollbar(self.frame, orient='vertical', command=self.textbox.yview)
        self.state = state
        self.importButton = tk.Button(self.frame, text='Import', command=self.importText)
        self.exportButton = tk.Button(self.frame, text='Export', command=self.exportText)
        self.setButton = tk.Button(self.frame, text='Set', command=self.setText)
        self.reloadButton = tk.Button(self.frame, text='Reload', command=self.reloadText)
        self.clearButton = tk.Button(self.frame, text='Clear', command=self.clearText)
        self.importButton.grid(row=0, column=0, sticky=NSEW)
        self.exportButton.grid(row=0, column=1, sticky=NSEW)
        self.label.grid(row=0, column=2, sticky=NSEW)
        self.setButton.grid(row=0, column=3, sticky=NSEW)
        self.reloadButton.grid(row=0, column=4, sticky=NSEW)
        self.clearButton.grid(row=0, column=5, sticky=NSEW)
        self.textbox.grid(row=1, column=0, columnspan=6, sticky=NSEW)
        self.scrollbar.grid(row=1, column=6, sticky=NS)
        self.textbox.configure(yscrollcommand=self.scrollbar.set)
        self.frame.columnconfigure(2, weight=1)
        self.frame.rowconfigure(1, weight=1)
        self.contents = None
        self.chosenId = None
        self.defaultsDict = None
        self.canvas_dict = None
        self.canvas_tab_dict = None
        self.canvas = None
        self.graph_obj = None
        self.type = None
        self.tab = None
        self.full_dict = None

    def getText(self):
        text = self.textbox.get('1.0', 'end-1c')
        return text

    def loadDefaultText(self, id, label_text, contents, defaults_dict):
        self.clearText()
        self.chosenId = id
        self.contents = contents
        self.textbox.delete('1.0', END)
        self.textbox.insert('1.0', contents)
        self.label.config(text = 'EDITING: '+label_text)
        self.defaultsDict = defaults_dict
        self.type = 'default'

    def loadNodeText(self, id, canv_dict, graph_obj, tab_dict=None, tab=None, full_dict=None):
        self.clearText()
        self.chosenId = id
        self.canvas_dict = canv_dict
        self.canvas_tab_dict = tab_dict
        self.graph_obj = graph_obj
        self.contents = self.canvas_dict[self.chosenId]['value']
        self.canvas = self.canvas_dict[self.chosenId]['canvas']
        label_text = self.canvas_dict[self.chosenId]['text']
        if self.canvas_tab_dict:
            canvas_text = self.canvas_tab_dict[self.canvas]['name']
        else:
            canvas_text = 'GROUP'
            self.tab = tab
            self.full_dict = full_dict
        self.textbox.delete('1.0', END)
        self.textbox.insert('1.0', self.contents)
        self.label.config(text = 'EDITING '+canvas_text+': '+label_text)
        self.type = 'node'

    def importText(self):
        if not self.chosenId:
            print('Must select Node or Default Option to edit first!')
            return
        filename = filedialog.askopenfilename(filetypes = (("Text files","*.txt"), ("all files","*.*"), ("Sketch files","*.sk")))
        if not filename:
            print('Cancelled')
            return
        with open(filename, 'rb') as fp:
            contents = fp.read()
        self.textbox.delete('1.0', END)
        self.textbox.insert('1.0', contents)

    def exportText(self):
        if not self.chosenId:
            print('Must select Node or Default Option to edit first!')
            return
        filename = filedialog.asksaveasfilename(filetypes = (("Text files","*.txt"), ("all files","*.*"), ("Sketch files","*.sk")))
        if not filename:
            print('Cancelled')
            return
        text = self.getText()
        with open(filename, 'wb') as fp:
            fp.write(bytes(text, 'UTF-8'))

    def setText(self):
        if not self.chosenId:
            print('Must select Node or Default to edit first!')
            return
        if self.type == 'default':
            if self.chosenId.base_value == 'NULL'+str(self.chosenId):
                self.label.config(text = 'DEFAULT NOT FOUND! EXPORT TEXT OR CLEAR')
            else:
                text = ast.literal_eval(self.getText())
                self.contents = text
                self.chosenId.base_value = text
                self.defaultsDict[self.chosenId['text']]['value'] = text
        elif self.type == 'node':
            if self.canvas_tab_dict:
                if (self.chosenId in self.canvas_dict) and (self.canvas in self.canvas_tab_dict):
                    try:
                        text = ast.literal_eval(self.getText())
                        self.contents = text
                        self.canvas_dict[self.chosenId]['value'] = text
                        self.graph_obj.editNode(self.chosenId, params=text)
                    except:
                        log("Invalid Parameters - literal_eval can't parse")
                        messagebox.showerror('Invalid Parameters', "Please enter parameters as a valid dictionary. \ne.g. {'kernel_size' : (2, 2)}")
        #             text = eval(self.getText())
        #             for node, param in text.items():
        #                 print(node, param)
        #                 node.setParams(params)
                else:
                    self.label.config(text = 'NODE NOT FOUND! EXPORT TEXT OR CLEAR')
            else:
                if (self.chosenId in self.canvas_dict) and (self.tab in self.full_dict):
                    try:
                        text = ast.literal_eval(self.getText())
                        self.contents = text
                        self.canvas_dict[self.chosenId]['value'] = text
                        self.graph_obj.editNode(self.chosenId, params=text)
                    except:
                        log("Invalid Parameters - literal_eval can't parse")
                        messagebox.showerror('Invalid Parameters', "Please enter parameters as a valid dictionary. \ne.g. {'kernel_size' : (2, 2)}")
        #             text = eval(self.getText())
        #             for node, param in text.items():
        #                 print(node, param)
        #                 node.setParams(params)
                else:
                    self.label.config(text = 'NODE NOT FOUND! EXPORT TEXT OR CLEAR')


    def reloadText(self):
        if not self.chosenId:
            print('Must select Node or Default Option to edit first!')
            return
        self.textbox.delete('1.0', END)
        self.textbox.insert('1.0', self.contents)
        print('Text reloaded')

    def clearText(self):
        self.chosenId = None
        self.contents = None
        self.defaultsDict = None
        self.canvas_dict = None
        self.canvas_tab_dict = None
        self.canvas = None
        self.graph_obj = None
        self.type = None
        self.tab = None
        self.full_dict = None
        self.label.config(text = 'Node and Default Edit')
        self.textbox.delete('1.0', END)





