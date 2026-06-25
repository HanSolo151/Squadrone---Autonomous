import tkinter as tk
import zmq

# ------------------------------
# ZMQ Setup (Publisher)
# ------------------------------
context = zmq.Context()
socket = context.socket(zmq.PUB)
socket.bind("tcp://*:5556")  # Publishes on this port

# ------------------------------
# GUI Setup
# ------------------------------
def send_coord1():
    socket.send_string("Coord1")
    print("✅ Sent: Coord1")

def send_coord2():
    socket.send_string("Coord2")
    print("✅ Sent: Coord2")

root = tk.Tk()
root.title("Coordinate Sender")
root.geometry("250x180")
root.resizable(False, False)

label = tk.Label(root, text="Send Coordinate Commands", font=("Arial", 12))
label.pack(pady=10)

button1 = tk.Button(root, text="Send Coord1", command=send_coord1,
                    height=2, width=20, bg="#2b8aed", fg="white")
button1.pack(pady=5)

button2 = tk.Button(root, text="Send Coord2", command=send_coord2,
                    height=2, width=20, bg="#28a745", fg="white")
button2.pack(pady=5)

 

root.mainloop()
