import cv2
import threading
from ultralytics import YOLO
from PySide6.QtCore import QObject, Signal

class VideoReader:
    def __init__(self, src):
        self.cap = cv2.VideoCapture(src)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.grabbed, self.frame = self.cap.read()
        self.started = False
        self.read_lock = threading.Lock()

    def start(self):
        if self.started: return self
        self.started = True
        self.thread = threading.Thread(target=self.update, args=())
        self.thread.daemon = True
        self.thread.start()
        return self

    def update(self):
        while self.started:
            grabbed, frame = self.cap.read()
            if grabbed:
                with self.read_lock:
                    self.grabbed = grabbed
                    self.frame = frame

    def read(self):
        with self.read_lock:
            # We copy here to ensure the detection logic has a clean frame
            frame = self.frame.copy() if self.frame is not None else None
            grabbed = self.grabbed
        return grabbed, frame

    def stop(self):
        self.started = False

class TrafficDetector(QObject):
    frame_ready = Signal(object, int, str, str, int) 

    def __init__(self):
        super().__init__()
        # Running YOLOv11n on Raspberry Pi 5
        self.model = YOLO("./yolo11n_ncnn_model", task="detect")
        self.ZONE = [100, 80, 540, 400] 
        self.running = True
        self.active_street = "Street A"
        self.is_counting = True
        self.light_color = "DETECTING"

    def get_duration(self, count):
        if count == 1: return 5
        elif count == 2: return 10
        elif count >= 3: return 15
        return 0 

    def process_street(self, frame, street_name, time_left):
        cup_count = 0
        display_color = "RED" 

        if street_name == self.active_street:
            display_color = self.light_color
            if self.is_counting:
                results = self.model(frame, imgsz=320, verbose=False, stream=True)
                cv2.rectangle(frame, (self.ZONE[0], self.ZONE[1]), (self.ZONE[2], self.ZONE[3]), (255, 255, 0), 2)
                for r in results:
                    for box in r.boxes:
                        if int(box.cls[0]) == 41: # Cup detection
                            x1, y1, x2, y2 = box.xyxy[0].tolist()
                            if (x1 >= self.ZONE[0] and y1 >= self.ZONE[1] and x2 <= self.ZONE[2] and y2 <= self.ZONE[3]):
                                cup_count += 1
                                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
            elif self.light_color == "GREEN":
                cv2.rectangle(frame, (self.ZONE[0], self.ZONE[1]), (self.ZONE[2], self.ZONE[3]), (0, 255, 0), 4)
            elif self.light_color == "YELLOW":
                cv2.rectangle(frame, (self.ZONE[0], self.ZONE[1]), (self.ZONE[2], self.ZONE[3]), (0, 255, 255), 4)

        # CRITICAL FIX: Emit a COPY of the frame to avoid memory conflicts
        self.frame_ready.emit(frame.copy(), cup_count, street_name, display_color, time_left)
        return cup_count