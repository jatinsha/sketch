import inspect

def stacktrace():
    for i in range(3):
        frame = inspect.stack()[i]
        print('fileName: '+ frame[1], 'lineno: '+ str(frame[2]), 'method:'+ frame[3])

def log(msg):
    print('['+ inspect.stack()[0][3] +']'+'['+ inspect.stack()[1][3] + ']: '+ msg)
