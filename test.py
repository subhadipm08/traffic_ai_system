import torch, cv2
from ultralytics import YOLO
import flask, numpy

print("Torch:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())
print("OpenCV:", cv2.__version__)

model = YOLO("yolov8n.pt")
print("YOLO model loaded successfully!")
