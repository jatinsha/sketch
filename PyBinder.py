import torch
import torch.nn as nn
from PyBinderCustom import *
from Graph import *
class PyBinder(object):
    def __init__(self):
        pass

    def getPrintableModel(self, model):
        return repr(model)

    def save(self, model, path):
        torch.save(model, path)

    def exportModel(self, graph):
        order, expanded_order = graph.topologicalSort()
        net = nn.Sequential()
        index = 0
        for id in order:
            index = index + 1
            node = graph.nodes.get(id)
            name = node.type
            m = node.params
#             print(id, name)

            if m.get('in_channels') :
                in_channels = m.get('in_channels')
            else:
                in_channels = 1

            if m.get('out_channels') :
                out_channels = m.get('out_channels')
            else:
                out_channels = 1

            if m.get('num_features') :
                num_features = m.get('num_features')
            else:
                num_features = 1

            if m.get('in_features') :
                in_features = m.get('in_features')
            else:
                in_features = 1

            if m.get('out_features') :
                out_features = m.get('out_features')
            else:
                out_features = 1

            if m.get('p') :
                p = m.get('p')
            else:
                p = 0.1

            if m.get('kernel_size') :
                kernel_size = m.get('kernel_size')
            else:
                kernel_size = (1,1)

            if m.get('stride') :
                stride = m.get('stride')
            else:
                stride = (1,1)

            if m.get('padding') :
                padding = m.get('padding')
            else:
                padding = (0,0)

            if m.get('subgraph'):
                subgraph = m.get('subgraph')

            if name == 'Conv2d':
                n = nn.Conv2d(in_channels, out_channels, kernel_size, stride, padding)
            elif name == 'BatchNorm2d':
                n = nn.BatchNorm2d(num_features)
            elif name == 'ReLU':
                n = nn.ReLU()
            elif name == 'Sigmoid':
                n = nn.Sigmoid()
            elif name == 'MaxPool2d':
                n = nn.MaxPool2d(kernel_size, stride, padding)
            elif name == 'AvgPool2d':
                n = nn.AvgPool2d(kernel_size, stride, padding)
            elif name == 'Linear':
                n = nn.Linear(in_channels, out_channels)
            elif name == 'Dropout':
                n = nn.Dropout(p)
            elif name == 'Softmax':
                n = nn.Softmax()
            elif name == 'Identity':
#                 n = nn.Sequential()
                n = Identity()
            elif name == 'Reshape':
                n = Reshape()
            elif name == 'BCELoss':
                n = nn.BCELoss()
            elif name == 'MSELoss':
                n = nn.MSELoss()
            else:
                # Group or Sequential nodes
                if node.group == True:
                    n = self.exportModel(subgraph)
                else:
                    # n = NotImplemented(name)
                    print('Not Implement',name)

#             net.add_module(str(id), n)
            net.add_module(str(index), n)

        return net

    def load(self, path):
        model = torch.load(path)
        print(model)
        return model

    def importModel(self, model):
        named_modules = list(model.named_children())
        graph = Graph()
        lastNodeId = None
        for id, module in named_modules:
            print(id, module)
            id = str(id)
            name = module.__class__.__name__

            if name == 'Conv2d':
                graph.addNode(Node(id, type=name, params={'in_channels':module.in_channels, 'out_channels':module.out_channels, 'kernel_size':module.kernel_size, 'stride':module.stride, 'padding':module.padding}))
            elif name == 'BatchNorm2d':
                graph.addNode(Node(id, type=name, params={'num_features':module.num_features}))
            elif name == 'ReLU':
                graph.addNode(Node(id, type=name, params={}))
            elif name == 'Sigmoid':
                graph.addNode(Node(id, type=name, params={}))
            elif name == 'MaxPool2d':
                graph.addNode(Node(id, type=name, params={'kernel_size':module.kernel_size, 'stride':module.stride, 'padding':module.padding}))
            elif name == 'AvgPool2d':
                graph.addNode(Node(id, type=name, params={'kernel_size':module.kernel_size, 'stride':module.stride, 'padding':module.padding}))
            elif name == 'Linear':
                graph.addNode(Node(id, type=name, params={'in_features':module.in_features, 'out_features':module.out_features}))
            elif name == 'Dropout':
                graph.addNode(Node(id, type=name, params={'p':module.p}))
            elif name == 'Softmax':
                graph.addNode(Node(id, type=name, params={}))
            elif name == 'Identity':
                graph.addNode(Node(id, type=name, params={}))
            elif name == 'Reshape':
                graph.addNode(Node(id, type=name, params={}))
            elif name == 'BCELoss':
                graph.addNode(Node(id, type=name, params={}))
            elif name == 'MSELoss':
                graph.addNode(Node(id, type=name, params={}))
            elif name == 'Sequential':
                subgraph = self.importModel(module)
                graph.addNode(Node(id, type='Sequential', params={'subgraph':subgraph}))
            else:
                graph.addNode(Node(id, type='NotImplemented', params={}))
                print('Not Implement',name)


            if lastNodeId:
