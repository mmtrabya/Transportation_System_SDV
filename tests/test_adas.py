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

# We still import SignRecognizer so the file doesn't crash, but we won't use it
from adas_inference import LaneDetector, ObjectDetector, SignRecognizer
import cv2
import logging
import time
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('Full_ADAS_Test')

# ADAS-specific Object Detection Classes (Correct COCO IDs)
OBJECT_CLASSES = {
    0: 'person',
    1: 'bicycle',
    2: 'car',
    5: 'bus',
    7: 'truck',
    9: 'traffic light'
}

# Traffic Sign Classes (GTSRB - German Traffic Sign Recognition Benchmark)
# This map is used by your TrafficSignDetectorYOLO
SIGN_CLASSES = {
    0: 'Speed limit (20km/h)', 1: 'Speed limit (30km/h)', 2: 'Speed limit (50km/h)', 
    3: 'Speed limit (60km/h)', 4: 'Speed limit (70km/h)', 5: 'Speed limit (80km/h)', 
    6: 'End of speed limit (80km/h)', 7: 'Speed limit (100km/h)', 8: 'Speed limit (120km/h)', 
    9: 'No passing', 10: 'No passing veh over 3.5 tons', 11: 'Right-of-way at intersection', 
    12: 'Priority road', 13: 'Yield', 14: 'Stop', 15: 'No vehicles', 
    16: 'Veh > 3.5 tons prohibited', 17: 'No entry', 18: 'General caution', 
    19: 'Dangerous curve left', 20: 'Dangerous curve right', 21: 'Double curve', 
    22: 'Bumpy road', 23: 'Slippery road', 24: 'Road narrows on the right', 
    25: 'Road work', 26: 'Traffic signals', 27: 'Pedestrians', 28: 'Children crossing', 
    29: 'Bicycles crossing', 30: 'Beware of ice/snow', 31: 'Wild animals crossing', 
    32: 'End speed + passing limits', 33: 'Turn right ahead', 34: 'Turn left ahead', 
    35: 'Ahead only', 36: 'Go straight or right', 37: 'Go straight or left', 
    38: 'Keep right', 39: 'Keep left', 40: 'Roundabout mandatory', 
    41: 'End of no passing', 42: 'End no passing veh > 3.5 tons'
}

