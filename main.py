import datetime
import socket
import time
import tkinter as tk
from tkinter import scrolledtext, ttk
import threading

from wisepaasdatahubedgesdk.EdgeAgent import EdgeAgent
import wisepaasdatahubedgesdk.Common.Constants as constant
from wisepaasdatahubedgesdk.Model.Edge import EdgeAgentOptions, MQTTOptions, DCCSOptions, EdgeData, EdgeTag, EdgeStatus, \
    EdgeDeviceStatus, EdgeConfig, NodeConfig, DeviceConfig, AnalogTagConfig, DiscreteTagConfig, TextTagConfig
from wisepaasdatahubedgesdk.Common.Utils import RepeatedTimer

sending_data = False
edgeAgent = None
HOST = '192.168.1.10'
PORT = 8888
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
value_for_temp = 0
ans = 0
def get_temp_value(value):
    global value_for_temp
    value_for_temp = value

def get_pro_value(value1,value2):
    global ans
    ans = (value1/value2)*100
def toggle_send_data():
    global sending_data
    sending_data = not sending_data
    if sending_data:
        send_SDK_button.config(text="Stop Sending Data")
        send_data_loop()
    else:
        send_SDK_button.config(text="Send Data to DB")

def send_data_loop():
    if sending_data:
        send_data_SDK(edgeAgent, value_for_temp, ans)
        root.after(1000, send_data_loop)  # Adjust the time interval as needed
def process_log(log_data):
    log_display.insert(tk.END, log_data + '\n')
    log_display.see(tk.END)

    if "SD printing byte" in log_data:
        try:
            progress_data = log_data.split("SD printing byte")[1].strip()
            current_byte, total_byte = map(int, progress_data.split('/'))
            update_progress_bar(current_byte, total_byte)
            get_pro_value(current_byte,total_byte)
        except Exception as e:
            print("Error parsing progress:", e)

    if "ok T:" in log_data:
        try:
            temp_data = log_data.split("ok T:")[1].strip()
            current_temp, target_temp, pid_number = temp_data.split(" ", 2)
            current_temp = float(current_temp)
            target_temp = float(target_temp.split('/')[1])
            pid_number = int(pid_number.split('@:')[1])
            update_temperature(current_temp, target_temp, pid_number)
            get_temp_value(current_temp)
        except Exception as e:
            print("Error parsing temperature:", e)

def recv_log_messages():
    buffer = ""
    while True:
        data = s.recv(4096).decode('utf-8')
        if data:
            buffer += data
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                process_log(line.strip())
        time.sleep(0.1)

def send_command():
    command = command_entry.get()
    cmd = command + "\n"
    s.send(cmd.encode('utf-8'))
    command_entry.delete(0, tk.END)

class PeriodicSend:
    def __init__(self, master):
        self.master = master
        self.frame = tk.Frame(self.master)
        self.frame.pack()

        self.periodic_command_entry = tk.Entry(self.frame, width=30)
        self.periodic_command_entry.pack(side=tk.LEFT)

        self.interval_entry = tk.Entry(self.frame, width=5)
        self.interval_entry.pack(side=tk.LEFT)
        self.interval_entry.insert(0, "5")

        self.periodic_sending = False
        self.toggle_button = tk.Button(self.frame, text="Start Periodic Send", command=self.toggle_periodic_send)
        self.toggle_button.pack(side=tk.LEFT)

    def periodic_send(self):
        if self.periodic_sending:
            commands = self.periodic_command_entry.get().split(';')
            for command in commands:
                cmd = command.strip() + "\n"
                s.send(cmd.encode('utf-8'))
            self.master.after(int(self.interval_entry.get()) * 1000, self.periodic_send)

    def toggle_periodic_send(self):
        self.periodic_sending = not self.periodic_sending
        if self.periodic_sending:
            self.toggle_button.config(text="Stop Periodic Send")
            self.master.after(int(self.interval_entry.get()) * 1000, self.periodic_send)
        else:
            self.toggle_button.config(text="Start Periodic Send")

def add_periodic_send():
    periodic_sends.append(PeriodicSend(root))


def update_progress_bar(current_byte, total_byte):
    progress = (current_byte / total_byte) * 100
    progress_var.set(progress)
    progress_label.config(text=f"Progress: {progress:.2f}%")

def update_temperature(current_temp, target_temp, pid_number):
    temp_var.set(f"Current Temp: {current_temp:.2f}°C\nTarget Temp: {target_temp:.2f}°C\nPID: {pid_number}")

# Create the main window
root = tk.Tk()
root.title("RoT 3-D Manager SoftwareTM")
# Create a frame for the host and port input
connection_frame = tk.Frame(root)
connection_frame.pack(pady=10)
def connect_to_host():
    host = host_entry.get()
    port = int(port_entry.get())
    s.connect((host, port))

    connect_button.config(text="Connected", state=tk.DISABLED)

    recv_thread = threading.Thread(target=recv_log_messages, daemon=True)
    recv_thread.start()

def SDK_connect(api_link, NodeID, cred_key):
    global edgeAgent  # Added global keyword to modify the global variable
    edgeAgentOption = EdgeAgentOptions(nodeId=NodeID)
    edgeAgentOption.connectType = constant.ConnectType['DCCS']
    DCCS_Config = DCCSOptions(apiUrl=api_link, credentialKey=cred_key)
    edgeAgentOption.DCCS = DCCS_Config
    edgeAgent = EdgeAgent(edgeAgentOption)
    edgeAgent.connect()

    # Update the SDK connection button's text
    SDK_connection_button.config(text='Connected to SDK Database', state=tk.DISABLED)


