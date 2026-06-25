import zmq
import tkinter as tk
from tkinter import ttk

ZMQ_ADDR = "tcp://127.0.0.1:7000"   # same as your push_capture endpoint

context = zmq.Context()
sock = context.socket(zmq.PUSH)
sock.bind(ZMQ_ADDR)   # or .connect() if needed

def send_capture():
    sock.send_string("CAPTURE")
    status_label.config(text="📸 Sent CAPTURE command")

root = tk.Tk()
root.title("Capture Sender")
root.geometry("250x120")

ttk.Label(root, text="Manual Capture Trigger").pack(pady=10)

btn = ttk.Button(root, text="CAPTURE", command=send_capture)
btn.pack(pady=5)

status_label = ttk.Label(root, text="")
status_label.pack()

root.mainloop()
