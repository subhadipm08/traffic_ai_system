import cv2
import torch
from ultralytics import YOLO
import time

# MODIFIED: Function now accepts a 'processed_frames' shared dictionary
def video_worker(video_path, lane, vehicle_counts, processed_frames):
    """
    Worker process: runs YOLO on the video for one lane
    Updates vehicle_counts[lane] and processed_frames[lane]
    """
    print(f"[{lane}] 🚦 Starting detection on {video_path}")

    # Load YOLO model inside this process
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = YOLO("yolov8n.pt").to(device)
    
    # NEW: Class names for drawing labels
    class_names = model.names

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[{lane}] ❌ Could not open video")
        vehicle_counts[lane] = 0
        processed_frames[lane] = None # NEW: Set frame to None on error
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            print(f"[{lane}] ✅ Finished video stream")
            break

        # Process the frame with YOLO
        results = model(frame, verbose=False)
        count = 0
        
        # MODIFIED: Draw boxes and count vehicles
        for r in results:
            boxes = r.boxes
            for box in boxes:
                cls_id = int(box.cls[0])
                # Check if the detected object is a vehicle
                if cls_id in [2, 3, 5, 7]: # car, motorcycle, bus, truck
                    count += 1
                    # Get coordinates
                    x1, y1, x2, y2 = box.xyxy[0]
                    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                    
                    # Draw rectangle
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    
                    # Put label
                    label = f'{class_names[cls_id]}'
                    cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Update the shared vehicle count
        vehicle_counts[lane] = count

        # NEW: Encode the processed frame to JPEG and update the shared dictionary
        ret, buffer = cv2.imencode('.jpg', frame)
        if ret:
            processed_frames[lane] = buffer.tobytes()

    cap.release()
    processed_frames[lane] = None # NEW: Clear the frame when video ends
    print(f"[{lane}] ❌ Worker stopped")
