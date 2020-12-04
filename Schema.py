# class Graph1(object):
#     def __init__(self, name):
#         self.name = name
#         self.nodes = {}
#
#     def display(self):
#         print("=============== GRAPH =================")
#         n = len(self.nodes)
#         if n == 0:
#             print("Empty Graph")
#         else:
#             for id, node in self.nodes.items():
#                 if node.status == False:
#                     continue
#                 print(id, "->", node.get())
#         print("=======================================")
#
#     def __str__(self):
#         pass
#
#     def addNode(self, id, type, params=None, status=True, **kwargs):
#         node = Node1(id, type, params, status, **kwargs)
#         if not self.nodes.get(node.id):
#             self.nodes.update({node.id : node})
#
#     def addEdge(self, src_nodeId, dst_nodeId):
#         src_node = self.nodes.get(src_nodeId)
#         dst_node = self.nodes.get(dst_nodeId)
#         if src_node and dst_node:
#             src_node.addOutput(dst_node)
#             dst_node.addInput(src_node)
#         else:
#             print("Src or Dst node dostn't exists")
#
#
# class Node1(object):
#     def __init__(self, id, type, params=None, status=True, **kwargs):
#         self.id = id
#         self.type = type
#         self.params = params
#         self.status = status
#         self.inputs = []
#         self.outputs = []
#
#     def __str__(self):
#         return self.id+"-"+self.type
#
#     def get(self):
#         return self.outputs
#
#     def addOutput(self, node):
#         self.outputs.append(node)
#
#     def addInput(self, node):
#         self.inputs.append(node)


import onnx
from onnx import checker, helper
import onnx.defs as defs
from onnx import TensorProto, AttributeProto, ValueInfoProto, TensorShapeProto, \
    NodeProto, ModelProto, GraphProto, OperatorSetIdProto, TypeProto, IR_VERSION

class Graph1(object):
    def __init__(self, name):
        self.name = name
        self.nodes = {}

    def __str__(self):
        pass

    def addNode(self, id, type, params=None, status=True, **kwargs):
        node = Node1(id, type, params, status, **kwargs)
        if not self.nodes.get(node.id):
            self.nodes.update({node.id : node})

    def addEdge(self, src_nodeId, dst_nodeId):
        src_node = self.nodes.get(src_nodeId)
        dst_node = self.nodes.get(dst_nodeId)
        if src_node and dst_node:
#             src_node.addOutput(dst_nodeId)
            dst_node.addInput(src_nodeId)
        else:
            print("Src or Dst node dostn't exists")

    def display(self):
        print("=============== GRAPH =================")
        n = len(self.nodes)
        if n == 0:
            print("Empty Graph")
        else:
            for id, node in self.nodes.items():
                if node.status == False:
                    continue
                print(id, "->", node.get())
        print("=======================================")

    def display2(self):
        print("=============== GRAPH =================")
        n = len(self.nodes)
        if n == 0:
            print("Empty Graph")
        else:
            for id, node in self.nodes.items():
                if node.status == False:
                    continue
                print(node.type, node.inputs, node.outputs)
        print("=======================================")

    def convert(self):
        onnx_file_name = "test1.onnx"
        name="test"
        domain="test.domain"

        #Inputs
        inputs = list()
        inputs.append(helper.make_tensor_value_info('X' , TensorProto.FLOAT, [1]))
#         inputs.append(helper.make_tensor_value_info('W1', TensorProto.FLOAT, [1]))
#         inputs.append(helper.make_tensor_value_info('B1', TensorProto.FLOAT, [1]))
#         inputs.append(helper.make_tensor_value_info('W2', TensorProto.FLOAT, [1]))
#         inputs.append(helper.make_tensor_value_info('B2', TensorProto.FLOAT, [1]))
#         inputs.append(helper.make_tensor_value_info('W5', TensorProto.FLOAT, [1]))
#         inputs.append(helper.make_tensor_value_info('B5', TensorProto.FLOAT, [1]))
#         inputs.append(helper.make_tensor_value_info('W6', TensorProto.FLOAT, [1]))
#         inputs.append(helper.make_tensor_value_info('B6', TensorProto.FLOAT, [1]))
#         inputs.append(helper.make_tensor_value_info('W9', TensorProto.FLOAT, [1]))
#         inputs.append(helper.make_tensor_value_info('B9', TensorProto.FLOAT, [1]))


        #Nodes
        nodes = list()
        n = len(self.nodes)
        if n == 0:
            print("Empty Graph")
        else:
            for id, node in self.nodes.items():
                if node.status == False:
                    continue
                if len(node.inputs) == 0 :
                    node.inputs.append('X')
                output = node.id
                nodes.append(helper.make_node(node.type, node.inputs, node.outputs, name=name, domain=domain))

        # Outputs
        outputs = list()
        outputs.append(helper.make_tensor_value_info(output, TensorProto.FLOAT, [1]))

        graph = helper.make_graph(nodes,name,inputs,outputs)
        onnx_id = helper.make_opsetid(domain, 1)
        model = helper.make_model(graph, producer_name=name, opset_imports=[onnx_id])
        checker.check_model(model)
        print(helper.printable_graph(model.graph))


class Node1(object):
    def __init__(self, id, type, params=None, status=True, **kwargs):
        self.id = id
        self.type = type
        self.params = params
        self.status = status
        self.inputs = []
        self.outputs = []
        self.addOutput(self.id)

    def __str__(self):
        return self.id+"-"+self.type

    def get(self):
        return self.outputs

    def addOutput(self, nodeId):
        self.outputs.append(nodeId)

    def addInput(self, nodeId):
        self.inputs.append(nodeId)



graph = Graph1('test')

graph.addNode('1', 'Conv', params=dict(dilations=[1, 1], group=1, kernel_shape=[11, 11], pads=[2, 2, 2, 2], strides=[4, 4]))
graph.addNode('2', 'BatchNormalization')
graph.addNode('3', 'Relu')
graph.addNode('4', 'MaxPool')
graph.addNode('5', 'Conv')
graph.addNode('6', 'BatchNormalization')

graph.addEdge('1', '2')
graph.addEdge('2', '3')
graph.addEdge('3', '4')
graph.addEdge('2', '5')
graph.addEdge('5', '6')

graph.display()
graph.display2()
graph.convert()