def send_data_SDK(agent,data1,data2):
    data = categorization(data1,data2)
    agent.sendData(data)
def categorization(temperature, progress):
    edgeData = EdgeData()
    Temp_Device = "3D Printer"
    tag_Temp_name = "Temperature"
    value_temp = temperature
    tag_Progress_name = "Progression"
    value_progress = progress
    tag_Temp = EdgeTag(Temp_Device, tag_Temp_name, value_temp)
    tag_Progress = EdgeTag(Temp_Device, tag_Progress_name, value_progress)
    edgeData.tagList.append(tag_Progress)
    edgeData.tagList.append(tag_Temp)
    edgeData.timestamp = datetime.datetime.now()
    return edgeData
def generateConfig():
    config = EdgeConfig()
    nodeConfig = NodeConfig(nodeType=constant.EdgeType['Gateway'])
    config.node = nodeConfig
    deviceConfig = DeviceConfig(id='3D Printer',
                                name='3D Printer',
                                description='Device',
                                deviceType='Smart Device',
                                retentionPolicyName='')
    analog1 = AnalogTagConfig(name='Temperature',
                                             description='ATag ',
                                             readOnly=False,
                                             arraySize=0,
                                             spanHigh=1000,
                                             spanLow=0,
                                             engineerUnit='',
                                             integerDisplayFormat=4,
                                             fractionDisplayFormat=2)
    analog2 = AnalogTagConfig(name='Progression',
                              description='ATag ',
                              readOnly=False,
                              arraySize=0,
                              spanHigh=1000,
                              spanLow=0,
                              engineerUnit='',
                              integerDisplayFormat=4,
                              fractionDisplayFormat=2)
    deviceConfig.analogTagList.append(analog1)
    deviceConfig.analogTagList.append(analog2)
    config.node.deviceList.append(deviceConfig)
    return config

def upload_config(config,agent):
    agent.uploadConfig(action=constant.ActionType['Create'], edgeConfig=config)

# Add StringVar variables
node_id = tk.StringVar()
api_url = tk.StringVar()
credential_key = tk.StringVar()

api_frame = tk.Frame(root)
api_frame.pack(pady=10)

api_label1 = tk.Label(api_frame, text="NodeID:")
api_label1.grid(row=0, column=0, sticky="e", padx=10, pady=10)
api_label2 = tk.Label(api_frame, text="API URL:")
api_label2.grid(row=1, column=0, sticky="e", padx=10, pady=10)
api_label3 = tk.Label(api_frame, text="Credential Key:")
api_label3.grid(row=2, column=0, sticky="e", padx=10, pady=10)

api_entry1 = tk.Entry(api_frame, textvariable=node_id)
api_entry1.grid(row=0, column=1, padx=10, pady=10)
api_entry2 = tk.Entry(api_frame, textvariable=api_url)
api_entry2.grid(row=1, column=1, padx=10, pady=10)
api_entry3 = tk.Entry(api_frame, textvariable=credential_key)
api_entry3.grid(row=2, column=1, padx=10, pady=10)

host_label = tk.Label(connection_frame, text="Host:")
host_label.pack(side=tk.LEFT)
host_entry = tk.Entry(connection_frame, width=15)
host_entry.insert(0, HOST)
host_entry.pack(side=tk.LEFT)

port_label = tk.Label(connection_frame, text="Port:")
port_label.pack(side=tk.LEFT)
port_entry = tk.Entry(connection_frame, width=5)
port_entry.insert(0, PORT)
port_entry.pack(side=tk.LEFT)

connect_button = tk.Button(connection_frame, text="Connect", command=connect_to_host)
connect_button.pack(side=tk.LEFT)

# Create a frame for the input field and buttons
input_frame = tk.Frame(root)
input_frame.pack()




# Create the input field for G-code commands
command_entry = tk.Entry(input_frame, width=30)
command_entry.pack(side=tk.LEFT)

# Create the send button
send_button = tk.Button(input_frame, text="Send", command=send_command)
send_button.pack(side=tk.LEFT)

SDK_connection_button = tk.Button(input_frame, text="Connect SDK database",
                                  command=lambda: SDK_connect(api_url.get(), node_id.get(), credential_key.get()))
SDK_connection_button.pack(side=tk.RIGHT)


send_SDK_button = tk.Button(input_frame, text="Send Data to DB", command=toggle_send_data)
send_SDK_button.pack(side=tk.RIGHT)

Create_config = tk.Button(input_frame, text="Configure JSON", command=lambda: upload_config(generateConfig(), edgeAgent))
Create_config.pack(side=tk.RIGHT)

# Create the add periodic send button
add_periodic_send_button = tk.Button(input_frame, text="+", command=add_periodic_send)
add_periodic_send_button.pack(side=tk.LEFT)

# Create a progress bar
progress_var = tk.DoubleVar()
progress_bar = ttk.Progressbar(root, orient="horizontal", length=200, mode="determinate", variable=progress_var)
progress_bar.pack(pady=10)

# Create a label to display progress percentage
progress_label = tk.Label(root, text="Progress: 0.00%")
progress_label.pack(pady=10)

# Create a label to display temperature values
temp_var = tk.StringVar()
temp_var.set("Current Temp: -\nTarget Temp: -\nPID:-")
temperature_label = tk.Label(root, textvariable=temp_var)
temperature_label.pack(pady=10)

# Create a scrolled text widget to display log messages
log_display = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=50, height=20)
log_display.pack(pady=10)

# Create a list to hold periodic send objects
periodic_sends = []

# Start the log message receiving loop in a separate thread
recv_thread = threading.Thread(target=recv_log_messages, daemon=True)
recv_thread.start()

# Start the main loop
root.mainloop()