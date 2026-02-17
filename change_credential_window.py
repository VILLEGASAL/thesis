import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QMessageBox,
                               QLabel, QLineEdit, QPushButton, QFrame, QGraphicsDropShadowEffect)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from database import Database_Manager

class Change_Credential_Window(QMainWindow):
    def __init__(self, target_user="admin"):
        super().__init__()
        self.target_user = target_user
        self.setWindowTitle("Security Update Required")
        self.resize(800, 700)
        self.setStyleSheet("background-color: #1E1E2E;")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.card = QFrame()
        self.card.setFixedSize(400, 550)
        self.card.setStyleSheet("QFrame { background-color: #E0E0E0; border-radius: 20px; }")
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setYOffset(5)
        self.card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(40, 40, 40, 40)
        card_layout.setSpacing(15)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.title = QLabel("UPDATE CREDENTIALS")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title.setStyleSheet("color: #252535; font-size: 18px; font-weight: bold; font-family: Segoe UI;")
        
        self.subtitle = QLabel("For security, please set a new username and password.")
        self.subtitle.setWordWrap(True)
        self.subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle.setStyleSheet("color: #555555; font-size: 12px; margin-bottom: 10px;")

        input_style = """
            QLineEdit { border: 1px solid #CCCCCC; border-radius: 8px; padding-left: 15px; font-size: 14px; color: #333; background-color: white; }
            QLineEdit:focus { border: 1px solid #4A4036; }
        """

        self.new_user_input = QLineEdit()
        self.new_user_input.setPlaceholderText("New Username")
        self.new_user_input.setFixedHeight(50)
        self.new_user_input.setStyleSheet(input_style)

        self.new_pass_input = QLineEdit()
        self.new_pass_input.setPlaceholderText("New Password")
        self.new_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_pass_input.setFixedHeight(50)
        self.new_pass_input.setStyleSheet(input_style)

        self.confirm_pass_input = QLineEdit()
        self.confirm_pass_input.setPlaceholderText("Confirm New Password")
        self.confirm_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_pass_input.setFixedHeight(50)
        self.confirm_pass_input.setStyleSheet(input_style)

        # CHANGED: Button text implies continuation
        self.update_btn = QPushButton("Next: Security Setup →")
        self.update_btn.setFixedHeight(50)
        self.update_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_btn.clicked.connect(self.handle_next)
        self.update_btn.setStyleSheet("""
            QPushButton { background-color: #4A4036; color: white; border-radius: 8px; font-size: 15px; font-weight: bold; }
            QPushButton:hover { background-color: #5D5245; }
            QPushButton:pressed { background-color: #3B332B; }
        """)

        card_layout.addWidget(self.title)
        card_layout.addWidget(self.subtitle)
        card_layout.addWidget(self.new_user_input)
        card_layout.addWidget(self.new_pass_input)
        card_layout.addWidget(self.confirm_pass_input)
        card_layout.addSpacing(10)
        card_layout.addWidget(self.update_btn)

        main_layout.addWidget(self.card)
        self.db = Database_Manager()

    def handle_next(self):
        user = self.new_user_input.text()
        pwd = self.new_pass_input.text()
        confirm = self.confirm_pass_input.text()

        if not user or not pwd:
            QMessageBox.warning(self, "Error", "All fields are required.")
            return

        if pwd != confirm:
            QMessageBox.warning(self, "Error", "Passwords do not match!")
            return

        # --- NEW CHECK: PREVENT OLD PASSWORD REUSE ---
        if self.db.check_password_reused(self.target_user, pwd):
            QMessageBox.warning(self, "Security Error", 
                                "Your new password cannot be the same as your old password.\n"
                                "Please choose a different password.")
            return
        # ---------------------------------------------

        # PASS DATA TO NEXT WINDOW (DO NOT SAVE YET)
        from recovery_setup_window import Recovery_Setup_Window
        self.recovery_window = Recovery_Setup_Window(
            old_username=self.target_user, 
            new_username=user, 
            new_password=pwd
        )
        self.recovery_window.show()
        self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Change_Credential_Window()
    window.show()
    sys.exit(app.exec())