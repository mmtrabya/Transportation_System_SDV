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
import os
import sys
import subprocess
import signal
import atexit

# Suppress ONNX Runtime warnings about CUDA
import os

# Force system Qt platform plugin
os.environ['QT_QPA_PLATFORM'] = 'xcb'
os.environ['QT_PLUGIN_PATH'] = '/usr/lib/qt5/plugins'
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = '/usr/lib/qt5/plugins/platforms'


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ADAS_Inference')
# ==================== KINECT PROCESS RELEASE HANDLER ====================

def release_kinect():
    """Force release of Kinect device handles from other Python/freenect sessions."""
    try:
        result = subprocess.run(
            "sudo fuser -v /dev/bus/usb/*/* 2>/dev/null | grep mmtrabya | awk '{print $2}'",
            shell=True, capture_output=True, text=True
        )
        pids = result.stdout.strip().split()
        for pid in pids:
            if pid.isdigit() and int(pid) != os.getpid():
                os.kill(int(pid), signal.SIGKILL)
                print(f"[INFO] Released Kinect process {pid}")
    except Exception as e:
        print(f"[WARN] Could not release Kinect: {e}")

# Register cleanup on exit
atexit.register(release_kinect)

# Run cleanup immediately before connecting Kinect (in case it’s busy)
release_kinect()

# ===============================================================

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
    segmentation_mask: Optional[np.ndarray] = None  # For visualization

@dataclass
class SignResult:
    """Traffic sign recognition result"""
    sign_type: str
    confidence: float
    bbox: Optional[Tuple[int, int, int, int]] = None

# Traffic Sign Classes (GTSRB)
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

# ==================== KINECT CAMERA INTERFACE ====================

class KinectCamera:
    """Robust Kinect v1 (libfreenect) wrapper using the sync API.
    - Retries on failure.
    - Does NOT open device handles for motor/audio to avoid libusb conflicts.
    - motor_available is False to prevent motor/LED operations from being called.
    """

    def __init__(self, initial_tilt: int = 0, max_attempts: int = 5, attempt_delay: float = 1.0):
        self.connected = False
        self.motor_available = False  # we don't touch motor to avoid double device claim
        self.initial_tilt = initial_tilt
        self._max_attempts = max_attempts
        self._attempt_delay = attempt_delay

        logger.info("=" * 60)
        logger.info("ATTEMPTING TO CONNECT TO KINECT CAMERA")
        logger.info("=" * 60)

        # Optional: ensure libfreenect audio is disabled (can also be set externally)
        os.environ.setdefault("FREENECT_DISABLE_AUDIO", "1")

        attempt = 0
        while attempt < self._max_attempts and not self.connected:
            attempt += 1
            try:
                logger.info(f"Attempt {attempt}/{self._max_attempts}: calling freenect.sync_get_video()...")
                sys.stdout.flush()

                # sync_get_video may return None (no device) — handle that gracefully
                frame_result = freenect.sync_get_video()
                if not frame_result:
                    logger.warning(f"Attempt {attempt}: no frame received (None). Retrying after {self._attempt_delay}s.")
                    time.sleep(self._attempt_delay)
                    continue

                # frame_result may be (frame, ts) or similar; handle safely
                if isinstance(frame_result, tuple) and len(frame_result) >= 1 and frame_result[0] is not None:
                    test_frame = frame_result[0]
                    timestamp = frame_result[1] if len(frame_result) > 1 else None
                    logger.info(f"Received frame - shape={getattr(test_frame, 'shape', None)}, timestamp={timestamp}")
                    self.connected = True
                    logger.info("=" * 60)
                    logger.info("✓ KINECT CAMERA CONNECTED SUCCESSFULLY!")
                    logger.info("=" * 60)
                    # small stabilization pause
                    time.sleep(0.5)
                    break
                else:
                    logger.warning(f"Attempt {attempt}: invalid frame_result structure. Retrying...")
                    time.sleep(self._attempt_delay)

            except Exception as e:
                # Catch common libusb/busy errors and log them without crashing
                errstr = str(e)
                if "LIBUSB_ERROR_BUSY" in errstr or "Busy" in errstr:
                    logger.error("Kinect interface appears busy (LIBUSB_ERROR_BUSY). Make sure no other process is using the Kinect.")
                else:
                    logger.error(f"Kinect initialization attempt {attempt} failed: {e}")
                logger.debug("Traceback:\n" + ''.join(__import__('traceback').format_exc()))
                time.sleep(self._attempt_delay)

        if not self.connected:
            logger.error("Kinect initialization failed after retries.")
            logger.info("Falling back to standard camera...")

    def get_frame(self) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """Return (rgb_frame, depth_frame). If not connected, returns (None, None)."""
        if not self.connected:
            return None, None

        try:
            rgb_result = freenect.sync_get_video()
            depth_result = freenect.sync_get_depth()

            if not rgb_result or rgb_result[0] is None:
                logger.warning("sync_get_video() returned None during runtime.")
                return None, None

            rgb_frame = rgb_result[0]
            # convert if necessary
            try:
                rgb_frame = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2BGR)
            except Exception:
                pass

            depth_frame = None
            if depth_result and depth_result[0] is not None:
                depth_frame = depth_result[0]

            return rgb_frame, depth_frame

        except Exception as e:
            logger.error(f"Error reading from Kinect: {e}")
            logger.debug("Traceback:\n" + ''.join(__import__('traceback').format_exc()))
            return None, None

    def get_bbox_distance(self, depth_frame: np.ndarray, bbox: Tuple[int, int, int, int]) -> float:
        """Same as before; safe on None depth."""
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

        return float(np.median(valid_depths) / 1000.0)

    def release(self):
        """Stop any freenect sync loops gracefully."""
        try:
            freenect.sync_stop()
        except Exception:
            pass


