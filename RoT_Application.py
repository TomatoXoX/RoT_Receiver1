import datetime

import numpy as np
from roboflow import Roboflow
from PIL import Image, ImageDraw, ImageFont, ImageTk
from io import BytesIO
import socket
import time
import requests
import tkinter as tk
from tkinter import scrolledtext, ttk
import threading
from tkinter import messagebox
from wisepaasdatahubedgesdk.EdgeAgent import EdgeAgent

import wisepaasdatahubedgesdk.Common.Constants as constant
from wisepaasdatahubedgesdk.Model.Edge import EdgeAgentOptions, MQTTOptions, DCCSOptions, EdgeData, EdgeTag, EdgeStatus, \
    EdgeDeviceStatus, EdgeConfig, NodeConfig, DeviceConfig, AnalogTagConfig, DiscreteTagConfig, TextTagConfig
from wisepaasdatahubedgesdk.Common.Utils import RepeatedTimer
# Import statements from the original code
class PeriodicSend:
    def __init__(self, master,device):
        self.master = master
        self.frame = tk.Frame(self.master)
        self.frame.pack()
        self.device = device
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
                self.device.send(cmd.encode('utf-8'))
            self.master.after(int(self.interval_entry.get()) * 1000, self.periodic_send)

    def toggle_periodic_send(self):
        self.periodic_sending = not self.periodic_sending
        if self.periodic_sending:
            self.toggle_button.config(text="Stop Periodic Send")
            self.master.after(int(self.interval_entry.get()) * 1000, self.periodic_send)
        else:
            self.toggle_button.config(text="Start Periodic Send")