#                 print(str(lastNodeId) + "-->" + str(id))
                graph.addEdge(Edge(lastNodeId, id))
            lastNodeId = id

        return graph

    ############################################################################
    # Helper methods
    ############################################################################
    def convertBranched(self, graph):
        order, expanded_order = graph.topologicalSort()
        layers = {}
        index = 0
        for id in order:
            index = index + 1
            node = graph.nodes.get(id)
            name = node.type
            m = node.params

            if m.get('in_channels') :
                in_channels = m.get('in_channels')
            else:
                in_channels = 1

            if m.get('out_channels') :
                out_channels = m.get('out_channels')
            else:
                out_channels = 1

            if m.get('num_features') :
                num_features = m.get('num_features')
            else:
                num_features = 1

            if m.get('p') :
                p = m.get('p')
            else:
                p = 0.1

            if m.get('kernel_size') :
                kernel_size = m.get('kernel_size')
            else:
                kernel_size = (1,1)

            if m.get('stride') :
                stride = m.get('stride')
            else:
                stride = (1,1)

            if m.get('padding') :
                padding = m.get('padding')
            else:
                padding = (0,0)

            if name == 'Conv2d':
                n = nn.Conv2d(in_channels, out_channels, kernel_size, stride, padding)
            elif name == 'BatchNorm2d':
                n = nn.BatchNorm2d(num_features)
            elif name == 'ReLU':
                n = nn.ReLU()
            elif name == 'Sigmoid':
                n = nn.Sigmoid()
            elif name == 'MaxPool2d':
                n = nn.MaxPool2d(kernel_size, stride, padding)
            elif name == 'AvgPool2d':
                n = nn.AvgPool2d(kernel_size, stride, padding)
            elif name == 'Linear':
                n = nn.Linear()
            elif name == 'Dropout':
                n = nn.Dropout(p)
            elif name == 'Softmax':
                n = nn.Softmax()
            elif name == 'Identity':
                n = Identity()
            elif name == 'Reshape':
                n = Reshape()
            elif name == 'BCELoss':
                n = nn.BCELoss()
            elif name == 'MSELoss':
                n = nn.MSELoss()
            else:
                n = NotImplemented(name)
                print('Not Implement',name)

#             net.add_module(str(id), n)
            layers.update({str(id) : n})

        print('here')
        def forward(self, input):
            print(self.__qualname__)
            src = next(iter(self.graph.adjacencyList.keys()))
            inputDict = {src: [input]}
            for name, children in self.graph.adjacencyList.items():
                print(name)
                node = self.layers.get(name)
                out = node(sum(inputDict.get(name)))
                if len(children) > 0:
                    for child in children:
                        existing_out = inputDict.get(child, [])
                        existing_out.append(out)
                        inputDict.update({child : existing_out})

            return out

#         def save(self):
#             """save class as self.name.txt"""
#             file = open(self.__qualname__+'.txt','w')
#             file.write(pickle.dumps(self.__dict__))
#             file.close()
#
#         def load(self):
#             """try load self.name.txt"""
#             file = open(self.__qualname__+'.txt','r')
#             dataPickle = file.read()
#             file.close()
#             self.__dict__ = pickle.loads(dataPickle)

#         def __str__(self):
#             return self.__qualname__

        model_name = 'CustomModel'
        model = type(model_name, (nn.Module, Graph), {'graph': graph, 'layers':layers, 'forward':classmethod(forward)})
        input = torch.ones(1,1,10,10)
        print(model.forward(input))
#         file = open("/home/jatin17/workspace/pySeer/sketch" + model.__qualname__+'.cls','w')
#         file.write(pickle.dumps(model))
#         file.close()
        return None

