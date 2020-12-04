from onnx import TensorProto, AttributeProto, ValueInfoProto, TensorShapeProto, \
    NodeProto, ModelProto, GraphProto, OperatorSetIdProto, TypeProto, IR_VERSION
import onnx
from onnx import checker, helper
import onnx.defs as defs
from onnx import mapping
from onnx.mapping import STORAGE_TENSOR_TYPE_TO_FIELD
from Graph import *


import collections
import numbers
from six import text_type, integer_types, binary_type

import google.protobuf.message
from onnx import TensorProto, AttributeProto, ValueInfoProto, TensorShapeProto, \
    NodeProto, ModelProto, GraphProto, OperatorSetIdProto, TypeProto, IR_VERSION
import onnx
import onnx.defs as defs
from onnx import mapping
from onnx.mapping import STORAGE_TENSOR_TYPE_TO_FIELD
from typing import Text, Sequence, Any, Optional, Dict, Union, TypeVar, Callable, Tuple, List, cast
import numpy as np  # type: ignore
from onnx import numpy_helper

class ONNXBinder(object):
    def __init__(self):
        pass

    def getPrintableModel(self, model):
        return helper.printable_graph(model.graph)

    # to export into onnx model
    def toTensor(self, numpy_array):
        return numpy_array.flatten().tolist()

    # for import into sketch
    def toNumpy(self, tensor):
        numpy_array = numpy.asarray(tensor)
#         # change the dtype to 'float64'
#         numpy_array = numpy_array.astype('float64')
        return numpy_array

    def isValid(self, t):
        if type(t) == type(None):
            return False
        else:
            return True

    def save(self, model, path):
        onnx.save(model, path)

    def parseModel(self, domain, graph, expInput=None, expOutput=None):
        order, expanded_order = graph.topologicalSort()
        index = 0

        #Inputs
        inputs = list()

        #inits
        initializers = list()

        #Nodes
        nodes = list()
#         print(len(expanded_order))
        for id, value in expanded_order.items():
            index = index + 1
            node = graph.nodes.get(id)
            name = node.type
            m = node.params
            l = node.learned_params
#             print(id, index, name, m)

            # it's important that the values in input and output are all string
