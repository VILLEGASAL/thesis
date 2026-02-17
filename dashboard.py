import sys
import cv2
import time
from gpiozero import DigitalOutputDevice
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, 
                             QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QGridLayout)
from PySide6.QtCore import Qt, QThread, Slot
from PySide6.QtGui import QImage, QPixmap, QFont
from detector import VideoReader, TrafficDetector 

# GPIO SETUP
A_GREEN, A_YELLOW, A_RED = DigitalOutputDevice(17), DigitalOutputDevice(27), DigitalOutputDevice(22)
B_GREEN, B_YELLOW, B_RED = DigitalOutputDevice(5), DigitalOutputDevice(6), DigitalOutputDevice(13)

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
        A_GREEN.off(); A_YELLOW.off(); A_RED.off()
        B_GREEN.off(); B_YELLOW.off(); B_RED.off()

        if self.detector.light_color == "DETECTING":
            A_RED.on(); B_RED.on()
        elif self.detector.active_street == "Street A":
            B_RED.on()
            if self.detector.light_color == "GREEN": A_GREEN.on()
            elif self.detector.light_color == "YELLOW": A_YELLOW.on()
        else:
            A_RED.on()
            if self.detector.light_color == "GREEN": B_GREEN.on()
            elif self.detector.light_color == "YELLOW": B_YELLOW.on()

    def run(self):
        while self.detector.running:
            self.update_hardware()
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
            self.msleep(10)

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
        self.setStyleSheet("""
            QMainWindow { background-color: #050505; } 
            QLabel { color: #ffffff; font-family: 'Courier New'; } 
            QFrame#Card { background-color: #1a1a1a; border: 2px solid #333; border-radius: 10px; }
            QPushButton#ExitBtn { background: #d32f2f; color: white; border-radius: 5px; padding: 10px; font-weight: bold; font-size: 16px; }
        """)
        central = QWidget(); self.setCentralWidget(central); main_lay = QVBoxLayout(central)
        header = QHBoxLayout()
        header.addWidget(QLabel("CCTV TRAFFIC MONITORING STATION")); header.addStretch()
        exit_btn = QPushButton("EXIT"); exit_btn.setObjectName("ExitBtn"); exit_btn.clicked.connect(self.close); header.addWidget(exit_btn)
        main_lay.addLayout(header)
        grid = QGridLayout(); grid.setSpacing(40)
        self.view_a = self.create_cam_card("STREET A")
        self.view_b = self.create_cam_card("STREET B")
        grid.addWidget(self.view_a['card'], 0, 0, alignment=Qt.AlignCenter); grid.addWidget(self.view_b['card'], 0, 1, alignment=Qt.AlignCenter)
        main_lay.addLayout(grid)
        self.detector = TrafficDetector()
        self.detector.frame_ready.connect(self.update_ui)
        self.worker = Worker(self.detector); self.worker.start()

    def create_cam_card(self, title_text):
        card = QFrame(); card.setObjectName("Card"); l = QVBoxLayout(card); l.setContentsMargins(15, 15, 15, 15)
        tit = QLabel(title_text); tit.setAlignment(Qt.AlignCenter); tit.setFont(QFont("Courier New", 24, QFont.Bold))
        v = QLabel(); v.setFixedSize(640, 480); v.setStyleSheet("background: black; border: 1px solid #555;")
        info_box = QHBoxLayout(); count_lbl = QLabel("DETECTED: 0"); count_lbl.setFont(QFont("Courier New", 18, QFont.Bold)); count_lbl.setStyleSheet("color: #2979ff;")
        timer_lbl = QLabel("00"); timer_lbl.setAlignment(Qt.AlignCenter); timer_lbl.setFont(QFont("Courier New", 50, QFont.Bold)); info_box.addWidget(count_lbl); info_box.addStretch(); info_box.addWidget(timer_lbl)
        status_lbl = QLabel("STATUS: STANDBY"); status_lbl.setAlignment(Qt.AlignCenter); status_lbl.setFont(QFont("Courier New", 20, QFont.Bold))
        l.addWidget(tit); l.addWidget(v); l.addLayout(info_box); l.addWidget(status_lbl)
        return {'card': card, 'video': v, 'timer': timer_lbl, 'status': status_lbl, 'count': count_lbl}

    @Slot(object, int, str, str, int)
    def update_ui(self, frame, count, street, status, time_left):
        if frame is None: return
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pix = QPixmap.fromImage(QImage(rgb.data, 640, 480, 640*3, QImage.Format_RGB888))
        v = self.view_a if street == "Street A" else self.view_b
        v['video'].setPixmap(pix)
        if street == self.detector.active_street:
            v['timer'].setText(f"{time_left:02d}"); v['count'].setText(f"DETECTED: {count}")
            color = "#00ff41" if status == "GREEN" else "#ffea00" if status == "YELLOW" else "#ff1744"
            v['status'].setText(f"STATUS: {status}"); v['status'].setStyleSheet(f"color: {color};"); v['timer'].setStyleSheet(f"color: {color};")
            other = self.view_b if street == "Street A" else self.view_a
            other['status'].setText("STATUS: RED"); other['status'].setStyleSheet("color: #ff1744;"); other['timer'].setText("--"); other['timer'].setStyleSheet("color: #444;"); other['count'].setText("DETECTED: --")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Dashboard(); window.show(); sys.exit(app.exec())