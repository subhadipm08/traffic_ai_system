import cv2
import torch
from ultralytics import YOLO

# MODIFIED: Renamed to image_worker and simplified for single image processing
def image_worker(image_path, lane, vehicle_counts, processed_frames):
    """
    Worker process: runs YOLO on a single image for one lane
    Updates vehicle_counts[lane] and processed_frames[lane]
    """
    print(f"[{lane}] 🖼️  Starting detection on {image_path}")

    # Load YOLO model
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = YOLO("yolov8n.pt").to(device)
    class_names = model.names

    # Read the image
    frame = cv2.imread(image_path)
    if frame is None:
        print(f"[{lane}] ❌ Could not open image")
        vehicle_counts[lane] = 0
        processed_frames[lane] = None
        return

    # Process the frame with YOLO
    results = model(frame, verbose=False)
    count = 0

    # Draw boxes and count vehicles
    for r in results:
        boxes = r.boxes
        for box in boxes:
            cls_id = int(box.cls[0])
            if cls_id in [2, 3, 5, 7]:  # car, motorcycle, bus, truck
                count += 1
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                # Draw rectangle and label
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                label = f'{class_names[cls_id]}'
                cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    # Update the shared vehicle count
    vehicle_counts[lane] = count
    print(f"[{lane}] Detected {count} vehicles")

    # Encode the processed frame to JPEG and update the shared dictionary
    ret, buffer = cv2.imencode('.jpg', frame)
    if ret:
        processed_frames[lane] = buffer.tobytes()

    print(f"[{lane}] ✅ Finished processing")