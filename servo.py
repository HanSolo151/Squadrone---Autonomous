
import tkinter as tk
from pymavlink import mavutil
import threading

# --- MAVLink Setup ---
master = mavutil.mavlink_connection('tcp:127.0.0.1:14550')

print("Waiting for heartbeat...")
master.wait_heartbeat()
print(f"✅ Connected to system {master.target_system}, component {master.target_component}")

 
 
def set_servo_pwm(channel, pwm_value):
    master.mav.command_long_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_CMD_DO_SET_SERVO,
        0,
        channel,       # Servo channel (e.g., 9 for SERVO9)
        pwm_value,     # PWM microseconds (1000–2000)
        0, 0, 0, 0, 0
    )
    print(f"Servo {channel} set to {pwm_value} µs")

# --- GUI Functions ---
def move_to_position1():
    threading.Thread(target=set_servo_pwm, args=(8, 800), daemon=True).start()  # Locked

def move_to_position2():
    threading.Thread(target=set_servo_pwm, args=(8, 2200), daemon=True).start()  # Release

# --- Tkinter GUI ---
root = tk.Tk()
root.title("Servo Control Panel")
root.geometry("300x180")
root.configure(bg="#1e1e1e")

title = tk.Label(root, text="Servo Control", fg="white", bg="#1e1e1e", font=("Segoe UI", 14))
title.pack(pady=15)

btn1 = tk.Button(root, text="Position 1", command=move_to_position1, font=("Segoe UI", 12), bg="#0078D7", fg="white", width=15)
btn1.pack(pady=10)

btn2 = tk.Button(root, text="Position 2", command=move_to_position2, font=("Segoe UI", 12), bg="#0078D7", fg="white", width=15)
btn2.pack(pady=10)

root.mainloop()
