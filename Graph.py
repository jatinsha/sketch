from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import collections
import numbers
from six import text_type, integer_types, binary_type
import numpy as np  # type: ignore

from Log import *
# from Binder import *
from tkinter import messagebox
from copy import copy, deepcopy


class Graph(object):
    def __init__(self, graph=None, adjacencyList=None, activeEdgeList=None, nodes=None):
        if graph:
            self.adjacencyList = deepcopy(graph.adjacencyList)
            self.activeEdgeList = deepcopy(graph.activeEdgeList)
            self.nodes = deepcopy(graph.nodes)
        elif adjacencyList and activeEdgeList and nodes:
            self.adjacencyList = deepcopy(adjacencyList)
            self.activeEdgeList = deepcopy(activeEdgeList)
            self.nodes = deepcopy(nodes)
        else:
            self.adjacencyList = {}
            self.activeEdgeList = {}
            self.nodes = {}

    def display(self):
        print("=============== GRAPH =================")
        n = len(self.adjacencyList)
        if n == 0:
            print("Empty Graph")
        else:
            for key, val in self.adjacencyList.items():
                node = self.nodes.get(key) # check if active
                if node.status == False:
                    continue
                print(key, "->", val)
        print("=======================================")

    def __str__(self):
        return self.getParamList()

#     def __repr__(self):
#         out = {}
#         for node in self.nodes.values():
#             out.update({node.id : node.params})
#
#         return str(out)

    def getParamList(self):
        out = []
        for node in self.nodes.values():
            out.append({node : node.params})

        return out

    def addNode(self, node):
        if not self.adjacencyList.get(node.id, None):
            self.nodes.update({node.id: node})
            self.adjacencyList.update({node.id : []})
        else:
            print('Node already exists')

    def editNode(self, id, type=None, params=None, status=True, group=None):
        node = self.nodes.get(id)
        if type:
            node.type = type
        if params:
            try:
                node.setParams(params)
            except:
                log("Invalid Parameters - params are not dictionary")
                messagebox.showerror('Invalid Parameters', "Please enter parameters as a valid dictionary. \ne.g. {'kernel_size': (2, 2), 'stride': (2, 2), 'padding': (0, 0)}")

        if status == 'setactive':
            node.status = True
        elif status == 'setinactive':
            node.status = False

        if group == True:
            node.group = True
        elif group == False:
            node.group = False
        self.nodes.update({id: node})

    def deleteNode(self, id):
        del self.nodes[id]
        if id in self.adjacencyList:
            del self.adjacencyList[id]
        if id in self.activeEdgeList:
            del self.activeEdgeList[id]

    def addEdge(self, edge):
        #1. get existing list for the source node
        adjacencies = self.adjacencyList.get(edge.source)
        #2. add new node (sink node) to the list
        adjacencies.append(edge.sink)
        #3. update the list
        self.adjacencyList.update({edge.source : adjacencies})
        self.activeEdgeList.update({edge.source : adjacencies})

    def editEdge(self, edge, activity=True):
        activeList = self.activeEdgeList.get(edge.source)
        if activity:
            if edge.sink in activeList:
                activeList.remove(edge.sink) # make inactive
        else:
            if edge.sink not in activeList:
                activeList.append(edge.sink) # make active
        self.activeEdgeList.update({edge.source : activeList})

    def deleteEdge(self, source, sink):
        #1. get existing list for the source node
        adjacencies = self.adjacencyList.get(source)
        activeList = self.activeEdgeList.get(source)

        if not adjacencies: # return if called after deleteNode
            return
        if sink in adjacencies:
            adjacencies.remove(sink)
        self.adjacencyList.update({source : adjacencies})

        if not activeList:
            return
        if sink in activeList:
            activeList.remove(sink)
        self.activeEdgeList.update({source : activeList})


        # A recursive function used by topologicalSort
    def topologicalSortUtil(self, nodeId, visited, stack):
        # Mark the current node as visited.
        visited.update({nodeId : True})
        # Recur for all the vertices adjacent to this vertex
        for node_id in self.adjacencyList.get(nodeId):
            if visited.get(node_id) == False:
                self.topologicalSortUtil(node_id, visited, stack)

        # Push current vertex to stack which stores result
        stack.insert(0, nodeId)

    # The function to do Topological Sort. It uses recursive
    # topologicalSortUtil()
    def topologicalSort(self):
        stack = []
        expanded_stack = {}
        # Mark all the vertices as not visited
        visited = {}
        for key, val in self.adjacencyList.items():
            node = self.nodes.get(key) # check if active
            if node.status == False:
                continue
            visited.update({key : False})

        # Call the recursive helper function to store Topological
        # Sort starting from all vertices one by one
        for key, val in self.adjacencyList.items():
            if visited.get(key) == False:
                self.topologicalSortUtil(key, visited, stack)

        # expand stack to find dependencies: prior to pull from and next to push to
        for value in stack:
            expanded_stack[value] = {'prior':[], 'next':[]}
            expanded_stack[value]['next'] = self.adjacencyList[value]
            for key, val in self.adjacencyList.items():
                if value in val:
                    expanded_stack[value]['prior'].append(key)

        # return contents of stack as topological sorted order
        return stack, expanded_stack

    def normalize(self):
        id_count = 0
        deleted_nodes = []
        convert_dict = {}
        topo, expanded = self.topologicalSort()
        for id in list(topo):
            if self.nodes.get(id).type == 'PASS':
                self.deleteNode(id)
                deleted_nodes.append(id)
                for node in self.adjacencyList:
                    if id in self.adjacencyList[node]:
                        self.adjacencyList[node].remove(id)
                for node in self.activeEdgeList:
                    if id in self.activeEdgeList[node]:
                        self.activeEdgeList[node].remove(id)
                expanded_prior = expanded[id]['prior']
                expanded_next = expanded[id]['next']
                for p_id in expanded_prior:  # connect prior to next for each empty group node
                    if p_id not in deleted_nodes:
                        for e_id in expanded_next:
                            if e_id not in deleted_nodes:
                                if p_id in self.adjacencyList and e_id not in self.adjacencyList[p_id]:
                                    self.adjacencyList[p_id].append(e_id)
                                if p_id in self.activeEdgeList and e_id not in self.activeEdgeList[p_id]:
                                    self.activeEdgeList[p_id].append(e_id)
                topo.remove(id)
                continue
            id_count += 1
            convert_dict[id] = id_count
        old_nodes = dict(self.nodes)
        old_adj = dict(self.adjacencyList)
        old_active = dict(self.activeEdgeList)
        self.nodes = {}
        self.adjacencyList = {}
        self.activeEdgeList = {}
        for id in old_nodes:
            self.nodes[convert_dict[id]] = old_nodes[id]
        for id in old_adj:
            new_adj_list = []
            old_adj_list = old_adj[id]
            for item in old_adj_list:
                new_adj_list.append(convert_dict[item])
            self.adjacencyList[convert_dict[id]] = list(new_adj_list)
        for id in old_active:
            new_active_list = []
            old_active_list = old_active[id]
            for item in old_active_list:
                new_active_list.append(convert_dict[item])
            self.activeEdgeList[convert_dict[id]] = list(new_active_list)
        return self

    def test_branches(self):
        graph = Graph()
        graph.addNode(Node("conv1", type="Conv2D", params={'nIn':1, 'nOut':6, 'kW':3, 'kH':3}))
        graph.addNode(Node("maxpool1", type="MaxPool2D", status = False))
        graph.addNode(Node("bn1", type="BatchNorm2D"))
        graph.addNode(Node("conv2a", type="Conv2D", params={'nIn':6, 'nOut':6, 'kW':3, 'kH':3}))
        graph.addNode(Node("conv2b", type="Conv2D", params={'nIn':6, 'nOut':6, 'kW':1, 'kH':1}))
        graph.addNode(Node("relu", type="ReLU"))
        graph.addNode(Node("maxpool2", type="MaxPool2D"))
