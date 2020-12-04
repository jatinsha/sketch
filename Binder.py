from multiprocessing import Pool
import sys
from Log import *

# debug mode flag
_debug_ = True
class Binder(object):
    def __init__(self, kernel):
        self.kernel = kernel
        self.output = None

    def exportModelTask(self, input):
        def local_func(input):
            binder = None
            graph, filepath = input[0], input[1]
            if self.kernel == "PyTorch":
                from PyBinder import PyBinder
                binder = PyBinder()
                self.output = binder.exportModel(graph)
            elif self.kernel == "LuaTorch":
                from LuaBinder import LuaBinder
                binder = LuaBinder()
                self.output = binder.exportModel(graph)
            elif self.kernel == "ONNX":
                from ONNXBinder import ONNXBinder
                binder = ONNXBinder()
                self.output = binder.exportModel(graph)

            if self.output:
                binder.save(self.output, filepath)
                return binder.getPrintableModel(self.output)
            else:
                return "No model returned"

        if _debug_ :
            log("debug mode")
            return local_func(input)
        else:
            try:
                return local_func(input)
            except:
                print("Oops!",sys.exc_info()[0],"occured."+ "\n"+ str(sys.exc_info()))
                return None

    def exportModel(self, graph, filepath):
        with Pool(processes=1) as pool:
            result = pool.map(self.exportModelTask, [[graph, filepath]], 1)
        return result[0]

    def importModelTask(self, filepath):
        def local_func(filepath):
            binder = None
            if self.kernel == "PyTorch":
                from PyBinder import PyBinder
                binder = PyBinder()
                model = binder.load(filepath)
                return binder.importModel(model)
            elif self.kernel == "LuaTorch":
                from LuaBinder import LuaBinder
                binder = LuaBinder()
                model = binder.load(filepath)
                return binder.importModel(model)
            elif self.kernel == "ONNX":
                from ONNXBinder import ONNXBinder
                binder = ONNXBinder()
                model = binder.load(filepath)
                return binder.importModel(model)

        if _debug_ :
            log("debug mode")
            return local_func(filepath)
        else:
            try:
                return local_func(filepath)
            except:
                print("Oops!",sys.exc_info()[0],"occured."+ "\n"+ str(sys.exc_info()))
                return None

    def importModel(self, filepath):
        with Pool(processes=1) as pool:
            result = pool.map(self.importModelTask, [filepath], 1)
        return result[0]

    ###########################################################################
    # Advanced
    ###########################################################################
    def saveBranchedTask(self, input):
        try:
            binder = None
            graph, filepath = input[0], input[1]
            if self.kernel == "PyTorch":
                from PyBinder import PyBinder
                binder = PyBinder()
                self.output = binder.convertBranched(graph)
            elif self.kernel == "LuaTorch":
                from LuaBinder import LuaBinder
                binder = LuaBinder()
                self.output = binder.convertBranched(graph)

            binder.save(self.output, filepath)
            print(self.output)
            return True
        except:
            print("Oops!",sys.exc_info()[0],"occured.")
            return False

    def saveBranched(self, graph, filepath):
        with Pool(processes=1) as pool:
            result = pool.map(self.saveBranchedTask, [[graph, filepath]], 1)
        return result[0]