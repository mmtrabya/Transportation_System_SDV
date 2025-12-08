#!/usr/bin/env python3
"""
ADAS ONNX Model Inference System (Fixed)
- Fixed background frame capture
- Fixed data type issue
- Simpler, more reliable approach
"""

import cv2
import numpy as np
import onnxruntime as ort
import time
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import logging
import os
import sys

# Import freenect
try:
    import freenect
    FREENECT_AVAILABLE = True
except ImportError:
    FREENECT_AVAILABLE = False
    print("[ERROR] freenect not available!")
    sys.exit(1)

# Suppress ONNX warnings
os.environ['ORT_LOGGING_LEVEL'] = '3'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ADAS')

# ==================== DATA STRUCTURES ====================

@dataclass
class DetectionResult:
    class_id: int
    class_name: str
    confidence: float
    bbox: Tuple[int, int, int, int]
    distance: Optional[float] = None
    is_pedestrian: bool = False

@dataclass
class LaneResult:
    lane_mask: Optional[np.ndarray]
    lane_departure: float
    confidence: float
    segmentation_mask: Optional[np.ndarray] = None

# Traffic Sign Classes
SIGN_CLASSES = {
    0: 'Speed 20', 1: 'Speed 30', 2: 'Speed 50', 3: 'Speed 60', 4: 'Speed 70',
    5: 'Speed 80', 6: 'End 80', 7: 'Speed 100', 8: 'Speed 120', 9: 'No passing',
    10: 'No pass >3.5t', 11: 'Right-of-way', 12: 'Priority', 13: 'Yield',
    14: 'Stop', 15: 'No vehicles', 16: '>3.5t prohib', 17: 'No entry',
    18: 'Caution', 19: 'Curve left', 20: 'Curve right', 21: 'Double curve',
    22: 'Bumpy', 23: 'Slippery', 24: 'Narrows right', 25: 'Road work',
    26: 'Traffic signals', 27: 'Pedestrians', 28: 'Children', 29: 'Bicycles',
    30: 'Ice/snow', 31: 'Animals', 32: 'End limits', 33: 'Turn right',
    34: 'Turn left', 35: 'Ahead only', 36: 'Straight/right', 37: 'Straight/left',
    38: 'Keep right', 39: 'Keep left', 40: 'Roundabout', 41: 'End no pass',
    42: 'End no pass >3.5t'
}

# ==================== KINECT CAMERA (SIMPLIFIED) ====================

class KinectCamera:
    """Simple synchronous Kinect wrapper - no threading, just works"""

    def __init__(self):
        self.connected = False
        
        if not FREENECT_AVAILABLE:
            logger.error("Freenect not available!")
            return

        logger.info("=" * 60)
        logger.info("CONNECTING TO KINECT")
        logger.info("=" * 60)

        # Set environment
        os.environ.setdefault("FREENECT_DISABLE_AUDIO", "1")
        
        # Kill any stuck processes
        try:
            os.system("pkill -9 -f freenect 2>/dev/null")
            time.sleep(0.2)
        except:
            pass

        # Connect
        logger.info("Initializing Kinect (may take a few seconds)...")
        start_time = time.time()
        
        try:
            test_frame = freenect.sync_get_video()
            
            if test_frame and test_frame[0] is not None:
                elapsed = time.time() - start_time
                logger.info(f"✓ Connected in {elapsed:.1f}s")
                logger.info(f"  Frame: {test_frame[0].shape}")
                self.connected = True
            else:
                logger.error("No frame received")
                return
                
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return

        logger.info("✓ KINECT READY")
        logger.info("=" * 60)

    def get_frame(self) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """Get RGB and depth frames"""
        if not self.connected:
            return None, None

        try:
            # Get RGB
            rgb_result = freenect.sync_get_video()
            if not rgb_result or rgb_result[0] is None:
                return None, None

            rgb_frame = rgb_result[0]
            rgb_frame = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2BGR)

            # Get depth
            depth_frame = None
            try:
                depth_result = freenect.sync_get_depth()
                if depth_result and depth_result[0] is not None:
                    depth_frame = depth_result[0]
            except:
                pass

            return rgb_frame, depth_frame

        except Exception as e:
            logger.error(f"Frame capture error: {e}")
            return None, None

    def get_bbox_distance(self, depth_frame: np.ndarray, bbox: Tuple[int, int, int, int]) -> float:
        """Calculate distance from depth"""
        if depth_frame is None:
            return -1.0

        x1, y1, x2, y2 = bbox
        h, w = depth_frame.shape[:2]
        
        x1 = max(0, min(x1, w - 1))
        x2 = max(0, min(x2, w - 1))
        y1 = max(0, min(y1, h - 1))
        y2 = max(0, min(y2, h - 1))

        roi = depth_frame[y1:y2, x1:x2]
        if roi.size == 0:
            return -1.0

        valid_depths = roi[(roi > 0) & (roi < 10000)]
        if len(valid_depths) == 0:
            return -1.0

        return float(np.median(valid_depths) / 1000.0)

    def release(self):
        """Cleanup"""
        try:
            freenect.sync_stop()
            logger.info("Kinect released")
        except:
            pass
        self.connected = False