#         graph.addNode(Node("maxpool_nc", type="MaxPool2D"))

        graph.addEdge(Edge("conv1", "maxpool1"))
        graph.addEdge(Edge("maxpool1", "bn1"))
        graph.addEdge(Edge("bn1", "conv2a"))
        graph.addEdge(Edge("bn1", "conv2b"))
        graph.addEdge(Edge("conv2a", "relu"))
        graph.addEdge(Edge("conv2b", "relu"))
        graph.addEdge(Edge("relu", "maxpool2"))
        graph.display()
        order = graph.topologicalSort()
        print(order)
        graph.createModel(order)

    def createModel_branch(self, order):
        i = 0
        for id in order:
            if i == 0:
                print(str(i) +": ", end="")
                print(id)
                i = i+1

            print(str(i) +": ", end="")
            print(self.adjacencyList.get(id, None))
            i = i+1


#     def test(self):
#         graph = Graph()
#         graph.addNode(Node("conv1", type="Conv2d", params={'in_channels':1, 'out_channels':6, 'kernel_size':(3,3)} ))
#         graph.addNode(Node("bn1", type="BatchNorm2d", params={'num_features':6} ))
#         graph.addNode(Node("relu1", type="ReLU", params={'inplace':False} ))
#         graph.addNode(Node("maxpool1", type="MaxPool2d", params={'kernel_size':(3,3), 'stride':None, 'padding':None} ))
#         graph.addNode(Node("conv2", type="Conv2d", params={'in_channels':6, 'out_channels':6, 'kernel_size':(3,3)} ))
#         graph.addNode(Node("bn2", type="BatchNorm2d", params={'num_features':6} ))
#         graph.addNode(Node("relu2", type="ReLU", params={'inplace':False} ))
#         graph.addNode(Node("avgpool2", type="AvgPool2d", params={'kernel_size':(3,3), 'stride':None, 'padding':None} ))
#         graph.addNode(Node("dropout", type="Dropout", params={'p':0.1} ))
#         graph.addNode(Node("softmax", type="Softmax", params={} ))
#         graph.addNode(Node("sigmoid", type="Sigmoid", params={} ))
#         graph.addNode(Node("bceloss", type="BCELoss", params={} ))
#         graph.addNode(Node("mseloss", type="MSELoss", params={} ))
#         graph.addNode(Node("identity", type="Identity", params={} ))
#         graph.addNode(Node("reshape", type="Reshape", params={} ))