#             layerName = prefix+"_"+str(id)
            layerName = str(id)
            input = list(map(str, value['prior']))
            if expOutput:
                expOutputNum = str(expOutput[0])
                input = [expOutputNum +"_"+ s for s in input]
                layerName = expOutputNum +"_"+ layerName

            if expInput:
               if len(input) == 0 :
                    input = expInput

            if expOutput and index == len(expanded_order):
                output = expOutput
                #XXX This handles the output of nested sequential modules
                # to come back into normal flow of ids
                layerName = expOutputNum #XXX
            else:
                output = [layerName]
            # for first node add a dummy input
            if len(input) == 0 :
                input = ['X']
                inputs.append(helper.make_tensor_value_info('X' , TensorProto.FLOAT, [1]))

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
                ratio = m.get('p')
            else:
                ratio = 0.1

            if m.get('kernel_size') :
                kernel_size = m.get('kernel_size')
                if type(kernel_size) == tuple:
                    kernel_size = list(kernel_size)
                else:
                    kernel_size = [kernel_size, kernel_size]
            else:
                kernel_size = [1,1]

            if m.get('stride') :
                stride = m.get('stride')
                if type(stride) == tuple:
                    stride = list(stride)
                else:
                    stride = [stride, stride]
            else:
                stride = [1,1]

            if m.get('padding') :
                padding = m.get('padding')
                if type(padding) == tuple:
                    padding = list(padding)
                    padding.extend(padding)
                else:
                    padding = [padding, padding, padding, padding]
            else:
                padding = [0,0,0,0]

            if m.get('subgraph'):
                subgraph = m.get('subgraph')

            # copy the network weights
            weight = l.get('weight')
            bias = l.get('bias')
            running_mean = l.get('running_mean')
            running_var = l.get('running_var')

            #helper.make_tensor(name='a',data_type=TensorProto.FLOAT, dims=(1,), vals=np.ones(1).tolist())
            if name == 'Conv2d':
                learned_input = ["learned_"+layerName+"_W", "learned_"+layerName+"_B"]
                input.extend(learned_input)

                # declare learned parameters
                inputs.append(helper.make_tensor_value_info("learned_"+layerName+"_W", TensorProto.FLOAT, [out_channels, in_channels, kernel_size[0], kernel_size[1]]))
                inputs.append(helper.make_tensor_value_info("learned_"+layerName+"_B", TensorProto.FLOAT, [out_channels]))

                # initialize learned parameters with existing weights
                if self.isValid(weight):
                    initializers.append(helper.make_tensor("learned_"+layerName+"_W", TensorProto.FLOAT, dims=[out_channels, in_channels, kernel_size[0], kernel_size[1]], vals=self.toTensor(weight) ))
                if self.isValid(bias):
                    initializers.append(helper.make_tensor("learned_"+layerName+"_B", TensorProto.FLOAT, dims=[out_channels], vals=self.toTensor(bias) ))

                nodes.append(helper.make_node("Conv", input, output, name=layerName, domain=domain, kernel_shape = kernel_size, strides = stride, pads = padding, dilations = [1, 1], group = 1))
            elif name == 'BatchNorm2d':
                learned_input = ["learned_"+layerName+"_W", "learned_"+layerName+"_B", "learned_"+layerName+"_M", "learned_"+layerName+"_V"]
                input.extend(learned_input)

                # declare learned parameters
                inputs.append(helper.make_tensor_value_info("learned_"+layerName+"_W", TensorProto.FLOAT, [num_features]))
                inputs.append(helper.make_tensor_value_info("learned_"+layerName+"_B", TensorProto.FLOAT, [num_features]))
                inputs.append(helper.make_tensor_value_info("learned_"+layerName+"_M", TensorProto.FLOAT, [num_features]))
                inputs.append(helper.make_tensor_value_info("learned_"+layerName+"_V", TensorProto.FLOAT, [num_features]))

                # initialize learned parameters with existing weights
                if self.isValid(weight):
                    initializers.append(helper.make_tensor("learned_"+layerName+"_W", TensorProto.FLOAT, [num_features], vals=self.toTensor(weight)))
                if self.isValid(bias):
                    initializers.append(helper.make_tensor("learned_"+layerName+"_B", TensorProto.FLOAT, [num_features], vals=self.toTensor(bias)))
                if self.isValid(running_mean):
                    initializers.append(helper.make_tensor("learned_"+layerName+"_M", TensorProto.FLOAT, [num_features], vals=self.toTensor(running_mean)))
                if self.isValid(running_var):
                    initializers.append(helper.make_tensor("learned_"+layerName+"_V", TensorProto.FLOAT, [num_features], vals=self.toTensor(running_var)))

                nodes.append(helper.make_node("BatchNormalization", input, output, name=layerName, domain=domain, epsilon = 9.99999974737875e-06, momentum = 1))
            elif name == 'ReLU':
                nodes.append(helper.make_node("Relu", input, output, name=layerName, domain=domain))
            elif name == 'Sigmoid':
                nodes.append(helper.make_node("Sigmoid", input, output, name=layerName, domain=domain))
            elif name == 'MaxPool2d':
                nodes.append(helper.make_node("MaxPool", input, output, name=layerName, domain=domain, kernel_shape = [3, 3], pads = [0, 0, 0, 0], strides = [2, 2]))
            elif name == 'AvgPool2d':
                nodes.append(helper.make_node("AveragePool", input, output, name=layerName, domain=domain, kernel_shape = [3, 3], pads = [0, 0, 0, 0], strides = [2, 2]))
            elif name == 'Linear':
                learned_input = [layerName+"_W", layerName+"_B"]
                input.extend(learned_input)

                # declare learned parameters
                inputs.append(helper.make_tensor_value_info("learned_"+layerName+"_W", TensorProto.FLOAT, [out_features, in_features]))
                inputs.append(helper.make_tensor_value_info("learned_"+layerName+"_B", TensorProto.FLOAT, [out_features]))

                # initialize learned parameters with existing weights
                if self.isValid(weight):
                    initializers.append(helper.make_tensor("learned_"+layerName+"_W", TensorProto.FLOAT, [out_features, in_features], vals=self.toTensor(weight)))
                if self.isValid(bias):
                    initializers.append(helper.make_tensor("learned_"+layerName+"_B", TensorProto.FLOAT, [out_features], vals=self.toTensor(bias)))

                nodes.append(helper.make_node("Gemm", input, output, name=layerName, domain=domain, alpha = 1, beta = 1, transB = 1))
            elif name == 'Dropout':
                nodes.append(helper.make_node("Dropout", input, output, name=layerName, domain=domain, ratio = ratio))
            elif name == 'Softmax':
                nodes.append(helper.make_node("Softmax", input, output, name=layerName, domain=domain))
            elif name == 'Identity':
                nodes.append(helper.make_node("Identity", input, output, name=layerName, domain=domain))
            elif name == 'Reshape':
                nodes.append(helper.make_node("Reshape", input, output, name=layerName, domain=domain))
            elif name == 'BCELoss':
                nodes.append(helper.make_node(name, input, output, name=layerName, domain=domain))
            elif name == 'MSELoss':
                nodes.append(helper.make_node(name, input, output, name=layerName, domain=domain))
            elif name == 'Sequential':
                sub_nodes, sub_inputs, sub_outputs, sub_initializers = self.parseModel(domain, subgraph, input, output)
