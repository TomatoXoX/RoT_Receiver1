import socket
import time
import tkinter as tk
from tkinter import scrolledtext, ttk
import threading

HOST = '192.168.1.10'
PORT = 8888
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST, PORT))

def process_log(log_data):
    log_display.insert(tk.END, log_data + '\n')
    log_display.see(tk.END)

    if "SD printing byte" in log_data:
        try:
            progress_data = log_data.split("SD printing byte")[1].strip()
            current_byte, total_byte = map(int, progress_data.split('/'))
            update_progress_bar(current_byte, total_byte)
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

    if progress >= 100:
        update_product_counter()

def update_temperature(current_temp, target_temp, pid_number):
    temp_var.set(f"Current Temp: {current_temp:.2f}°C\nTarget Temp: {target_temp:.2f}°C\nPID: {pid_number}")

# Create the main window
root = tk.Tk()
root.title("ESP 3D G-Code Sender")

# Create a frame for the input field and buttons
input_frame = tk.Frame(root)
input_frame.pack()

# Create the input field for G-code commands
command_entry = tk.Entry(input_frame, width=30)
command_entry.pack(side=tk.LEFT)

# Create the send button
send_button = tk.Button(input_frame, text="Send", command=send_command)
send_button.pack(side=tk.LEFT)

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