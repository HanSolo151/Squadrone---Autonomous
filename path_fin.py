from pymavlink import mavutil
import time
import asyncio
import zmq
import zmq.asyncio
import math
import matplotlib.pyplot as plt
from shapely.geometry import Polygon, LineString, Point
from shapely.ops import transform
import pyproj
import math


context = zmq.Context()
socket = context.socket(zmq.PUB)
socket.bind("tcp://*:5556")  

def generate_inward_lawnmower_path(points, spacing=5, buffer_m=2, decimals=7):
    """
    points: list of (lat, lon) tuples defining polygon
    spacing: distance between lawnmower lines in meters
    buffer_m: inward buffer distance in meters
    decimals: number of decimal places for output coords
    Returns: list of (lat, lon) tuples representing the lawnmower path
    """

    def truncate_number(num, decimals=7):
        factor = 10 ** decimals
        return math.trunc(num * factor) / factor

    # --- Build original polygon ---
    poly = Polygon([(lon, lat) for lat, lon in points])

    # --- Projection to meters ---
    proj_latlon = pyproj.CRS("EPSG:4326")
    proj_local = pyproj.CRS.from_proj4(
        f"+proj=tmerc +lat_0={poly.centroid.y} +lon_0={poly.centroid.x} +units=m +datum=WGS84"
    )
    project_to_m = pyproj.Transformer.from_crs(proj_latlon, proj_local, always_xy=True).transform
    project_to_deg = pyproj.Transformer.from_crs(proj_local, proj_latlon, always_xy=True).transform

    # --- Offset polygon inward ---
    poly_m = transform(project_to_m, poly)
    poly_inward_m = poly_m.buffer(-buffer_m)
    poly_inward = transform(project_to_deg, poly_inward_m)
    inward_coords = [(truncate_number(lat, decimals), truncate_number(lon, decimals)) 
                     for lon, lat in poly_inward.exterior.coords]
    inward_coords.pop()  # remove duplicate last point

    # --- Generate lawnmower path ---
    poly_m = transform(project_to_m, Polygon([(lon, lat) for lat, lon in inward_coords]))
    minx, miny, maxx, maxy = poly_m.bounds
    lines = []
    y = miny
    while y <= maxy:
        lines.append(LineString([(minx, y), (maxx, y)]))
        y += spacing

    segments = []
    for i, line in enumerate(lines):
        clipped = line.intersection(poly_m)
        if clipped.is_empty:
            continue
        if clipped.geom_type == 'LineString':
            segments.append(list(clipped.coords))
        elif clipped.geom_type == 'MultiLineString':
            for seg in clipped.geoms:
                segments.append(list(seg.coords))

    path = []
    for i, seg in enumerate(segments):
        path.extend(seg if i % 2 == 0 else seg[::-1])

    path_latlon = [transform(project_to_deg, Point(x, y)) for x, y in path]
    lawnmower_path = [(truncate_number(pt.y, decimals), truncate_number(pt.x, decimals)) for pt in path_latlon]

    # --- Calculate Centroid ---
    centroid = poly_inward.centroid
    centroid_latlon = (truncate_number(centroid.y, decimals), truncate_number(centroid.x, decimals))

    return lawnmower_path

points = [
    (18.4898357, 73.8516485), 
    (18.4897898, 73.8509642),
    (18.4899831, 73.8509296),
    (18.4900890, 73.8515808)
]

path = generate_inward_lawnmower_path(points)

print(path)

 
 


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
