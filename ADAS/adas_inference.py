#!/usr/bin/env python3
"""
ADAS ONNX Model Inference System
Generic inference engine for Lane Detection, Object Detection, and Traffic Sign Recognition
Works with any ONNX models trained on Kaggle
"""

import cv2
import numpy as np
import onnxruntime as ort
import time
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('ADAS_Inference')

# ==================== DATA STRUCTURES ====================

@dataclass
class DetectionResult:
    """Object detection result"""
    class_id: int
    class_name: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    distance: Optional[float] = None  # meters

@dataclass
class LaneResult:
    """Lane detection result"""
    left_lane: Optional[np.ndarray]  # Lane points
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

# ==================== BASE ONNX MODEL CLASS ====================

class ONNXModel:
    """Base class for ONNX model inference"""
    
    def __init__(self, model_path: str, providers: List[str] = None):
        """
        Initialize ONNX model
        
        Args:
            model_path: Path to .onnx model file
            providers: Execution providers (CPU, CUDA, etc.)
        """
        if providers is None:
            # Use CPU by default, add CUDA if available
            providers = ['CPUExecutionProvider']
        
        try:
            self.session = ort.InferenceSession(model_path, providers=providers)
            self.input_name = self.session.get_inputs()[0].name
            self.output_names = [output.name for output in self.session.get_outputs()]
            
            # Get input shape
            input_shape = self.session.get_inputs()[0].shape
            self.input_height = input_shape[2] if len(input_shape) > 2 else 640
            self.input_width = input_shape[3] if len(input_shape) > 3 else 640
            
            logger.info(f"Model loaded: {model_path}")
            logger.info(f"Input shape: {input_shape}")
            logger.info(f"Providers: {self.session.get_providers()}")
            
        except Exception as e:
            logger.error(f"Failed to load model {model_path}: {e}")
            raise
    
    def preprocess(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess image for model input
        Override this in child classes for specific preprocessing
        """
        # Resize
        img = cv2.resize(image, (self.input_width, self.input_height))
        
        # Convert BGR to RGB
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Normalize to [0, 1]
        img = img.astype(np.float32) / 255.0
        
        # Transpose to NCHW format (Batch, Channels, Height, Width)
        img = np.transpose(img, (2, 0, 1))
        
        # Add batch dimension
        img = np.expand_dims(img, axis=0)
        
        return img
    
    def inference(self, preprocessed_input: np.ndarray) -> List[np.ndarray]:
        """Run inference"""
        outputs = self.session.run(self.output_names, {self.input_name: preprocessed_input})
        return outputs
    
    def postprocess(self, outputs: List[np.ndarray], original_image: np.ndarray):
        """
        Postprocess model outputs
        Override this in child classes
        """
        raise NotImplementedError("Postprocess must be implemented in child class")

# ==================== LANE DETECTION ====================

class LaneDetector(ONNXModel):
    """Lane detection using ONNX model"""
    
    def __init__(self, model_path: str):
        super().__init__(model_path)
        self.lane_history = []
        self.history_size = 5
    
    def postprocess(self, outputs: List[np.ndarray], original_image: np.ndarray) -> LaneResult:
        """
        Postprocess lane detection output
        
        Expected output formats:
        - Segmentation mask: [1, num_classes, H, W]
        - Coordinate points: [1, num_points, 2]
        """
        output = outputs[0]
        
        # Handle segmentation mask output
        if len(output.shape) == 4:  # [1, C, H, W]
            lane_mask = output[0]  # Remove batch dimension
            
            # Get lane pixels (assuming class 1 and 2 are left/right lanes)
            if lane_mask.shape[0] > 2:
                left_mask = lane_mask[1]  # Class 1
                right_mask = lane_mask[2]  # Class 2
            else:
                # Binary segmentation
                combined_mask = lane_mask[0] if lane_mask.shape[0] == 1 else lane_mask.max(axis=0)
                left_mask = combined_mask.copy()
                right_mask = combined_mask.copy()
            
            # Resize masks to original image size
            h, w = original_image.shape[:2]
            left_mask = cv2.resize(left_mask, (w, h))
            right_mask = cv2.resize(right_mask, (w, h))
            
            # Extract lane points
            left_lane = self._extract_lane_points(left_mask, side='left')
            right_lane = self._extract_lane_points(right_mask, side='right')
            
        # Handle coordinate output
        elif len(output.shape) == 3:  # [1, num_points, 2]
            points = output[0]
            h, w = original_image.shape[:2]
            
            # Scale points to original image size
            points[:, 0] *= w
            points[:, 1] *= h
            
            # Split into left and right lanes (assume first half is left)
            mid = len(points) // 2
            left_lane = points[:mid]
            right_lane = points[mid:]
        
        else:
            logger.warning(f"Unexpected lane detection output shape: {output.shape}")
            return LaneResult(None, None, None, 0.0, 0.0)
        
        # Calculate lane center and departure
        lane_center = None
        lane_departure = 0.0
        
        if left_lane is not None and right_lane is not None and len(left_lane) > 0 and len(right_lane) > 0:
            # Calculate center line
            lane_center = (left_lane + right_lane) / 2
            
            # Calculate lane departure (at bottom of image)
            image_center = original_image.shape[1] / 2
            lane_bottom_center = lane_center[-1][0] if len(lane_center) > 0 else image_center
            lane_departure = (lane_bottom_center - image_center) / image_center
        
        # Calculate confidence (based on mask quality)
        confidence = 0.8 if left_lane is not None and right_lane is not None else 0.3
        
        # Smooth lanes using history
        left_lane = self._smooth_lane(left_lane)
        right_lane = self._smooth_lane(right_lane)
        
        return LaneResult(left_lane, right_lane, lane_center, lane_departure, confidence)
    
    def _extract_lane_points(self, mask: np.ndarray, side: str, threshold: float = 0.5) -> np.ndarray:
        """Extract lane points from segmentation mask"""
        # Threshold mask
        mask = (mask > threshold).astype(np.uint8)
        
        if mask.sum() < 10:  # Not enough pixels
            return None
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return None
        
        # Get largest contour
        largest_contour = max(contours, key=cv2.contourArea)
        
        # Fit polynomial to contour points
        points = largest_contour.reshape(-1, 2)
        
        # Sort by y coordinate
        points = points[points[:, 1].argsort()]
        
        return points
    
    def _smooth_lane(self, lane: np.ndarray) -> np.ndarray:
        """Smooth lane using temporal history"""
        if lane is None:
            return None
        
        self.lane_history.append(lane)
        if len(self.lane_history) > self.history_size:
            self.lane_history.pop(0)
        
        # Average over history
        if len(self.lane_history) > 1:
            # Simple moving average
            return np.mean(self.lane_history, axis=0)
        
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
        
        # Draw lane departure indicator
        h, w = image.shape[:2]
        center_x = int(w / 2)
        departure_pixels = int(lane_result.lane_departure * w / 2)
        
        color = (0, 255, 0) if abs(lane_result.lane_departure) < 0.1 else (0, 165, 255) if abs(lane_result.lane_departure) < 0.3 else (0, 0, 255)
        cv2.circle(overlay, (center_x + departure_pixels, h - 50), 10, color, -1)
        cv2.putText(overlay, f"Departure: {lane_result.lane_departure:.2f}", (10, h - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        return overlay

# ==================== OBJECT DETECTION (YOLOv8) ====================

class ObjectDetector(ONNXModel):
    """Object detection using ONNX model (YOLOv8 format)"""
    
    def __init__(self, model_path: str, class_names: List[str] = None, conf_threshold: float = 0.5):
        super().__init__(model_path)
        self.conf_threshold = conf_threshold
        self.iou_threshold = 0.45
        
        # Default COCO classes if not provided
        self.class_names = class_names or [
            'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck',
            'boat', 'traffic light', 'fire hydrant', 'stop sign', 'parking meter', 'bench',
            'bird', 'cat', 'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra',
            'giraffe', 'backpack', 'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee'
        ]
    
    def postprocess(self, outputs: List[np.ndarray], original_image: np.ndarray) -> List[DetectionResult]:
        """
        Postprocess YOLOv8 output
        
        Expected output: [1, num_detections, 85] or [1, 84, num_detections]
        Format: [x, y, w, h, conf, class_scores...]
        """
        output = outputs[0]
        
        # Handle different output formats
        if output.shape[1] == 84 or output.shape[1] > 100:
            # Format: [1, 84, 8400] - transpose needed
            output = output[0].T  # Now [8400, 84]
        else:
            # Format: [1, 8400, 84]
            output = output[0]  # Now [8400, 84]
        
        detections = []
        h, w = original_image.shape[:2]
        
        # Scale factors
        scale_x = w / self.input_width
        scale_y = h / self.input_height
        
        for detection in output:
            # Extract box coordinates
            x_center, y_center, width, height = detection[:4]
            
            # Extract confidence and class scores
            if len(detection) > 5:
                confidence = detection[4]
                class_scores = detection[5:]
            else:
                # Some models combine confidence with class scores
                class_scores = detection[4:]
                confidence = class_scores.max()
            
            if confidence < self.conf_threshold:
                continue
            
            # Get class with highest score
            class_id = int(class_scores.argmax())
            class_conf = class_scores[class_id]
            
            if class_conf < self.conf_threshold:
                continue
            
            # Convert to corner coordinates
            x1 = int((x_center - width / 2) * scale_x)
            y1 = int((y_center - height / 2) * scale_y)
            x2 = int((x_center + width / 2) * scale_x)
            y2 = int((y_center + height / 2) * scale_y)
            
            # Clip to image boundaries
            x1 = max(0, min(x1, w))
            y1 = max(0, min(y1, h))
            x2 = max(0, min(x2, w))
            y2 = max(0, min(y2, h))
            
            # Estimate distance (simple heuristic based on bbox height)
            distance = self._estimate_distance(y2 - y1, h)
            
            class_name = self.class_names[class_id] if class_id < len(self.class_names) else f"class_{class_id}"
            
            detections.append(DetectionResult(
                class_id=class_id,
                class_name=class_name,
                confidence=float(class_conf),
                bbox=(x1, y1, x2, y2),
                distance=distance
            ))
        
        # Apply NMS (Non-Maximum Suppression)
        detections = self._apply_nms(detections)
        
        return detections
    
    def _apply_nms(self, detections: List[DetectionResult]) -> List[DetectionResult]:
        """Apply Non-Maximum Suppression"""
        if len(detections) == 0:
            return []
        
        boxes = np.array([det.bbox for det in detections])
        scores = np.array([det.confidence for det in detections])
        
        # Convert to x1, y1, x2, y2 format
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
        """
        Estimate distance based on bounding box height
        This is a simple heuristic - calibrate for your camera setup
        """
        # Assume: object height = 1.7m (person), focal length estimated
        # distance = (real_height * focal_length) / pixel_height
        
        if bbox_height == 0:
            return 100.0  # Far away
        
        # Simple inverse relationship (needs calibration)
        focal_length = image_height * 0.5  # Rough estimate
        real_height = 1.7  # meters
        
        distance = (real_height * focal_length) / bbox_height
        return min(distance, 100.0)  # Cap at 100m
    
    def draw_detections(self, image: np.ndarray, detections: List[DetectionResult]) -> np.ndarray:
        """Draw detected objects on image"""
        overlay = image.copy()
        
        for det in detections:
            x1, y1, x2, y2 = det.bbox
            
            # Color based on class
            color = self._get_color(det.class_id)
            
            # Draw bbox
            cv2.rectangle(overlay, (x1, y1), (x2, y2), color, 2)
            
            # Draw label
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
        
        # Default sign classes (GTSRB dataset)
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
        """
        Postprocess traffic sign classification output
        
        Expected output: [1, num_classes]
        """
        output = outputs[0][0]  # Remove batch dimension
        
        # Get class with highest confidence
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
        
        # Draw at top-right corner
        (label_w, label_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        cv2.rectangle(overlay, (w - label_w - 20, 10), (w - 10, label_h + 30), (0, 0, 0), -1)
        cv2.putText(overlay, label, (w - label_w - 15, label_h + 20), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        
        return overlay

# ==================== INTEGRATED ADAS SYSTEM ====================

class AdasSystem:
    """Integrated ADAS system running all models"""
    
    def __init__(self, lane_model: str, object_model: str, sign_model: str):
        """
        Initialize ADAS system with model paths
        
        Args:
            lane_model: Path to lane detection ONNX model
            object_model: Path to object detection ONNX model
            sign_model: Path to traffic sign recognition ONNX model
        """
        logger.info("Initializing ADAS System...")
        
        self.lane_detector = LaneDetector(lane_model)
        self.object_detector = ObjectDetector(object_model)
        self.sign_recognizer = SignRecognizer(sign_model)
        
        self.fps = 0
        self.frame_times = []
        
        logger.info("ADAS System ready!")
    
    def process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, Dict]:
        """
        Process single frame through all ADAS modules
        
        Returns:
            Tuple of (annotated_frame, results_dict)
        """
        start_time = time.time()
        
        # Lane Detection
        lane_input = self.lane_detector.preprocess(frame)
        lane_output = self.lane_detector.inference(lane_input)
        lane_result = self.lane_detector.postprocess(lane_output, frame)
        
        # Object Detection
        obj_input = self.object_detector.preprocess(frame)
        obj_output = self.object_detector.inference(obj_input)
        detections = self.object_detector.postprocess(obj_output, frame)
        
        # Traffic Sign Recognition (on full frame or detected signs)
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
        
        # Draw FPS
        cv2.putText(annotated, f"FPS: {self.fps:.1f}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # Compile results
        results = {
            'lane': lane_result,
            'objects': detections,
            'sign': sign_result,
            'fps': self.fps
        }
        
        return annotated, results

# ==================== EXAMPLE USAGE ====================

def main():
    """Example usage of ADAS system"""
    
    # Model paths (update these with your actual model paths)
    LANE_MODEL = "models/lane_detection.onnx"
    OBJECT_MODEL = "models/yolov8n.onnx"
    SIGN_MODEL = "models/traffic_signs.onnx"
    
    # Initialize ADAS
    adas = AdasSystem(LANE_MODEL, OBJECT_MODEL, SIGN_MODEL)
    
    # Open camera or video
    cap = cv2.VideoCapture(0)  # 0 for webcam, or video file path
    
    # Set camera resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    logger.info("Starting ADAS processing...")
    logger.info("Press 'q' to quit")
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Process frame
            annotated, results = adas.process_frame(frame)
            
            # Display
            cv2.imshow('ADAS System', annotated)
            
            # Print results
            print(f"\n=== Frame Results ===")
            print(f"FPS: {results['fps']:.1f}")
            print(f"Lane Departure: {results['lane'].lane_departure:.3f}")
            print(f"Objects Detected: {len(results['objects'])}")
            for det in results['objects'][:5]:  # Show first 5
                print(f"  - {det.class_name}: {det.confidence:.2f} ({det.distance:.1f}m)")
            print(f"Traffic Sign: {results['sign'].sign_type} ({results['sign'].confidence:.2f})")
            
            # Quit on 'q'
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        logger.info("ADAS system stopped")

if __name__ == "__main__":
    main()