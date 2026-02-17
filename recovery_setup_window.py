import sys
import secrets
import string
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QMessageBox,
                               QLabel, QLineEdit, QPushButton, QFrame, QComboBox, QScrollArea, QGraphicsDropShadowEffect)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QClipboard, QGuiApplication
from database import Database_Manager

class Recovery_Setup_Window(QMainWindow):
    def __init__(self, old_username, new_username, new_password):
        super().__init__()
        
        # Store the pending credentials temporarily
        # We will save these to the DB only when the user finishes this step.
        self.old_username = old_username
        self.new_username = new_username
        self.new_password = new_password

        self.db = Database_Manager()
        
        self.setWindowTitle("Account Recovery Setup")
        self.resize(900, 600) # Wider default size for 2 columns
        self.setStyleSheet("background-color: #1E1E2E;")

        # --- Main Scroll Area (Responsive) ---
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;") 
        self.setCentralWidget(scroll)
        
        content_widget = QWidget()
        scroll.setWidget(content_widget)
        
        # Center the card in the window
        main_layout = QVBoxLayout(content_widget)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.setContentsMargins(40, 40, 40, 40)

        # --- THE CARD FRAME ---
        self.card = QFrame()
        self.card.setFixedWidth(800) # Limit max width for readability
        self.card.setStyleSheet("""
            QFrame {
                background-color: #E0E0E0;
                border-radius: 20px;
            }
        """)
        
        # Drop Shadow for depth
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setYOffset(10)
        self.card.setGraphicsEffect(shadow)

        # Card Internal Layout
        card_main_layout = QVBoxLayout(self.card)
        card_main_layout.setSpacing(20)
        card_main_layout.setContentsMargins(40, 40, 40, 40)

        # 1. Header Section (Full Width)
        header_layout = QVBoxLayout()
        title = QLabel("SECURITY SETUP")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #252535; font-size: 24px; font-weight: bold; letter-spacing: 1px;")
        
        subtitle = QLabel("Please complete your account recovery configuration.\nThis is the ONLY way to restore access if you lose your password.")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #555; font-size: 14px; margin-bottom: 10px;")
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        card_main_layout.addLayout(header_layout)

        # 2. Content Section (Two Columns)
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(40) # Space between Left and Right columns

        # --- LEFT COLUMN: RECOVERY KEY ---
        left_col = QVBoxLayout()
        
        lbl_key_title = QLabel("1. RECOVERY KEY")
        lbl_key_title.setStyleSheet("color: #4A4036; font-size: 16px; font-weight: bold;")
        left_col.addWidget(lbl_key_title)

        # Key Display Box
        self.generated_key = self.generate_recovery_key()
        self.key_display = QLineEdit(self.generated_key)
        self.key_display.setReadOnly(True)
        self.key_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.key_display.setStyleSheet("""
            QLineEdit { 
                background-color: #FFFFFF; 
                border: 2px dashed #FF4C4C; 
                border-radius: 8px;
                color: #FF4C4C;
                font-family: Consolas, monospace; 
                font-size: 22px; 
                font-weight: bold; 
                padding: 15px; 
                margin-top: 10px;
            }
        """)
        left_col.addWidget(self.key_display)

        # Copy Button
        btn_copy = QPushButton("Copy to Clipboard")
        btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy.clicked.connect(self.copy_key)
        btn_copy.setStyleSheet("""
            QPushButton { background-color: #AAA; color: white; border-radius: 5px; padding: 5px; font-weight: bold;}
            QPushButton:hover { background-color: #888; }
        """)
        left_col.addWidget(btn_copy)

        # Important Note
        note_box = QFrame()
        note_box.setStyleSheet("background-color: #FFF3CD; border-radius: 8px; border: 1px solid #FFECB5;")
        note_layout = QVBoxLayout(note_box)
        
        lbl_warning = QLabel("⚠️ IMPORTANT WARNING")
        lbl_warning.setStyleSheet("color: #856404; font-weight: bold; font-size: 12px; border: none;")
        
        lbl_note_text = QLabel(
            "You must WRITE DOWN this key and keep it in a secure, physical location.\n\n"
            "If you forget your password and lose this key, you will be permanently locked out of the system."
        )
        lbl_note_text.setWordWrap(True)
        lbl_note_text.setStyleSheet("color: #856404; font-size: 12px; border: none;")
        
        note_layout.addWidget(lbl_warning)
        note_layout.addWidget(lbl_note_text)
        left_col.addWidget(note_box)
        left_col.addStretch() # Push everything up

        # --- RIGHT COLUMN: SECURITY QUESTIONS ---
        right_col = QVBoxLayout()
        
        lbl_sec_title = QLabel("2. SECURITY QUESTIONS")
        lbl_sec_title.setStyleSheet("color: #4A4036; font-size: 16px; font-weight: bold;")
        right_col.addWidget(lbl_sec_title)

        questions_list = [
            "What is your mother's maiden name?",
            "What was the name of your first pet?",
            "What city were you born in?",
            "What is your favorite food?",
            "What was the model of your first car?",
            "What represents your favorite color?"
        ]

        # Q1
        right_col.addWidget(self.create_label("Question 1"))
        self.cb_q1 = QComboBox()
        self.cb_q1.addItems(questions_list)
        self.cb_q1.setStyleSheet(self.combo_style())
        right_col.addWidget(self.cb_q1)
        self.ans_q1 = QLineEdit()
        self.ans_q1.setPlaceholderText("Answer...")
        self.ans_q1.setStyleSheet(self.input_style())
        right_col.addWidget(self.ans_q1)

        # Q2
        right_col.addWidget(self.create_label("Question 2"))
        self.cb_q2 = QComboBox()
        self.cb_q2.addItems(questions_list)
        self.cb_q2.setCurrentIndex(1)
        self.cb_q2.setStyleSheet(self.combo_style())
        right_col.addWidget(self.cb_q2)
        self.ans_q2 = QLineEdit()
        self.ans_q2.setPlaceholderText("Answer...")
        self.ans_q2.setStyleSheet(self.input_style())
        right_col.addWidget(self.ans_q2)

        # Q3
        right_col.addWidget(self.create_label("Question 3"))
        self.cb_q3 = QComboBox()
        self.cb_q3.addItems(questions_list)
        self.cb_q3.setCurrentIndex(2)
        self.cb_q3.setStyleSheet(self.combo_style())
        right_col.addWidget(self.cb_q3)
        self.ans_q3 = QLineEdit()
        self.ans_q3.setPlaceholderText("Answer...")
        self.ans_q3.setStyleSheet(self.input_style())
        right_col.addWidget(self.ans_q3)

        # Add columns to the Horizontal Layout
        columns_layout.addLayout(left_col, 1) # Stretch factor 1
        columns_layout.addLayout(right_col, 1) # Stretch factor 1
        
        card_main_layout.addLayout(columns_layout)

        # 3. Footer Button (Full Width)
        btn_finish = QPushButton("CONFIRM & FINISH SETUP")
        btn_finish.setFixedHeight(60)
        btn_finish.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_finish.clicked.connect(self.finish_setup)
        btn_finish.setStyleSheet("""
            QPushButton { 
                background-color: #2ecc71; 
                color: white; 
                border-radius: 10px; 
                font-weight: bold; 
                font-size: 16px; 
                margin-top: 20px;
            }
            QPushButton:hover { background-color: #27ae60; }
            QPushButton:pressed { background-color: #1e8449; }
        """)
        card_main_layout.addWidget(btn_finish)

        main_layout.addWidget(self.card)

    def generate_recovery_key(self):
        chars = string.ascii_uppercase + string.digits
        parts = [''.join(secrets.choice(chars) for _ in range(4)) for _ in range(4)]
        return '-'.join(parts)

    def copy_key(self):
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(self.generated_key)
        QMessageBox.information(self, "Copied", "Recovery key copied to clipboard.")

    def finish_setup(self):
        a1 = self.ans_q1.text()
        a2 = self.ans_q2.text()
        a3 = self.ans_q3.text()

        if not a1 or not a2 or not a3:
            self.show_custom_message(self, "Required", "Please answer all 3 security questions.", "warning")
            return

        # --- FINAL SAVE: ATOMIC TRANSACTION ---
        # This calls the method we created to update everything at once.
        success = self.db.finalize_account_setup(
            self.old_username,
            self.new_username,
            self.new_password,
            self.generated_key,
            self.cb_q1.currentText(), a1,
            self.cb_q2.currentText(), a2,
            self.cb_q3.currentText(), a3
        )

        if success:
            self.show_custom_message(self, "Setup Complete", 
                "Security setup successful!\n\n"
                "You will now be redirected to the login screen.", "info")
            
            # Open Login Window
            from authentication_window import Authentication_Window
            
            self.login_window = Authentication_Window()
            self.login_window.show()
            self.close()
        else:
            self.show_custom_message(self, "Error", "Database update failed.", "error")

    def show_custom_message(self, parent, title, text, icon_type="info"):
        msg = QMessageBox(parent)
        msg.setWindowTitle(title)
        msg.setText(text)
        
        # Set the icon based on type
        if icon_type == "error":
            msg.setIcon(QMessageBox.Icon.Critical)
        elif icon_type == "warning":
            msg.setIcon(QMessageBox.Icon.Warning)
        else:
            msg.setIcon(QMessageBox.Icon.Information)

        # --- THE STYLING ---
        # We style QMessageBox, the Text (QLabel), and the Buttons (QPushButton)
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #1E1E2E; /* Dark Background */
            }
            QLabel {
                color: #E0E0E0; /* Light Text */
                font-size: 13px;
            }
            QPushButton {
                background-color: #4A4036; /* Your Button Color */
                color: white;
                border-radius: 5px;
                padding: 5px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5D5245;
            }
            QPushButton:pressed {
                background-color: #3B332B;
            }
        """)
        
        msg.exec()

    # --- Styles ---
    def create_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #555; font-size: 12px; font-weight: bold; margin-top: 5px;")
        return lbl

    def input_style(self):
        return """
            QLineEdit { border: 1px solid #CCC; border-radius: 6px; padding: 8px; background: #FFF; color: #333; }
            QLineEdit:focus { border: 1px solid #4A4036; background: #FFF; }
        """

    def combo_style(self):
        return """
            QComboBox { 
                border: 1px solid #CCC; 
                border-radius: 6px; 
                padding: 5px 10px; 
                background: #FFF; 
                color: #333; 
                font-size: 13px;
            }
            QComboBox:hover {
                border: 1px solid #4A4036;
            }
            QComboBox::drop-down { 
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 35px;
                border-left-width: 1px;
                border-left-color: #DDD;
                border-left-style: solid; 
                border-top-right-radius: 6px; 
                border-bottom-right-radius: 6px;
                background: #F0F0F0;
            }
            
            /* FIXED ARROW STYLE */
            QComboBox::down-arrow {
                image: url(none); /* Remove default */
                
                /* Reset borders first to avoid 'solid' default messing up */
                border: none; 
                
                /* Now define the triangle */
                border-left: 6px solid rgba(0, 0, 0, 0);   /* Transparent Left */
                border-right: 6px solid rgba(0, 0, 0, 0);  /* Transparent Right */
                border-top: 7px solid #333333;             /* Dark Grey Top (Pointing Down) */
                
                width: 0px;
                height: 0px;
                
                margin-top: 2px;
                margin-right: 2px;
            }
            
            QComboBox::down-arrow:on { 
                top: 1px;
                left: 1px;
            }
        """

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Test call
    w = Recovery_Setup_Window("admin", "newuser", "newpass")
    w.show()
    sys.exit(app.exec())