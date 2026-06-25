from pymavlink import mavutil
import time
import asyncio

 
master = mavutil.mavlink_connection('tcp:127.0.0.1:14550') 

print("Waiting for heartbeat from vehicle...")
master.wait_heartbeat()
print(f"✅ Connected to system {master.target_system}, component {master.target_component}")

GUIDED_MODE = 4  # ArduCopter mode enum: 4 = GUIDED

master.mav.set_mode_send(
    master.target_system,
    mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
    GUIDED_MODE
)

async def pre_takeoff_check():

        
  
    
    print("Arming...")
    master.arducopter_arm()
    master.motors_armed_wait() 

 

    master.mav.command_long_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
        0,    # confirmation
        0, 0, 0, 0,  # param 1-4 unused
        0, 0,        # lat/lon 0 = use current
        15
    ) 

    master.mav.command_long_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH,
        0, 0, 0, 0, 0, 0, 0, 0
    )
    print("Returning to Launch")
    
async def take_off():
        
    print("Arming...")
    master.arducopter_arm()
    master.motors_armed_wait() 

 

    master.mav.command_long_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
        0,    # confirmation
        0, 0, 0, 0,  # param 1-4 unused
        0, 0,        # lat/lon 0 = use current
        15
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

    await pre_takeoff_check()
 

if __name__ == "__main__":

    asyncio.run(main())