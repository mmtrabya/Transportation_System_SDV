#!/usr/bin/env python3
"""
Driver Monitoring System (DMS)
Uses Raspberry Pi Camera v2 for in-cabin driver monitoring
Monitors: Face detection, drowsiness, distraction, emotion, gaze direction
Location: ~/Graduation_Project_SDV/raspberry_pi/driver_monitoring.py
"""

import cv2
import numpy as np
import onnxruntime as ort
import time
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import logging
from picamera2 import Picamera2
from collections import deque

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('Driver_Monitoring')

# ==================== DATA STRUCTURES ====================

class DriverState(Enum):
    """Driver attention states"""
    NORMAL = "Normal"
    DROWSY = "Drowsy"
    DISTRACTED = "Distracted"
    EYES_CLOSED = "Eyes Closed"
    LOOKING_AWAY = "Looking Away"
    USING_PHONE = "Using Phone"
    YAWNING = "Yawning"

class EmotionType(Enum):
    """Emotion classifications"""
    NEUTRAL = "Neutral"
    HAPPY = "Happy"
    SAD = "Sad"
    ANGRY = "Angry"
    SURPRISED = "Surprised"
    FEARFUL = "Fearful"
    DISGUSTED = "Disgusted"

@dataclass
class FaceDetection:
    """Face detection result"""
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    confidence: float
    landmarks: Optional[np.ndarray] = None  # 5 points: left_eye, right_eye, nose, left_mouth, right_mouth

@dataclass
class EyeState:
    """Eye state detection"""
    left_eye_open: bool
    right_eye_open: bool
    left_eye_ratio: float  # Eye Aspect Ratio
    right_eye_ratio: float
    both_eyes_closed_duration: float  # seconds

@dataclass
class GazeDirection:
    """Gaze/head pose detection"""
    pitch: float  # Up/down (-90 to 90)
    yaw: float    # Left/right (-90 to 90)
    roll: float   # Tilt (-90 to 90)
    looking_forward: bool
    gaze_score: float  # 0-1, 1=looking at road

@dataclass
class DriverMonitoringResult:
    """Complete driver monitoring result"""
    face_detected: bool
    face: Optional[FaceDetection]
    eye_state: Optional[EyeState]
    gaze: Optional[GazeDirection]
    emotion: EmotionType
    emotion_confidence: float
    driver_state: DriverState
    alert_level: int  # 0=ok, 1=warning, 2=critical
    timestamp: float

# ==================== PI CAMERA INTERFACE ====================

class PiCameraInterface:
    """Raspberry Pi Camera v2 interface"""
    
    def __init__(self, resolution: Tuple[int, int] = (640, 480), framerate: int = 30):
        """
        Initialize Pi Camera
        
        Args:
            resolution: Camera resolution (width, height)
            framerate: Frames per second
        """
        self.resolution = resolution
        self.framerate = framerate
        self.camera = None
        self.connected = False
        
        try:
            self.camera = Picamera2()
            
            # Configure camera
            config = self.camera.create_preview_configuration(
                main={"size": resolution, "format": "RGB888"}
            )
            self.camera.configure(config)
            
            # Start camera
            self.camera.start()
            time.sleep(2)  # Warm-up time
            
            self.connected = True
            logger.info(f"✓ Pi Camera v2 connected ({resolution[0]}x{resolution[1]} @ {framerate}fps)")
            
        except Exception as e:
            logger.error(f"Failed to initialize Pi Camera: {e}")
            logger.info("Falling back to USB camera...")
    
    def get_frame(self) -> Optional[np.ndarray]:
        """Get frame from Pi Camera"""
        if not self.connected or not self.camera:
            return None
        
        try:
            # Capture frame
            frame = self.camera.capture_array()
            
            # Convert RGB to BGR for OpenCV
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
            return frame
            
        except Exception as e:
            logger.error(f"Error reading from Pi Camera: {e}")
            return None
    
    def release(self):
        """Release camera resources"""
        if self.camera:
            self.camera.stop()
            logger.info("Pi Camera released")

# ==================== BASE ONNX MODEL ====================

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
            self.input_height = input_shape[2] if len(input_shape) > 2 else 224
            self.input_width = input_shape[3] if len(input_shape) > 3 else 224
            
            logger.info(f"Model loaded: {model_path}")
            
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

