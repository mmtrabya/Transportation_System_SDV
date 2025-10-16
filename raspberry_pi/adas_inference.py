#!/usr/bin/env python3
"""
ADAS ONNX Model Inference System (Road Monitoring)
Uses Xbox 360 Kinect Camera for external environment monitoring
Modules: Lane Detection, Object Detection, Traffic Sign Recognition, Pedestrian Detection
Location: ~/Graduation_Project_SDV/raspberry_pi/adas_inference.py
"""

import cv2
import numpy as np
import onnxruntime as ort
import time
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import logging
import freenect

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('ADAS_Inference')

# ==================== DATA STRUCTURES ====================

@dataclass
class DetectionResult:
    """Object/Pedestrian detection result"""
    class_id: int
    class_name: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    distance: Optional[float] = None  # meters (from Kinect depth)
    is_pedestrian: bool = False

@dataclass
class LaneResult:
    """Lane detection result"""
    left_lane: Optional[np.ndarray]
    right_lane: Optional[np.ndarray]
    lane_center: Optional[np.ndarray]
    lane_departure: float  # -1 to 1, 0 = centered
    confidence: float

@dataclass
class SignResult:
    """Traffic sign recognition result"""
    sign_type: str
    confidence: float
    bbox: Optional[Tuple[int, int, int, int]] = None

# ==================== KINECT CAMERA INTERFACE ====================

class KinectCamera:
    """Xbox 360 Kinect camera interface"""
    
    def __init__(self):
        """Initialize Kinect camera"""
        self.ctx = None
        self.dev = None
        self.connected = False
        
        try:
            # Initialize Kinect
            self.ctx = freenect.init()
            self.dev = freenect.open_device(self.ctx, 0)
            
            if self.dev:
                # Set LED to green
                freenect.set_led(self.dev, freenect.LED_GREEN)
                self.connected = True
                logger.info("✓ Kinect camera connected")
            else:
                logger.error("Failed to open Kinect device")
        except Exception as e:
            logger.error(f"Kinect initialization failed: {e}")
            logger.info("Falling back to standard camera...")
    
    def get_frame(self) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """Get RGB and Depth frames from Kinect"""
        if not self.connected:
            return None, None
        
        try:
            rgb_frame, _ = freenect.sync_get_video()
            depth_frame, _ = freenect.sync_get_depth()
            rgb_frame = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2BGR)
            return rgb_frame, depth_frame
        except Exception as e:
            logger.error(f"Error reading from Kinect: {e}")
            return None, None
    
    def get_bbox_distance(self, depth_frame: np.ndarray, bbox: Tuple[int, int, int, int]) -> float:
        """Calculate average distance for bounding box"""
        if depth_frame is None:
            return -1.0
        
        x1, y1, x2, y2 = bbox
        x1 = max(0, min(x1, depth_frame.shape[1] - 1))
        x2 = max(0, min(x2, depth_frame.shape[1] - 1))
        y1 = max(0, min(y1, depth_frame.shape[0] - 1))
        y2 = max(0, min(y2, depth_frame.shape[0] - 1))
        
        roi = depth_frame[y1:y2, x1:x2]
        if roi.size == 0:
            return -1.0
        
        valid_depths = roi[(roi > 0) & (roi < 10000)]
        if len(valid_depths) == 0:
            return -1.0
        
        return np.median(valid_depths) / 1000.0
    
    def release(self):
        """Release Kinect resources"""
        if self.connected and self.dev:
            freenect.set_led(self.dev, freenect.LED_OFF)
            freenect.close_device(self.dev)
            logger.info("Kinect camera released")

# ==================== BASE ONNX MODEL CLASS ====================

