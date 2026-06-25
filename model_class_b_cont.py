import os
import time
from ultralytics import YOLO

CAPTURE_DIR = r"C:\Users\THINKPAD\Desktop\Autonomous Squadrone\captures"
model = YOLO("best.pt")

processed = set()

# Accumulator: { "person": { "conf": 0.91, "box": [..], "count": 1 }, ... }
objects_seen = {}

print("📡 YOLO watcher started… monitoring captured frames...\n")

while True:

    for fname in os.listdir(CAPTURE_DIR):
        if not fname.lower().endswith((".jpg", ".png", ".jpeg")):
            continue

        if fname in processed:
            continue

        img_path = os.path.join(CAPTURE_DIR, fname)
        print(f"\n🖼️ New image: {fname}")

        # ---- YOLO inference ----
        results = model(img_path)
        r = results[0]

        if len(r.boxes) == 0:
            print("   ❌ No objects detected.")
        else:
            for box in r.boxes:
                cls = int(box.cls[0])
                label = r.names[cls]
                conf = float(box.conf[0])
                xyxy = box.xyxy[0].tolist()

                # ---- ACCUMULATE RESULTS ----
                if label not in objects_seen:
                    # first time seeing this object
                    objects_seen[label] = {
                        "conf": conf,
                        "box": xyxy,
                        "count": 1
                    }
                else:
                    # object already exists → update only if new conf is better
                    if conf > objects_seen[label]["conf"]:
                        objects_seen[label]["conf"] = conf
                        objects_seen[label]["box"] = xyxy
                    objects_seen[label]["count"] += 1

                print(f"   ✔ {label}  conf={conf:.2f}  box={xyxy}")

        # Save annotated output
        out_dir = "runs/detect_live"
        os.makedirs(out_dir, exist_ok=True)
        r.save(filename=f"{out_dir}/{fname}")

        processed.add(fname)

        # ---- PRINT CURRENT BEST STATE ----
        print("\n📊 CURRENT BEST OBJECT SET:")
        for obj, info in objects_seen.items():
            print(f"   - {obj} → best_conf={info['conf']:.2f}, seen={info['count']} times")

    time.sleep(0.5)
