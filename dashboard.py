import sys
import cv2
import time
import os
import threading
from gpiozero import DigitalOutputDevice
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, 
                             QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QGridLayout)
from PySide6.QtCore import Qt, QThread, Slot, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap, QFont
from detector import VideoReader, TrafficDetector 

# GPIO SETUP: 3 pins for logic circuit + 1 pin for Active-Low Relay
PIN_A = DigitalOutputDevice(17)
PIN_B = DigitalOutputDevice(27)
PIN_C = DigitalOutputDevice(22)

# Pin 23 for Active-Low Relay. 
# active_high=False means .on() outputs LOW (0V) and .off() outputs HIGH (3.3V)
RELAY_PIN = DigitalOutputDevice(23, active_high=False, initial_value=False)

class AudioSirenThread(QThread):
    siren_signal = Signal()

    def __init__(self):
        super().__init__()
        self.running = True

    def run(self):
        # Suppress TensorFlow terminal spam
        os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' 
        os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
        
        import sounddevice as sd
        import numpy as np
        import tensorflow_hub as hub
        import csv

        # Load model inside the thread so it doesn't freeze the GUI during startup
        model = hub.load('https://tfhub.dev/google/yamnet/1')
        
        class_map_path = model.class_map_path().numpy().decode('utf-8')
        class_names = []
        with open(class_map_path) as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                class_names.append(row['display_name'])

        TARGET_CLASSES = ['Siren', 'Ambulance (siren)', 'Police car (siren)', 'Fire engine, fire truck (siren)']
        EXCLUDE_CLASSES = ['Whistle', 'Wind']
        
        target_indices = [i for i, name in enumerate(class_names) if name in TARGET_CLASSES]
        exclude_indices = [i for i, name in enumerate(class_names) if name in EXCLUDE_CLASSES]

        # Lowered to 0.40 because we are now summing the probabilities together
        CONFIDENCE_THRESHOLD = 0.40 
        REQUIRED_CONSECUTIVE_HITS = 2
        self.consecutive_hits = 0

        def audio_callback(indata, frames, time_info, status):
            if not self.running: return
            
            audio_data = np.squeeze(indata)
            scores, embeddings, spectrogram = model(audio_data)
            mean_scores = np.mean(scores, axis=0)
            
            max_exclude_score = max([mean_scores[ex] for ex in exclude_indices])
            siren_detected_this_frame = False
            
            # THE FIX: Sum all the target scores together to catch "split" probabilities
            total_siren_score = sum([mean_scores[i] for i in target_indices])
            
            if total_siren_score > CONFIDENCE_THRESHOLD:
                if total_siren_score > max_exclude_score:
                    siren_detected_this_frame = True
                    # Find which specific class contributed the most for our debug print
                    best_target_idx = max(target_indices, key=lambda i: mean_scores[i])
                    print(f"AI Heard: Siren Cluster (Mainly {class_names[best_target_idx]}) | Total Confidence: {total_siren_score*100:.1f}%")

            if siren_detected_this_frame:
                self.consecutive_hits += 1
                if self.consecutive_hits >= REQUIRED_CONSECUTIVE_HITS:
                    self.siren_signal.emit()
                    self.consecutive_hits = 0
            else:
                if self.consecutive_hits > 0:
                    self.consecutive_hits = 0

        try:
            # ---> IMPORTANT: CHANGE THIS DEVICE ID TO MATCH YOUR USB MIC <---
            MIC_DEVICE_ID = 0 
            
            print(f"Starting Audio AI on Device ID: {MIC_DEVICE_ID}...")
            
            # Requires 16kHz mono audio
            with sd.InputStream(device=MIC_DEVICE_ID, samplerate=16000, channels=1, callback=audio_callback, blocksize=16000):
                while self.running:
                    self.msleep(100) # Keep thread alive
        except Exception as e:
            print(f"Audio Thread Error: {e}")

    def stop(self):
        self.running = False
        self.wait()

