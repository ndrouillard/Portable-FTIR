"""
Created on Sun Feb 21 2021

@author: Nathan Drouillard, modified from BitScope_GUI_fast.py
A special thanks is owed to Aananth Kanagaraj (Codenio)

Notes: -use BL_STREAM mode in bitlib_read_data_for_GUI
       -the stage functions are from "micronix_functions(Feb21).py"
"""
import numba
import tkinter as tk
import tkinter.font as font #this is needed but unused?
from tkinter.filedialog import asksaveasfile
import time
from datetime import datetime
import os

# import matplotlib.pyplot as plt
import numpy as np
# import drawnow as drawnow

from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg)
# Implement the default Matplotlib key bindings.
from matplotlib.backend_bases import key_press_handler
from matplotlib.figure import Figure

from pandas import DataFrame

from bitlib_read_data_for_GUI import stream #this is a script I wrote from "bitlib-read-data.py"

import serial
#%%

root = tk.Tk()
root.geometry("1024x768")
root.title("FTIR GUI")

myFont = tk.font.Font(family='Helvetica', size=15, weight='bold')

#%% Major variables
global Nt, scanRate, now
scanRate = 20000000 #1000000 is the default sample rate of the BitScope, 20 MHz is the max
Nt = 60000#12228 #maximum is 12228 but 60,000 is much faster?
myFont = ("Helvetica",12)
now = str(datetime.now()) #this is for naming the csv file by the date
#%%

#%% Micronix Stuff
c = 3e8
poslim = 1e-2 #1cm (these are the stage limits)
neglim = -1e-2
d = poslim + np.abs(neglim)
optical_t = np.linspace(0,d/c,Nt)

#%% Open the COM port
ser = serial.Serial('/dev/ttyUSB_MICRONIX',38400)

#%% Home the stage
def home():

    ser.write(b'1HOM\r')
    ser.flush()
    time.sleep(1)
    #ser.write(b'1WTM42\r')
    ser.write(b'1WST\r')
    time.sleep(1)
    print("stopped")
    ser.flush()
    #isstopped = ser.readline()
    ser.write(b'1ZRO\r')
    time.sleep(1)
    ser.flush()
    #zeroed = ser.readline()
    print("zeroed")

#%% Setup for feedback loop
def params():
    min_pos = float(startpos.get())
    max_pos = float(stoppos.get())

    ser.write(b'1VEL5.0\r') #set velocity to 5 mm/s
    time.sleep(1)
    ser.flush()
    #velset = ser.readline()
    print("velset")

    min_pos_str = "1TLN" + str(min_pos) + "\r"
    # ser.write(b'1POS?\r')
    # ser.write(b'1MVA0\r')
    min_pos_byt = str.encode(min_pos_str) #encode soft travel limit in the negative direction
    ser.write(min_pos_byt) #write it to the controller
    ser.flush()
    #neglim = ser.readline()
    time.sleep(1)
    print("neglim")

    max_pos_str = "1TLP" + str(max_pos) + "\r"
    max_pos_byt = str.encode(max_pos_str)
    ser.write(max_pos_byt)
    ser.flush()
    #poslim = ser.readline()
    time.sleep(1)
    print("poslim")

    ser.write(b'1EPL1\r') #ensure the correct encoder polarity for the feedback loop
    ser.flush()
    #polset = ser.readline()
    ser.write(b'1FBK3\r') #closed loop feedback mode
    ser.flush()
    #fbkset = ser.readline()
    ser.write(b'4DBD5,0\r') #set closed loop deadband parameters (0 means it will never timeout)
    ser.flush()
    time.sleep(1)
    print("Params set")
    #dbdset = ser.readline()

#%% Move the stage (moves one way, but not back and forth)
def move():

    #home()
    #time.sleep()
    #params()
    for i in range(0,4):
        # ser.write(b'1PGL0\r') #loop program continuously
        ser.write(b'1MLN\r') #move to negative limit
        time.sleep(1)
        print("moved neg")
        # ser.write(b'1MVA-2\r')
        ser.flush()
        ser.write(b'1WST\r')
        time.sleep(1)
        ser.flush()
        #movedneg = ser.readline()
        #ser.flush()
        #print(movedneg)
        # ser.write(b'1WTM5000\r') #wait for 5000 ms
        ser.write(b'1MLP\r') #move to positive limit
        # ser.write(b'1MVA2\r')
        time.sleep(1)
        ser.flush()
        ser.write(b'1WST\r')
        time.sleep(1)
        ser.flush()
        #movedpos = ser.readline()
        #ser.flush()
        print("movedpos")

#%% Close COM port (important)
def close():

    ser.close()

#%% GUI functions
global t_vec, y, w_vec, yw_vec, all_t_vec, all_y, all_w_vec, all_yw_vec
tic = time.time()
t_vec = np.empty(1)
y = np.empty(1)
w_vec = np.empty(1)
yw_vec = np.empty(1)
all_t_vec = np.empty(1)
all_y = np.empty(1)
all_w_vec = np.empty(1)
all_yw_vec = np.empty(1)
old_time = 0

