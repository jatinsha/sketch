################################################################################
# This file defines utility classes and tools
################################################################################

import copy

class Clipboard(object):
    def __init__(self, bufferLength=30):
        self.bufferLength = bufferLength
        self.buffer = list()
        self.current = 0

    def __repr__(self):
        return "Clipboard(["+ str(self.bufferLength)+','+str(self.buffer) + "])"

    def __str__(self):
        return str(self.buffer)

    def add(self, state):
        state = copy.deepcopy(state)
        # if we make changes at an intermediate state
        # set this as present and make changes from here
        if self.current !=0 :
            for i in range(self.current):
                self.current -= 1
                self.buffer.remove(self.buffer[0])
        # insert new state in the buffer
        self.buffer.insert(self.current, state)
        # if buffer exceeds max capacity then remove last element
        if len(self.buffer) > self.bufferLength :
            self.buffer.pop()

    def undo(self):
        if self.current < len(self.buffer)-1:
            self.current += 1

    def redo(self):
        if self.current > 0:
            self.current -= 1

    def get(self):
        return self.buffer[self.current]

    def testMe(self):
        c = Clipboard()
        c.add(0)
        c.add(1)
        c.add(2)
        c.add(3)#3
        print(c.get())
        print(c)
        c.undo()#2
        print(c.get())
        c.undo()#1
        print(c.get())
        c.redo()#2
        print(c.get())
        print(c)
        c.add(13)#13
        c.add(14)#14
        c.add(15)#15
        print(c.get())
        print(c)