class DeviceGUI(tk.Frame):
    def __init__(self, parent, host, port):
        super().__init__(parent)
        self.parent = parent
        self.host = host
        self.port = port
        self.timer_value = "None"
        self.sending_data = False
        self.edgeAgent = None
        self.temp_var = "None"
        self.value_for_temp = 0
        self.ans = 0
        self.init_gui()
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.config_track = "None"
        # AI    
        self.AI_link = "None"
        self.model  = 0
        self.img_np = 0
        # Image display
            # Old code use for backup    
            #self.image_label = tk.Label(self)
            #self.image_label.grid(row=3, column=0, columnspan=2, padx=5, pady=5)
        # Create a new window for image display

         
    def init_gui(self):
        self.periodic_sends = []
        self.node_id = tk.StringVar()
        self.api_url = tk.StringVar()
        self.print_time = tk.StringVar()
        self.credential_key = tk.StringVar()
        self.ESPCAM = tk.StringVar()
        self.printing_progress = tk.DoubleVar()
        self.temp_display = tk.StringVar()
        self.temp_display.set("Current Temp: -\nTarget Temp: -\nPID:-")
        self.coordinate = [0,0,0,0]
        self.Fault_detect = False
        self.Fault_Confidence = 0

        # Set row and column weights
        self.grid_rowconfigure(0, weight=1)

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(3, weight=1)

        # Device Image
        image_window = tk.LabelFrame(self, text="Device Image")
        image_window.grid(row=0, column=2, padx=10, pady=10, sticky="nsew", columnspan=3)
        image_window.columnconfigure(0, weight=1)
        image_window.rowconfigure(0, weight=1)
        self.image_label = tk.Label(image_window)
        self.image_label.grid(row=0, column=0, padx=5, pady=5, sticky="nsew", columnspan=2,rowspan=3)

        # Device configuration
        device_config = tk.LabelFrame(self,text="Configure Device")
        device_config.grid(row=2,column=2,padx=5, pady=5, sticky="nsew", columnspan=2)
        device_config.columnconfigure(0,weight=1)
        device_config.columnconfigure(1,weight=1)
        self.Device_name=tk.StringVar()
        self.Device_ID =tk.StringVar()
        self.Device_descript = tk.StringVar()
        self.Device_name_label = tk.Label(device_config,text="Device Name")
        self.Device_name_label.grid(row=0,column=0,padx=5, pady=5, sticky="w")
        self.device_name_value = tk.Entry(device_config,textvariable=self.Device_name)
        self.device_name_value.grid(row=0,column=1,padx=5, pady=5, sticky="w")
        self.Device_desc_label = tk.Label(device_config,text="Device Description")
        self.Device_desc_label.grid(row=1,column=0,padx=5, pady=5, sticky="w")
        self.Device_desc_value = tk.Entry(device_config,textvariable=self.Device_descript)
        self.Device_desc_value.grid(row = 1,column=1,padx=5, pady=5, sticky="w")
        self.Device_ID_label = tk.Label(device_config, text="Device ID")
        self.Device_ID_label.grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.Device_ID_value = tk.Entry(device_config, textvariable=self.Device_ID)
        self.Device_ID_value.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        # Device Info
        device_info = tk.LabelFrame(self, text="Device Information")
        device_info.grid(row=0, column=0, padx=10, pady=10, sticky="nsew", columnspan=2)
        device_info.columnconfigure(0, weight=1)
        device_info.columnconfigure(1, weight=1)

        self.print_time_label = tk.Label(device_info,text="Printing Time")
        self.print_time_label.grid(row=2, column=0, padx=5, pady=5, sticky="w")

        self.print_time_value = tk.Label(device_info, textvariable=self.print_time)
        self.print_time_value.grid(row=2, column=1, padx=5, pady=5, sticky="w")

        self.temp_label = tk.Label(device_info, text="Temperature:")
        self.temp_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.temp_value_label = tk.Label(device_info, textvariable=self.temp_display)
        self.temp_value_label.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        self.progress_label = tk.Label(device_info, text="Printing Progress:")
        self.progress_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")

        self.progress_bar = ttk.Progressbar(device_info, orient="horizontal", length=200, mode="determinate",
                                            variable=self.printing_progress)
        self.progress_bar.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # Connection Settings
        connection_settings = tk.LabelFrame(self, text="Connection Settings")
        connection_settings.grid(row=1, column=0, padx=10, pady=10, sticky="nsew", columnspan=2)
        connection_settings.columnconfigure(0, weight=1)
        connection_settings.columnconfigure(1, weight=1)

        self.api_label1 = tk.Label(connection_settings, text="NodeID:")
        self.api_label1.grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.api_entry1 = tk.Entry(connection_settings, textvariable=self.node_id)
        self.api_entry1.grid(row=0, column=1, padx=5, pady=5)

        self.api_label2 = tk.Label(connection_settings, text="API URL:")
        self.api_label2.grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.api_entry2 = tk.Entry(connection_settings, textvariable=self.api_url)
        self.api_entry2.grid(row=1, column=1, padx=5, pady=5)

        self.api_label3 = tk.Label(connection_settings, text="Credential Key:")
        self.api_label3.grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.api_entry3 = tk.Entry(connection_settings, textvariable=self.credential_key)
        self.api_entry3.grid(row=2, column=1, padx=5, pady=5)

        self.connect_button = tk.Button(connection_settings, text="Connect Device", command=self.connect)
        self.connect_button.grid(row=3, column=0, padx=5, pady=5)

        self.connect_sdk_button = tk.Button(connection_settings, text="Connect SDK",
                                            command=lambda: self.SDK_connect(self.api_url.get(), self.node_id.get(),
                                                                             self.credential_key.get()))
        self.connect_sdk_button.grid(row=3, column=1, padx=5, pady=5)
        self.ESPCam_label = tk.Entry(connection_settings,textvariable=self.ESPCAM)
        self.ESPCam_label.grid(row=3, column=2, padx=5, pady=5, sticky="e")
        self.ESPCam_Btn = tk.Button(connection_settings,text="Connect to ESP-CAM",command = self.buttonCallback)
        self.ESPCam_Btn.grid(row =3, column = 5,padx=5, pady=5, sticky="e")
        # Log Display
        self.log_display = scrolledtext.ScrolledText(self, wrap=tk.WORD, width=50, height=20)
        self.log_display.grid(row=2, column=0, padx=10, pady=10, sticky="nsew", columnspan=2)

        # Command and Periodic Send
        command_section = tk.LabelFrame(self, text="Command and Periodic Send")
        command_section.grid(row=3, column=0, padx=10, pady=10, sticky="nsew", columnspan=2)
        command_section.columnconfigure(0, weight=4)
        command_section.columnconfigure(1, weight=1)

        self.command_entry = ttk.Entry(command_section)
        self.command_entry.grid(row=0, column=0, padx=5, pady=5, sticky="we")

        self.send_button = ttk.Button(command_section, text="Send", command=self.send_command)
        self.send_button.grid(row=0, column=1, padx=5, pady=5)

        self.add_periodic_send_button = tk.Button(command_section, text="+", command=self.add_periodic_send)
        self.add_periodic_send_button.grid(row=0, column=2, padx=5, pady=5)

        # Other Actions
        other_actions = tk.LabelFrame(self, text="Other Actions")
        other_actions.grid(row=3, column=2, padx=10, pady=10, sticky="ew", rowspan=3)
        other_actions.columnconfigure(0, weight=1)

        self.create_config = tk.Button(other_actions, text="Configure JSON",
                                       command=lambda: self.upload_config(self.generateConfig(self.Device_name.get(),self.Device_descript.get(),self.Device_ID.get()), self.edgeAgent))
        self.create_config.grid(row=0, column=0, padx=5, pady=5)

        self.update_con = tk.Button(other_actions,text="Update JSON",command=lambda: self.update_config(self.generateConfig(self.Device_name.get(),self.Device_descript.get(),self.Device_ID.get()),self.edgeAgent))
        self.update_con.grid(row=1,column=0,padx=5, pady=5)
        self.send_SDK_button = ttk.Button(other_actions, text="Send Data to DB", command=self.toggle_send_data)
        self.send_SDK_button.grid(row=2, column=0, padx=5, pady=5)
        self.pack(expand=True, fill=tk.BOTH)

    def buttonCallback(self):
        try:
            rf = Roboflow(api_key="GIV3u0jdRC9OYmwV4pSC")
            project = rf.workspace().project("3d-printing-defects")
            self.model = project.version(3).model
            print(self.ESPCAM.get())
            # Global variable to store the processed image
            self.processed_image = None         # Usage = ?, delete soon

            threading.Thread(target=self.getImage,daemon=True).start()
            
        except Exception as e:
            print(e)         
    # Get images from ESP-32CAM
    def getImage(self):
        while True:
           try: 
            self.process_image(self.ESPCAM.get())
           except Exception as e:
               print(e) 
           time.sleep(1)     
    # Process images from ESP-32CAM
    def process_image(self, image_url):
        # Retrieve the image from the URL
        response = requests.get(image_url)
        if response.status_code == 200:  # 200 = Normal
            image = Image.open(BytesIO(response.content))
            self.img_np = np.array(image)

            # Resize the image to a constant size (480x480)
            image = image.resize((800,800))

            predictions = self.model.predict(self.img_np, confidence=30, overlap=30).json()
            self.Fault_detect = self.has_prediction(predictions)


            # Process the predictions and draw bounding boxes on the image
            draw = ImageDraw.Draw(image)
            for prediction in predictions['predictions']:
                cx = int(prediction['x'])
                cy = int(prediction['y'])
                w = int(prediction['width'])
                h = int(prediction['height'])
                class_label = prediction['class']
                confidence = prediction['confidence']
                if self.Fault_detect:
                    self.Fault_Confidence = confidence
                else:
                    self.Fault_Confidence = 0

                # Calculate the coordinates of the top-left and bottom-right corners
                x1 = cx - w // 2
                y1 = cy - h // 2
                x2 = cx + w // 2
                y2 = cy + h // 2

                # Draw the rectangle on the image
                draw.rectangle([(x1, y1), (x2, y2)], outline=(0, 255, 0), width=2)

                # Customize label appearance
                label_text = f"{class_label}: {confidence:.2f}"
                label_position = (x1, y1)
                label_font = ImageFont.load_default()
                #label_font = ImageFont.truetype("path_to_font_file.ttf", size=12)  # Replace "path_to_font_file.ttf" with the actual font file path
                label_color = (0, 0, 0)  # Black text color
                label_background_color = (128, 0, 128)  # Purple background color

                # Determine the size of the label text
                label_width, label_height = draw.textsize(label_text, font=label_font)

                # Create a background rectangle for the label
                background_top_left = (label_position[0], label_position[1] - label_height)
                background_bottom_right = (label_position[0] + label_width, label_position[1])
                draw.rectangle([background_top_left, background_bottom_right], fill=label_background_color)

                # Write label on the image
                draw.text(label_position, label_text, font=label_font, fill=label_color)

            # Show the processed image

            self.display_image(image)
    def display_image(self, image):
        # Convert the image to PhotoImage format
        photo = ImageTk.PhotoImage(image)

        # Update the label with the new image
        self.image_label.configure(image=photo)
        self.image_label.image = photo

    def has_prediction(self, predictions):
        if len(predictions['predictions']) > 0:
            print(self.Fault_Confidence)
            return True
        else:
            return False
    def connect(self):
        try:
            self.s.connect((self.host, self.port))
            threading.Thread(target=self.recv_log_messages, daemon=True).start()
            self.connect_button.config(text="Connected", state=tk.DISABLED)
        except Exception as e:
            print(e)
    # Add the rest of the methods from your original code as instance methods of the DeviceGUI class
    def get_temp_value(self, value):
        self.value_for_temp = value

    def update_temperature(self, current_temp, target_temp, pid_number):
        self.temp_display.set(f"Current Temp: {current_temp:.2f}°C\nTarget Temp: {target_temp:.2f}°C\nPID: {pid_number}")
    def toggle_send_data(self):
        self.sending_data = not self.sending_data
        if self.sending_data:
            self.send_SDK_button.config(text="Stop Sending Data")
            self.send_data_loop()
        else:
            self.send_SDK_button.config(text="Send Data to DB")
    def send_data_loop(self):
        if self.sending_data:
            self.send_data_SDK(self.edgeAgent, self.value_for_temp, self.ans)
            self.after(1000, self.send_data_loop)  # Adjust the time interval as needed
    def process_log(self, log_data):
        self.log_display.insert(tk.END, log_data + '\n')
        self.log_display.see(tk.END)
        if "X:" in log_data:
            try:
                cord = log_data.split(" ")
                self.coordinate[0] = float(cord[0].split(":")[1])
                self.coordinate[1] = float(cord[1].split(":")[1])
                self.coordinate[2] = float(cord[2].split(":")[1])
                self.coordinate[3] = float(cord[3].split(":")[1])

            except Exception as e:
                print(f"Error parsing Coordinate:{e}")

        if "SD printing byte" in log_data:
            try:
                progress_data = log_data.split("SD printing byte")[1].strip()
                current_byte, total_byte = map(int, progress_data.split('/'))
                progress = (current_byte/total_byte)*100
                self.ans = progress
                self.update_progress_bar(progress)
            except Exception as e:
                print("Error parsing progress:", e)
        if "ok T:" in log_data:
            try:
                temp_data = log_data.split("ok T:")[1].strip()
                current_temp, target_temp, pid_number = temp_data.split(" ", 2)
                current_temp = float(current_temp)
                target_temp = float(target_temp.split('/')[1])
                pid_number = int(pid_number.split('@:')[1])
                self.update_temperature(current_temp, target_temp, pid_number)
                self.get_temp_value(current_temp)
            except Exception as e:
                print("Error parsing temperature:", e)
        if "echo:Print time:" in log_data:
            try:
                print_time = log_data.split("echo:Print time:")[1].strip()
                self.timer_value = print_time
                self.print_time.set(print_time)
            except Exception as e:
                print("Error parsing run time:", e)
        # Rest of the process_log method
    def recv_log_messages(self):
        buffer = ""
        while True:
            data = self.s.recv(4096).decode('utf-8')
            if data:
                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    self.process_log(line.strip())
            time.sleep(0.1)
    def SDK_connect(self,api_link, NodeID, cred_key):
        self.edgeAgent  # Added global keyword to modify the global variable
        self.edgeAgentOption = EdgeAgentOptions(nodeId=NodeID)
        self.edgeAgentOption.connectType = constant.ConnectType['DCCS']
        self.DCCS_Config = DCCSOptions(apiUrl=api_link, credentialKey=cred_key)
        self.edgeAgentOption.DCCS = self.DCCS_Config
        self.edgeAgent = EdgeAgent(self.edgeAgentOption)
        self.edgeAgent.connect()
        # Update the SDK connection button's text
        self.connect_sdk_button.config(text='Connected to SDK Database', state=tk.DISABLED)
    def send_command(self):
        command = self.command_entry.get()
        cmd = command + "\n"
        self.s.send(cmd.encode('utf-8'))
        self.command_entry.delete(0, tk.END)
    def send_data_SDK(self, edge_agent, temperature, progress):
        data = self.categorization(temperature, progress)
        edge_agent.sendData(data)
        pass
    def generateConfig(self,name,descript,ID):
        config = EdgeConfig()
        nodeConfig = NodeConfig(nodeType=constant.EdgeType['Gateway'])
        config.node = nodeConfig
        deviceConfig = DeviceConfig(id=ID,
                                    name=name,
                                    description=descript,
                                    deviceType='Smart Device',
                                    retentionPolicyName='')
        analog1 = AnalogTagConfig(name='Temperature',
                                  description='Temperature monitoring of Printer head',
                                  readOnly=False,
                                  arraySize=0,
                                  spanHigh=1000,
                                  spanLow=0,
                                  engineerUnit='',
                                  integerDisplayFormat=4,
                                  fractionDisplayFormat=2)
        analog2 = AnalogTagConfig(name='Progression',
                                  description='Product print progress',
                                  readOnly=False,
                                  arraySize=0,
                                  spanHigh=1000,
                                  spanLow=0,
                                  engineerUnit='',
                                  integerDisplayFormat=4,
                                  fractionDisplayFormat=2)
        text = AnalogTagConfig(name='Print_Time',
                               description='Product run time',
                               readOnly=False,
                               arraySize=0,
                               spanHigh=1000,
                               spanLow=0,
                               engineerUnit='',
                               integerDisplayFormat=4,
                               fractionDisplayFormat=2)
        coord1 = AnalogTagConfig(name='X',
                               description='X coordinate',
                               readOnly=False,
                               arraySize=0,
                               spanHigh=1000,
                               spanLow=0,
                               engineerUnit='',
                               integerDisplayFormat=4,
                               fractionDisplayFormat=2)
        coord2 = AnalogTagConfig(name='Y',
                                 description='Y coordinate',
                                 readOnly=False,
                                 arraySize=0,
                                 spanHigh=1000,
                                 spanLow=0,
                                 engineerUnit='',
                                 integerDisplayFormat=4,
                                 fractionDisplayFormat=2)
        coord3 = AnalogTagConfig(name='Z',
                                 description='Layer Height',
                                 readOnly=False,
                                 arraySize=0,
                                 spanHigh=1000,
                                 spanLow=0,
                                 engineerUnit='',
                                 integerDisplayFormat=4,
                                 fractionDisplayFormat=2)
        extruder = AnalogTagConfig(name='E',
                                 description='Filament spent in (mm)',
                                 readOnly=False,
                                 arraySize=0,
                                 spanHigh=1000,
                                 spanLow=0,
                                 engineerUnit='',
                                 integerDisplayFormat=4,
                                 fractionDisplayFormat=2)
        Fault1 = AnalogTagConfig(name='Fault',
                                   description='AI Detected Fault',
                                   readOnly=False,
                                   arraySize=0,
                                   spanHigh=1000,
                                   spanLow=0,
                                   engineerUnit='',
                                   integerDisplayFormat=4,
                                   fractionDisplayFormat=2)
        Fault2 = AnalogTagConfig(name='Falt_Confidence',
                                   description='Detection Confidence',
                                   readOnly=False,
                                   arraySize=0,
                                   spanHigh=1000,
                                   spanLow=0,
                                   engineerUnit='',
                                   integerDisplayFormat=4,
                                   fractionDisplayFormat=2)

        deviceConfig.analogTagList.append(analog1)
        deviceConfig.analogTagList.append(analog2)
        deviceConfig.analogTagList.append(text)
        deviceConfig.analogTagList.append(coord1)
        deviceConfig.analogTagList.append(coord2)
        deviceConfig.analogTagList.append(coord3)
        deviceConfig.analogTagList.append(extruder)
        deviceConfig.analogTagList.append(Fault1)
        deviceConfig.analogTagList.append(Fault2)
        config.node.deviceList.append(deviceConfig)
        return config
    def upload_config(self,config, agent):
        if agent is None:
            tk.messagebox.showerror("Error", "Please connect to the SDK database before configuring JSON")
            return
        agent.uploadConfig(action=constant.ActionType['Create'], edgeConfig=config)
    def update_config(self,config, agent):
        if agent is None:
            tk.messagebox.showerror("Error", "Please connect to the SDK database before configuring JSON")
            return
        agent.uploadConfig(action=constant.ActionType['Update'], edgeConfig=config)
    def categorization(self,temperature, progress):
        self.edgeData = EdgeData()

        Temp_Device = self.Device_ID.get()

        tag_Temp_name = "Temperature"
        self.value_temp = temperature

        tag_Progress_name = "Progression"
        self.value_progress = progress

        tag_Timer_name = "Print_Time"
        self.value_timer = self.timer_value

        tag_Coordinate_X = "X"
        tag_Coordinate_Y = "Y"
        tag_Coordinate_Z = "Z"
        tag_Coordinate_E = "E"
        tag_Fault = "Fault"
        tag_Confidence = "Falt_Confidence"
        if self.Fault_detect:
            temp_var = "True"
        else:
            temp_var = "False"

        tag_X = EdgeTag(Temp_Device,tag_Coordinate_X,self.coordinate[0])
        tag_Y = EdgeTag(Temp_Device, tag_Coordinate_Y, self.coordinate[1])
        tag_Z = EdgeTag(Temp_Device, tag_Coordinate_Z, self.coordinate[2])
        tag_E = EdgeTag(Temp_Device, tag_Coordinate_E, self.coordinate[3])
        tag_Temp = EdgeTag(Temp_Device, tag_Temp_name, self.value_temp)
        tag_Timer = EdgeTag(Temp_Device, tag_Timer_name, self.value_timer)
        tag_Progress = EdgeTag(Temp_Device, tag_Progress_name, self.value_progress)
        tag_F = EdgeTag(Temp_Device, tag_Fault, temp_var)
        tag_C = EdgeTag(Temp_Device, tag_Confidence, self.Fault_Confidence)

        self.edgeData.tagList.append(tag_Timer)
        self.edgeData.tagList.append(tag_Progress)
        self.edgeData.tagList.append(tag_Temp)
        self.edgeData.tagList.append(tag_X)
        self.edgeData.tagList.append(tag_Y)
        self.edgeData.tagList.append(tag_Z)
        self.edgeData.tagList.append(tag_E)
        self.edgeData.tagList.append(tag_F)
        self.edgeData.tagList.append(tag_C)
        print(temp_var)

        self.edgeData.timestamp = datetime.datetime.now()
        return self.edgeData
    def update_progress_bar(self, progress):
        # Implement the method to update the progress bar
        self.printing_progress.set(progress)
        self.progress_label.config(text=f"Progress: {progress:.2f}%")
        self.progress_bar.update(progress)

        pass

    def add_periodic_send(self):
        periodic_send_frame = tk.Frame(self)
        periodic_send_frame.grid(row=len(self.periodic_sends) + 6, column=0, columnspan=2, padx=5, pady=5, sticky="we")
        periodic_send = PeriodicSend(periodic_send_frame,self.s)
        self.periodic_sends.append(periodic_send)

    # Add the rest of the methods here, as instance methods of the DeviceGUI class

