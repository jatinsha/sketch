import PyTorch
import PyTorchAug
from PyTorchAug import nn
from Graph import *
class LuaBinder(object):
    def __init__(self):
        pass

    def getPrintableModel(self, model):
        return repr(model)

    def toTorch(self, numpy_array):
        if numpy_array.dtype == 'float32':
            return PyTorch.asFloatTensor(numpy_array)
        elif numpy_array.dtype == 'float64':
            return PyTorch.asDoubleTensor(numpy_array)
        elif numpy_array.dtype == 'uint8':
            return PyTorch.asByteTensor(numpy_array)
        else:
            return PyTorch.asDoubleTensor(numpy_array)

    def toNumpy(self, torch_tensor):
        return torch_tensor.asNumpyTensor()

    def isValid(self, t):
        if type(t) == type(None):
            return False
        else:
            return True

    def copyWeights(self, toW, fromNumpyW):
        if self.isValid(fromNumpyW):
            # XXX force convert input numpy array to double
            # as PyTorchLua model weights are always double
            # find workaround to typecast the tensor itself
            # in the model
            fromNumpyW = fromNumpyW.astype('float64')
            toW.fill(1)
            toW.cmul(self.toTorch(fromNumpyW))

    def save(self, model, path):
        PyTorchAug.save(path, model)

    def exportModel(self, graph):
        order, expanded_order = graph.topologicalSort()
        net = nn.Sequential()
        for id in order:
            node = graph.nodes.get(id)
            name = node.type
            m = node.params
            l = node.learned_params

            if m.get('in_channels') :
                nInputPlane = m.get('in_channels')
            else:
                nInputPlane = 1

            if m.get('out_channels') :
                nOutputPlane = m.get('out_channels')
            else:
                nOutputPlane = 1

            if m.get('num_features') :
                nFeatures = m.get('num_features')
            else:
                nFeatures = 1

            if m.get('in_features') :
                inputDimension = m.get('in_features')
            else:
                inputDimension = 1

            if m.get('out_features') :
                outputDimension = m.get('out_features')
            else:
                outputDimension = 1

            if m.get('p') :
                p = m.get('p')
            else:
                p = 0.1

            if m.get('kernel_size') :
                kernel_size = m.get('kernel_size')
                if type(kernel_size) == type((3,3)):
                    kW = kernel_size[0]
                    kH = kernel_size[1]
                else:
                    kW = kernel_size
                    kH = kernel_size
            else:
                kW = 1
                kH = 1

            if m.get('stride') :
                stride = m.get('stride')
                if type(stride) == type((3,3)):
                    dW = stride[0]
                    dH = stride[1]
                else:
                    dW = stride
                    dH = stride
            else:
                dW = 1
                dH = 1

            if m.get('padding') :
                padding = m.get('padding')
                if type(padding) == type((3,3)):
                    padW = padding[0]
                    padH = padding[1]
                else:
                    padW = padding
                    padH = padding
            else:
                padW = 0
                padH = 0

            if m.get('subgraph'):
                subgraph = m.get('subgraph')

            # copy the network architecture
            if name == 'Conv2d':
                n = nn.SpatialConvolution(nInputPlane, nOutputPlane, kW, kH, dW, dH, padW, padH)
            elif name == 'BatchNorm2d':
                n = nn.SpatialBatchNormalization(nFeatures)
            elif name == 'ReLU':
                n = nn.ReLU()
            elif name == 'Sigmoid':
                n = nn.Sigmoid()
            elif name == 'MaxPool2d':
                n = nn.SpatialMaxPooling(kW, kH, dW, dH, padW, padH)
            elif name == 'AvgPool2d':
                n = nn.SpatialAveragePooling(kW, kH, dW, dH, padW, padH)
            elif name == 'Linear':
                n = nn.Linear(inputDimension, outputDimension)
            elif name == 'Dropout':
                n = nn.Dropout(p)
            elif name == 'Softmax':
                n = nn.SoftMax()
            elif name == 'Identity':
                n = nn.Identity()
            elif name == 'Reshape':
                # add params here
                n = nn.Reshape()
            elif name == 'BCELoss':
                n = nn.BCECriterion()
            elif name == 'MSELoss':
                n = nn.MSECriterion()
            elif name == 'Sequential':
                n = self.exportModel(subgraph)
            elif name == 'ResNet':
                n, core, _ = self.createResidualLayer()
                core.add(nn.SpatialConvolution(128,128, 3,3, 2,2, 1,1))
                core.add(nn.SpatialBatchNormalization(128))
                core.add(nn.ReLU())
                core.add(nn.SpatialConvolution(128,128, 3,3, 1,1, 1,1))
                core.add(nn.SpatialBatchNormalization(128))
            else:
                # Group or Sequential nodes
                if node.group == True:
                    n = self.exportModel(subgraph)
                else:
                    print('Not Implement', name)

            # copy the network weights
            weight = l.get('weight')
            bias = l.get('bias')
            running_mean = l.get('running_mean')
            running_var = l.get('running_var')
            # copy over the learned params if they exist
            self.copyWeights(n.weight, weight)
            self.copyWeights(n.bias, bias)
            self.copyWeights(n.running_mean, running_mean)
            self.copyWeights(n.running_var, running_var)

            net.add(n)

        return net

    def load(self, path):
        # dont remove this line. This is important to init the PyTorch nn
        self.init_modules()
        print('loading from: ' + path)
        model = PyTorchAug.load(path)
        print(model)
        return model

    def importModel(self, model):
        lastNodeId = None
        graph = Graph()
        for id in range (1, len(model.modules)+1):