class Worker(QThread):
    def __init__(self, detector):
        super().__init__()
        self.detector = detector
        self.cam_a = VideoReader(0).start()
        self.cam_b = VideoReader(2).start() 
        self.start_time = time.time()
        self.current_duration = 5 
        self.last_valid_count = 0

    def update_hardware(self):
        try:
            a, b, c = 0, 0, 0

            # Emergency Mode
            if self.detector.emergency_mode:
                a, b, c = 0, 1, 0
                RELAY_PIN.on() # Triggers the active-low relay (Pulls to GND)
            
            # Detecting State
            elif self.detector.light_color == "DETECTING":
                a, b, c = 0, 1, 0
                RELAY_PIN.off() # Ensure relay is OFF
            
            # Street A Active
            elif self.detector.active_street == "Street A":
                RELAY_PIN.off()
                if self.detector.light_color == "GREEN":
                    a, b, c = 0, 0, 0
                elif self.detector.light_color == "YELLOW":
                    a, b, c = 0, 0, 1
            
            # Street B Active
            elif self.detector.active_street == "Street B":
                RELAY_PIN.off()
                if self.detector.light_color == "GREEN":
                    a, b, c = 0, 1, 1
                elif self.detector.light_color == "YELLOW":
                    a, b, c = 1, 0, 0

            # Write the binary state to the 3 GPIO pins
            if a: PIN_A.on()
            else: PIN_A.off()
            
            if b: PIN_B.on()
            else: PIN_B.off()
            
            if c: PIN_C.on()
            else: PIN_C.off()

        except: pass

    def run(self):
        while self.detector.running:
            self.update_hardware()
            if not self.detector.emergency_mode:
                elapsed = time.time() - self.start_time
                time_left = max(0, int(self.current_duration - elapsed))
                ret_a, frame_a = self.cam_a.read()
                ret_b, frame_b = self.cam_b.read()

                if ret_a and frame_a is not None:
                    c_a = self.detector.process_street(frame_a, "Street A", time_left)
                    if self.detector.active_street == "Street A" and self.detector.is_counting:
                        self.last_valid_count = c_a
                if ret_b and frame_b is not None:
                    c_b = self.detector.process_street(frame_b, "Street B", time_left)
                    if self.detector.active_street == "Street B" and self.detector.is_counting:
                        self.last_valid_count = c_b

                if elapsed >= self.current_duration:
                    self.handle_transition()
            else:
                ret_a, frame_a = self.cam_a.read()
                ret_b, frame_b = self.cam_b.read()
                if ret_a and frame_a is not None: self.detector.process_street(frame_a, "Street A", 0)
                if ret_b and frame_b is not None: self.detector.process_street(frame_b, "Street B", 0)
            
            self.msleep(60) 

    def handle_transition(self):
        if self.detector.is_counting:
            duration = self.detector.get_duration(self.last_valid_count)
            if duration > 0:
                self.start_time = time.time(); self.detector.is_counting = False
                self.detector.light_color = "GREEN"; self.current_duration = duration
            else: self.swap_lanes()
        elif self.detector.light_color == "GREEN":
            self.start_time = time.time(); self.detector.light_color = "YELLOW"; self.current_duration = 3
        else: self.swap_lanes()

    def swap_lanes(self):
        self.start_time = time.time(); self.detector.is_counting = True
        self.detector.light_color = "DETECTING"; self.current_duration = 5 
        self.last_valid_count = 0
        self.detector.active_street = "Street B" if self.detector.active_street == "Street A" else "Street A"

class Dashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.showFullScreen()
        self.setStyleSheet("QMainWindow { background-color: #050505; } QLabel { color: #ffffff; font-family: 'Courier New'; } QFrame#Card { background-color: #1a1a1a; border: 2px solid #333; border-radius: 10px; }")
        central = QWidget(); self.setCentralWidget(central); main_lay = QVBoxLayout(central)
        
        self.title_label = QLabel("CCTV TRAFFIC MONITORING STATION")
        self.title_label.setFont(QFont("Courier New", 20, QFont.Bold))
        header = QHBoxLayout(); header.addWidget(self.title_label); header.addStretch()
        exit_btn = QPushButton("EXIT"); exit_btn.setStyleSheet("background: #d32f2f; color: white; border-radius: 5px; padding: 10px; font-weight: bold;")
        exit_btn.clicked.connect(self.close); header.addWidget(exit_btn); main_lay.addLayout(header)

        grid = QGridLayout(); grid.setSpacing(40)
        self.view_a = self.create_cam_card("STREET A")
        self.view_b = self.create_cam_card("STREET B")
        grid.addWidget(self.view_a['card'], 0, 0, alignment=Qt.AlignCenter); grid.addWidget(self.view_b['card'], 0, 1, alignment=Qt.AlignCenter); main_lay.addLayout(grid)
        
        self.detector = TrafficDetector()
        self.detector.frame_ready.connect(self.update_ui)
        self.worker = Worker(self.detector); self.worker.start()

        self.last_siren_time = 0
        self.watchdog_timer = QTimer()
        self.watchdog_timer.timeout.connect(self.check_emergency_timeout)
        self.watchdog_timer.start(500)

        self.audio_thread = AudioSirenThread()
        self.audio_thread.siren_signal.connect(self.activate_emergency)
        self.audio_thread.start()

    def create_cam_card(self, title):
        card = QFrame(); card.setObjectName("Card"); l = QVBoxLayout(card); l.setContentsMargins(15, 15, 15, 15)
        tit = QLabel(title); tit.setAlignment(Qt.AlignCenter); tit.setFont(QFont("Courier New", 24, QFont.Bold))
        v = QLabel(); v.setFixedSize(640, 480); v.setStyleSheet("background: black; border: 1px solid #555;")
        info = QHBoxLayout(); c_lbl = QLabel("DETECTED: 0"); c_lbl.setFont(QFont("Courier New", 18, QFont.Bold)); c_lbl.setStyleSheet("color: #2979ff;")
        t_lbl = QLabel("00"); t_lbl.setAlignment(Qt.AlignCenter); t_lbl.setFont(QFont("Courier New", 50, QFont.Bold)); info.addWidget(c_lbl); info.addStretch(); info.addWidget(t_lbl)
        s_lbl = QLabel("STATUS: STANDBY"); s_lbl.setAlignment(Qt.AlignCenter); s_lbl.setFont(QFont("Courier New", 20, QFont.Bold))
        l.addWidget(tit); l.addWidget(v); l.addLayout(info); l.addWidget(s_lbl)
        return {'card': card, 'video': v, 'timer': t_lbl, 'status': s_lbl, 'count': c_lbl}

    @Slot()
    def activate_emergency(self):
        self.last_siren_time = time.time()
        if not self.detector.emergency_mode:
            self.detector.emergency_mode = True
            self.title_label.setText("!!! EMERGENCY VEHICLE DETECTED - ALL RED !!!")
            self.title_label.setStyleSheet("color: #ff1744; font-weight: bold;")

    def check_emergency_timeout(self):
        if self.detector.emergency_mode:
            # Using 3.0 seconds timeout so the alarm has time to clear
            if time.time() - self.last_siren_time > 3.0:
                self.deactivate_emergency()

    def deactivate_emergency(self):
        self.detector.emergency_mode = False
        self.title_label.setText("CCTV TRAFFIC MONITORING STATION")
        self.title_label.setStyleSheet("color: white;")
        self.worker.start_time = time.time()

    @Slot(object, int, str, str, int, bool)
    def update_ui(self, frame, count, street, status, time_left, is_emergency):
        if frame is None: return
        try:
            img = frame.copy()
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            q_img = QImage(rgb.data, 640, 480, 640 * 3, QImage.Format_RGB888)
            pix = QPixmap.fromImage(q_img).copy()
            v = self.view_a if street == "Street A" else self.view_b
            v['video'].setPixmap(pix)

            if is_emergency:
                v['status'].setText("!!! EMERGENCY !!!"); v['status'].setStyleSheet("color: #ff1744;")
                v['timer'].setText("--"); v['count'].setText("DETECTED: --")
            elif street == self.detector.active_street:
                v['timer'].setText(f"{time_left:02d}"); v['count'].setText(f"DETECTED: {count}")
                color = "#00ff41" if status == "GREEN" else "#ffea00" if status == "YELLOW" else "#ff1744"
                v['status'].setText(f"STATUS: {status}"); v['status'].setStyleSheet(f"color: {color};"); v['timer'].setStyleSheet(f"color: {color};")
                other = self.view_b if street == "Street A" else self.view_a
                other['status'].setText("STATUS: RED"); other['status'].setStyleSheet("color: #ff1744;"); other['timer'].setText("--")
        except: pass

    def closeEvent(self, event):
        self.detector.running = False
        self.worker.quit(); self.worker.wait()
        self.audio_thread.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)                                
    window = Dashboard(); window.show(); sys.exit(app.exec())