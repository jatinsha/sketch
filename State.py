################################################################################
# This file contains the source code for the state management between the
# sessions
################################################################################

import sys
import os
from os import path
import pickle as pkl
import getpass
from Log import *

class State(object):
    def __init__(self):
        if sys.platform.startswith('win32'): # added platforms
            self.statePath = 'C:/Users/'+getpass.getuser()+'/.sketch/sketch.state'
        elif sys.platform.startswith('linux'):
            self.statePath = '/home/'+getpass.getuser()+'/.sketch/sketch.state'
        else:
            self.statePath = os.path.join(os.getcwd(), '.sketch/sketch.state')
        self.load()

    def __str__(self):
        return str(self.dom)

    def load(self):
        if path.isfile(self.statePath):
            # load state
            state_file = open(self.statePath, mode='rb')
            self.dom = pkl.load(state_file)
            log('Existing State ' + str(self.statePath))
        else:
            self.reset()
            log('New State ' + str(self.statePath))

    def update(self, key, value):
        self.dom[key] = value

    def overwrite(self, dictionary):
        self.dom = dict(dictionary)

    def save(self):
        # check and create dir structure if file does not exists
        os.makedirs(os.path.dirname(self.statePath), exist_ok=True)
        state_file = open(self.statePath, mode='wb+')
        pkl.dump(self.dom, state_file)
        state_file.close()
        log('State saved ' + str(self.statePath))

    def reset(self):
        self.dom = {'cwd' : os.getcwd(), 'version' : 'v1.0', 'canvas' : '', 'notebook' : '', 'canvastab' : 0, 'notebooktab' : 0, 'groupcanvas' : ''}

    def export(self):
        return dict(self.dom)