# ==================== ONNX MODEL BASE ====================

class ONNXModel:
    """Base ONNX model class"""
    
    def __init__(self, model_path: str):
        try:
            sess_options = ort.SessionOptions()
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            sess_options.intra_op_num_threads = 4
            sess_options.inter_op_num_threads = 2
            
            self.session = ort.InferenceSession(
                model_path, 
                sess_options=sess_options, 
                providers=['CPUExecutionProvider']
            )
            
            self.input_name = self.session.get_inputs()[0].name
            self.output_names = [output.name for output in self.session.get_outputs()]
            
            input_shape = self.session.get_inputs()[0].shape
            
            if len(input_shape) > 2:
                self.input_height = input_shape[2] if isinstance(input_shape[2], int) else 640
                self.input_width = input_shape[3] if len(input_shape) > 3 and isinstance(input_shape[3], int) else 640
            else:
                self.input_height = 640
                self.input_width = 640
            
            logger.info(f"✓ {os.path.basename(model_path)} ({self.input_width}x{self.input_height})")
            
        except Exception as e:
            logger.error(f"Failed to load {model_path}: {e}")
            raise
    
    def preprocess(self, image: np.ndarray) -> np.ndarray:
        """Preprocess image - returns float32"""
        img = cv2.resize(image, (self.input_width, self.input_height))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = np.transpose(img, (2, 0, 1))
        img = np.expand_dims(img, axis=0)
        return img.astype(np.float32)  # CRITICAL: Ensure float32
    
    def inference(self, preprocessed_input: np.ndarray) -> List[np.ndarray]:
        """Run inference"""
        outputs = self.session.run(self.output_names, {self.input_name: preprocessed_input})
        return outputs


# ==================== LANE DETECTOR ====================