#         graph.addEdge(Edge("conv1", "bn1"))
#         graph.addEdge(Edge("bn1", "relu1"))
#         graph.addEdge(Edge("relu1", "maxpool1"))
#         graph.addEdge(Edge("maxpool1", "conv2"))
#         graph.addEdge(Edge("conv2", "bn2"))
#         graph.addEdge(Edge("bn2", "relu2"))
#         graph.addEdge(Edge("relu2", "avgpool2"))
#         graph.addEdge(Edge("avgpool2", "dropout"))
#         graph.addEdge(Edge("dropout", "softmax"))
#         graph.addEdge(Edge("softmax", "sigmoid"))
#         graph.addEdge(Edge("sigmoid", "bceloss"))
#         graph.addEdge(Edge("bceloss", "mseloss"))
#         graph.addEdge(Edge("mseloss", "identity"))
#         graph.addEdge(Edge("identity", "reshape"))
#         graph.display()

# #         binder = Binder("LuaTorch")
# #         model_text = binder.exportModel(graph, "/home/jatin17/workspace/pySeer/sketch/test_model.net")
# #         graph = binder.importModel("/home/jatin17/workspace/pySeer/sketch/test_model.net")
# #         graph.display()
# #
# #         binder = Binder("PyTorch")
# #         model_text = binder.exportModel(graph, "/home/jatin17/workspace/pySeer/sketch/test_model.pth")
# #         graph = binder.importModel("/home/jatin17/workspace/pySeer/sketch/test_model.pth")
# #         graph.display()

#         binder = Binder("ONNX")
#         model_text = binder.exportModel(graph, "/home/jatin17/workspace/pySeer/sketch/test_model.onnx")
#         print(model_text)


#     def test2(self):
#         graph = Graph()
#         graph.addNode(Node("conv1", type="Conv2d", params={'in_channels':1, 'out_channels':6, 'kernel_size':(3,3)} ))
#         graph.addNode(Node("relu1", type="ReLU", params={'inplace':False} ))
#         graph.addNode(Node("maxpool1", type="MaxPool2d", params={'kernel_size':(3,3), 'stride':None, 'padding':None} ))

#         graph.addNode(Node("conv2a", type="Conv2d", params={'in_channels':6, 'out_channels':6, 'kernel_size':(3,3)} ))

#         graph.addNode(Node("conv2b", type="Conv2d", params={'in_channels':6, 'out_channels':6, 'kernel_size':(3,3)} ))
#         graph.addNode(Node("relu2", type="ReLU", params={'inplace':False} ))


#         graph.addNode(Node("avgpool2", type="AvgPool2d", params={'kernel_size':(3,3), 'stride':None, 'padding':None} ))
#         graph.addNode(Node("dropout", type="Dropout", params={'p':0.1} ))
# #         graph.addNode(Node("softmax", type="Softmax", params={} ))

#         graph.addEdge(Edge("conv1", "relu1"))
#         graph.addEdge(Edge("relu1", "maxpool1"))

#         graph.addEdge(Edge("maxpool1", "conv2a"))

#         graph.addEdge(Edge("maxpool1", "conv2b"))
#         graph.addEdge(Edge("conv2b", "relu2"))

#         graph.addEdge(Edge("relu2", "avgpool2"))
#         graph.addEdge(Edge("conv2a", "avgpool2"))
#         graph.addEdge(Edge("avgpool2", "dropout"))
# #         graph.addEdge(Edge("dropout", "softmax"))
#         graph.display()

