import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QMessageBox,
                               QLabel, QLineEdit, QPushButton, QFrame, QGraphicsDropShadowEffect)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from change_credential_window import Change_Credential_Window
from database import Database_Manager
from dashboard import Dashboard

class Authentication_Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login UI")
        self.resize(800, 700)
        self.setStyleSheet("background-color: #1E1E2E;")

        central_widget = QWidget(); self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget); main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.card = QFrame(); self.card.setFixedSize(400, 500); self.card.setStyleSheet("background-color: #E0E0E0; border-radius: 20px;")
        shadow = QGraphicsDropShadowEffect(); shadow.setBlurRadius(25); shadow.setXOffset(0); shadow.setYOffset(5); shadow.setColor(QColor(0, 0, 0, 40))
        self.card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(self.card); card_layout.setContentsMargins(40, 50, 40, 50); card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter); card_layout.setSpacing(15)
        self.title = QLabel("SMART TRAFFIC LIGHT SYSTEM"); self.title.setAlignment(Qt.AlignmentFlag.AlignCenter); self.title.setStyleSheet("color: #252535; font-size: 20px; font-weight: bold;")
        
        input_style = "QLineEdit { border: 1px solid #CCCCCC; border-radius: 8px; padding-left: 15px; font-size: 14px; color: #333333; background-color: white; }"
        self.username_input = QLineEdit(); self.username_input.setPlaceholderText("Username"); self.username_input.setFixedHeight(60); self.username_input.setStyleSheet(input_style)
        self.password_input = QLineEdit(); self.password_input.setPlaceholderText("Password"); self.password_input.setEchoMode(QLineEdit.Password); self.password_input.setFixedHeight(60); self.password_input.setStyleSheet(input_style)

        self.login_btn = QPushButton("Log In"); self.login_btn.setFixedHeight(55); self.login_btn.clicked.connect(self.login_btn_clicked); self.login_btn.setStyleSheet("QPushButton { background-color: #5C6F2B; color: white; border-radius: 8px; font-weight: bold; }")

        card_layout.addWidget(self.title); card_layout.addWidget(self.username_input); card_layout.addWidget(self.password_input); card_layout.addWidget(self.login_btn)
        main_layout.addWidget(self.card)
        self.database = Database_Manager()
    
    def show_custom_message(self, title, text, icon_type="info"):
        msg = QMessageBox(self); msg.setWindowTitle(title); msg.setText(text)
        if icon_type == "error": msg.setIcon(QMessageBox.Icon.Critical)
        elif icon_type == "warning": msg.setIcon(QMessageBox.Icon.Warning)
        else: msg.setIcon(QMessageBox.Icon.Information)
        msg.setStyleSheet("QMessageBox { background-color: #1E1E2E; } QLabel { color: #E0E0E0; } QPushButton { background-color: #4A4036; color: white; }")
        msg.exec()

    def login_btn_clicked(self):
        username = self.username_input.text()
        password = self.password_input.text()
        self.authenticate_user = self.database.verify_user(username, password)

        if self.authenticate_user is None:
            self.show_custom_message("Error", "Invalid Username or Password!", "error")
        elif self.authenticate_user == 1:
            self.show_custom_message("Security Alert", "First time login detected.", "warning")
            self.change_cred_window = Change_Credential_Window(); self.change_cred_window.show(); self.close()
        elif self.authenticate_user == 0:
            # ONLY create and show the dashboard once here
            self.dashboard = Dashboard()
            self.dashboard.show()
            self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Authentication_Window(); window.show(); sys.exit(app.exec())