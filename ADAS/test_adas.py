#!/usr/bin/env python3
"""
test_adas.py - Test your ADAS system
"""

from adas_inference import AdasSystem
import cv2

# Initialize with your model paths
adas = AdasSystem(
    lane_model="models/lane_detection.onnx",
    object_model="models/yolov8n.onnx",
    sign_model="models/traffic_signs.onnx"
)

# Test with webcam
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    # Process frame
    result_frame, results = adas.process_frame(frame)
    
    # Show results
    cv2.imshow('ADAS', result_frame)
    
    # Print detections
    print(f"Lane departure: {results['lane'].lane_departure:.2f}")
    print(f"Objects: {len(results['objects'])}")
    print(f"Sign: {results['sign'].sign_type}")
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()