class TrafficSignDetectorYOLO(ObjectDetector):
    """Traffic Sign Detector using YOLOv8 (Detection model, not classification)"""
    
    def __init__(self, model_path: str, conf_threshold: float = 0.4):
        # Initialize with sign classes instead of object classes
        # This assumes your 'last.onnx' model was trained with IDs 0-42
        # matching the SIGN_CLASSES dictionary.
        super().__init__(model_path, class_names=SIGN_CLASSES, conf_threshold=conf_threshold)
        logger.info(f"Traffic Sign Detector (YOLO) initialized with {len(SIGN_CLASSES)} classes")
    
    def draw_signs(self, image: np.ndarray, detections):
        """Draw detected traffic signs with labels"""
        overlay = image.copy()
        
        for det in detections:
            x1, y1, x2, y2 = det.bbox
            color = (255, 0, 255)  # Magenta for signs
            
            cv2.rectangle(overlay, (x1, y1), (x2, y2), color, 3)
            
            # Sign label with proper name lookup
            label = f"{det.class_name}: {det.confidence:.2f}"
            
            # Draw label background
            (label_w, label_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(overlay, (x1, y1 - label_h - 10), (x1 + label_w, y1), color, -1)
            cv2.putText(overlay, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        return overlay

def main():
    """Test complete ADAS system"""
    
    # Model paths
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    LANE_MODEL = os.path.join(project_root, "models", "Lane_Detection", "enet_sad.onnx")
    OBJECT_MODEL = os.path.join(project_root, "models", "Object_Detection", "yolov8n.onnx")
    
    # === SIMPLIFIED SIGN MODEL LOADING ===
    # We only look for the YOLO detection model now
    SIGN_MODEL_YOLO = os.path.join(project_root, "models", "Traffic_Sign", "last.onnx")
    
    # Check which models exist
    models_info = []
    
    if os.path.exists(LANE_MODEL):
        models_info.append(("Lane", LANE_MODEL))
        logger.info("✓ Lane Detection model found")
    else:
        logger.warning(f"✗ Lane model not found: {LANE_MODEL}")
    
    if os.path.exists(OBJECT_MODEL):
        models_info.append(("Object", OBJECT_MODEL))
        logger.info("✓ Object Detection model found")
    else:
        logger.warning(f"✗ Object model not found: {OBJECT_MODEL}")
    
    # === SIMPLIFIED SIGN MODEL LOADING ===
    if os.path.exists(SIGN_MODEL_YOLO):
        models_info.append(("Sign", SIGN_MODEL_YOLO))
        logger.info("✓ Traffic Sign YOLO model found")
    else:
        logger.warning(f"✗ No sign model found at {SIGN_MODEL_YOLO}")
    
    if not models_info:
        logger.error("No models found! Please check your model paths.")
        return
    
    # Initialize detectors
    lane_detector = None
    object_detector = None
    sign_detector = None
    # 'sign_is_classifier' flag is removed
    
    try:
        # === SIMPLIFIED MODEL LOADING ===
        for model_type, model_path in models_info:
            if model_type == "Lane":
                lane_detector = LaneDetector(model_path)
                logger.info("✓ Lane Detector loaded")
            elif model_type == "Object":
                object_detector = ObjectDetector(model_path, class_names=OBJECT_CLASSES, conf_threshold=0.5)
                logger.info("✓ Object Detector loaded")
            elif model_type == "Sign":
                # We only load the YOLO detector now
                sign_detector = TrafficSignDetectorYOLO(model_path, conf_threshold=0.4)
                logger.info("✓ Traffic Sign YOLO Detector loaded")
    except Exception as e:
        logger.error(f"Failed to load models: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Setup camera
    logger.info("Opening webcam...")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        logger.error("Failed to open webcam")
        return
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    logger.info("\n" + "="*60)
    logger.info("Starting Complete ADAS Test")
    logger.info("="*60)
    logger.info("Controls:")
    logger.info("  'q' - Quit")
    logger.info("  's' - Save screenshot")
    logger.info("  '1' - Toggle lane detection")
    logger.info("  '2' - Toggle object detection")
    logger.info("  '3' - Toggle sign detection")
    logger.info("="*60 + "\n")
    
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
            # 'sign_result' is removed
            
            # Lane Detection
            if lane_detector and show_lane:
                try:
                    lane_input = lane_detector.preprocess(frame)
                    lane_output = lane_detector.inference(lane_input)
                    lane_result = lane_detector.postprocess(lane_output, frame)
                    annotated = lane_detector.draw_lanes(annotated, lane_result)
                except Exception as e:
                    logger.error(f"Lane detection error: {e}")
            
            # Object Detection (includes pedestrians)
            if object_detector and show_objects:
                try:
                    obj_input = object_detector.preprocess(frame)
                    obj_output = object_detector.inference(obj_input)
                    # We pass 'frame' to postprocess, but not depth_frame (which is None)
                    object_detections = object_detector.postprocess(obj_output, frame)
                    annotated = object_detector.draw_detections(annotated, object_detections)
                except Exception as e:
                    logger.error(f"Object detection error: {e}")
            
            # Traffic Sign Detection/Recognition
            if sign_detector and show_signs:
                try:
                    sign_input = sign_detector.preprocess(frame)
                    sign_output = sign_detector.inference(sign_input)
                    
                    # === SIMPLIFIED SIGN PROCESSING ===
                    # We only expect a list of detections now
                    sign_detections = sign_detector.postprocess(sign_output, frame)
                    annotated = sign_detector.draw_signs(annotated, sign_detections)
                except Exception as e:
                    logger.error(f"Sign detection error: {e}")
            
            # Calculate FPS
            frame_time = time.time() - start_time
            fps_list.append(frame_time)
            if len(fps_list) > 30:
                fps_list.pop(0)
            fps = 1.0 / (sum(fps_list) / len(fps_list)) if fps_list else 0
            
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
                # === SIMPLIFIED TEXT ===
                sign_type = "Detector"
                cv2.putText(annotated, f"[3] Signs ({sign_type}): {status}", (10, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                y_offset += 30
            
            # Detection counts
            y_bottom = h - 20
            
            # === SIMPLIFIED SIGN COUNT ===
            if show_signs:
                cv2.putText(annotated, f"Signs: {len(sign_detections)}", (10, y_bottom),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                y_bottom -= 30
            
            if show_objects:
                total_objects = len(object_detections)
                pedestrians = sum(1 for det in object_detections if det.is_pedestrian)
                cv2.putText(annotated, f"Objects: {total_objects} | Pedestrians: {pedestrians}", (10, y_bottom),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                y_bottom -= 30
            
            if lane_result and show_lane:
                cv2.putText(annotated, f"Lane Dep: {lane_result.lane_departure:.3f}", (10, y_bottom),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            # Display
            cv2.imshow('Complete ADAS Test - Press Q to quit', annotated)
            
            # Print info every 30 frames
            frame_count += 1
            if frame_count % 30 == 0:
                print(f"\n{'='*60}")
                print(f"Frame {frame_count} | FPS: {fps:.1f}")
                print(f"{'='*60}")
                
                if lane_result and show_lane:
                    print(f"🛣️  Lane Departure: {lane_result.lane_departure:.3f}")
                    if abs(lane_result.lane_departure) < 0.1:
                        print("   Status: ✓ Centered")
                    elif abs(lane_result.lane_departure) < 0.3:
                        print("   Status: ⚠️ Slight deviation")
                    else:
                        print("   Status: ⚠️ High deviation")
                
                if show_objects and object_detections:
                    pedestrians = [det for det in object_detections if det.is_pedestrian]
                    vehicles = [det for det in object_detections if det.class_name in ['car', 'truck']]
                    
                    print(f"🚶 Pedestrians: {len(pedestrians)}")
                    for i, det in enumerate(pedestrians[:3], 1):
                        dist_str = f"{det.distance:.1f}m" if det.distance else "N/A"
                        print(f"   {i}. Conf: {det.confidence:.2f}, Dist: {dist_str}")
                    
                    print(f"🚗 Vehicles: {len(vehicles)}")
                    for i, det in enumerate(vehicles[:3], 1):
                        dist_str = f"{det.distance:.1f}m" if det.distance else "N/A"
                        print(f"   {i}. {det.class_name}: {det.confidence:.2f}, {dist_str}")
                
                # === SIMPLIFIED SIGN PRINTING ===
                if show_signs:
                    if sign_detections:
                        print(f"🚦 Traffic Signs: {len(sign_detections)}")
                        for i, det in enumerate(sign_detections[:3], 1):
                            print(f"   {i}. {det.class_name}: {det.confidence:.2f}")
                    else:
                        print(f"🚦 Traffic Signs: 0")
            
            # Handle keypresses
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q'):
                logger.info("Quit requested by user")
                break
            elif key == ord('s'):
                screenshot_dir = os.path.join(project_root, "screenshots")
                os.makedirs(screenshot_dir, exist_ok=True)
                screenshot_path = os.path.join(screenshot_dir, f"adas_full_screenshot_{frame_count}.jpg")
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
        logger.info("\nInterrupted by user")
    
    finally:
        cap.release()
        cv2.destroyAllWindows()
        logger.info("\n" + "="*60)
        logger.info("ADAS test completed")
        logger.info(f"Total frames processed: {frame_count}")
        if fps_list:
            avg_fps = 1.0 / (sum(fps_list) / len(fps_list))
            logger.info(f"Average FPS: {avg_fps:.1f}")
        logger.info("="*60)

if __name__ == "__main__":
    main()