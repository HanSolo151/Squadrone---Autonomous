from pymavlink import mavutil
import time
import asyncio
import zmq
import zmq.asyncio
import coordinates_calc as cc
import math

context = zmq.Context()
socket = context.socket(zmq.PUB)
socket.bind("tcp://*:5556")  

points = [
    (18.4898357, 73.8516485), 
    (18.4897898, 73.8509642),
    (18.4899831, 73.8509296),
    (18.4900890, 73.8515808)
]

path, drop_zone = cc.generate_inward_lawnmower_path(points)

print(path, drop_zone)
 
 


msg_queue = asyncio.Queue()

 
master = mavutil.mavlink_connection('tcp:127.0.0.1:14550') 

  

print("Waiting for heartbeat from vehicle...")
master.wait_heartbeat()
print(f"✅ Connected to system {master.target_system}, component {master.target_component}")


def haversine(lat1, lon1, lat2, lon2): 
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))



def set_servo_pwm(pwm_value):
    master.mav.command_long_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_CMD_DO_SET_SERVO,
        0,
        8,       # Servo channel (e.g., 9 for SERVO9)
        pwm_value,     # PWM microseconds (1000–2000)
        0, 0, 0, 0, 0
    )
    print(f"Servo 8 set to {pwm_value} µs")




async def pre_check():
        
    GUIDED_MODE = 4  

    master.mav.set_mode_send(
        master.target_system,
        mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
        GUIDED_MODE
    )

 
 

async def flight_ops():

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
        msg = await msg_queue.get()
        if msg.get("mavpackettype") == "GLOBAL_POSITION_INT":
            alt = msg["relative_alt"] / 1000.0
            print(f"Current altitude: {alt:.2f} m")
            if alt >= takeoff_alt:
                print("✅ Target altitude reached.")
                break
         
        
    for i, (lat, lon) in enumerate(path):

        while True:
            msg = await msg_queue.get()
            if msg.get("mavpackettype") == "GLOBAL_POSITION_INT":
                curr_lat = msg["lat"] / 1e7
                curr_lon = msg["lon"] / 1e7
                dist = haversine(curr_lat, curr_lon, lat, lon)
                print(f"Distance to WP{i+1}: {dist:.2f} m")
                
                master.mav.set_position_target_global_int_send(
                0,   
                master.target_system,
                master.target_component,
                mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
                int(0b110111111000),  # mask for position only
                int(lat * 1e7),
                int(lon * 1e7),
                takeoff_alt,
                0, 0, 0, 0, 0, 0, 0, 0
                ) 
                if dist < 1.0:  # within 1 meter
                    print(f"✅ Reached waypoint {i+1}")
                    break

    
    
    
    while True:

        msg = await msg_queue.get()
        if msg.get("mavpackettype") == "GLOBAL_POSITION_INT":
            curr_lat = msg["lat"] / 1e7
            curr_lon = msg["lon"] / 1e7
            dist = haversine(curr_lat, curr_lon, drop_zone[0], drop_zone[1])
            print(f"Distance to Drop Zone: {dist:.2f} m")
            master.mav.set_position_target_global_int_send(
                0,   
                master.target_system,
                master.target_component,
                mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
                int(0b110111111000),  # mask for position only
                int(drop_zone[0] * 1e7),
                int(drop_zone[1] * 1e7),
                takeoff_alt,
                0, 0, 0, 0, 0, 0, 0, 0
            )
            if dist < 1.0:  # within 1 meter
                print(f"✅ Reached Centroid")
                break

    
    drop_alt = 5
    
    
    
    while True:
        msg = await msg_queue.get()
        if msg.get("mavpackettype") == "GLOBAL_POSITION_INT":
            alt = msg["relative_alt"] / 1000.0
            print(f"Current altitude: {alt:.2f} m")
            master.mav.set_position_target_global_int_send(
                0,   
                master.target_system,
                master.target_component,
                mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
                int(0b110111111000),  # mask for position only
                int(drop_zone[0] * 1e7),
                int(drop_zone[1] * 1e7),
                drop_alt,
                0, 0, 0, 0, 0, 0, 0, 0
            )  
            if alt <= drop_alt:
                print("✅ Drop altitude reached.")
                break

    for j, (lat, lon) in enumerate(triangulation_coord):

        master.mav.set_position_target_global_int_send(
                0,   
                master.target_system,
                master.target_component,
                mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
                int(0b110111111000),  # mask for position only
                int(lat * 1e7),
                int(lon * 1e7),
                drop_alt,
                0, 0, 0, 0, 0, 0, 0, 0
            ) 
        
        while True:
            msg = await msg_queue.get()
            if msg.get("mavpackettype") == "GLOBAL_POSITION_INT":
                curr_lat = msg["lat"] / 1e7
                curr_lon = msg["lon"] / 1e7
                dist = haversine(curr_lat, curr_lon, lat, lon)
                print(f"Distance to WP{j+1}: {dist:.2f} m")
                if dist < 0.2:  # within 1 meter
                    print(f"✅ Reached waypoint {j+1}")
                    break
    
   
 

latest_position = None


async def test():

    global latest_position

    while True:

        print(1)

        await asyncio.sleep(2)
        print(latest_position)

     


async def telem_data_check(): 

    global latest_position
 
    while True:
        msg = await asyncio.to_thread(master.recv_match, blocking=True, timeout=1)
        if msg:
            await msg_queue.put(msg.to_dict())
            msg = msg.to_dict()
            #print(msg)
            if msg.get("mavpackettype") == "GLOBAL_POSITION_INT":
                latest_position = (
                    msg['lat'] / 1e7 ,
                    msg['lon'] / 1e7 ,
                    msg.get('hdg', 0) / 100.0
                )
                #print(latest_position)


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

    #await pre_check()

    await asyncio.gather(telem_data_check(),
                         test()
                         )
                         

    '''await flight_ops()
       



    await rtl()
    await rtl()
    await rtl()
    await rtl()
    await rtl()
    await rtl()
    await rtl()'''

if __name__ == "__main__":
    asyncio.run(main())