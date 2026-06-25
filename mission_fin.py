from pymavlink import mavutil
import time
import asyncio
import zmq
import zmq.asyncio
import coordinates_calc as cc
import math

context = zmq.asyncio.Context()
socket = context.socket(zmq.PUB)
socket.bind("tcp://*:5556") 

socket_recv_micro_coords = context.socket(zmq.SUB)
socket_recv_micro_coords.connect("tcp://127.0.0.1:6000")

push_capture = context.socket(zmq.PUSH)
push_capture.bind("tcp://127.0.0.1:7000")
 

points = [
    (12.8579488, 77.4411603),
    (12.8582210, 77.4413001),
    (12.8581422, 77.4415192),
    (12.8578366, 77.4414079),
]

 

path = [(12.8581776, 77.4413297), (12.8581745, 77.4413752), (12.8581589, 77.4414185), (12.8581433, 77.4414617), (12.8581324, 77.4414787), (12.8581324, 77.4414327), (12.8581324, 77.4413866), (12.8581324, 77.4413405), (12.8581324, 77.4412945), (12.8581089, 77.4412631), (12.8580872, 77.4412732), (12.8580872, 77.4413192), (12.8580872, 77.4413653), (12.8580872, 77.4414114), (12.8580872, 77.4414574), (12.8580649, 77.4414714), (12.858042, 77.4414418), (12.858042, 77.4413958), (12.858042, 77.4413497), (12.858042, 77.4413037), (12.858042, 77.4412576), (12.8580269, 77.441221), (12.8579968, 77.4412173), (12.8579968, 77.4412633), (12.8579968, 77.4413094), (12.8579968, 77.4413554), (12.8579968, 77.4414015), (12.8579958, 77.4414462), (12.8579532, 77.4414308), (12.8579516, 77.4413859), (12.8579516, 77.4413398), (12.8579516, 77.4412938), (12.8579516, 77.4412477), (12.8579516, 77.4412016), (12.8579343, 77.4412357), (12.8579154, 77.4412775), (12.8579064, 77.4413215), (12.8579064, 77.4413676), (12.8579063, 77.4414137)]
 


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
    takeoff_alt = 8  # meters
    
    flag = False
    first_waypoint = False

    while True:
        msg = await msg_queue.get()
        if msg.get("mavpackettype") == "GLOBAL_POSITION_INT":
            alt = msg["relative_alt"] / 1000.0
            print(f"Current altitude: {alt:.2f} m")
            master.mav.command_long_send(
            master.target_system,
            master.target_component,
            mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
            0,    
            0, 0, 0, 0,  
            0, 0,        
            takeoff_alt
            )
            if alt >= takeoff_alt:
                print("✅ Target altitude reached.")
                break
        
    
         
        
    for i, (lat, lon) in enumerate(path):

        first_waypoint = True

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
                int(0b110111111000), 
                int(lat * 1e7),
                int(lon * 1e7),
                takeoff_alt,
                0, 0, 0, 0, 0, 0, 0, 0
                ) 
                if dist < 0.5:  
                    print(f"✅ Reached waypoint {i+1}")
                    break

        await asyncio.sleep(1)
        push_capture.send_string("CAPTURE")
        



        while True and not flag and first_waypoint:

            new_coords = await socket_recv_micro_coords.recv_json()
            if new_coords[0] == None and new_coords[1] == None:
                break

            
            master.mav.set_position_target_global_int_send(
                0,   
                master.target_system,
                master.target_component,
                mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
                int(0b110111111000),  # mask for position only
                int(new_coords[0] * 1e7),
                int(new_coords[1] * 1e7),
                takeoff_alt,
                0, 0, 0, 0, 0, 0, 0, 0
                ) 
            
            if new_coords[2] == True:

                while True:
                    msg = await msg_queue.get()
                    if msg.get("mavpackettype") == "GLOBAL_POSITION_INT":
                        alt = msg["relative_alt"] / 1000.0
                        print(f"Current altitude: {alt:.2f} m")
                        if new_coords[0] is None or new_coords[1] is None:
                            continue

                        master.mav.set_position_target_global_int_send(
                            0,   
                            master.target_system,
                            master.target_component,
                            mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
                            int(0b110111111000),  
                            int(new_coords[0] * 1e7),
                            int(new_coords[1] * 1e7),
                            5,
                            0, 0, 0, 0, 0, 0, 0, 0
                        )  
                        if alt <= 5:
                            print("✅ Drop altitude reached.")
                            break

                set_servo_pwm(2200)
                await asyncio.sleep(2)
                set_servo_pwm(800)

                set_servo_pwm(2200)
                await asyncio.sleep(0.1)
                set_servo_pwm(800)
                set_servo_pwm(2200)
                await asyncio.sleep(0.1)
                set_servo_pwm(800)
                set_servo_pwm(2200)
                await asyncio.sleep(0.1)
                set_servo_pwm(800)
                set_servo_pwm(2200)
                await asyncio.sleep(0.1)
                set_servo_pwm(800)

                flag = True
                break

            
    
 
   
 

latest_position = None


 
    
async def telem_data_check(): 
    global latest_position
    while True:
        msg = await asyncio.to_thread(master.recv_match, blocking=True, timeout=1)
        if msg:
            await msg_queue.put(msg.to_dict())
            msg = msg.to_dict()
           
            if msg.get("mavpackettype") == "GLOBAL_POSITION_INT":
                latest_position = (
                    msg['lat'] / 1e7 ,
                    msg['lon'] / 1e7 ,
                    msg.get('hdg', 0) / 100.0
                ) 

                await socket.send_json(latest_position)



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

    asyncio.create_task(telem_data_check())

    await flight_ops()
       



    await rtl()
    await rtl()
    await rtl()
    await rtl()
    await rtl()
    await rtl()
    await rtl()

if __name__ == "__main__":
    asyncio.run(main())