#                 onnx_graph = helper.make_graph(sub_nodes, model_name", sub_inputs, sub_outputs)
#                 print(helper.printable_graph(onnx_graph))
                nodes.extend(sub_nodes)
                inputs.extend(sub_inputs)
                initializers.extend(sub_initializers)
            else:
                # Group or Sequential nodes
                if node.group == True:
                    sub_nodes, sub_inputs, sub_outputs, sub_initializers = self.parseModel(domain, subgraph, input, output)
                    nodes.extend(sub_nodes)
                    inputs.extend(sub_inputs)
                    initializers.extend(sub_initializers)
                else:
                    print('Not Implement',name)

        # Outputs
        outputs = list()
        outputs.append(helper.make_tensor_value_info(layerName, TensorProto.FLOAT, [1]))
        return nodes, inputs, outputs, initializers

    def exportModel(self, graph):
        # ToDo make them variables coming from state/user
        producer = "sketch"
        model_name="model_name"
        domain="onnx.ai"
        version = 1

        nodes, inputs, outputs, initializers = self.parseModel(domain, graph)
        onnx_graph = helper.make_graph(nodes, model_name, inputs, outputs, initializer=initializers)
        onnx_id = helper.make_opsetid(domain, version)
        model = helper.make_model(onnx_graph, producer_name=producer, opset_imports=[onnx_id])
        checker.check_model(model)
        return model

    def load(self, path):
        model = onnx.load(path)
        return model

    def get_attribute(self, attr, subgraphs=False):  # type: (AttributeProto, bool) -> Union[Text, Tuple[Text, List[GraphProto]]]
        content = []
        content.append(attr.name)
        content.append("=")

        def str_float(f):  # type: (float) -> Text
            # NB: Different Python versions print different numbers of trailing
            # decimals, specifying this explicitly keeps it consistent for all
            # versions
            return '{:.15g}'.format(f)

        def str_int(i):  # type: (int) -> Text
            # NB: In Python 2, longs will repr() as '2L', which is ugly and
            # unnecessary.  Explicitly format it to keep it consistent.
            return '{:d}'.format(i)

        def str_str(s):  # type: (Text) -> Text
            return repr(s)

        _T = TypeVar('_T')  # noqa

        def str_list(str_elem, xs):  # type: (Callable[[_T], Text], Sequence[_T]) -> Text
            return '[' + ', '.join(map(str_elem, xs)) + ']'

        # for now, this logic should continue to work as long as we are running on a proto3
        # implementation. If/when we switch to proto3, we will need to use attr.type

        # To support printing subgraphs, if we find a graph attribute, print out
        # its name here and pass the graph itself up to the caller for later
        # printing.
        graphs = []
        if attr.HasField("f"):
            content.append(str_float(attr.f))
        elif attr.HasField("i"):
            content.append(str_int(attr.i))
        elif attr.HasField("s"):
            # TODO: Bit nervous about Python 2 / Python 3 determinism implications
            content.append(repr(_sanitize_str(attr.s)))
        elif attr.HasField("t"):
            if len(attr.t.dims) > 0:
                content.append("<Tensor>")
            else:
                # special case to print scalars
                field = STORAGE_TENSOR_TYPE_TO_FIELD[attr.t.data_type]
                content.append('<Scalar Tensor {}>'.format(str(getattr(attr.t, field))))
        elif attr.HasField("g"):
            content.append("<graph {}>".format(attr.g.name))
            graphs.append(attr.g)
        elif attr.floats:
            content.append(str_list(str_float, attr.floats))
        elif attr.ints:
            content.append(str_list(str_int, attr.ints))
        elif attr.strings:
            # TODO: Bit nervous about Python 2 / Python 3 determinism implications
            content.append(str(list(map(_sanitize_str, attr.strings))))
        elif attr.tensors:
            content.append("[<Tensor>, ...]")
        elif attr.graphs:
            content.append('[')
            for i, g in enumerate(attr.graphs):
                comma = ',' if i != len(attr.graphs) - 1 else ''
                content.append('<graph {}>{}'.format(g.name, comma))
            content.append(']')
            graphs.extend(attr.graphs)
        else:
            content.append("<Unknown>")
        if subgraphs:
            return ' '.join(content), graphs
        else:
            return ' '.join(content)


