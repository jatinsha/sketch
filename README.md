# Sketch

## Overview
Sketch is a Drawing-based Neural Network Development Tool.

## Requirements
Install python3 and then make sure you have the following python packages installed. 
Some of them may be already available while the others may require installation through pip.
- numpy
- tkinter
- tkinter-dnd
- PIL
- multiprocessing
- pickle
- getpass
- glob
- six
- copy
- inspect
- google.protobuf.message
- typing

* Required if you need LuaTorch kernel
- PyTorch (This is a wraper around LuaTorch/torch7 for Python and not the official pytorch)
- PyTorchAug 

* Required if you need PyTorch kernel
- torch

* Required if you need ONNX kernel
- onnx


## Setup
1. Please download/clone the repository from https://github.com/jatinsha/sketch.
2. Go inside the ‘sketch’ directory. 
``` 
cd sketch 
```

## Running Sketch
1. Run the GUI tool using ‘python3 testSketch’
```
python3 testSketch.py
```
2. This should bring up a Graphical User Interface (GUI) on your screen. At the center of the screen you'll see a blank canvas (or for returning users the tool will automatically load the previous working projects).
3. On the top you'll see a Taskbar. Here choose the desired Kernel (e.g.  ONNX). Make sure you have the specified toolchain (i.e. LuaTorch, PyTorch) installed in your system to use them.

## Draw
On the left side you'd see a Toolbox with various popular neural network layers. You can Drag and Drop them to the canvas and connect them to each other through interconnections. Click on the border of any layer which would create a green link. Now drag it to any other layer and release the mouse to complete the connection. 
For instance, drag Conv2d, BatchNorm2d and ReLU one by one to the canvas. Click-down on the Blue edges of these blocks to start the Green inter-connection/link and then drop that on another block to complete a connection.

## Delete
Select an element by left click, this will change it's color to Blue which signifies that it is selected. You can also select multiple items together by creating a selection box using mouse. Use <Ctrl + Delete> to delete selected elements. 
This is to prevent any accidental deletes. 

## Compile
Once you connect Conv2d -> BatchNorm2d -> ReLU, you have a basic model ready. Hit "Compile" button and choose a file name (e.g. test.onnx). The tool will compile the sketch and save the onnx file. It will also show the output on a new text editor on right side.

## Edit Properties
Right click on any Layer/Block and its properties will show up in the "Node and Default Edit" window. You can edit them as desired.

## Create Custom Layers
Drag the Yellow Sequential Block into the existing canvas. This will activate the "Group Canvas" window below. "Double right-click" on Sequential Block that you just dragged on the canvas and Change the name to “ConvBNReLU”. Now whatever model you draw within the Group Canvas would go inside the custom ConvBNReLU Layer. You can edit the properties of individual layers like before and export them to say ConvBNReLU.sk to use them in future.



## Cite this work
To cite this work, please use the following Bibtex entry-

```
@misc{sharma2020,
      title={Draw your Neural Networs},
      author={Jatin Sharma and Shobha Lata},
      year={2020},
      eprint={2010.05123},
      archivePrefix={arXiv},
      primaryClass={cs.AI},
      url = {https://arxiv.org/abs/2010.05123}
}
```