# ==================== FACE DETECTION ====================

class FaceDetector:
    """Face detection using ONNX model or OpenCV"""
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize face detector
        
        Args:
            model_path: Path to face detection ONNX model (optional, uses Haar Cascade if None)
        """
        self.use_onnx = False
        
        if model_path:
            try:
                self.model = ONNXModel(model_path)
                self.use_onnx = True
                logger.info("Using ONNX face detection model")
            except:
                logger.warning("Failed to load ONNX model, using Haar Cascade")
        
        if not self.use_onnx:
            # Fallback to OpenCV Haar Cascade
            self.face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            logger.info("Using Haar Cascade face detection")
    
    def detect(self, frame: np.ndarray) -> List[FaceDetection]:
        """Detect faces in frame"""
        if self.use_onnx:
            return self._detect_onnx(frame)
        else:
            return self._detect_haar(frame)
    
    def _detect_haar(self, frame: np.ndarray) -> List[FaceDetection]:
        """Detect faces using Haar Cascade"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
        )
        
        detections = []
        for (x, y, w, h) in faces:
            detections.append(FaceDetection(
                bbox=(x, y, x+w, y+h),
                confidence=1.0
            ))
        
        return detections
    
    def _detect_onnx(self, frame: np.ndarray) -> List[FaceDetection]:
        """Detect faces using ONNX model"""
        # Implement ONNX-based face detection if model is available
        preprocessed = self.model.preprocess(frame)
        outputs = self.model.inference(preprocessed)
        
        # Parse outputs (format depends on your model)
        # This is a placeholder - adapt to your model's output format
        detections = []
        return detections

# ==================== EYE STATE DETECTION ====================

class EyeStateDetector:
    """Eye state and drowsiness detection"""
    
    def __init__(self):
        """Initialize eye state detector"""
        self.eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_eye.xml'
        )
        self.eye_closed_threshold = 0.2  # EAR threshold
        self.eye_closed_frames = 0
        self.eye_closed_duration = 0.0
        self.last_time = time.time()
    
    def detect(self, face_roi: np.ndarray) -> EyeState:
        """
        Detect eye state
        
        Args:
            face_roi: Face region of interest
        
        Returns:
            EyeState with eye opening status
        """
        gray_roi = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
        eyes = self.eye_cascade.detectMultiScale(gray_roi, scaleFactor=1.1, minNeighbors=5)
        
        current_time = time.time()
        dt = current_time - self.last_time
        self.last_time = current_time
        
        # Simple heuristic: if we detect eyes, they're open
        left_eye_open = False
        right_eye_open = False
        
        if len(eyes) >= 2:
            left_eye_open = True
            right_eye_open = True
            self.eye_closed_frames = 0
            self.eye_closed_duration = 0.0
        elif len(eyes) == 1:
            left_eye_open = True
            right_eye_open = False
            self.eye_closed_frames += 1
            self.eye_closed_duration += dt * 0.5
        else:
            # No eyes detected - likely closed
            left_eye_open = False
            right_eye_open = False
            self.eye_closed_frames += 1
            self.eye_closed_duration += dt
        
        # Calculate Eye Aspect Ratio (simplified)
        left_ear = 0.3 if left_eye_open else 0.15
        right_ear = 0.3 if right_eye_open else 0.15
        
        return EyeState(
            left_eye_open=left_eye_open,
            right_eye_open=right_eye_open,
            left_eye_ratio=left_ear,
            right_eye_ratio=right_ear,
            both_eyes_closed_duration=self.eye_closed_duration if not (left_eye_open or right_eye_open) else 0.0
        )

# ==================== GAZE/HEAD POSE DETECTION ====================

