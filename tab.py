from os import path
import inspect

from tkinter import *
from tkinter import ttk

from tkinter import *
from tkinter import filedialog
from tkinter import Menu
from tkinter import scrolledtext
from tkinter import messagebox
from DirectoryTree import *


################################################################################
# DOM
################################################################################
dom = {}
dom['cwd'] = os.getcwd()
dom['openFiles'] = {}
dom['openTabs'] = {}
dom['tabControl'] = None

################################################################################
# Helper methods
################################################################################

def stacktrace():
    for i in range(3):
        frame = inspect.stack()[i]
        print('fileName: '+ frame[1], 'lineno: '+ str(frame[2]), 'method:'+ frame[3])

def log(msg):
    print('['+ inspect.stack()[0][3] +']'+'['+ inspect.stack()[1][3] + ']: '+ msg)
#     if inspect.stack()[0] and inspect.stack()[1]:
#         print('['+ inspect.stack()[0][3] +']'+'['+ inspect.stack()[1][3] + ']: '+ msg)
#     else:
#         if inspect.stack()[0]:
#             print('['+ inspect.stack()[0][3] + msg)
#         if inspect.stack()[1]:
#             print('['+ inspect.stack()[1][3] + msg)

def file_content(filepath):
    if path.isfile(filepath):
        file_new = open(filepath, "r+")
        content = file_new.read()
        file_new.close()
    else:
        content = None
    return content

def open_tab(tab_name=None):
    if tab_name == None or tab_name == '' :
         tab_name = dom['cwd'] + '/Untitled.txt'

    tab = dom['openTabs'].get(tab_name)
    if tab == None:
        tab = ttk.Frame(dom['tabControl'])
        dom['tabControl'].add(tab, text=tab_name)
        dom['openTabs'].update( {tab_name : tab} )
        add_scrollbox(tab, file_content(tab_name))
        log(tab_name + ' (new)')
    else:
        log(tab_name + ' (existing)')

    # focus on open
    dom['tabControl'].select(tab)
    return tab

def add_scrollbox(tab, content=None):
    txt_new = scrolledtext.ScrolledText(tab)
    txt_new.pack(expand=True, fill='both')
    txt_new.bind("<Control-s>", clicked_save)
    if content:
        txt_new.insert(INSERT, content)
    else:
        # empty file content into the scrollable/editable text region
        txt_new.insert(INSERT,'<----- You sketch goes here ----->\n')

def file_open(filepath):
    # XXX focus on opened tab
    # create new tab with file name as label
    tab_new = open_tab(filepath)



################################################################################
# Tab Control-MiddlePane (ToDo: add/delete tabs)
################################################################################
def init_tabControl(frame):
    # XXX load last opened windows before closed
    dom['tabControl'] = ttk.Notebook(frame)
    dom['tabControl'].pack(expand=1, fill='both')
    tab_new = open_tab()


################################################################################
# Callback methods
################################################################################
def callback_changed(filepath):
    # on file change set active/changed
    pass

def clicked_new():
    tab_new = open_tab()

def clicked_open():
    # file dialog - specific extensions
    filepath = filedialog.askopenfilename(filetypes = (("Text files","*.txt"), ("all files","*.*"), ("Sketch files","*.sk") ))
    log(filepath)
    file_open(filepath)

def clicked_close():
    tab_id = tab_control.select()
    tab_text = tab_control.tab(tab_id, "text")
    current_txt = event.widget
    log(tab_text)

def clicked_save(event):
    tab_id = tab_control.select()
    tab_text = tab_control.tab(tab_id, "text")
    log(tab_text)
    current_txt = event.widget
    content = current_txt.get('1.0', 'end-1c')
    filepath = tab_text
    file_new = open(filepath, "w+")
    file_new.write(content)
    file_new.close()

# def clicked_save(event):
# #     tab_id = tab_control.select()
# # #     tab_id = tab_control.index(tab_control.select())
# #     tab_text = tab_control.tab(tab_id, "text")
# #     t = tab_control.tab(tab_id)
# #     print('id:', tab_id)
# #     print('name', tab_text)
# #     print(t)
# #     print(event)
# #     list = tab_control.winfo_children()
# #     print(list)
# #     print(list[0].winfo_children())
# #     for item in list :
# #         print(item)
#     print(event.widget.children.values())
#     print(event.widget)
#     current_txt = event.widget
#     print(current_txt.get('1.0', 'end-1c'))


#     # create scrollable/editable text region in new tab
#     txt_new = scrolledtext.ScrolledText(tab_new)
#     txt_new.pack(expand=True, fill='both')
#     # copy the file content into the scrollable/editable text region
#     file_new = open(file,"r+")
#     content = file_new.read()
#     txt_new.insert(INSERT, content)
#
#     textFile = open('/home/colin/documents/prog/py/todopad/todo', 'w')
#     #contents = self.textPad.get(self, 1.0, END) # The line in question
#     #textFile.write(contents)
#     textFile.close()
#     root.destroy()


################################################################################
# Main Window
################################################################################
window = Tk()
window.title("Sketch")
window.geometry('1200x800') # wxh


################################################################################
# Menu Bar
################################################################################
menu = Menu(window)
item_file = Menu(menu)
item_file.add_command(label='New', command=clicked_new)
item_file.add_command(label='Open', command=clicked_open)
item_file.add_command(label='Save', command=clicked_save)
item_file.add_command(label='Save As', command=None)
item_file.add_command(label='Close', command=clicked_close)
item_file.add_separator()
item_file.add_command(label='Other', command=None)

item_import = Menu(menu, tearoff=0)
item_import.add_command(label='Import sketch', command=None)
item_import.add_command(label='import code', command=None)

item_run = Menu(menu)
item_run.add_command(label='execute', command=None)
item_run.add_command(label='debug', command=None)

item_kernel = Menu(menu)
item_kernel.add_command(label='luaTorch', command=None)
item_kernel.add_command(label='pyTorch', command=None)
item_kernel.add_command(label='TensorFlow', command=None)

menu.add_cascade(label='File', menu=item_file)
menu.add_cascade(label='Import', menu=item_import)
menu.add_cascade(label='Run', menu=item_run)
menu.add_cascade(label='Kernel', menu=item_kernel)
window.config(menu=menu)


################################################################################
# Pan Windows
################################################################################
win = PanedWindow(window)
# win.pack(fill = BOTH, expand = 1)
# win.grid(column=0, row=0, sticky='nswe')
win.grid()

left = PanedWindow(win)
win.add(left)

middle = PanedWindow(win)
win.add(middle)

right = PanedWindow(win)
win.add(right)


init_tabControl(middle)
DirectoryTree(right)


################################################################################
# Widgets
################################################################################

# lbl1 = Label(tab1, text= 'label1')
# lbl1.grid(column=0, row=0)
#
# lbl2 = Label(tab2, text= 'label2')
# lbl2.grid(column=0, row=0)
#
# scale = Scale(tab3, orient = HORIZONTAL)
# scale.grid(column=0, row=0)
#
# btn = Button(tab1, text = "OK")
# btn.grid(column=0, row=0)



################################################################################
# End
################################################################################
window.mainloop()
