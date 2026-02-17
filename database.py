import sqlite3
import bcrypt

class Database_Manager:
    def __init__(self, db_name="traffic_system.db"):
        self.db_name = db_name
        self.init_tables()
        self.create_default_admin()

    def connect(self):
        return sqlite3.connect(self.db_name)

    def init_tables(self):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    is_default_password INTEGER DEFAULT 1,
                    recovery_key_hash TEXT,
                    sec_q1 TEXT, sec_a1_hash TEXT,
                    sec_q2 TEXT, sec_a2_hash TEXT,
                    sec_q3 TEXT, sec_a3_hash TEXT
                )
            """)
            conn.commit()

    def create_default_admin(self):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT count(*) FROM users")
            if cursor.fetchone()[0] == 0:
                # Hash default password "admin"
                hashed_pw = bcrypt.hashpw(b"admin", bcrypt.gensalt())
                cursor.execute("INSERT INTO users (username, password, is_default_password) VALUES (?, ?, ?)", 
                               ("admin", hashed_pw, 1))
                conn.commit()

    def verify_user(self, username, plain_password):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT password, is_default_password FROM users WHERE username = ?", (username,))
            result = cursor.fetchone()
            if result:
                stored_hash, is_default = result
                input_bytes = plain_password.encode('utf-8')
                if isinstance(stored_hash, str): stored_hash = stored_hash.encode('utf-8')

                try:
                    if bcrypt.checkpw(input_bytes, stored_hash):
                        return is_default 
                except ValueError:
                    return None
        return None 

    # --- NEW FEATURE: Check if password is reused ---
    def check_password_reused(self, username, new_password_plain):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
            result = cursor.fetchone()
            
            if result:
                stored_hash = result[0]
                if isinstance(stored_hash, str): stored_hash = stored_hash.encode('utf-8')
                
                # Check if the NEW password matches the OLD hash
                if bcrypt.checkpw(new_password_plain.encode('utf-8'), stored_hash):
                    return True # It IS reused (Bad)
        return False # Not reused (Good)

    # --- ATOMIC SAVE: Updates everything at once ---
    def finalize_account_setup(self, old_username, new_username, new_password, 
                             recovery_key, q1, a1, q2, a2, q3, a3):
        # Hash everything
        pwd_bytes = new_password.encode('utf-8')
        hashed_pw = bcrypt.hashpw(pwd_bytes, bcrypt.gensalt())
        key_hash = bcrypt.hashpw(recovery_key.encode('utf-8'), bcrypt.gensalt())
        a1_hash = bcrypt.hashpw(a1.strip().lower().encode('utf-8'), bcrypt.gensalt())
        a2_hash = bcrypt.hashpw(a2.strip().lower().encode('utf-8'), bcrypt.gensalt())
        a3_hash = bcrypt.hashpw(a3.strip().lower().encode('utf-8'), bcrypt.gensalt())

        with self.connect() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    UPDATE users 
                    SET username = ?, password = ?,
                        recovery_key_hash = ?, 
                        sec_q1 = ?, sec_a1_hash = ?,
                        sec_q2 = ?, sec_a2_hash = ?,
                        sec_q3 = ?, sec_a3_hash = ?,
                        is_default_password = 0
                    WHERE username = ?
                """, (new_username, hashed_pw, key_hash, 
                      q1, a1_hash, q2, a2_hash, q3, a3_hash, 
                      old_username))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False