class ONNXModel:
    """Base class for ONNX model inference"""
    
    def __init__(self, model_path: str, providers: List[str] = None):
        if providers is None:
            providers = ['CPUExecutionProvider']
        
        try:
            self.session = ort.InferenceSession(model_path, providers=providers)
            self.input_name = self.session.get_inputs()[0].name
            self.output_names = [output.name for output in self.session.get_outputs()]
            
            input_shape = self.session.get_inputs()[0].shape
            
            # Handle dynamic dimensions (strings like 'batch', 'height', 'width')
            if len(input_shape) > 2:
                # Try to get height from index 2
                if isinstance(input_shape[2], int):
                    self.input_height = input_shape[2]
                else:
                    self.input_height = 640  # Default for dynamic dimension
                
                # Try to get width from index 3
                if len(input_shape) > 3 and isinstance(input_shape[3], int):
                    self.input_width = input_shape[3]
                else:
                    self.input_width = 640  # Default for dynamic dimension
            else:
                self.input_height = 640
                self.input_width = 640
            
            logger.info(f"Model loaded: {model_path}")
            logger.info(f"Input shape: {input_shape}")
            logger.info(f"Using input size: {self.input_width}x{self.input_height}")
            
        except Exception as e:
            logger.error(f"Failed to load model {model_path}: {e}")
            raise
    
    def preprocess(self, image: np.ndarray) -> np.ndarray:
        """Preprocess image for model input"""
        img = cv2.resize(image, (self.input_width, self.input_height))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = img.astype(np.float32) / 255.0
        img = np.transpose(img, (2, 0, 1))
        img = np.expand_dims(img, axis=0)
        return img
    
    def inference(self, preprocessed_input: np.ndarray) -> List[np.ndarray]:
        """Run inference"""
        outputs = self.session.run(self.output_names, {self.input_name: preprocessed_input})
        return outputs
    
    def postprocess(self, outputs: List[np.ndarray], original_image: np.ndarray):
        """Postprocess model outputs - override in child classes"""
        raise NotImplementedError

# ==================== LANE DETECTION ====================