def record():

    global Nt, scanRate, old_time
    global t_vec, y, w_vec, yw_vec, tic, all_t_vec, all_y, all_w_vec, all_yw_vec

    y = stream(scanRate,Nt)

    tmin = old_time
    tmax = time.perf_counter()
    old_time = tmax
    t_vec = np.linspace(tmin,tmax,len(y))
    dt = t_vec[1]-t_vec[0]
    w_vec = 2*np.pi/(2*dt)*np.linspace(-1,1,len(y))
    dw = w_vec[1]-w_vec[0]
    yw_vec = np.fft.fftshift(np.fft.fft(np.fft.fftshift(y)))

    return (t_vec, y, w_vec, yw_vec)

dummy_button = tk.Button(root, text="Example")
dummy_button.after(int(1e-6), record)

def append_data():

    global t_vec, y, w_vec, yw_vec, all_t_vec, all_y, all_w_vec, all_yw_vec

    all_y = np.append(all_y, y)
    all_t_vec = np.append(all_t_vec, t_vec)
    all_w_vec = np.append(all_w_vec, w_vec)
    all_yw_vec = np.append(all_yw_vec, yw_vec)

    count = len(all_yw_vec)
    data_count_disp.config(text=count)
    data_count_disp.after(int(1e-6),append_data)

    return (all_t_vec, all_y, all_w_vec, all_yw_vec)

data_count_disp = tk.Label(root, font = myFont)
data_count_disp.place(x=750, y=600)

data_count_text = tk.Label(root, text = 'Data Points Processed', font = myFont)
data_count_text.place(x=575, y=600)

def write_to_file():

    (t,y,w,yw) = append_data()
    data = np.array([t[1:],y[1:],w[1:],yw[1:]])
    data = data.T
    df = DataFrame(data, columns = ['Time','Voltage','Wavelength', 'Intensity'])
    file = open("/home/pi/Documents/BitScope Data"+ now +"save_test.csv","a")
    df.to_csv (file, sep='\t', index = False, header=True)
    print("Data saved")

#%% Plotting stuff

fig_time = Figure(figsize=(5,4))
ax_time = fig_time.add_subplot(111)
canvas_time = FigureCanvasTkAgg(fig_time, master=root)

f = Figure(figsize=(5,5),dpi=100)#, tight_layout=True)
f2 = Figure(figsize=(5,5),dpi=100)
#f3 = Figure(figsize=(5,5),dpi=100)
#d = f3.add_subplot(111)
a = f.add_subplot(111)
b = f2.add_subplot(111)
g = Figure(figsize=(5,5),dpi=100)
c = g.add_subplot(111)

canvas = FigureCanvasTkAgg(f, root)
canvas2 = FigureCanvasTkAgg(f2, root)

def plot():

    global t_vec, y, w_vec, yw_vec

    a.cla()
    a.plot(t_vec,y,'.-')
    a.set_xlabel('Time (s)')
    a.set_ylabel('Voltage (V)')

    b.cla()
    b.plot(w_vec,np.abs(yw_vec))
    b.set_xlabel('Frequency (Hz)')
    b.set_ylabel('Intensity (a.u.)')

    canvas.draw()
    canvas2.draw()
    canvas.get_tk_widget().place(x=25, y=25)
    canvas2.get_tk_widget().place(x=525, y=25)
    fig_plot.after(1,plot)

fig_plot = tk.Frame(root)
tk.Frame(plot()).pack()

#%% Buttons

start_stage_text = tk.Label(root, text = 'Start Position', font = myFont)
start_stage_text.place(x=100, y=530)
startpos = tk.StringVar(root)
startpos.set("0")
start_stage_spin = tk.Spinbox(root,
                        from_ = -6, to = 6,
                        width = 5,
                        textvariable = startpos,
                        font = myFont)
start_stage_spin.place(x=125, y=550)

stop_stage_text = tk.Label(root, text = 'Stop Position', font = myFont)
stop_stage_text.place(x=250, y=530)
stoppos = tk.StringVar(root)
stoppos.set("1")
start_spin = tk.Spinbox(root,
                        from_ = -6, to = 6,
                        width = 5,
                        textvariable = stoppos,
                        font = myFont)
start_spin.place(x=275, y=550)

button_home_stage = tk.Button(root,
    # command =
    text="Home",
    width = 10,
    height = 2,
    command = lambda: [home()],
    bg = "yellow",
    fg = "white",
    font = myFont,
    )
button_home_stage.place(x=100,y=580)

button_move = tk.Button(root, #this button is an edited version of the start_stage_button from FTIR_GUI_Thorlabs(Final).py
    text="Move Stage",
    width = 10,
    height = 2,
    command = lambda: [move()],#, data_count()],
    bg = "green",
    fg = "white",
    font = myFont,
    )
button_move.place(x=400, y=580)

button_record = tk.Button(root, #this button is an edited version of the start_stage_button from FTIR_GUI_Thorlabs(Final).py
    text="Start recording",
    width = 10,
    height = 2,
    command = lambda: [append_data()],#, data_count()],
    bg = "blue",
    fg = "white",
    font = myFont,
    )
button_record.place(x=250, y=580)

button_save = tk.Button(root, text = 'Save data', width = 10, height = 2, bg = 'purple', fg = 'white', command = lambda : [write_to_file()])
button_save.place(x=850, y = 580)

button_quit = tk.Button(root,
    text="Quit",
    command = lambda: [root.destroy()],#, close_BitScope()],
    width = 10,
    height = 2,
    bg = "red",
    fg = "black",
    font = myFont,
    )
button_quit.place(x=850,y=640)

#record()
#home()
params()
root.mainloop()