#         binder = Binder("PyTorch")
#         binder.saveBranched(graph, "/home/jatin17/workspace/pySeer/sketch/test_model.pth")


    def newGraph(self):
        graph = Graph()
        graph.addNode(Node("conv1", type="Conv2d", params={'in_channels':1, 'out_channels':6, 'kernel_size':(3,3)} ))
        graph.addNode(Node("bn1", type="BatchNorm2d", params={'num_features':6} ))
        graph.addNode(Node("relu1", type="ReLU", params={'inplace':False} ))
        graph.addNode(Node("maxpool1", type="MaxPool2d", params={'kernel_size':(3,3), 'stride':None, 'padding':None} ))
        graph.addNode(Node("conv2", type="Conv2d", params={'in_channels':6, 'out_channels':6, 'kernel_size':(3,3)} ))
        graph.addNode(Node("bn2", type="BatchNorm2d", params={'num_features':6} ))
        graph.addNode(Node("relu2", type="ReLU", params={'inplace':False} ))
        graph.addNode(Node("avgpool2", type="AvgPool2d", params={'kernel_size':(3,3), 'stride':None, 'padding':None} ))
        graph.addNode(Node("dropout", type="Dropout", params={'p':0.1} ))
        graph.addNode(Node("softmax", type="Softmax", params={} ))
        graph.addNode(Node("sigmoid", type="Sigmoid", params={} ))
        graph.addNode(Node("bceloss", type="BCELoss", params={} ))
        graph.addNode(Node("mseloss", type="MSELoss", params={} ))
        graph.addNode(Node("identity", type="Identity", params={} ))
        graph.addNode(Node("reshape", type="Reshape", params={} ))

        graph.addEdge(Edge("conv1", "bn1"))
        graph.addEdge(Edge("bn1", "relu1"))
        graph.addEdge(Edge("relu1", "maxpool1"))
        graph.addEdge(Edge("maxpool1", "conv2"))
        graph.addEdge(Edge("conv2", "bn2"))
        graph.addEdge(Edge("bn2", "relu2"))
        graph.addEdge(Edge("relu2", "avgpool2"))
        graph.addEdge(Edge("avgpool2", "dropout"))
        graph.addEdge(Edge("dropout", "softmax"))
        graph.addEdge(Edge("softmax", "sigmoid"))
        graph.addEdge(Edge("sigmoid", "bceloss"))
        graph.addEdge(Edge("bceloss", "mseloss"))
        graph.addEdge(Edge("mseloss", "identity"))
        graph.addEdge(Edge("identity", "reshape"))
        return graph

class Node(object):
    def __init__(self, id, type, params={}, learned_params={}, status=True, group=False, **kwargs):
        self.id = id
        self.type = type
        self.status = status
        self.setParams(params)
        self.setLearnedParams(learned_params)
        self.group = group

    def setParams(self, params):
        assert type(params) == type(dict())
        self.params = self.typeCast(params)

    def setLearnedParams(self, learned_params):
        assert type(learned_params) == type(dict())
        self.learned_params = learned_params

#     def __str__(self):
#         return self.__repr__()
#
#     def __repr__(self):
#         return '({}) {}{}'.format(self.id, self.type, self.params)

    def typeCast(self, params):
        dataType = {'in_channels': int, 'out_channels': int, 'kernel_size': int,
                    'stride': int, 'padding': int, 'bias': bool,
                    'num_features': int, 'in_features': int, 'out_features': int,
                    'p': float, 'subgraph': Graph, 'dilation': int, 'groups': int,
                    'padding_mode': str, 'eps': float, 'momentum': float,
                    'affine': bool, 'track_running_stats':bool, 'return_indices':bool,
                    'ceil_mode':bool, 'count_include_pad': bool, 'inplace': bool,
                    'dim': int}

        for key, value in params.items():
            cast = dataType.get(key)
#             print(key, "-->", cast)
            if type(value) == type(None):
                # use the None as is or use default
                params[key] = value
            elif type(value) == tuple:
                params[key] = tuple(map(cast, value))
            elif type(value) == list:
                params[key] = tuple(map(cast, value))
            elif type(value) == dict:
                if key == "subgraph":
                    for nodeId, param in value.items():
                        param = self.typeCast(param)
                        value.update({nodeId : param})
#                         print(nodeId, param)
            else:
#                 print(key, value)
                params[key] = cast(value)

        return params

    def getDetails(self):
        print("--------------")
        print(self.type)
        print(self.learned_params)

class Edge(object):
    def __init__(self, source, sink, status=True):
        self.source = source
        self.sink = sink
        self.status = status

class Save(object):
    def __init__(self, tab_text, saved_canvas, saved_arrows, saved_graph_active_edge, saved_graph_nodes, saved_graph_obj):
        self.tab_text = deepcopy(tab_text)
        self.saved_canvas = deepcopy(saved_canvas)
        self.saved_arrows = deepcopy(saved_arrows)
        self.saved_graph_active_edge = deepcopy(saved_graph_active_edge)
        self.saved_graph_nodes = deepcopy(saved_graph_nodes)
        self.saved_graph_obj = deepcopy(saved_graph_obj)