# ==================== BASE ONNX MODEL CLASS ====================

class ONNXModel:
    """Base class for ONNX model inference"""
    
    def __init__(self, model_path: str, providers: List[str] = None):
        if providers is None:
            # CPU-only optimization
            providers = ['CPUExecutionProvider']
        
        try:
            # Set session options for better CPU performance
            sess_options = ort.SessionOptions()
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            sess_options.intra_op_num_threads = 4  # Use 4 CPU threads
            sess_options.inter_op_num_threads = 2
            sess_options.execution_mode = ort.ExecutionMode.ORT_PARALLEL
            
            self.session = ort.InferenceSession(model_path, sess_options=sess_options, providers=providers)
            self.input_name = self.session.get_inputs()[0].name
            self.output_names = [output.name for output in self.session.get_outputs()]
            
            # Log which provider is being used
            logger.info(f"Execution provider: {self.session.get_providers()[0]}")
            
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
        # img = img.astype(np.float32) / 255.0
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
        # Color map for lane classes (similar to 'jet' colormap)
        self.lane_colors = [
            (0, 0, 0),       # 0: Background
            (255, 0, 0),     # 1: Lane 1 (Blue in BGR)
            (0, 255, 0),     # 2: Lane 2 (Green)
            (0, 255, 255),   # 3: Lane 3 (Yellow)
            (0, 0, 255),     # 4: Lane 4 (Red)
            (255, 0, 255),   # 5: Lane 5 (Magenta)
            (255, 255, 0),   # 6: Lane 6 (Cyan)
            (255, 255, 255)  # 7: Lane 7 (White)
        ]
    
    def postprocess(self, outputs: List[np.ndarray], original_image: np.ndarray) -> LaneResult:
        """Postprocess lane detection output"""
        
        def softmax(x, axis=1):
            """Compute softmax values for numpy array along specified axis"""
            # Subtract max for numerical stability
            x_max = np.max(x, axis=axis, keepdims=True)
            exp_x = np.exp(x - x_max)
            return exp_x / np.sum(exp_x, axis=axis, keepdims=True)

        output = outputs[0]
    
        seg_pred = softmax(output, axis=1)
        seg_mask = np.argmax(seg_pred[0], axis=0)
        
        # Resize lane_result to match original image size
        h, w = original_image.shape[:2]
        seg_mask_resized = cv2.resize(seg_mask, (w, h), interpolation=cv2.INTER_NEAREST)
        
        seg_mask_refined = self._refine_lane_mask(seg_mask_resized)

        lane_departure = self._calculate_lane_departure(seg_mask_refined, original_image.shape)
        
        confidence = self._calculate_prediction_confidence(seg_mask)

        return LaneResult(seg_mask_refined, lane_departure, confidence, seg_mask)
    
    def _calculate_prediction_confidence(self, lane_result: np.ndarray) -> float:
        """
        Calculate overall confidence for lane segmentation prediction
        
        Args:
            lane_result: Segmentation mask with class predictions (H, W)
        
        Returns:
            Confidence score between 0 and 1
        """
        h, w = lane_result.shape
        total_pixels = h * w
        
        # 1. Coverage confidence (30% weight)
        lane_pixels = np.sum(lane_result > 0)
        coverage_ratio = lane_pixels / total_pixels
        
        # Typical lane coverage is 5-20% of image
        if coverage_ratio < 0.02:
            coverage_confidence = coverage_ratio / 0.02
        elif coverage_ratio > 0.30:
            coverage_confidence = max(0, 1.0 - (coverage_ratio - 0.30) / 0.30)
        else:
            coverage_confidence = 1.0
        
        # 2. Spatial consistency confidence (40% weight)
        lane_classes = np.unique(lane_result[lane_result > 0])
        consistency_scores = []
        
        for class_id in lane_classes:
            class_mask = (lane_result == class_id).astype(np.uint8)
            num_components, labels, stats, _ = cv2.connectedComponentsWithStats(class_mask, connectivity=8)
            
            if num_components <= 1:
                continue
            
            areas = [stats[i, cv2.CC_STAT_AREA] for i in range(1, num_components)]
            if len(areas) == 0:
                continue
            
            max_area = max(areas)
            total_area = sum(areas)
            dominance = max_area / total_area if total_area > 0 else 0
            component_penalty = 1.0 / (1.0 + (num_components - 1) * 0.2)
            
            consistency_scores.append(dominance * component_penalty)
        
        spatial_consistency = np.mean(consistency_scores) if len(consistency_scores) > 0 else 0.0
        
        # 3. Geometry confidence (30% weight)
        bottom_half = lane_result[h//2:, :]
        top_half = lane_result[:h//2, :]
        
        bottom_pixels = np.sum(bottom_half > 0)
        top_pixels = np.sum(top_half > 0)
        
        if bottom_pixels > 0:
            ratio = bottom_pixels / (bottom_pixels + top_pixels + 1e-6)
            if 0.5 <= ratio <= 0.9:
                geometry_confidence = 1.0
            else:
                geometry_confidence = max(0, 1.0 - abs(ratio - 0.7) / 0.3)
        else:
            geometry_confidence = 0.0
        
        # Combined confidence
        overall_confidence = (
            0.3 * coverage_confidence +
            0.4 * spatial_consistency +
            0.3 * geometry_confidence
        )
        
        return float(np.clip(overall_confidence, 0, 1))

    def _calculate_lane_departure(self, lane_result: np.ndarray, image_shape: tuple) -> tuple:
        """Calculate lane departure from segmentation mask"""
        h, w = image_shape[:2]
        
        left_lane = None
        right_lane = None
        lane_center = None
        lane_departure = 0.0
        
        # Extract lane boundaries from segmentation mask
        # Scan from bottom to top to find left and right lane edges
        bottom_half_start = h // 2  # Focus on bottom half of image
        
        left_points = []
        right_points = []
        image_center_x = w / 2
        
        # Scan each row from bottom to top
        for y in range(h - 1, bottom_half_start, -5):  # Step by 5 for efficiency
            row = lane_result[y, :]
            lane_pixels = np.where(row > 0)[0]  # Find all lane pixels in this row
            
            if len(lane_pixels) == 0:
                continue
            
            # Split pixels into left (< center) and right (> center)
            left_pixels = lane_pixels[lane_pixels < image_center_x]
            right_pixels = lane_pixels[lane_pixels > image_center_x]
            
            # Get rightmost left lane pixel and leftmost right lane pixel
            if len(left_pixels) > 0:
                left_points.append([left_pixels[-1], y])  # Rightmost left pixel
            
            if len(right_pixels) > 0:
                right_points.append([right_pixels[0], y])  # Leftmost right pixel
        
        # Convert to numpy arrays
        if len(left_points) > 10:
            left_lane = np.array(left_points)
        
        if len(right_points) > 10:
            right_lane = np.array(right_points)
        
        # Calculate lane center and departure
        if left_lane is not None and right_lane is not None:
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
            
            # Calculate center with matching shapes
            lane_center = (left_lane + right_lane) / 2
            
            # Calculate departure at bottom of image
            lane_bottom_center = lane_center[-1][0] if len(lane_center) > 0 else image_center_x
            lane_departure = (lane_bottom_center - image_center_x) / image_center_x
        
        return lane_departure
    
    def _refine_lane_mask(self, lane_result: np.ndarray) -> np.ndarray:
        """Refine lane segmentation mask: sharpen, connect close regions, remove noise"""

        if lane_result is None:
            return None
        
        refined_mask = np.zeros_like(lane_result)
        h, w = lane_result.shape
        
        # Process each lane class separately (1-7)
        for class_id in range(1, 8):
            # Extract binary mask for this class
            class_mask = (lane_result == class_id).astype(np.uint8)
            
            if np.sum(class_mask) == 0:
                continue
            
            # Step 1: Connect nearby components using morphological closing
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
            connected_mask = cv2.morphologyEx(class_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
            
            # Step 2: Remove small components AND components far from bottom of image
            num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(connected_mask, connectivity=8)
            
            min_size = 800  # Minimum pixels to keep a component
            min_bottom_y = h * 0.3  # Component must extend to at least bottom 70% of image
            
            for i in range(1, num_labels):
                area = stats[i, cv2.CC_STAT_AREA]
                if area < min_size:
                    continue  # Skip small components
                
                # Get all points in this component
                component_mask = (labels == i).astype(np.uint8)
                points = np.column_stack(np.where(component_mask > 0))  # (y, x) format
                
                if len(points) < 10:
                    continue
                
                # Check if component extends toward bottom of image (lanes should)
                max_y = points[:, 0].max()
                if max_y < min_bottom_y:
                    continue  # Skip components that don't reach lower part of image
                
                # Convert to (x, y) format
                y_coords = points[:, 0]
                x_coords = points[:, 1]
                
                # Sort by y-coordinate (top to bottom)
                sorted_indices = np.argsort(y_coords)
                y_coords = y_coords[sorted_indices]
                x_coords = x_coords[sorted_indices]
                
                # Fit polynomial curve
                try:
                    degree = 2  # Use 2 for gentle curves, 3 for more complex lanes
                    coeffs = np.polyfit(y_coords, x_coords, degree)
                    poly = np.poly1d(coeffs)
                    
                    # Generate smooth curve points
                    y_smooth = np.arange(y_coords.min(), y_coords.max() + 1)
                    x_smooth = poly(y_smooth).astype(np.int32)
                    
                    # Clip x coordinates to image bounds
                    x_smooth = np.clip(x_smooth, 0, refined_mask.shape[1] - 1)
                    
                    # Draw the smooth curve with thickness
                    points_smooth = np.column_stack((x_smooth, y_smooth))
                    cv2.polylines(refined_mask, [points_smooth], False, class_id, thickness=8)
                    
                except:
                    # If polynomial fitting fails, just keep original component
                    refined_mask[component_mask == 1] = class_id
        
        return refined_mask
    
    def draw_lanes(self, image: np.ndarray, lane_result: LaneResult) -> np.ndarray:
        """Draw detected lanes on image with segmentation overlay"""
        overlay = image.copy()
        h, w = image.shape[:2]
        
        lane_mask = lane_result.lane_mask

        # Normalize mask values from 1-7 to 0-255 for colormap application
        mask_normalized = np.zeros_like(lane_mask, dtype=np.uint8)
        mask_normalized[lane_mask > 0] = ((lane_mask[lane_mask > 0] - 1) * 255 // 6).astype(np.uint8)
        
        # Apply jet colormap
        colored_mask = cv2.applyColorMap(mask_normalized, cv2.COLORMAP_JET)
        
        # Create binary mask for valid lane pixels (where lane_mask >= 1)
        valid_mask = (lane_mask >= 1).astype(np.uint8)
        valid_mask_3ch = np.stack([valid_mask] * 3, axis=-1)
        
        # Apply the colored mask only where valid lanes exist
        colored_mask = colored_mask * valid_mask_3ch
        
        # Blend with original image (alpha=0.7)
        overlay = cv2.addWeighted(overlay, 1.0, colored_mask, 0.7, 0)
        
        # Draw lane departure indicator
        center_x = int(w / 2)
        departure_pixels = int(lane_result.lane_departure * w / 2)
        
        color = (0, 255, 0) if abs(lane_result.lane_departure) < 0.1 else (0, 165, 255) if abs(lane_result.lane_departure) < 0.3 else (0, 0, 255)
        # cv2.circle(overlay, (center_x + departure_pixels, h - 50), 10, color, -1)
        cv2.putText(overlay, f"Departure: {lane_result.lane_departure:.2f}", (10, h - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        return overlay

# ==================== OBJECT & PEDESTRIAN DETECTION ====================

class ObjectDetector(ONNXModel):
    """Object and pedestrian detection using YOLOv8"""
    
    def __init__(self, model_path: str, class_names: Dict[int, str] = None, conf_threshold: float = 0.5):
        super().__init__(model_path)
        self.conf_threshold = conf_threshold
        self.iou_threshold = 0.45
        
        # COCO class IDs for ADAS (YOLOv8 standard COCO classes)
        self.class_names = class_names or {
            0: 'person',      # COCO ID 0
            1: 'bicycle',     # COCO ID 1
            2: 'car',         # COCO ID 2
            3: 'motorcycle',  # COCO ID 3
            5: 'bus',         # COCO ID 5
            7: 'truck',       # COCO ID 7
            9: 'traffic light' # COCO ID 9
        }
        
        self.pedestrian_classes = ['person']
    
    def postprocess(self, outputs: List[np.ndarray], original_image: np.ndarray, 
                   depth_frame: Optional[np.ndarray] = None, kinect: Optional[KinectCamera] = None) -> List[DetectionResult]:
        """Postprocess YOLOv8 output with Kinect depth"""
        output = outputs[0]
        
        # If shape is [1, 84, 8400], transpose it to [1, 8400, 84]
        if output.shape[1] < output.shape[2]:
            output = output.transpose(0, 2, 1)

        # Now, output shape is [1, 8400, 84] (or similar)
        output = output[0] # Get the [8400, 84] array of detections
        
        detections = []
        h, w = original_image.shape[:2]
        scale_x = w / self.input_width
        scale_y = h / self.input_height
        
        # Get the number of attributes (e.g., 84)
        num_attrs = output.shape[1]
        
        for detection in output:
            x_center, y_center, width, height = detection[:4]
            
            # Get all class scores (from index 4 to the end)
            class_scores = detection[4:num_attrs]
            
            # Find the highest score and its class ID
            class_id = int(class_scores.argmax())
            confidence = class_scores[class_id]
            
            # Check if the highest score is above our threshold
            if confidence < self.conf_threshold:
                continue
            
            class_conf = confidence 
            
            # Filter to only ADAS-relevant classes
            if class_id not in self.class_names:
                continue
            
            # Bounding box calculation
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
            
            class_name = self.class_names[class_id]
            is_pedestrian = class_name in self.pedestrian_classes
            
            detections.append(DetectionResult(
                class_id=class_id,
                class_name=class_name,
                confidence=float(class_conf),
                bbox=(x1, y1, x2, y2),
                distance=distance,
                is_pedestrian=is_pedestrian
            ))
        
        detections = self.apply_nms(detections)
        return detections

    def apply_nms(self, detections: List[DetectionResult]) -> List[DetectionResult]:
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

# ==================== INTEGRATED ADAS SYSTEM ====================

class AdasSystem:
    """Integrated ADAS system for road monitoring (Xbox Kinect)"""
    
    def __init__(self, lane_model: str, object_model: str, sign_model: str, use_kinect: bool = True, kinect_tilt: int = 0):
        """Initialize ADAS system
        
        Args:
            lane_model: Path to lane detection ONNX model
            object_model: Path to object detection ONNX model
            sign_model: Path to traffic sign ONNX model
            use_kinect: Whether to use Kinect camera
            kinect_tilt: Initial Kinect motor tilt angle (-30 to +30 degrees)
        """
        logger.info("Initializing ADAS System (Road Monitoring)...")
        
        logger.info("Loading Lane Detection model...")
        self.lane_detector = LaneDetector(lane_model)
        
        logger.info("Loading Object Detection model...")
        self.object_detector = ObjectDetector(object_model)
        
        logger.info("Loading Traffic Sign Detection model...")
        self.sign_detector = ObjectDetector(sign_model, class_names=SIGN_CLASSES, conf_threshold=0.4)
        logger.info("✓ Traffic sign detector initialized as YOLOv8 detection model")
        
        self.use_kinect = use_kinect
        if use_kinect:
            logger.info("Initializing Kinect camera...")
            self.kinect = KinectCamera(initial_tilt=kinect_tilt)
            if not self.kinect.connected:
                logger.warning("Kinect not available, falling back to standard camera")
                self.use_kinect = False
                self.kinect = None
        else:
            self.kinect = None
        
        self.fps = 0
        self.frame_times = []
        
        # Performance optimization for Raspberry Pi 5: Process modules at different intervals
        self.frame_counter = 0
        self.lane_process_interval = 2      # Process lanes every 2 frames
        self.sign_process_interval = 5      # Process signs every 5 frames (less critical)
        self.last_lane_result = LaneResult(None, None, None, 0.0, 0.0, None)
        self.last_sign_detections = []
        
        logger.info("=" * 60)
        logger.info("✓ ADAS SYSTEM READY!")
        logger.info("=" * 60)
    
    def get_frame(self) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """Get frame from Kinect or standard camera"""
        if self.use_kinect and self.kinect:
            return self.kinect.get_frame()
        return None, None
    
    def process_frame(self, frame: np.ndarray, depth_frame: Optional[np.ndarray] = None) -> Tuple[np.ndarray, Dict]:
        """Process single frame through all ADAS modules"""
        start_time = time.time()
        
        self.frame_counter += 1
        
        # Lane Detection (Process every 2 frames for Pi 5 optimization)
        if self.frame_counter % self.lane_process_interval == 0:
            lane_input = self.lane_detector.preprocess(frame)
            lane_output = self.lane_detector.inference(lane_input)
            self.last_lane_result = self.lane_detector.postprocess(lane_output, frame)
        
        lane_result = self.last_lane_result
        
        # Object & Pedestrian Detection (Always process - most critical for safety)
        obj_input = self.object_detector.preprocess(frame)
        obj_output = self.object_detector.inference(obj_input/255.0)
        detections = self.object_detector.postprocess(obj_output, frame, depth_frame, self.kinect)
        
        # Traffic Sign Detection (Process every 5 frames for Pi 5 optimization)
        if self.frame_counter % self.sign_process_interval == 0:
            sign_input = self.sign_detector.preprocess(frame)
            sign_output = self.sign_detector.inference(sign_input/255.0)
            self.last_sign_detections = self.sign_detector.postprocess(sign_output, frame, depth_frame, self.kinect)
        
        sign_detections = self.last_sign_detections
        
        # Draw all results
        annotated = frame.copy()
        annotated = self.lane_detector.draw_lanes(annotated, lane_result)
        annotated = self.object_detector.draw_detections(annotated, detections)
        
        # Draw traffic sign detections with magenta color
        for det in sign_detections:
            x1, y1, x2, y2 = det.bbox
            color = (255, 0, 255)  # Magenta for signs
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 3)
            
            label = f"{det.class_name}: {det.confidence:.2f}"
            (label_w, label_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(annotated, (x1, y1 - label_h - 10), (x1 + label_w, y1), color, -1)
            cv2.putText(annotated, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
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
        
        # Display sign count
        if len(sign_detections) > 0:
            cv2.putText(annotated, f"Traffic Signs: {len(sign_detections)}", (10, 110),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 255), 2)
        
        results = {
            'lane': lane_result,
            'objects': detections,
            'pedestrians': [det for det in detections if det.is_pedestrian],
            'signs': sign_detections,
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
    
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--headless', action='store_true', help='Run without display (save to file)')
    parser.add_argument('--output', default='output.jpg', help='Output filename for headless mode')
    parser.add_argument('--tilt', type=int, default=0, help='Initial Kinect motor tilt angle (-30 to +30 degrees)')
    args = parser.parse_args()
    
    # === RASPBERRY PI 5 OPTIMIZATIONS ===
    # Enable performance mode (requires sudo or setting at boot)
    try:
        # Set CPU governor to performance (temporary - resets on reboot)
        os.system("echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor")
    except:
        logger.warning("Could not set CPU governor to performance mode")
    
    LANE_MODEL = "../models/Lane_Detection/enet_sad.onnx"
    OBJECT_MODEL = "../models/Object_Detection/yolov8n.onnx"
    SIGN_MODEL = "../models/Traffic_Sign/last.onnx"

    logger.info("=" * 60)
    logger.info("STARTING ADAS SYSTEM INITIALIZATION")
    logger.info("=" * 60)
    
    adas = AdasSystem(
        lane_model=LANE_MODEL,
        object_model=OBJECT_MODEL,
        sign_model=SIGN_MODEL,
        use_kinect=True,
        kinect_tilt=args.tilt
    )
    
    # Fallback to standard camera if Kinect not available
    if not adas.use_kinect:
        logger.info("Opening standard camera as fallback...")
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            logger.error("Failed to open camera! Trying camera index 1...")
            cap = cv2.VideoCapture(1)
        
        if not cap.isOpened():
            logger.error("No camera found! Please check camera connection.")
            return
        
        logger.info("Camera opened successfully")
        
        # Optimized resolution for Pi 5 (balance between quality and speed)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        # Log actual camera settings
        actual_width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        actual_height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        actual_fps = cap.get(cv2.CAP_PROP_FPS)
        logger.info(f"Camera resolution: {actual_width}x{actual_height} @ {actual_fps}fps")
    
    logger.info("=" * 60)
    logger.info("STARTING ADAS PROCESSING LOOP")
    logger.info("=" * 60)
    logger.info("Keyboard Controls:")
    logger.info("  'q' - Quit")
    if adas.use_kinect and adas.kinect.motor_available:
        logger.info("  'w' - Tilt camera UP (+5°)")
        logger.info("  's' - Tilt camera DOWN (-5°)")
        logger.info("  'r' - Reset camera to 0°")
        logger.info("  'a' - Show accelerometer data")
        logger.info("  'l' - Toggle LED (Green/Yellow/Red)")
    logger.info("=" * 60)
    
    frame_count = 0
    led_state = 0  # For LED cycling: 0=green, 1=yellow, 2=red
    led_colors = [freenect.LED_GREEN, freenect.LED_YELLOW, freenect.LED_RED]
    
    try:
        while True:
            if adas.use_kinect:
                frame, depth_frame = adas.get_frame()
                if frame is None:
                    logger.error("Failed to get frame from Kinect")
                    break
            else:
                ret, frame = cap.read()
                if not ret:
                    logger.error("Failed to read from camera")
                    break
                depth_frame = None
            
            frame_count += 1
            if frame_count % 30 == 0:
                logger.info(f"Processing frame {frame_count}...")
            
            annotated, results = adas.process_frame(frame, depth_frame)
            
            # Display or save based on mode
            if args.headless:
                # Headless mode - save every 30 frames
                if frame_count % 30 == 0:
                    output_file = f"{args.output.replace('.jpg', '')}_{frame_count}.jpg"
                    cv2.imwrite(output_file, annotated)
                    logger.info(f"Saved frame to {output_file}")
            else:
                # Normal mode - display window
                cv2.imshow('ADAS System - Road Monitoring', annotated)
            
            # Print results every 30 frames to avoid flooding console
            if frame_count % 30 == 0:
                print(f"\n{'='*50}")
                print(f"Frame {frame_count} - ADAS Results")
                print(f"{'='*50}")
                print(f"FPS: {results['fps']:.1f}")
                print(f"Lane Departure: {results['lane'].lane_departure:.3f}")
                print(f"Objects Detected: {len(results['objects'])}")
                print(f"Pedestrians: {len(results['pedestrians'])}")
                for det in results['pedestrians']:
                    print(f"  - Pedestrian: {det.confidence:.2f} ({det.distance:.1f}m)")
                
                print(f"Traffic Signs: {len(results['signs'])}")
                for det in results['signs']:
                    print(f"  - {det.class_name}: {det.confidence:.2f}")
                print(f"{'='*50}\n")
            
            # Handle key press
            if args.headless:
                # In headless mode, run for 300 frames then exit
                if frame_count >= 300:
                    logger.info("Headless mode: 300 frames processed, exiting...")
                    break
                time.sleep(0.001)  # Small delay
            else:
                # Normal mode: wait for key
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('q'):
                    logger.info("User pressed 'q' - exiting...")
                    break
                
                # Motor and LED controls (only if Kinect motor is available)
                if adas.use_kinect and adas.kinect.motor_available:
                    if key == ord('w'):
                        # Tilt UP
                        new_tilt = adas.kinect.get_tilt() + 5
                        adas.kinect.set_tilt(new_tilt)
                    
                    elif key == ord('s'):
                        # Tilt DOWN
                        new_tilt = adas.kinect.get_tilt() - 5
                        adas.kinect.set_tilt(new_tilt)
                    
                    elif key == ord('r'):
                        # Reset tilt to 0
                        adas.kinect.set_tilt(0)
                        logger.info("Camera tilt reset to 0°")
                    
                    elif key == ord('a'):
                        # Show accelerometer data
                        accel = adas.kinect.get_accelerometer()
                        if accel:
                            logger.info(f"Accelerometer: X={accel[0]:.2f}g, Y={accel[1]:.2f}g, Z={accel[2]:.2f}g")
                        else:
                            logger.warning("Accelerometer data not available")
                    
                    elif key == ord('l'):
                        # Cycle LED colors
                        led_state = (led_state + 1) % 3
                        adas.kinect.set_led(led_colors[led_state])
                        led_names = ['GREEN', 'YELLOW', 'RED']
                        logger.info(f"LED set to {led_names[led_state]}")
                
    except KeyboardInterrupt:
        logger.info("Interrupted by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"Error in main loop: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        logger.info("Cleaning up...")
        adas.release()
        if not adas.use_kinect:
            cap.release()
        cv2.destroyAllWindows()
        logger.info("=" * 60)
        logger.info("ADAS SYSTEM STOPPED")
        logger.info("=" * 60)

if __name__ == "__main__":
    main()