class GazeDetector:
    """Head pose and gaze direction estimation"""
    
    def __init__(self):
        """Initialize gaze detector"""
        # Simplified gaze detection using face position
        self.frame_center_x = 320
        self.frame_center_y = 240
        self.gaze_history = deque(maxlen=10)
    
    def detect(self, face_bbox: Tuple[int, int, int, int], frame_shape: Tuple[int, int]) -> GazeDirection:
        """
        Estimate gaze direction from face position
        
        Args:
            face_bbox: Face bounding box (x1, y1, x2, y2)
            frame_shape: Frame dimensions (height, width)
        
        Returns:
            GazeDirection with estimated head pose
        """
        x1, y1, x2, y2 = face_bbox
        h, w = frame_shape[:2]
        
        # Calculate face center
        face_center_x = (x1 + x2) / 2
        face_center_y = (y1 + y2) / 2
        
        # Calculate center of frame
        frame_center_x = w / 2
        frame_center_y = h / 2
        
        # Estimate yaw (left/right) based on horizontal displacement
        yaw_offset = (face_center_x - frame_center_x) / frame_center_x
        yaw = yaw_offset * 45  # Scale to degrees
        
        # Estimate pitch (up/down) based on vertical displacement
        pitch_offset = (face_center_y - frame_center_y) / frame_center_y
        pitch = pitch_offset * 30
        
        # Roll estimation (simplified - would need landmarks for accuracy)
        roll = 0.0
        
        # Calculate gaze score (1.0 = looking forward, 0.0 = looking away)
        distance = np.sqrt((face_center_x - frame_center_x)**2 + (face_center_y - frame_center_y)**2)
        max_distance = np.sqrt(frame_center_x**2 + frame_center_y**2)
        gaze_score = 1.0 - min(distance / max_distance, 1.0)
        
        # Smooth gaze score
        self.gaze_history.append(gaze_score)
        smoothed_gaze_score = np.mean(self.gaze_history)
        
        # Determine if looking forward
        looking_forward = abs(yaw) < 20 and abs(pitch) < 15 and smoothed_gaze_score > 0.7
        
        return GazeDirection(
            pitch=pitch,
            yaw=yaw,
            roll=roll,
            looking_forward=looking_forward,
            gaze_score=smoothed_gaze_score
        )

# ==================== EMOTION RECOGNITION ====================

class EmotionRecognizer(ONNXModel):
    """Emotion recognition using ONNX model"""
    
    def __init__(self, model_path: str):
        """Initialize emotion recognition model"""
        super().__init__(model_path)
        self.emotions = [
            EmotionType.ANGRY,
            EmotionType.DISGUSTED,
            EmotionType.FEARFUL,
            EmotionType.HAPPY,
            EmotionType.NEUTRAL,
            EmotionType.SAD,
            EmotionType.SURPRISED
        ]
    
    def recognize(self, face_roi: np.ndarray) -> Tuple[EmotionType, float]:
        """
        Recognize emotion from face ROI
        
        Args:
            face_roi: Face region of interest
        
        Returns:
            Tuple of (emotion, confidence)
        """
        preprocessed = self.preprocess(face_roi)
        outputs = self.inference(preprocessed)
        
        # Get emotion probabilities
        probs = outputs[0][0]
        emotion_id = int(np.argmax(probs))
        confidence = float(probs[emotion_id])
        
        emotion = self.emotions[emotion_id] if emotion_id < len(self.emotions) else EmotionType.NEUTRAL
        
        return emotion, confidence

# ==================== DRIVER STATE ANALYZER ====================

class DriverStateAnalyzer:
    """Analyze driver state based on all inputs"""
    
    def __init__(self):
        """Initialize driver state analyzer"""
        self.drowsiness_threshold = 2.0  # seconds
        self.distraction_threshold = 3.0  # seconds
        self.alert_history = deque(maxlen=30)  # 30 frames history
    
    def analyze(self, face: Optional[FaceDetection], eye_state: Optional[EyeState], 
                gaze: Optional[GazeDirection], emotion: EmotionType) -> Tuple[DriverState, int]:
        """
        Analyze driver state
        
        Args:
            face: Face detection result
            eye_state: Eye state result
            gaze: Gaze direction result
            emotion: Detected emotion
        
        Returns:
            Tuple of (driver_state, alert_level)
        """
        if not face:
            return DriverState.DISTRACTED, 2
        
        # Check drowsiness
        if eye_state and eye_state.both_eyes_closed_duration > self.drowsiness_threshold:
            return DriverState.DROWSY, 2
        
        if eye_state and not eye_state.left_eye_open and not eye_state.right_eye_open:
            return DriverState.EYES_CLOSED, 2
        
        # Check distraction
        if gaze and not gaze.looking_forward:
            if abs(gaze.yaw) > 40:
                return DriverState.LOOKING_AWAY, 1
        
        # Check for yawning (would need more sophisticated detection)
        # Placeholder: using emotion as proxy
        if emotion == EmotionType.SURPRISED:
            return DriverState.YAWNING, 1
        
        # Check attention score
        if gaze and gaze.gaze_score < 0.5:
            return DriverState.DISTRACTED, 1
        
        return DriverState.NORMAL, 0

