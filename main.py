import sys
import sqlite3
import hashlib
import os
import random
import string
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLineEdit, QPushButton, QLabel, 
                             QStackedWidget, QMessageBox, QFrame, QComboBox)
from PySide6.QtCore import Qt

try:
    from dashboard import Dashboard
except ImportError:
    class Dashboard(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Dashboard Placeholder")
            self.setCentralWidget(QLabel("Dashboard could not be loaded."))

class AuthDatabase:
    def __init__(self):
        self.conn = sqlite3.connect("traffic_system_v3.db")
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                password_hash BLOB,
                salt BLOB,
                secret_code TEXT,
                q1_text TEXT, q1_ans TEXT,
                q2_text TEXT, q2_ans TEXT,
                q3_text TEXT, q3_ans TEXT,
                is_first_login INTEGER DEFAULT 1
            )
        ''')
        self.cursor.execute("SELECT COUNT(*) FROM users")
        if self.cursor.fetchone()[0] == 0:
            self.reset_to_default()
        self.conn.commit()

    def reset_to_default(self):
        salt = os.urandom(32)
        pwd_hash = hashlib.pbkdf2_hmac('sha256', b'admin', salt, 100000)
        self.cursor.execute("DELETE FROM users")
        self.cursor.execute("""INSERT INTO users (id, username, password_hash, salt, is_first_login) 
                               VALUES (1, ?, ?, ?, 1)""", ('admin', pwd_hash, salt))
        self.conn.commit()

STYLE = """
    QMainWindow { background-color: #0f172a; }
    QMessageBox { background-color: #1e293b; border: 1px solid #38bdf8; }
    QMessageBox QLabel { color: #f8fafc; font-size: 14px; }
    QMessageBox QPushButton { background-color: #38bdf8; color: #0f172a; font-weight: bold; padding: 5px 15px; border-radius: 5px; }

    QFrame#Card { background-color: #1e293b; border-radius: 20px; border: 1px solid #334155; }
    QLabel { color: #f8fafc; font-family: 'Segoe UI'; font-size: 14px; }
    QLabel#Title { font-size: 28px; font-weight: 800; color: #38bdf8; margin-bottom: 10px; }
    QLabel#CodeDisplay { background: #0f172a; padding: 15px; border-radius: 8px; color: #fbbf24; font-family: 'Consolas'; font-size: 18px; border: 1px dashed #fbbf24; }
    
    QLineEdit, QComboBox {
        background-color: #0f172a; border: 2px solid #334155;
        border-radius: 10px; padding: 10px; color: #ffffff; font-size: 14px; margin-bottom: 5px;
    }
    QComboBox QAbstractItemView { background-color: #0f172a; color: #ffffff; selection-background-color: #38bdf8; }

    QPushButton { background-color: #38bdf8; color: #0f172a; font-weight: bold; border-radius: 10px; padding: 12px; font-size: 14px; margin-top: 5px; }
    QPushButton:hover { background-color: #7dd3fc; }
    QPushButton#ExitBtn { background-color: #ef4444; color: #ffffff; border-radius: 5px; padding: 5px 15px; }
    QPushButton#LinkBtn { background: transparent; color: #94a3b8; border: none; text-decoration: underline; }
"""

class TrafficAuthApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = AuthDatabase()
        self.setStyleSheet(STYLE)
        self.setWindowFlags(Qt.FramelessWindowHint)
        
        main_widget = QWidget()
        self.main_layout = QVBoxLayout(main_widget)
        self.setCentralWidget(main_widget)
        
        header = QHBoxLayout(); header.addStretch()
        exit_btn = QPushButton("✕ Exit System", objectName="ExitBtn")
        exit_btn.clicked.connect(self.close)
        header.addWidget(exit_btn); self.main_layout.addLayout(header)

        self.stack = QStackedWidget()
        self.main_layout.addWidget(self.stack)
        
        self.all_questions = [
            "What was your first car?", "What is your mother's maiden name?",
            "What was the name of your first pet?", "In what city were you born?",
            "What is your favorite food?", "What was your high school's name?",
            "What is your favorite movie?", "What was your dream job as a child?"
        ]
        
        self.init_ui()
        self.showFullScreen()

    def clear_inputs(self):
        """Clears all QLineEdit inputs in the window to protect data on screen change."""
        for widget in self.findChildren(QLineEdit):
            widget.clear()

    def change_page(self, index):
        """Helper to clear inputs whenever the stack index changes."""
        self.clear_inputs()
        self.stack.setCurrentIndex(index)

    def create_page_container(self, title_text):
        page = QWidget(); layout = QVBoxLayout(page)
        container = QHBoxLayout(); container.addStretch()
        card = QFrame(objectName="Card"); card.setFixedWidth(550)
        card_layout = QVBoxLayout(card); card_layout.setContentsMargins(40, 30, 40, 30)
        title = QLabel(title_text, objectName="Title"); title.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(title); container.addWidget(card); container.addStretch()
        layout.addStretch(); layout.addLayout(container); layout.addStretch()
        return page, card_layout

    def init_ui(self):
        # 1. LOGIN
        self.login_p, l_lay = self.create_page_container("System Login")
        self.u_in = QLineEdit(placeholderText="Username")
        self.p_in = QLineEdit(placeholderText="Password", echoMode=QLineEdit.Password)
        login_btn = QPushButton("Unlock System")
        forgot_btn = QPushButton("Recovery Options", objectName="LinkBtn")
        login_btn.clicked.connect(self.handle_login)
        forgot_btn.clicked.connect(lambda: self.change_page(2))
        for w in [self.u_in, self.p_in, login_btn, forgot_btn]: l_lay.addWidget(w)

        # 2. SETUP
        self.setup_p, s_lay = self.create_page_container("First-Time Setup")
        self.set_u = QLineEdit(placeholderText="New Username")
        self.set_p = QLineEdit(placeholderText="New Password", echoMode=QLineEdit.Password)
        self.gen_code_lbl = QLabel("Generating...", objectName="CodeDisplay")
        self.gen_code_lbl.setAlignment(Qt.AlignCenter)
        
        self.combo1 = QComboBox(); self.combo2 = QComboBox(); self.combo3 = QComboBox()
        self.combos = [self.combo1, self.combo2, self.combo3]
        self.combo1.addItems(self.all_questions); self.combo1.setCurrentIndex(0)
        self.combo2.addItems(self.all_questions); self.combo2.setCurrentIndex(1)
        self.combo3.addItems(self.all_questions); self.combo3.setCurrentIndex(2)

        for c in self.combos:
            c.currentIndexChanged.connect(self.filter_questions)
        
        self.ans1 = QLineEdit(placeholderText="Answer 1")
        self.ans2 = QLineEdit(placeholderText="Answer 2")
        self.ans3 = QLineEdit(placeholderText="Answer 3")
        
        save_btn = QPushButton("Complete Setup")
        save_btn.clicked.connect(self.handle_setup)
        s_lay.addWidget(QLabel("Recovery Secret Key (SAVE THIS):"))
        for w in [self.gen_code_lbl, self.set_u, self.set_p, self.combo1, self.ans1, self.combo2, self.ans2, self.combo3, self.ans3, save_btn]: 
            s_lay.addWidget(w)

        # 3. RECOVERY MAIN
        self.recover_p, r_lay = self.create_page_container("Account Recovery")
        btn_key = QPushButton("Recover by Secret Key")
        btn_qs = QPushButton("Recover by Security Questions")
        btn_key.clicked.connect(lambda: self.change_page(3))
        btn_qs.clicked.connect(self.load_recovery_questions)
        back_l = QPushButton("Back to Login", objectName="LinkBtn")
        back_l.clicked.connect(lambda: self.change_page(0))
        for w in [btn_key, btn_qs, back_l]: r_lay.addWidget(w)

        # 4. KEY INPUT
        self.key_page, k_lay = self.create_page_container("Verify Secret Key")
        self.k_input = QLineEdit(placeholderText="Enter 12-char Key")
        k_confirm = QPushButton("Reset Credentials")
        k_confirm.clicked.connect(self.handle_key_recovery)
        k_lay.addWidget(self.k_input); k_lay.addWidget(k_confirm)

        # 5. QS INPUT
        self.qs_page, q_lay = self.create_page_container("Verify Security Questions")
        self.rq1_lbl = QLabel(); self.rq1_in = QLineEdit(placeholderText="Answer 1")
        self.rq2_lbl = QLabel(); self.rq2_in = QLineEdit(placeholderText="Answer 2")
        self.rq3_lbl = QLabel(); self.rq3_in = QLineEdit(placeholderText="Answer 3")
        qs_confirm = QPushButton("Verify Answers")
        qs_confirm.clicked.connect(self.handle_qs_recovery)
        for w in [self.rq1_lbl, self.rq1_in, self.rq2_lbl, self.rq2_in, self.rq3_lbl, self.rq3_in, qs_confirm]: q_lay.addWidget(w)

        self.stack.addWidget(self.login_p); self.stack.addWidget(self.setup_p)
        self.stack.addWidget(self.recover_p); self.stack.addWidget(self.key_page); self.stack.addWidget(self.qs_page)

    def filter_questions(self):
        selections = [c.currentText() for c in self.combos]
        for i, combo in enumerate(self.combos):
            combo.blockSignals(True)
            current_val = combo.currentText()
            others = [sel for j, sel in enumerate(selections) if i != j]
            available = [q for q in self.all_questions if q not in others]
            combo.clear()
            combo.addItems(available)
            if current_val in available: combo.setCurrentText(current_val)
            combo.blockSignals(False)

    def load_recovery_questions(self):
        self.db.cursor.execute("SELECT q1_text, q2_text, q3_text FROM users WHERE id=1")
        res = self.db.cursor.fetchone()
        if res and res[0]:
            self.rq1_lbl.setText(res[0]); self.rq2_lbl.setText(res[1]); self.rq3_lbl.setText(res[2])
            self.change_page(4)
        else: QMessageBox.warning(self, "Error", "No questions found. Use Secret Key.")

    def handle_login(self):
        self.db.cursor.execute("SELECT password_hash, salt, is_first_login FROM users WHERE username=?", (self.u_in.text(),))
        res = self.db.cursor.fetchone()
        if res and hashlib.pbkdf2_hmac('sha256', self.p_in.text().encode(), res[1], 100000) == res[0]:
            if res[2]: 
                code = '-'.join(''.join(random.choices(string.ascii_uppercase + string.digits, k=4)) for _ in range(3))
                self.gen_code_lbl.setText(code)
                self.change_page(1)
            else:
                self.dash = Dashboard(); self.dash.show(); self.close()
        else: QMessageBox.warning(self, "Error", "Invalid credentials.")

    def handle_setup(self):
        # REQUIRED FIELDS VALIDATION
        inputs = [self.set_u.text().strip(), self.set_p.text().strip(), 
                  self.ans1.text().strip(), self.ans2.text().strip(), self.ans3.text().strip()]
        
        if not all(inputs):
            QMessageBox.critical(self, "Error", "All fields are required!")
            return

        salt = os.urandom(32)
        pwd_hash = hashlib.pbkdf2_hmac('sha256', self.set_p.text().encode(), salt, 100000)
        data = (self.set_u.text(), pwd_hash, salt, self.gen_code_lbl.text(), self.combo1.currentText(), self.ans1.text(), self.combo2.currentText(), self.ans2.text(), self.combo3.currentText(), self.ans3.text())
        self.db.cursor.execute("UPDATE users SET username=?, password_hash=?, salt=?, secret_code=?, q1_text=?, q1_ans=?, q2_text=?, q2_ans=?, q3_text=?, q3_ans=?, is_first_login=0 WHERE id=1", data)
        self.db.conn.commit()
        QMessageBox.information(self, "Success", "Security Configured.")
        self.change_page(0)

    def handle_key_recovery(self):
        self.db.cursor.execute("SELECT secret_code FROM users WHERE id=1")
        res = self.db.cursor.fetchone()
        if res and self.k_input.text().strip() == res[0]:
            self.db.reset_to_default()
            QMessageBox.information(self, "Success", "Reset to admin/admin.")
            self.change_page(0)
        else:
            QMessageBox.critical(self, "Error", "INCORRECT SECRET KEY")
            self.change_page(0)

    def handle_qs_recovery(self):
        self.db.cursor.execute("SELECT q1_ans, q2_ans, q3_ans FROM users WHERE id=1")
        ans = self.db.cursor.fetchone()
        if [self.rq1_in.text().strip(), self.rq2_in.text().strip(), self.rq3_in.text().strip()] == [ans[0], ans[1], ans[2]]:
            self.db.reset_to_default()
            QMessageBox.information(self, "Success", "Reset to admin/admin.")
            self.change_page(0)
        else:
            QMessageBox.critical(self, "Error", "INVALID!")
            self.change_page(0)

if __name__ == "__main__":
    app = QApplication(sys.argv); window = TrafficAuthApp(); window.show(); sys.exit(app.exec())