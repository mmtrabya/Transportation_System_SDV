#!/usr/bin/env python3
"""
test_full_adas.py - Complete ADAS System Test
Tests: Lane Detection + Object Detection + Traffic Sign Detection + Pedestrian Detection
Location: ~/Graduation_Project_SDV/tests/test_full_adas.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'raspberry_pi'))

from adas_inference import LaneDetector, ObjectDetector
import cv2
import logging
import time
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('Full_ADAS_Test')

# Traffic Sign Classes (GTSRB - German Traffic Sign Recognition Benchmark)
SIGN_CLASSES = [
    'Speed limit (20km/h)', 'Speed limit (30km/h)', 'Speed limit (50km/h)',
    'Speed limit (60km/h)', 'Speed limit (70km/h)', 'Speed limit (80km/h)',
    'End of speed limit (80km/h)', 'Speed limit (100km/h)', 'Speed limit (120km/h)',
    'No passing', 'No passing for vehicles over 3.5 metric tons',
    'Right-of-way at the next intersection', 'Priority road', 'Yield', 'Stop',
    'No vehicles', 'Vehicles over 3.5 metric tons prohibited', 'No entry',
    'General caution', 'Dangerous curve to the left', 'Dangerous curve to the right',
    'Double curve', 'Bumpy road', 'Slippery road', 'Road narrows on the right',
    'Road work', 'Traffic signals', 'Pedestrians', 'Children crossing',
    'Bicycles crossing', 'Beware of ice/snow', 'Wild animals crossing',
    'End of all speed and passing limits', 'Turn right ahead', 'Turn left ahead',
    'Ahead only', 'Go straight or right', 'Go straight or left', 'Keep right',
    'Keep left', 'Roundabout mandatory', 'End of no passing',
    'End of no passing by vehicles over 3.5 metric tons'
]

class TrafficSignDetector(ObjectDetector):
    """Traffic Sign Detector using YOLOv8"""
    
    def __init__(self, model_path: str, conf_threshold: float = 0.5):
        super().__init__(model_path, class_names=SIGN_CLASSES[:47], conf_threshold=conf_threshold)
        self.sign_classes = SIGN_CLASSES
        logger.info(f"Traffic Sign Detector initialized with {len(self.sign_classes)} classes")
    
    def draw_signs(self, image: np.ndarray, detections):
        """Draw detected traffic signs with labels"""
        overlay = image.copy()
        
        for det in detections:
            x1, y1, x2, y2 = det.bbox
            color = (255, 0, 255)  # Magenta for signs
            
            cv2.rectangle(overlay, (x1, y1), (x2, y2), color, 2)
            
            # Sign label
            sign_name = self.sign_classes[det.class_id] if det.class_id < len(self.sign_classes) else f"Sign {det.class_id}"
            label = f"{sign_name}: {det.confidence:.2f}"
            
            # Draw label background
            (label_w, label_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
            cv2.rectangle(overlay, (x1, y1 - label_h - 10), (x1 + label_w, y1), color, -1)
            cv2.putText(overlay, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        return overlay

def main():
    """Test complete ADAS system"""
    
    # Model paths
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    LANE_MODEL = os.path.join(project_root, "models", "Lane_Detection", "enet_sad.onnx")
    OBJECT_MODEL = os.path.join(project_root, "models", "Object_Detection", "yolov8n.onnx")
    SIGN_MODEL = os.path.join(project_root, "models", "Traffic_Sign", "yolov8n.onnx")
    
    # Check which models exist
    models_to_load = []
    
    if os.path.exists(LANE_MODEL):
        models_to_load.append(("Lane", LANE_MODEL))
        logger.info("✓ Lane Detection model found")
    else:
        logger.warning(f"✗ Lane model not found: {LANE_MODEL}")
    
    if os.path.exists(OBJECT_MODEL):
        models_to_load.append(("Object", OBJECT_MODEL))
        logger.info("✓ Object Detection model found")
    else:
        logger.warning(f"✗ Object model not found: {OBJECT_MODEL}")
    
    if os.path.exists(SIGN_MODEL):
        models_to_load.append(("Sign", SIGN_MODEL))
        logger.info("✓ Traffic Sign model found")
    else:
        logger.warning(f"✗ Sign model not found: {SIGN_MODEL}")
    
    if not models_to_load:
        logger.error("No models found! Please check your model paths.")
        return
    
    # Initialize detectors
    lane_detector = None
    object_detector = None
    sign_detector = None
    
    try:
        for model_type, model_path in models_to_load:
            if model_type == "Lane":
                lane_detector = LaneDetector(model_path)
                logger.info("✓ Lane Detector loaded")
            elif model_type == "Object":
                object_detector = ObjectDetector(model_path, conf_threshold=0.5)
                logger.info("✓ Object Detector loaded")
            elif model_type == "Sign":
                sign_detector = TrafficSignDetector(model_path, conf_threshold=0.4)
                logger.info("✓ Traffic Sign Detector loaded")
    except Exception as e:
        logger.error(f"Failed to load models: {e}")
        return
    
    # Setup camera
    logger.info("Opening webcam...")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        logger.error("Failed to open webcam")
        return
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    logger.info("Starting Complete ADAS Test...")
    logger.info("Controls:")
    logger.info("  'q' - Quit")
    logger.info("  's' - Save screenshot")
    logger.info("  '1' - Toggle lane detection")
    logger.info("  '2' - Toggle object detection")
    logger.info("  '3' - Toggle sign detection")
    
    frame_count = 0
    fps_list = []
    
    # Toggle flags
    show_lane = True
    show_objects = True
    show_signs = True
    
    try:
        while True:
            start_time = time.time()
            
            # Get frame
            ret, frame = cap.read()
            if not ret:
                logger.warning("Failed to read from webcam")
                break
            
            annotated = frame.copy()
            
            # Process each module
            lane_result = None
            object_detections = []
            sign_detections = []
            
            # Lane Detection
            if lane_detector and show_lane:
                lane_input = lane_detector.preprocess(frame)
                lane_output = lane_detector.inference(lane_input)
                lane_result = lane_detector.postprocess(lane_output, frame)
                annotated = lane_detector.draw_lanes(annotated, lane_result)
            
            # Object Detection (includes pedestrians)
            if object_detector and show_objects:
                obj_input = object_detector.preprocess(frame)
                obj_output = object_detector.inference(obj_input)
                object_detections = object_detector.postprocess(obj_output, frame)
                annotated = object_detector.draw_detections(annotated, object_detections)
            
            # Traffic Sign Detection
            if sign_detector and show_signs:
                sign_input = sign_detector.preprocess(frame)
                sign_output = sign_detector.inference(sign_input)
                sign_detections = sign_detector.postprocess(sign_output, frame)
                annotated = sign_detector.draw_signs(annotated, sign_detections)
            
            # Calculate FPS
            frame_time = time.time() - start_time
            fps_list.append(frame_time)
            if len(fps_list) > 30:
                fps_list.pop(0)
            fps = 1.0 / (sum(fps_list) / len(fps_list))
            
            # Draw info panel
            h, w = annotated.shape[:2]
            
            # FPS
            cv2.putText(annotated, f"FPS: {fps:.1f}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            # Module status
            y_offset = 70
            if lane_detector:
                status = "ON" if show_lane else "OFF"
                color = (0, 255, 0) if show_lane else (128, 128, 128)
                cv2.putText(annotated, f"[1] Lane: {status}", (10, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                y_offset += 30
            
            if object_detector:
                status = "ON" if show_objects else "OFF"
                color = (0, 255, 0) if show_objects else (128, 128, 128)
                cv2.putText(annotated, f"[2] Objects: {status}", (10, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                y_offset += 30
            
            if sign_detector:
                status = "ON" if show_signs else "OFF"
                color = (0, 255, 0) if show_signs else (128, 128, 128)
                cv2.putText(annotated, f"[3] Signs: {status}", (10, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                y_offset += 30
            
            # Detection counts
            if lane_result and show_lane:
                cv2.putText(annotated, f"Lane Dep: {lane_result.lane_departure:.3f}", (10, h - 80),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            if show_objects:
                total_objects = len(object_detections)
                pedestrians = sum(1 for det in object_detections if det.is_pedestrian)
                cv2.putText(annotated, f"Objects: {total_objects} | Pedestrians: {pedestrians}", (10, h - 50),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            if show_signs:
                cv2.putText(annotated, f"Signs: {len(sign_detections)}", (10, h - 20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Display
            cv2.imshow('Complete ADAS Test - Press Q to quit', annotated)
            
            # Print info every 30 frames
            frame_count += 1
            if frame_count % 30 == 0:
                print(f"\n{'='*50}")
                print(f"Frame {frame_count} | FPS: {fps:.1f}")
                print(f"{'='*50}")
                
                if lane_result and show_lane:
                    print(f"🛣️  Lane Departure: {lane_result.lane_departure:.3f}")
                    if abs(lane_result.lane_departure) < 0.1:
                        print("   Status: ✓ Centered")
                    elif abs(lane_result.lane_departure) < 0.3:
                        print("   Status: ⚠ Slight deviation")
                    else:
                        print("   Status: ⚠ High deviation")
                
                if show_objects and object_detections:
                    pedestrians = [det for det in object_detections if det.is_pedestrian]
                    vehicles = [det for det in object_detections if det.class_name in ['car', 'truck', 'bus', 'motorcycle']]
                    
                    print(f"🚶 Pedestrians: {len(pedestrians)}")
                    for i, det in enumerate(pedestrians[:3], 1):
                        print(f"   {i}. Conf: {det.confidence:.2f}, Dist: {det.distance:.1f}m")
                    
                    print(f"🚗 Vehicles: {len(vehicles)}")
                    for i, det in enumerate(vehicles[:3], 1):
                        print(f"   {i}. {det.class_name}: {det.confidence:.2f}, {det.distance:.1f}m")
                
                if show_signs and sign_detections:
                    print(f"🚦 Traffic Signs: {len(sign_detections)}")
                    for i, det in enumerate(sign_detections[:3], 1):
                        sign_name = SIGN_CLASSES[det.class_id] if det.class_id < len(SIGN_CLASSES) else f"Sign {det.class_id}"
                        print(f"   {i}. {sign_name}: {det.confidence:.2f}")
            
            # Handle keypresses
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q'):
                logger.info("Quit requested by user")
                break
            elif key == ord('s'):
                screenshot_path = f"adas_full_screenshot_{frame_count}.jpg"
                cv2.imwrite(screenshot_path, annotated)
                logger.info(f"Screenshot saved: {screenshot_path}")
            elif key == ord('1'):
                show_lane = not show_lane
                logger.info(f"Lane detection: {'ON' if show_lane else 'OFF'}")
            elif key == ord('2'):
                show_objects = not show_objects
                logger.info(f"Object detection: {'ON' if show_objects else 'OFF'}")
            elif key == ord('3'):
                show_signs = not show_signs
                logger.info(f"Sign detection: {'ON' if show_signs else 'OFF'}")
    
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    
    finally:
        cap.release()
        cv2.destroyAllWindows()
        logger.info("ADAS test completed")

if __name__ == "__main__":
    main()