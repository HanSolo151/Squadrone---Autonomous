from pymavlink import mavutil
import time
import asyncio
import zmq
import zmq.asyncio

 
master = mavutil.mavlink_connection('tcp:127.0.0.1:14550') 

master = mavutil.mavlink_connection('/dev/ttyACM0', baud=57600)

context = zmq.asyncio.Context()
socket = context.socket(zmq.SUB)
socket.connect("tcp://localhost:5556")
socket.subscribe("")  

msg_queue = asyncio.Queue()

print("Waiting for heartbeat from vehicle...")
master.wait_heartbeat()
print(f"✅ Connected to system {master.target_system}, component {master.target_component}")

master.arducopter_arm()
master.motors_armed_wait() 

async def pre_check():
        
    GUIDED_MODE = 4  

    master.mav.set_mode_send(
        master.target_system,
        mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
        GUIDED_MODE
    )
 
async def take_off():

    print("Arming...")
    master.arducopter_arm()
    master.motors_armed_wait() 


    takeoff_alt = 1  # meters

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
        msg = master.recv_match(type='GLOBAL_POSITION_INT', blocking=True, timeout=1)
        if msg:
            alt = msg.relative_alt / 1000.0  # in meters
            print(f"Current altitude: {alt:.2f} m")
            if alt >= takeoff_alt:
                print("✅ Target altitude reached")
                break 
 

async def telem_data_check(): 
    while True:
        msg = await asyncio.to_thread(master.recv_match, blocking=True, timeout=1)
        if msg:
            await msg_queue.put(msg.to_dict())
        await asyncio.sleep(0)


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
    await take_off()
    await asyncio.sleep(5)
    await rtl()
    await rtl()
    await rtl()
    await rtl()
    await rtl()
    await rtl()

if __name__ == "__main__":
    asyncio.run(main())