#     def get_dim(self, dim):  # type: (TensorShapeProto.Dimension) -> Text
#         which = dim.WhichOneof('value')
#         assert which is not None
#         return str(getattr(dim, which))
#
#     def get_type(self, t):  # type: (TypeProto) -> Text
#         if t.WhichOneof('value') == "tensor_type":
#             s = TensorProto.DataType.Name(t.tensor_type.elem_type)
#             if t.tensor_type.HasField('shape'):
#                 if len(t.tensor_type.shape.dim):
#                     s += str(', ' + 'x'.join(map(get_dim, t.tensor_type.shape.dim)))
#                 else:
#                     s += str(', scalar')
#             return s
#         if t.WhichOneof('value') is None:
#             return ""
#         return 'Unknown type {}'.format(t.WhichOneof('value'))
#
#     def get_value_info(self, v):  # type: (ValueInfoProto) -> Text
#         s = '%{}'.format(v.name)
#         if v.type:
#             s = '{}[{}]'.format(s, self.get_type(v.type))
#         return s

    def get_graph(self, graph):  # type: (GraphProto, Text) -> Text
        sketch_graph = Graph()

        # header
        model_name = graph.name

#         #method-1: index of tensor values
#         initialized = dict([(init.name, numpy_helper.to_array(init)) for init in graph.initializer])

        #method-2: index of position
        initializer_list = list(graph.initializer)
        initializer_index = dict([(initializer_list[index].name, index) for index in range(len(initializer_list))])

        # read the model architecture
        for node in graph.node:
            printed_attrs = [self.get_attribute(attr) for attr in node.attribute]
            attributes = ', '.join(sorted(printed_attrs))
            attributes = eval("dict("+attributes+")")
            learned_token = "learned_"
            actual_inputs = [input_name for input_name in node.input if learned_token not in input_name and input_name != 'X']
            learned_inputs = [input_name for input_name in node.input if learned_token in input_name and input_name != 'X']

#             actual_inputs = [input_name for input_name in node.input if input_name not in initializer_index]
#             learned_inputs = [input_name for input_name in node.input if input_name in initializer_index]


            # Parse learned parameters
            # "learned_"+layerName+"_W"
            weight, bias, running_mean, running_var = None, None, None, None
            for learned_input in learned_inputs:
#                 print(learned_input)
#                 print(initializer_list)
#                 print(initializer_list[initializer_index[learned_input]])
                tensor = numpy_helper.to_array(initializer_list[initializer_index[learned_input]])
#                 print(tensor.shape)
                if learned_input.find("_W") > 0:
                    weight = tensor
                elif learned_input.find("_B") > 0:
                    bias = tensor
                elif learned_input.find("_M") > 0:
                    running_mean = tensor
                elif learned_input.find("_V") > 0:
                    running_var = tensor
                else:
                    print("Unrecognized initializer: " + str(learned_input))

#             print(actual_inputs)
            layerMap = {'Conv':'Conv2d', 'BatchNormalization': 'BatchNorm2d',
                        'Relu': 'ReLU', 'Sigmoid': 'Sigmoid', 'MaxPool': 'MaxPool2d',
                        'AveragePool': 'AvgPool2d', 'Gemm': 'Linear',
                        'Dropout':'Dropout', 'Softmax':'Softmax', 'Identity':'Identity',
                        'Reshape':'Reshape', 'BCELoss':'BCELoss', 'MSELoss':'MSELoss'}

            paramMap = {'kernel_shape':'kernel_size', 'strides': 'stride',
                    'pads': 'padding', 'ratio': 'p', 'dilations': 'dilation',
                    'epsilon': 'eps', 'group':'groups'}

            keys = list(attributes.keys())
            for key in keys:
                key_new = paramMap.get(key)
                if key_new:
                    value = attributes[key]
                    del attributes[key]
                    # XXX as ONNX has 4 pad values just take first 2 for Graph
                    if key_new == "padding":
                        value = value[:2]
                    if type(value) == list:
                        value = tuple(value)
                    attributes[key_new] = value

            id = node.name
            name = layerMap.get(node.op_type)

            #copy existing weights into learned_parameters
            if name == 'Conv2d':
                out_channels, in_channels = weight.shape[0], weight.shape[1]
                params_extra = {'in_channels':in_channels, 'out_channels':out_channels}
                attributes.update(params_extra)
            elif name == 'BatchNorm2d':
                num_features = weight.shape[0]
                params_extra = {'num_features':num_features}
                attributes.update(params_extra)
            elif name == 'Linear':
                out_features, in_features, = weight.shape[0], weight.shape[1]
                params_extra = {'out_features':out_features, 'in_features':in_features}
                attributes.update(params_extra)

            learned_params = {'weight':weight, 'bias':bias, 'running_mean':running_mean, 'running_var':running_var}
            if name:
                sketch_graph.addNode(Node(id, type=name, params=attributes, learned_params=learned_params))
            else:
                sketch_graph.addNode(Node(id, type='NotImplemented', params={}, learned_params={}))
                print('Not Implement',name)

            for in_node_id in actual_inputs:
#                 print(in_node_id + " --> "+id)
                sketch_graph.addEdge(Edge(in_node_id, id))

        return sketch_graph


    def importModel(self, model):
        graph = self.get_graph(model.graph)
        return graph

