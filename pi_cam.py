import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import numpy as np
import cv2

# Initialize GStreamer
Gst.init(None)

# Change this to match your Jetson UDP stream
UDP_PORT = 5000
gst_pipeline = (
    f"udpsrc port={UDP_PORT} caps=application/x-rtp,encoding-name=H264,payload=96 ! "
    "rtpjitterbuffer latency=100 ! rtph264depay ! avdec_h264 ! "
    "videoconvert ! video/x-raw,format=BGR ! appsink name=sink emit-signals=true max-buffers=1 drop=true"
)

# Callback for new frames
def on_new_sample(sink):
    sample = sink.emit("pull-sample")
    if not sample:
        return Gst.FlowReturn.ERROR

    buf = sample.get_buffer()
    caps = sample.get_caps()
    width = caps.get_structure(0).get_value('width')
    height = caps.get_structure(0).get_value('height')

    success, map_info = buf.map(Gst.MapFlags.READ)
    if not success:
        return Gst.FlowReturn.ERROR

    # Convert to NumPy array
    frame = np.frombuffer(map_info.data, dtype=np.uint8).reshape((height, width, 3))
    buf.unmap(map_info)

    # --- Your ML code here ---
    cv2.imshow("Jetson Stream", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        GLib.MainLoop().quit()

    return Gst.FlowReturn.OK

# Build pipeline
pipeline = Gst.parse_launch(gst_pipeline)
sink = pipeline.get_by_name("sink")
sink.connect("new-sample", on_new_sample)

# Start streaming
pipeline.set_state(Gst.State.PLAYING)
loop = GLib.MainLoop()
try:
    print("📡 Receiving stream on Windows...")
    loop.run()
except KeyboardInterrupt:
    pass
finally:
    pipeline.set_state(Gst.State.NULL)
    cv2.destroyAllWindows()



'''
from picamera2 import Picamera2
import gi
import cv2
import numpy as np



gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

# Initialize GStreamer
Gst.init(None)

def start_stream():
    # Initialize camera
    picam2 = Picamera2()
    video_config = picam2.create_video_configuration(main={"format": "RGB888", "size": (640, 480)})
    picam2.configure(video_config)
    picam2.start()

    # GStreamer pipeline expects raw RGB input, then converts internally
    pipeline_str = (
		"appsrc name=mysrc is-live=true block=true format=TIME ! "
		"video/x-raw,format=RGB,width=640,height=480,framerate=30/1 ! "
		"videoconvert ! "
		"x264enc tune=zerolatency bitrate=4000000 speed-preset=superfast key-int-max=30 byte-stream=true ! "
		"rtph264pay config-interval=1 pt=96 ! "
		"udpsink host=192.168.0.100 port=5000"
	)

    # Launch GStreamer pipeline
    pipeline = Gst.parse_launch(pipeline_str)
    appsrc = pipeline.get_by_name("mysrc")

    def on_need_data(src, length):
        frame = picam2.capture_array()  # This is RGB888
        bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        
        data = bgr.tobytes()                    

        buf = Gst.Buffer.new_allocate(None, len(data), None)
        buf.fill(0, data)
        buf.duration = Gst.util_uint64_scale_int(1, Gst.SECOND, 30)
        timestamp = on_need_data.timestamp
        buf.pts = buf.dts = int(timestamp)
        buf.offset = timestamp
        on_need_data.timestamp += buf.duration

        retval = src.emit("push-buffer", buf)
        if retval != Gst.FlowReturn.OK:
            print("❌ Failed to push buffer")

    on_need_data.timestamp = 0
    appsrc.connect("need-data", on_need_data)

    pipeline.set_state(Gst.State.PLAYING)

    # Main loop
    loop = GLib.MainLoop()
    try:
        print("📡 Streaming RGB → H264 → Jetson...")
        loop.run()
    except KeyboardInterrupt:
        print("🛑 Stopping stream...")

    pipeline.set_state(Gst.State.NULL)

# Entry point
if _name_ == "_main_":
    start_stream()
'''