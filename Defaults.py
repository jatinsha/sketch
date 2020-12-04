import sys
import os
import pickle
import getpass

class ChoiceDefaults(object):
    def __init__(self, *args):
        if sys.platform.startswith('win32'): # added platforms
            self.defPath = 'C:/Users/'+getpass.getuser()+'/.sketch/default.config'
            self.customPath = 'C:/Users/'+getpass.getuser()+'/.sketch/custom.config'
        elif sys.platform.startswith('linux'):
            self.defPath = '/home/'+getpass.getuser()+'/.sketch/default.config'
            self.customPath = '/home/'+getpass.getuser()+'/.sketch/custom.config'
        else:
            self.defPath = os.path.join(os.getcwd(), '.sketch/default.config')
            self.customPath = os.path.join(os.getcwd(), '.sketch/custom.config')
        self.defImagePath = os.path.join(os.getcwd(), 'images') # placeholder, change this to install loc
        self.custom = ''
        self.configCheck()

    def configCheck(self):
        if not os.path.isfile(self.defPath):
            os.makedirs(os.path.dirname(self.defPath), exist_ok=True)
            default = Defaults(self.defImagePath)
            with open(self.defPath, 'wb') as saveFile:
                pickle.dump(default, saveFile)

    def load(self, revert=False):
        if os.path.isfile(self.customPath) and not revert:
            path = self.customPath
        else:
            path = self.defPath
        with open(path, 'rb') as saveFile:
            DefaultObj = pickle.load(saveFile)
        return DefaultObj

    def save(self, defList, defDict, defGeo):
        with open(self.customPath, 'wb') as saveFile:
            pickle.dump(CustomSave(defList, defDict, defGeo), saveFile)


class Defaults(object):
    def __init__(self, defImagePath):
        self.defList = []
        self.defDict = {}
        self.defGeo = {'height':45, 'width':165}
        tags = {
                'Conv2d':{'in_channels': 1, 'out_channels': 1, 'kernel_size': (3, 3), 'stride': (1, 1), 'padding': (1, 1), 'bias':True},
                'BatchNorm2d':{'num_features': 1},
                'ReLU':{},
                'Sigmoid':{},
                'MaxPool2d':{'kernel_size': (2, 2), 'stride': (2, 2), 'padding': (0, 0)},
                'AvgPool2d':{'kernel_size': (2, 2), 'stride': (2, 2), 'padding': (0, 0)},
                'Linear':{'in_features': 1, 'out_features': 1, 'bias': True},
                'Dropout':{'p': 0.1},
                'SoftMax':{'dim': 0},
                'Identity':{},
                'Tanh':{},
                'Sequential':{'subgraph':None}
               }
        self.defList = ['Conv2d', 'BatchNorm2d', 'ReLU', 'Sigmoid', 'MaxPool2d', 'AvgPool2d', 'Linear', 'Dropout', 'SoftMax', 'Identity', 'Tanh', 'Sequential']
        for key in tags:
            imagePath = os.path.join(defImagePath, key+'.png')
            if not os.path.isfile(imagePath):
                imagePath = None
            self.defDict.update({key:{'value':tags[key], 'image':imagePath}})

class CustomSave(object):
    def __init__(self, defList, defDict, defGeo):
        self.defList = defList
        self.defDict = defDict
        self.defGeo = defGeo



