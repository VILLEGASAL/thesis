import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QLabel, QProgressBar, QFrame, QGraphicsDropShadowEffect)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor

class Loading_Window(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 1. Window Setup
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(600, 400)
        
        # 2. Main Container
        self.container = QFrame(self)
        self.container.setGeometry(10, 10, 580, 380)
        self.container.setStyleSheet("""
            QFrame {
                background-color: #1B211A;
                border-radius: 20px;
                border: 2px solid #628141;
            }
        """)
        
        # Shadow Effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 150))
        self.container.setGraphicsEffect(shadow)
        
        # 3. Layout
        layout = QVBoxLayout(self.container)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(50, 50, 50, 50)
        layout.setSpacing(20)
        
        # 4. Text Labels
        self.lbl_title = QLabel("SMART TRAFFIC LIGHT SYSTEM")
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_title.setStyleSheet("""
            color: #EBD5AB;
            font-size: 20px;
            font-weight: bold;
            font-family: Segoe UI;
            letter-spacing: 2px;
            border: none;
        """)
        layout.addWidget(self.lbl_title)
        
        self.lbl_subtitle = QLabel("SYSTEM INITIALIZATION")
        self.lbl_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_subtitle.setStyleSheet("color: #628141; font-size: 14px; letter-spacing: 5px; border: none; font-weight: bold;")
        layout.addWidget(self.lbl_subtitle)
        
        layout.addSpacing(30)
        
        self.lbl_status = QLabel("Starting Interface...")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet("color: #FFFFFF; font-size: 12px; border: none;")
        layout.addWidget(self.lbl_status)
        
        # 5. Progress Bar
        self.progress = QProgressBar()
        self.progress.setFixedHeight(10)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar {
                background-color: #2b2b3d;
                border-radius: 5px;
                border: none;
            }
            QProgressBar::chunk {
                background-color: #628141;
                border-radius: 5px;
            }
        """)
        layout.addWidget(self.progress)
        
        # Logic Variables
        self.counter = 0
        self.main_station = None # Ref to Dashboard
        
        # UI Timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.progress_function)
        self.timer.start(35) 

        # Start heavy loading after a brief delay to allow window to show
        QTimer.singleShot(500, self.load_heavy_resources)

    def load_heavy_resources(self):
        """Loads AI and Hardware modules without freezing the splash screen."""
        try:
            self.lbl_status.setText("Connecting to AI Core (YOLOv11)...")
            
            # Local import prevents redundant initialization
            from dashboard import Dashboard
            
            # Create the dashboard instance
            # This triggers the hardware setup once and only once
            self.main_station = Dashboard()
            
        except Exception as e:
            self.lbl_status.setText(f"Initialization Error: {str(e)}")
            print(f"Error loading dashboard: {e}")

    def progress_function(self):
        self.counter += 1
        self.progress.setValue(self.counter)
        
        # Update text based on progress
        if self.counter == 20:
            self.lbl_status.setText("Checking Hardware Interlocks...")
        elif self.counter == 45:
            self.lbl_status.setText("Loading Neural Network Weights...")
        elif self.counter == 75:
            self.lbl_status.setText("Synchronizing Camera Streams...")
        elif self.counter >= 100:
            self.timer.stop()
            self.finish_loading()

    def finish_loading(self):
        """Transition to the main dashboard."""
        if self.main_station:
            self.main_station.show()
            self.close()
        else:
            # If dashboard isn't ready, wait another 500ms
            self.lbl_status.setText("Finalizing hardware link...")
            QTimer.singleShot(500, self.finish_loading)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Loading_Window()
    window.show()
    sys.exit(app.exec())