class LaneDetector(ONNXModel):
    """Lane detection"""
    
    def postprocess(self, outputs: List[np.ndarray], original_image: np.ndarray) -> LaneResult:
        """Postprocess lane output"""
        output = outputs[0]
        
        # Softmax
        exp_x = np.exp(output - np.max(output, axis=1, keepdims=True))
        seg_pred = exp_x / np.sum(exp_x, axis=1, keepdims=True)
        seg_mask = np.argmax(seg_pred[0], axis=0)
        
        # Resize
        h, w = original_image.shape[:2]
        seg_mask = cv2.resize(seg_mask, (w, h), interpolation=cv2.INTER_NEAREST)
        
        # Calculate departure
        departure = self._calc_departure(seg_mask, (h, w))
        
        return LaneResult(seg_mask, departure, 0.8, None)
    
    def _calc_departure(self, mask: np.ndarray, shape: tuple) -> float:
        """Calculate lane departure"""
        h, w = shape
        center_x = w / 2
        
        # Bottom half
        bottom = mask[h//2:, :]
        lane_px = np.where(bottom > 0)
        
        if len(lane_px[1]) == 0:
            return 0.0
        
        lane_center = np.mean(lane_px[1])
        departure = (lane_center - center_x) / center_x
        
        return float(np.clip(departure, -1.0, 1.0))
    
    def draw(self, image: np.ndarray, result: LaneResult) -> np.ndarray:
        """Draw lanes"""
        overlay = image.copy()
        
        if result.lane_mask is not None:
            # Green overlay for lanes
            colored = np.zeros_like(image)
            colored[result.lane_mask > 0] = [0, 255, 0]
            overlay = cv2.addWeighted(overlay, 0.7, colored, 0.3, 0)
        
        # Departure indicator
        h, w = image.shape[:2]
        color = (0, 255, 0) if abs(result.lane_departure) < 0.1 else (0, 165, 255) if abs(result.lane_departure) < 0.3 else (0, 0, 255)
        cv2.putText(overlay, f"Departure: {result.lane_departure:.2f}", 
                   (10, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        return overlay


# ==================== OBJECT DETECTOR ====================

class ObjectDetector(ONNXModel):
    """YOLOv8 detector"""
    
    def __init__(self, model_path: str, class_names: Dict[int, str] = None, conf_threshold: float = 0.5):
        super().__init__(model_path)
        self.conf_threshold = conf_threshold
        self.iou_threshold = 0.45
        
        self.class_names = class_names or {
            0: 'person', 1: 'bicycle', 2: 'car', 3: 'motorcycle',
            5: 'bus', 7: 'truck', 9: 'traffic light'
        }
        
        self.pedestrian_classes = ['person']
    
    def postprocess(self, outputs: List[np.ndarray], original_image: np.ndarray,
                   depth_frame: Optional[np.ndarray] = None, 
                   kinect: Optional[KinectCamera] = None) -> List[DetectionResult]:
        """YOLOv8 postprocess"""
        output = outputs[0]
        
        # Transpose if needed
        if output.shape[1] < output.shape[2]:
            output = output.transpose(0, 2, 1)
        
        output = output[0]
        
        detections = []
        h, w = original_image.shape[:2]
        scale_x = w / self.input_width
        scale_y = h / self.input_height
        
        for detection in output:
            x_center, y_center, width, height = detection[:4]
            class_scores = detection[4:]
            
            class_id = int(class_scores.argmax())
            confidence = float(class_scores[class_id])
            
            if confidence < self.conf_threshold or class_id not in self.class_names:
                continue
            
            # Bounding box
            x1 = int((x_center - width / 2) * scale_x)
            y1 = int((y_center - height / 2) * scale_y)
            x2 = int((x_center + width / 2) * scale_x)
            y2 = int((y_center + height / 2) * scale_y)
            
            x1 = max(0, min(x1, w))
            y1 = max(0, min(y1, h))
            x2 = max(0, min(x2, w))
            y2 = max(0, min(y2, h))
            
            # Distance
            distance = None
            if depth_frame is not None and kinect is not None:
                distance = kinect.get_bbox_distance(depth_frame, (x1, y1, x2, y2))
            
            class_name = self.class_names[class_id]
            
            detections.append(DetectionResult(
                class_id=class_id,
                class_name=class_name,
                confidence=confidence,
                bbox=(x1, y1, x2, y2),
                distance=distance,
                is_pedestrian=(class_name in self.pedestrian_classes)
            ))
        
        return self.nms(detections)
    
    def nms(self, detections: List[DetectionResult]) -> List[DetectionResult]:
        """Non-maximum suppression"""
        if len(detections) == 0:
            return []
        
        boxes = np.array([d.bbox for d in detections])
        scores = np.array([d.confidence for d in detections])
        
        x1, y1, x2, y2 = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
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
    
    def draw(self, image: np.ndarray, detections: List[DetectionResult]) -> np.ndarray:
        """Draw detections"""
        overlay = image.copy()
        
        for det in detections:
            x1, y1, x2, y2 = det.bbox
            color = (0, 0, 255) if det.is_pedestrian else (0, 255, 0)
            thickness = 3 if det.is_pedestrian else 2
            
            cv2.rectangle(overlay, (x1, y1), (x2, y2), color, thickness)
            
            label = f"{det.class_name}: {det.confidence:.2f}"
            if det.distance and det.distance > 0:
                label += f" ({det.distance:.1f}m)"
            
            cv2.putText(overlay, label, (x1, y1 - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        return overlay


# ==================== ADAS SYSTEM ====================

class AdasSystem:
    """Main ADAS system"""
    
    def __init__(self, lane_model: str, object_model: str, sign_model: str):
        logger.info("Initializing ADAS...")
        
        self.lane_detector = LaneDetector(lane_model)
        self.object_detector = ObjectDetector(object_model)
        self.sign_detector = ObjectDetector(sign_model, SIGN_CLASSES, 0.4)
        
        self.kinect = KinectCamera()
        if not self.kinect.connected:
            logger.error("Kinect failed!")
            sys.exit(1)
        
        self.fps = 0
        self.frame_times = []
        self.frame_count = 0
        
        self._last_lane = LaneResult(None, 0.0, 0.0, None)
        self._last_signs = []
        
        logger.info("✓ ADAS READY!")
    
    def process(self, frame: np.ndarray, depth: Optional[np.ndarray] = None):
        """Process one frame"""
        start = time.time()
        self.frame_count += 1
        
        # Lane (every 2 frames)
        if self.frame_count % 2 == 0:
            lane_in = self.lane_detector.preprocess(frame)
            lane_out = self.lane_detector.inference(lane_in)
            self._last_lane = self.lane_detector.postprocess(lane_out, frame)
        
        # Objects (always)
        obj_in = self.object_detector.preprocess(frame)
        obj_out = self.object_detector.inference(obj_in / 255.0)
        objects = self.object_detector.postprocess(obj_out, frame, depth, self.kinect)
        
        # Signs (every 5 frames)
        if self.frame_count % 5 == 0:
            sign_in = self.sign_detector.preprocess(frame)
            sign_out = self.sign_detector.inference(sign_in / 255.0)
            self._last_signs = self.sign_detector.postprocess(sign_out, frame, depth, self.kinect)
        
        # Draw
        annotated = frame.copy()
        annotated = self.lane_detector.draw(annotated, self._last_lane)
        annotated = self.object_detector.draw(annotated, objects)
        annotated = self.object_detector.draw(annotated, self._last_signs)
        
        # FPS
        elapsed = time.time() - start
        self.frame_times.append(elapsed)
        if len(self.frame_times) > 30:
            self.frame_times.pop(0)
        self.fps = 1.0 / (sum(self.frame_times) / len(self.frame_times))
        
        cv2.putText(annotated, f"FPS: {self.fps:.1f}", 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # Pedestrian count
        pedestrians = [d for d in objects if d.is_pedestrian]
        if len(pedestrians) > 0:
            cv2.putText(annotated, f"Pedestrians: {len(pedestrians)}", 
                       (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        # Sign count
        if len(self._last_signs) > 0:
            cv2.putText(annotated, f"Signs: {len(self._last_signs)}", 
                       (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 255), 2)
        
        results = {
            'lane': self._last_lane,
            'objects': objects,
            'pedestrians': pedestrians,
            'signs': self._last_signs,
            'fps': self.fps
        }
        
        return annotated, results
    
    def release(self):
        """Cleanup"""
        self.kinect.release()


# ==================== MAIN ====================

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--headless', action='store_true')
    args = parser.parse_args()
    
    # Model paths
    LANE = "models/Lane_Detection/scnn.onnx"
    OBJECT = "models/Object_Detection/yolov8n.onnx"
    SIGN = "models/Traffic_Sign/last.onnx"
    
    logger.info("=" * 60)
    logger.info("STARTING ADAS")
    logger.info("=" * 60)
    
    adas = AdasSystem(LANE, OBJECT, SIGN)
    
    logger.info("Press 'q' to quit")
    logger.info("=" * 60)
    
    frame_count = 0
    
    try:
        while True:
            frame, depth = adas.kinect.get_frame()
            
            if frame is None:
                logger.warning("No frame")
                time.sleep(0.01)
                continue
            
            frame_count += 1
            annotated, results = adas.process(frame, depth)
            
            if not args.headless:
                cv2.imshow('ADAS', annotated)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            else:
                if frame_count % 30 == 0:
                    cv2.imwrite(f"output_{frame_count}.jpg", annotated)
                if frame_count >= 300:
                    break
            
            # Stats every 30 frames
            if frame_count % 30 == 0:
                logger.info(f"Frame {frame_count} | FPS: {results['fps']:.1f} | "
                           f"Objects: {len(results['objects'])} | "
                           f"Pedestrians: {len(results['pedestrians'])} | "
                           f"Signs: {len(results['signs'])}")
                
    except KeyboardInterrupt:
        logger.info("Stopped")
    finally:
        adas.release()
        cv2.destroyAllWindows()
        logger.info("Done")


if __name__ == "__main__":
    main()