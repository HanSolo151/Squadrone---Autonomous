from pymavlink import mavutil
import time
import asyncio
import zmq
import zmq.asyncio

 
master = mavutil.mavlink_connection('tcp:127.0.0.1:14550') 

context = zmq.asyncio.Context()
socket = context.socket(zmq.SUB)
socket.connect("tcp://localhost:5556")
socket.subscribe("")  

print("Waiting for heartbeat from vehicle...")
master.wait_heartbeat()
print(f"✅ Connected to system {master.target_system}, component {master.target_component}")



async def pre_check():
        
    GUIDED_MODE = 4  

    master.mav.set_mode_send(
        master.target_system,
        mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
        GUIDED_MODE
    )

    

    master.mav.command_long_send(
    master.target_system,
    master.target_component,
    mavutil.mavlink.MAV_CMD_DO_CHANGE_SPEED,
    0,      # confirmation
    1,      # 1 = groundspeed
    2,      # 2 m/s
    -1,     # throttle (ignored)
    0, 0, 0, 0
    )
 
async def take_off():

    print("Arming...")
    master.arducopter_arm()
    master.motors_armed_wait() 


    takeoff_alt = 10  # meters

    master.mav.command_long_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
        0,    # confirmation
        0, 0, 0, 0,  # param 1-4 unused
        0, 0,        # lat/lon 0 = use current
        takeoff_alt
    ) 

    while True:

        message = await socket.recv_string()
        if message == "Coord1": 
            master.mav.set_position_target_global_int_send(
                0,  # time_boot_ms
                master.target_system,
                master.target_component,
                mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
                int(0b110111111000),  # mask for position only
                int(18.4897898 * 1e7),
                int(73.8509642 * 1e7),
                takeoff_alt,
                0, 0, 0, 0, 0, 0, 0, 0
            ) 
        
        if message == "Coord2": 
            master.mav.set_position_target_global_int_send(
                0,  # time_boot_ms
                master.target_system,
                master.target_component,
                mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
                int(0b110111111000),  # mask for position only
                int(18.4898357 * 1e7),
                int(73.8516485 * 1e7),
                takeoff_alt,
                0, 0, 0, 0, 0, 0, 0, 0
            ) 
 


    




async def rtl():
    
    master.mav.command_long_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH,
        0, 0, 0, 0, 0, 0, 0, 0
    )
    print("Returning to Launch")

async def main():

    await pre_check()
    await asyncio.sleep(5)
    await take_off()
    await asyncio.sleep(45)
    await rtl()
    await rtl()
    await rtl()

if __name__ == "__main__":
    asyncio.run(main())





'''

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
    threading.Thread(target=set_servo_pwm, args=(8, 1000), daemon=True).start()  # Locked

def move_to_position2():
    threading.Thread(target=set_servo_pwm, args=(8, 2000), daemon=True).start()  # Release

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


'''