# ==================== INTEGRATED DRIVER MONITORING SYSTEM ====================

class DriverMonitoringSystem:
    """Complete driver monitoring system"""
    
    def __init__(self, emotion_model: str, face_model: Optional[str] = None, use_pi_camera: bool = True):
        """
        Initialize Driver Monitoring System
        
        Args:
            emotion_model: Path to emotion recognition ONNX model
            face_model: Path to face detection ONNX model (optional)
            use_pi_camera: Use Pi Camera v2 (True) or USB camera (False)
        """
        logger.info("Initializing Driver Monitoring System...")
        
        # Initialize camera
        self.use_pi_camera = use_pi_camera
        if use_pi_camera:
            self.pi_camera = PiCameraInterface(resolution=(640, 480), framerate=30)
            if not self.pi_camera.connected:
                logger.warning("Pi Camera not available, falling back to USB camera")
                self.use_pi_camera = False
                self.pi_camera = None
        
        # Initialize detectors
        self.face_detector = FaceDetector(face_model)
        self.eye_detector = EyeStateDetector()
        self.gaze_detector = GazeDetector()
        self.emotion_recognizer = EmotionRecognizer(emotion_model)
        self.state_analyzer = DriverStateAnalyzer()
        
        # Statistics
        self.fps = 0
        self.frame_times = []
        self.alert_count = 0
        
        logger.info("Driver Monitoring System ready!")
    
    def get_frame(self) -> Optional[np.ndarray]:
        """Get frame from Pi Camera or USB camera"""
        if self.use_pi_camera and self.pi_camera:
            return self.pi_camera.get_frame()
        return None
    
    def process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, DriverMonitoringResult]:
        """
        Process frame for driver monitoring
        
        Args:
            frame: Input frame from camera
        
        Returns:
            Tuple of (annotated_frame, monitoring_result)
        """
        start_time = time.time()
        
        # Detect face
        faces = self.face_detector.detect(frame)
        
        face = faces[0] if len(faces) > 0 else None
        eye_state = None
        gaze = None
        emotion = EmotionType.NEUTRAL
        emotion_conf = 0.0
        
        if face:
            x1, y1, x2, y2 = face.bbox
            face_roi = frame[y1:y2, x1:x2]
            
            # Detect eye state
            if face_roi.size > 0:
                eye_state = self.eye_detector.detect(face_roi)
            
            # Detect gaze direction
            gaze = self.gaze_detector.detect(face.bbox, frame.shape)
            
            # Recognize emotion
            if face_roi.size > 0:
                emotion, emotion_conf = self.emotion_recognizer.recognize(face_roi)
        
        # Analyze driver state
        driver_state, alert_level = self.state_analyzer.analyze(face, eye_state, gaze, emotion)
        
        # Track alerts
        if alert_level > 0:
            self.alert_count += 1
        
        # Create result
        result = DriverMonitoringResult(
            face_detected=face is not None,
            face=face,
            eye_state=eye_state,
            gaze=gaze,
            emotion=emotion,
            emotion_confidence=emotion_conf,
            driver_state=driver_state,
            alert_level=alert_level,
            timestamp=time.time()
        )
        
        # Draw annotations
        annotated = self._draw_annotations(frame, result)
        
        # Calculate FPS
        frame_time = time.time() - start_time
        self.frame_times.append(frame_time)
        if len(self.frame_times) > 30:
            self.frame_times.pop(0)
        self.fps = 1.0 / (sum(self.frame_times) / len(self.frame_times))
        
        return annotated, result
    
    def _draw_annotations(self, frame: np.ndarray, result: DriverMonitoringResult) -> np.ndarray:
        """Draw monitoring results on frame"""
        annotated = frame.copy()
        h, w = frame.shape[:2]
        
        # Draw FPS and camera source
        camera_source = "Pi Camera v2" if self.use_pi_camera else "USB Camera"
        cv2.putText(annotated, f"DMS FPS: {self.fps:.1f} ({camera_source})", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Draw face bounding box
        if result.face:
            x1, y1, x2, y2 = result.face.bbox
            color = (0, 255, 0) if result.alert_level == 0 else (0, 165, 255) if result.alert_level == 1 else (0, 0, 255)
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        
        # Draw driver state
        state_color = (0, 255, 0) if result.alert_level == 0 else (0, 165, 255) if result.alert_level == 1 else (0, 0, 255)
        cv2.putText(annotated, f"State: {result.driver_state.value}", (10, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, state_color, 2)
        
        # Draw emotion
        cv2.putText(annotated, f"Emotion: {result.emotion.value} ({result.emotion_confidence:.2f})", (10, 110),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        
        # Draw eye state
        if result.eye_state:
            eye_text = f"Eyes: {'Open' if result.eye_state.left_eye_open and result.eye_state.right_eye_open else 'Closed'}"
            if result.eye_state.both_eyes_closed_duration > 0:
                eye_text += f" ({result.eye_state.both_eyes_closed_duration:.1f}s)"
            cv2.putText(annotated, eye_text, (10, 150),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Draw gaze direction
        if result.gaze:
            gaze_text = f"Gaze: {'Forward' if result.gaze.looking_forward else 'Away'} (Score: {result.gaze.gaze_score:.2f})"
            cv2.putText(annotated, gaze_text, (10, 190),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(annotated, f"Yaw: {result.gaze.yaw:.1f}° Pitch: {result.gaze.pitch:.1f}°", (10, 230),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Draw alert banner if critical
        if result.alert_level == 2:
            cv2.rectangle(annotated, (0, h-100), (w, h), (0, 0, 255), -1)
            cv2.putText(annotated, "CRITICAL ALERT!", (w//2 - 150, h-50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
            cv2.putText(annotated, result.driver_state.value, (w//2 - 100, h-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        elif result.alert_level == 1:
            cv2.putText(annotated, f"WARNING: {result.driver_state.value}", (10, h-20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)
        
        return annotated
    
    def release(self):
        """Release camera resources"""
        if self.pi_camera:
            self.pi_camera.release()

# ==================== EXAMPLE USAGE ====================

def main():
    """Example usage of Driver Monitoring System"""
    
    EMOTION_MODEL = "models/emotion_recognition.onnx"
    FACE_MODEL = None  # Will use Haar Cascade
    
    dms = DriverMonitoringSystem(EMOTION_MODEL, FACE_MODEL, use_pi_camera=True)
    
    # Fallback to USB camera if Pi Camera not available
    if not dms.use_pi_camera:
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    logger.info("Starting Driver Monitoring...")
    logger.info("Press 'q' to quit")
    
    try:
        while True:
            if dms.use_pi_camera:
                frame = dms.get_frame()
                if frame is None:
                    break
            else:
                ret, frame = cap.read()
                if not ret:
                    break
            
            annotated, result = dms.process_frame(frame)
            
            cv2.imshow('Driver Monitoring System', annotated)
            
            # Print results
            print(f"\n=== Driver Monitoring Results ===")
            print(f"FPS: {dms.fps:.1f}")
            print(f"Face Detected: {result.face_detected}")
            print(f"Driver State: {result.driver_state.value}")
            print(f"Alert Level: {result.alert_level}")
            print(f"Emotion: {result.emotion.value} ({result.emotion_confidence:.2f})")
            if result.eye_state:
                print(f"Eyes Open: {result.eye_state.left_eye_open and result.eye_state.right_eye_open}")
            if result.gaze:
                print(f"Looking Forward: {result.gaze.looking_forward}")
                print(f"Gaze Score: {result.gaze.gaze_score:.2f}")
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        dms.release()
        if not dms.use_pi_camera:
            cap.release()
        cv2.destroyAllWindows()
        logger.info("Driver Monitoring System stopped")

if __name__ == "__main__":
    main()