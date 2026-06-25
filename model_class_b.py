import os
from ultralytics import YOLO

# --- PATHS ---
CAPTURE_DIR = r"C:\Users\THINKPAD\Desktop\Autonomous Squadrone\captures"

# --- LOAD MODEL ---
model = YOLO("yolov8n.pt")

# --- PROCESS ALL IMAGES IN FOLDER ---
for fname in os.listdir(CAPTURE_DIR):
    if fname.lower().endswith((".jpg", ".png", ".jpeg")):

        img_path = os.path.join(CAPTURE_DIR, fname)
        print(f"\n🖼️ Processing: {fname}")

        # Run inference
        results = model(img_path)

        # results is a list, take first
        r = results[0]

        # print detections
        if len(r.boxes) == 0:
            print("   ❌ No objects detected.")
            continue

        for box in r.boxes:
            cls = int(box.cls[0])                     # class index
            label = r.names[cls]                      # class name
            conf = float(box.conf[0])                 # confidence
            xyxy = box.xyxy[0].tolist()               # [x1,y1,x2,y2]

            print(f"   ✔ {label}  conf={conf:.2f}  box={xyxy}")

        # OPTIONAL: Save image with bounding boxes
        r.save(filename=f"runs/detect/{fname}")

print("\n✅ Done processing all images.")