#             module.weight,output,gradInput
            module = model.modules.get(id)
            id = str(id)
            name = module.__class__.__name__
#             print(id, name)

            if module.weight:
                weight = self.toNumpy(module.weight)
            else:
                weight = None

            if module.bias:
                bias = self.toNumpy(module.bias)
            else:
                bias = None

            if module.running_mean:
                running_mean = self.toNumpy(module.running_mean)
            else:
                running_mean = None

            if module.running_var:
                running_var = self.toNumpy(module.running_var)
            else:
                running_var = None

            learned_params = {'weight':weight, 'bias':bias, 'running_mean':running_mean, 'running_var':running_var}

            if name == 'SpatialConvolution':
                graph.addNode(Node(id, type='Conv2d', params={'in_channels':module.nInputPlane, 'out_channels':module.nOutputPlane, 'kernel_size':(module.kW,module.kH), 'stride':(module.dW,module.dH), 'padding':(module.padW,module.padH)}, learned_params=learned_params))
            elif name == 'SpatialBatchNormalization':
                graph.addNode(Node(id, type='BatchNorm2d', params={'num_features':module.bias.size()[0]}, learned_params=learned_params))
            elif name == 'ReLU':
                graph.addNode(Node(id, type='ReLU', params={}))
            elif name == 'Sigmoid':
                graph.addNode(Node(id, type='Sigmoid', params={}))
            elif name == 'SpatialMaxPooling':
                graph.addNode(Node(id, type='MaxPool2d', params={'kernel_size':(module.kW,module.kH), 'stride':(module.dW,module.dH), 'padding':(module.padW,module.padH)}))
            elif name == 'SpatialAveragePooling':
                graph.addNode(Node(id, type='AvgPool2d', params={'kernel_size':(module.kW,module.kH), 'stride':(module.dW,module.dH), 'padding':(module.padW,module.padH)}))
            elif name == 'Linear':
                graph.addNode(Node(id, type='Linear', params={}, learned_params=learned_params))
            elif name == 'Dropout':
                graph.addNode(Node(id, type='Dropout', params={'p':module.p}))
            elif name == 'SoftMax':
                graph.addNode(Node(id, type='Softmax', params={}))
            elif name == 'Identity':
                graph.addNode(Node(id, type='Identity', params={}))
            elif name == 'Reshape':
                graph.addNode(Node(id, type='Reshape', params={}))
            elif name == 'BCECriterion':
                graph.addNode(Node(id, type='BCELoss', params={}))
            elif name == 'MSECriterion':
                graph.addNode(Node(id, type='MSELoss', params={}))
            elif name == 'Sequential':
                subgraph = self.importModel(module)
                subgraph.display()
                graph.addNode(Node(id, type='Sequential', params={'subgraph':subgraph}))
            else:
                graph.addNode(Node(id, type='NotImplemented', params={}))
                print('Not Implement',name)

            if lastNodeId:
#                 print(str(lastNodeId)+"-->"+ str(id))
                graph.addEdge(Edge(lastNodeId, id))
            lastNodeId = id

        return graph

    ############################################################################
    # Helper methods
    ############################################################################
    def init_modules(self):
        n = nn.Sequential()
        n = nn.SpatialConvolution(1, 1, 1,1, 1,1, 1,1)
        n = nn.SpatialBatchNormalization(1)
        n = nn.ReLU()
        n = nn.Sigmoid()
        n = nn.SpatialMaxPooling(1,1, 1,1, 1,1)
        n = nn.SpatialAveragePooling(1,1, 1,1, 1,1)
        n = nn.Linear(1, 1)
        n = nn.Dropout(0.1)
        n = nn.SoftMax()
        n = nn.Identity()
        n = nn.Reshape(1)
        n = nn.BCECriterion()
        n = nn.MSECriterion()

    def createResidualLayer(self, customLayer=None):
      core1 = nn.Sequential()
      if customLayer:
        core2 = customLayer
      else:
        core2 = nn.Identity()

      core = nn.ConcatTable()
      core.add(core1)
      core.add(core2)
      layer = nn.Sequential()
      layer.add(core)
      layer.add(nn.CAddTable())
      layer.add(nn.ReLU())
      return layer, core1, core2


# import PyTorch
# import PyTorchAug
# from PyTorchAug import nn
# l=nn.SpatialBatchNormalization(6)
#
# a = PyTorch.FloatTensor(2,3)
#
# a = PyTorch.DoubleTensor(2,3)
#
#
# PyTorch.asDoubleTensor(fromTensorf.asNumpyTensor().astype('float64'))



