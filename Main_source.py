import socket
import time
import tkinter as tk
from tkinter import scrolledtext, ttk

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

def periodic_send():
    global periodic_sending
    if periodic_sending:
        command = periodic_command_entry.get()
        cmd = command + "\n"
        s.send(cmd.encode('utf-8'))
        root.after(int(interval_entry.get()) * 1000, periodic_send)

def toggle_periodic_send():
    global periodic_sending
    periodic_sending = not periodic_sending
    if periodic_sending:
        toggle_button.config(text="Stop Periodic Send")
        root.after(int(interval_entry.get()) * 1000, periodic_send)
    else:
        toggle_button.config(text="Start Periodic Send")

def update_progress_bar(current_byte, total_byte):
    progress = (current_byte / total_byte) * 100
    progress_var.set(progress)

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

# Create a frame for the periodic sending input and button
periodic_frame = tk.Frame(root)
periodic_frame.pack()

# Create the input field for periodic G-code commands
periodic_command_entry = tk.Entry(periodic_frame, width=30)
periodic_command_entry.pack(side=tk.LEFT)

# Create the input field for the interval in seconds
interval_entry = tk.Entry(periodic_frame, width=5)
interval_entry.pack(side=tk.LEFT)
interval_entry.insert(0, "5")

# Create the button to toggle periodic sending
periodic_sending = False
toggle_button = tk.Button(periodic_frame, text="Start Periodic Send", command=toggle_periodic_send)
toggle_button.pack(side=tk.LEFT)

# Create a progress bar
progress_var = tk.DoubleVar()
progress_bar = ttk.Progressbar(root, orient="horizontal", length=200, mode="determinate", variable=progress_var)
progress_bar.pack(pady=10)

# Create a text widget for displaying log messages
log_display = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=60, height=20)
log_display.pack()

# Start receiving log messages in a separate thread
import threading
recv_thread = threading.Thread(target=recv_log_messages, daemon=True)
recv_thread.start()

# Start the GUI event loop
root.mainloop()

# Close the connection when the GUI is closed
s.close()
print("Connection closed.")