class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Multi-Device Manager")
        self.geometry("1028x900")

        self.add_device_frame = tk.Frame(self)
        self.add_device_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        self.ip_label = ttk.Label(self.add_device_frame, text="IP Address:")
        self.ip_label.pack(side=tk.LEFT)
        self.ip_entry = ttk.Entry(self.add_device_frame)
        self.ip_entry.pack(side=tk.LEFT, padx=5)

        self.port_label = ttk.Label(self.add_device_frame, text="Port:")
        self.port_label.pack(side=tk.LEFT)
        self.port_entry = ttk.Entry(self.add_device_frame)
        self.port_entry.pack(side=tk.LEFT, padx=5)

        self.add_device_button = ttk.Button(self.add_device_frame, text="Add Device", command=self.add_new_device)
        self.add_device_button.pack(side=tk.LEFT, padx=5)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(expand=True, fill=tk.BOTH)

    def add_new_device(self):
        ip = self.ip_entry.get()
        port = int(self.port_entry.get())
        if ip and port:
            device_page = DeviceGUI(self, ip, port)
            self.notebook.add(device_page, text=f"Device {len(self.notebook.tabs()) + 1}")
            self.ip_entry.delete(0, tk.END)
            self.port_entry.delete(0, tk.END)
        else:
            messagebox.showerror("Error", "Please enter a valid IP address and port.")

if __name__ == "__main__":
    app = MainApp()
    app.mainloop()
