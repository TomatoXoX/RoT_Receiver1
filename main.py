import socket
import datetime
import tkinter
from tkinter import ttk
from tkinter import messagebox
import string
import random
import threading
import time
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from wisepaasdatahubedgesdk.EdgeAgent import EdgeAgent
import wisepaasdatahubedgesdk.Common.Constants as constant
from wisepaasdatahubedgesdk.Model.Edge import EdgeAgentOptions, MQTTOptions, DCCSOptions, EdgeData, EdgeTag, EdgeStatus, EdgeDeviceStatus, EdgeConfig, NodeConfig, DeviceConfig, AnalogTagConfig, DiscreteTagConfig, TextTagConfig
from wisepaasdatahubedgesdk.Common.Utils import RepeatedTimer
from pymongo import MongoClient
uri = "mongodb+srv://trunghothegadfly:dtrung2003@cluster0.wm7pzmb.mongodb.net/?retryWrites=true&w=majority"
# Create client
client = MongoClient(uri,server_api=ServerApi('1'))
db = client["RoT"]
collection = db["3D_Printer_Status"]
collection2 = db["3D_Printer_Data"]
# Connect to the ESP3D Telnet server
HOST = '192.168.1.4'
PORT = 8888
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST, PORT))
def check_temp():
    cmd = 'M105\n'
    s.send(cmd.encode('utf-8'))
    time.sleep(1)
    # Wait for the response
    data = s.recv(1028).decode('utf-8')
    temp_num = []
    if len(data) >= 18 and len(data) <= 35:
        for i in range(len(data)):
            a=data[i]
            if a.isdigit():
                temp_num.append(int(a))

    if len(temp_num) > 0:
        if temp_num[0] <= 2:
            temp_num = temp_num[0:4]
            temperature = temp_num[0] * 100 + temp_num[1]*10 + temp_num[2]*1  + temp_num[3] * 0.1
            print(temperature)
            return temperature
        else:
            temp_num = temp_num[0:4]
            temperature = temp_num[0] * 10 + temp_num[1]*1  + temp_num[2]*0.1 + temp_num[3] * 0.01
            print(temperature)
            return temperature

def send_command(command):
    model_string = "echo:Print time:"
    cmd= command+"\n"
    s.send(cmd.encode('utf-8'))
    time.sleep(1)
    data = s.recv(4096).decode('utf-8')
    check = model_string in data
    if check == True:
        print(data[17:23])
        return data[17:23]
    else:
        return "Busy"

while 1>0:
    collection.insert_one({"temperature":check_temp()})
    collection2.insert_one({"Status": send_command("M27\n")})
# Close the connection
s.close()