class LaneDetector(ONNXModel):
    """Lane detection using ONNX model (ENet/ENet-SAD/SCNN)"""
    
    def __init__(self, model_path: str):
        super().__init__(model_path)
        self.lane_history = []
        self.history_size = 5
    
    def postprocess(self, outputs: List[np.ndarray], original_image: np.ndarray) -> LaneResult:
        """Postprocess lane detection output"""
        output = outputs[0]
        
        if len(output.shape) == 4:  # [1, C, H, W]
            lane_mask = output[0]
            
            if lane_mask.shape[0] > 2:
                left_mask = lane_mask[1]
                right_mask = lane_mask[2]
            else:
                combined_mask = lane_mask[0] if lane_mask.shape[0] == 1 else lane_mask.max(axis=0)
                left_mask = combined_mask.copy()
                right_mask = combined_mask.copy()
            
            h, w = original_image.shape[:2]
            left_mask = cv2.resize(left_mask, (w, h))
            right_mask = cv2.resize(right_mask, (w, h))
            
            left_lane = self._extract_lane_points(left_mask, side='left')
            right_lane = self._extract_lane_points(right_mask, side='right')
            
        elif len(output.shape) == 3:  # [1, num_points, 2]
            points = output[0]
            h, w = original_image.shape[:2]
            points[:, 0] *= w
            points[:, 1] *= h
            mid = len(points) // 2
            left_lane = points[:mid]
            right_lane = points[mid:]
        else:
            logger.warning(f"Unexpected lane detection output shape: {output.shape}")
            return LaneResult(None, None, None, 0.0, 0.0)
        
        lane_center = None
        lane_departure = 0.0
        
        if left_lane is not None and right_lane is not None and len(left_lane) > 0 and len(right_lane) > 0:
            # Interpolate lanes to have same number of points
            max_len = max(len(left_lane), len(right_lane))
            
            # Interpolate left lane
            if len(left_lane) != max_len:
                left_y = np.linspace(left_lane[0, 1], left_lane[-1, 1], max_len)
                left_x = np.interp(left_y, left_lane[:, 1], left_lane[:, 0])
                left_lane = np.column_stack([left_x, left_y])
            
            # Interpolate right lane
            if len(right_lane) != max_len:
                right_y = np.linspace(right_lane[0, 1], right_lane[-1, 1], max_len)
                right_x = np.interp(right_y, right_lane[:, 1], right_lane[:, 0])
                right_lane = np.column_stack([right_x, right_y])
            
            # Now calculate center with matching shapes
            lane_center = (left_lane + right_lane) / 2
            
            image_center = original_image.shape[1] / 2
            lane_bottom_center = lane_center[-1][0] if len(lane_center) > 0 else image_center
            lane_departure = (lane_bottom_center - image_center) / image_center
        
        confidence = 0.8 if left_lane is not None and right_lane is not None else 0.3
        left_lane = self._smooth_lane(left_lane)
        right_lane = self._smooth_lane(right_lane)
        
        return LaneResult(left_lane, right_lane, lane_center, lane_departure, confidence)
    
    def _extract_lane_points(self, mask: np.ndarray, side: str, threshold: float = 0.5) -> np.ndarray:
        """Extract lane points from segmentation mask"""
        mask = (mask > threshold).astype(np.uint8)
        if mask.sum() < 10:
            return None
        
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None
        
        largest_contour = max(contours, key=cv2.contourArea)
        points = largest_contour.reshape(-1, 2)
        points = points[points[:, 1].argsort()]
        return points
    
    def _smooth_lane(self, lane: np.ndarray) -> np.ndarray:
        """Smooth lane using temporal history"""
        if lane is None:
            return None
        
        # Only smooth if lane has consistent shape
        if len(self.lane_history) > 0:
            # Check if new lane has same shape as previous
            if self.lane_history[-1] is not None and lane.shape != self.lane_history[-1].shape:
                # Clear history if shape changed
                self.lane_history = []
        
        self.lane_history.append(lane)
        if len(self.lane_history) > self.history_size:
            self.lane_history.pop(0)
        
        # Only average if we have multiple frames with same shape
        if len(self.lane_history) > 1:
            try:
                return np.mean(self.lane_history, axis=0)
            except ValueError:
                # If averaging fails due to shape mismatch, clear history and return current
                self.lane_history = [lane]
                return lane
        
        return lane
    
    def draw_lanes(self, image: np.ndarray, lane_result: LaneResult) -> np.ndarray:
        """Draw detected lanes on image"""
        overlay = image.copy()
        
        if lane_result.left_lane is not None:
            pts = lane_result.left_lane.astype(np.int32)
            cv2.polylines(overlay, [pts], False, (0, 255, 0), 3)
        
        if lane_result.right_lane is not None:
            pts = lane_result.right_lane.astype(np.int32)
            cv2.polylines(overlay, [pts], False, (0, 255, 0), 3)
        
        if lane_result.lane_center is not None:
            pts = lane_result.lane_center.astype(np.int32)
            cv2.polylines(overlay, [pts], False, (255, 0, 0), 2)
        
        h, w = image.shape[:2]
        center_x = int(w / 2)
        departure_pixels = int(lane_result.lane_departure * w / 2)
        
        color = (0, 255, 0) if abs(lane_result.lane_departure) < 0.1 else (0, 165, 255) if abs(lane_result.lane_departure) < 0.3 else (0, 0, 255)
        cv2.circle(overlay, (center_x + departure_pixels, h - 50), 10, color, -1)
        cv2.putText(overlay, f"Departure: {lane_result.lane_departure:.2f}", (10, h - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        return overlay

# ==================== OBJECT & PEDESTRIAN DETECTION ====================

class ObjectDetector(ONNXModel):
    """Object and pedestrian detection using YOLOv8"""
    
    def __init__(self, model_path: str, class_names: List[str] = None, conf_threshold: float = 0.5):
        super().__init__(model_path)
        self.conf_threshold = conf_threshold
        self.iou_threshold = 0.45
        
        self.class_names = class_names or [
            'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck',
            'boat', 'traffic light', 'fire hydrant', 'stop sign', 'parking meter', 'bench',
            'bird', 'cat', 'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra',
            'giraffe', 'backpack', 'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee'
        ]
        self.pedestrian_classes = ['person']
    
    def postprocess(self, outputs: List[np.ndarray], original_image: np.ndarray, 
                   depth_frame: Optional[np.ndarray] = None, kinect: Optional[KinectCamera] = None) -> List[DetectionResult]:
        """Postprocess YOLOv8 output with Kinect depth"""
        output = outputs[0]
        
        if output.shape[1] == 84 or output.shape[1] > 100:
            output = output[0].T
        else:
            output = output[0]
        
        detections = []
        h, w = original_image.shape[:2]
        scale_x = w / self.input_width
        scale_y = h / self.input_height
        
        for detection in output:
            x_center, y_center, width, height = detection[:4]
            
            if len(detection) > 5:
                confidence = detection[4]
                class_scores = detection[5:]
            else:
                class_scores = detection[4:]
                confidence = class_scores.max()
            
            if confidence < self.conf_threshold:
                continue
            
            class_id = int(class_scores.argmax())
            class_conf = class_scores[class_id]
            
            if class_conf < self.conf_threshold:
                continue
            
            x1 = int((x_center - width / 2) * scale_x)
            y1 = int((y_center - height / 2) * scale_y)
            x2 = int((x_center + width / 2) * scale_x)
            y2 = int((y_center + height / 2) * scale_y)
            
            x1 = max(0, min(x1, w))
            y1 = max(0, min(y1, h))
            x2 = max(0, min(x2, w))
            y2 = max(0, min(y2, h))
            
            distance = None
            if depth_frame is not None and kinect is not None:
                distance = kinect.get_bbox_distance(depth_frame, (x1, y1, x2, y2))
            
            if distance is None or distance <= 0:
                distance = self._estimate_distance(y2 - y1, h)
            
            class_name = self.class_names[class_id] if class_id < len(self.class_names) else f"class_{class_id}"
            is_pedestrian = class_name in self.pedestrian_classes
            
            detections.append(DetectionResult(
                class_id=class_id,
                class_name=class_name,
                confidence=float(class_conf),
                bbox=(x1, y1, x2, y2),
                distance=distance,
                is_pedestrian=is_pedestrian
            ))
        
        detections = self._apply_nms(detections)
        return detections
    
    def _apply_nms(self, detections: List[DetectionResult]) -> List[DetectionResult]:
        """Apply Non-Maximum Suppression"""
        if len(detections) == 0:
            return []
        
        boxes = np.array([det.bbox for det in detections])
        scores = np.array([det.confidence for det in detections])
        
        x1 = boxes[:, 0]
        y1 = boxes[:, 1]
        x2 = boxes[:, 2]
        y2 = boxes[:, 3]
        
        areas = (x2 - x1) * (y2 - y1)
        order = scores.argsort()[::-1]
        
        keep = []
        while len(order) > 0:
            i = order[0]
            keep.append(i)
            
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])
            
            w = np.maximum(0, xx2 - xx1)
            h = np.maximum(0, yy2 - yy1)
            
            inter = w * h
            iou = inter / (areas[i] + areas[order[1:]] - inter)
            
            inds = np.where(iou <= self.iou_threshold)[0]
            order = order[inds + 1]
        
        return [detections[i] for i in keep]
    
    def _estimate_distance(self, bbox_height: int, image_height: int) -> float:
        """Estimate distance based on bounding box height"""
        if bbox_height == 0:
            return 100.0
        focal_length = image_height * 0.5
        real_height = 1.7
        distance = (real_height * focal_length) / bbox_height
        return min(distance, 100.0)
    
    def draw_detections(self, image: np.ndarray, detections: List[DetectionResult]) -> np.ndarray:
        """Draw detected objects/pedestrians on image"""
        overlay = image.copy()
        
        for det in detections:
            x1, y1, x2, y2 = det.bbox
            
            if det.is_pedestrian:
                color = (0, 0, 255)
                thickness = 3
            else:
                color = self._get_color(det.class_id)
                thickness = 2
            
            cv2.rectangle(overlay, (x1, y1), (x2, y2), color, thickness)
            
            label = f"{det.class_name}: {det.confidence:.2f}"
            if det.distance:
                label += f" ({det.distance:.1f}m)"
            
            (label_w, label_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
            cv2.rectangle(overlay, (x1, y1 - label_h - 10), (x1 + label_w, y1), color, -1)
            cv2.putText(overlay, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        return overlay
    
    def _get_color(self, class_id: int) -> Tuple[int, int, int]:
        """Get consistent color for class"""
        np.random.seed(class_id)
        return tuple(np.random.randint(0, 255, 3).tolist())

# ==================== TRAFFIC SIGN RECOGNITION ====================

class SignRecognizer(ONNXModel):
    """Traffic sign recognition using ONNX model"""
    
    def __init__(self, model_path: str, sign_classes: List[str] = None, conf_threshold: float = 0.7):
        super().__init__(model_path)
        self.conf_threshold = conf_threshold
        
        self.sign_classes = sign_classes or [
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
    
    def postprocess(self, outputs: List[np.ndarray], original_image: np.ndarray) -> SignResult:
        """Postprocess traffic sign classification output"""
        output = outputs[0][0]
        
        class_id = int(output.argmax())
        confidence = float(output[class_id])
        
        if confidence < self.conf_threshold:
            return SignResult("No sign detected", confidence)
        
        sign_type = self.sign_classes[class_id] if class_id < len(self.sign_classes) else f"Unknown sign {class_id}"
        return SignResult(sign_type, confidence)
    
    def draw_sign(self, image: np.ndarray, sign_result: SignResult) -> np.ndarray:
        """Draw recognized sign on image"""
        overlay = image.copy()
        h, w = image.shape[:2]
        
        if sign_result.confidence >= self.conf_threshold:
            label = f"{sign_result.sign_type}: {sign_result.confidence:.2f}"
            color = (0, 255, 0)
        else:
            label = "No sign detected"
            color = (0, 0, 255)
        
        (label_w, label_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        cv2.rectangle(overlay, (w - label_w - 20, 10), (w - 10, label_h + 30), (0, 0, 0), -1)
        cv2.putText(overlay, label, (w - label_w - 15, label_h + 20), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        
        return overlay

# ==================== INTEGRATED ADAS SYSTEM ====================

class AdasSystem:
    """Integrated ADAS system for road monitoring (Xbox Kinect)"""
    
    def __init__(self, lane_model: str, object_model: str, sign_model: str, use_kinect: bool = True):
        """Initialize ADAS system"""
        logger.info("Initializing ADAS System (Road Monitoring)...")
        
        self.lane_detector = LaneDetector(lane_model)
        self.object_detector = ObjectDetector(object_model)
        self.sign_recognizer = SignRecognizer(sign_model)
        
        self.use_kinect = use_kinect
        if use_kinect:
            self.kinect = KinectCamera()
            if not self.kinect.connected:
                logger.warning("Kinect not available, falling back to standard camera")
                self.use_kinect = False
                self.kinect = None
        else:
            self.kinect = None
        
        self.fps = 0
        self.frame_times = []
        
        logger.info("✓ ADAS System ready!")
    
    def get_frame(self) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """Get frame from Kinect or standard camera"""
        if self.use_kinect and self.kinect:
            return self.kinect.get_frame()
        return None, None
    
    def process_frame(self, frame: np.ndarray, depth_frame: Optional[np.ndarray] = None) -> Tuple[np.ndarray, Dict]:
        """Process single frame through all ADAS modules"""
        start_time = time.time()
        
        # Lane Detection
        lane_input = self.lane_detector.preprocess(frame)
        lane_output = self.lane_detector.inference(lane_input)
        lane_result = self.lane_detector.postprocess(lane_output, frame)
        
        # Object & Pedestrian Detection
        obj_input = self.object_detector.preprocess(frame)
        obj_output = self.object_detector.inference(obj_input)
        detections = self.object_detector.postprocess(obj_output, frame, depth_frame, self.kinect)
        
        # Traffic Sign Recognition
        sign_input = self.sign_recognizer.preprocess(frame)
        sign_output = self.sign_recognizer.inference(sign_input)
        sign_result = self.sign_recognizer.postprocess(sign_output, frame)
        
        # Draw all results
        annotated = frame.copy()
        annotated = self.lane_detector.draw_lanes(annotated, lane_result)
        annotated = self.object_detector.draw_detections(annotated, detections)
        annotated = self.sign_recognizer.draw_sign(annotated, sign_result)
        
        # Calculate FPS
        frame_time = time.time() - start_time
        self.frame_times.append(frame_time)
        if len(self.frame_times) > 30:
            self.frame_times.pop(0)
        self.fps = 1.0 / (sum(self.frame_times) / len(self.frame_times))
        
        # Draw FPS and camera source
        camera_source = "Kinect" if self.use_kinect else "Standard"
        cv2.putText(annotated, f"FPS: {self.fps:.1f} ({camera_source})", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # Count pedestrians
        pedestrian_count = sum(1 for det in detections if det.is_pedestrian)
        if pedestrian_count > 0:
            cv2.putText(annotated, f"Pedestrians: {pedestrian_count}", (10, 70),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        results = {
            'lane': lane_result,
            'objects': detections,
            'pedestrians': [det for det in detections if det.is_pedestrian],
            'sign': sign_result,
            'fps': self.fps
        }
        
        return annotated, results
    
    def release(self):
        """Release camera resources"""
        if self.kinect:
            self.kinect.release()

# ==================== EXAMPLE USAGE ====================

def main():
    """Example usage of ADAS system with Kinect"""
    
    # Available lane detection models:
    # - models/Lane_Detection/enet.onnx
    # - models/Lane_Detection/enet_sad.onnx
    # - models/Lane_Detection/scnn.onnx
    
    LANE_MODEL = "models/Lane_Detection/enet_sad.onnx"  # Choose: enet.onnx, enet_sad.onnx, or scnn.onnx
    OBJECT_MODEL = "models/Object_Detection/yolov8n.onnx"
    SIGN_MODEL = "models/Traffic_Sign_Recognition/traffic_signs.onnx"
    
    adas = AdasSystem(
        lane_model=LANE_MODEL,
        object_model=OBJECT_MODEL,
        sign_model=SIGN_MODEL,
        use_kinect=True
    )
    
    # Fallback to standard camera if Kinect not available
    if not adas.use_kinect:
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    logger.info("Starting ADAS processing...")
    logger.info("Press 'q' to quit")
    
    try:
        while True:
            if adas.use_kinect:
                frame, depth_frame = adas.get_frame()
                if frame is None:
                    break
            else:
                ret, frame = cap.read()
                if not ret:
                    break
                depth_frame = None
            
            annotated, results = adas.process_frame(frame, depth_frame)
            
            cv2.imshow('ADAS System - Road Monitoring', annotated)
            
            # Print results
            print(f"\n=== Frame Results (ADAS) ===")
            print(f"FPS: {results['fps']:.1f}")
            print(f"Lane Departure: {results['lane'].lane_departure:.3f}")
            print(f"Objects Detected: {len(results['objects'])}")
            print(f"Pedestrians: {len(results['pedestrians'])}")
            for det in results['pedestrians']:
                print(f"  - Pedestrian: {det.confidence:.2f} ({det.distance:.1f}m)")
            print(f"Traffic Sign: {results['sign'].sign_type} ({results['sign'].confidence:.2f})")
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        adas.release()
        if not adas.use_kinect:
            cap.release()
        cv2.destroyAllWindows()
        logger.info("ADAS system stopped")

if __name__ == "__main__":
    main()