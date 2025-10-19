import sqlite3
import datetime
from config import DATABASE_NAME

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DATABASE_NAME, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                is_premium INTEGER DEFAULT 0,
                premium_expiry DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Fake emails table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fake_emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                email_address TEXT UNIQUE,
                password TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Premium codes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS premium_codes (
                code TEXT PRIMARY KEY,
                created_by INTEGER,
                used_by INTEGER DEFAULT NULL,
                used_at TIMESTAMP DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (created_by) REFERENCES users (user_id)
            )
        ''')
        
        # Inbox messages table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inbox_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_address TEXT,
                sender TEXT,
                subject TEXT,
                body TEXT,
                received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_read INTEGER DEFAULT 0
            )
        ''')
        
        self.conn.commit()

    # User management methods
    def get_user(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return cursor.fetchone()

    def create_user(self, user_id, username):
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                'INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)',
                (user_id, username)
            )
            self.conn.commit()
            return True
        except:
            return False

    def update_user_premium(self, user_id, is_premium=True, expiry_days=30):
        cursor = self.conn.cursor()
        expiry_date = datetime.datetime.now() + datetime.timedelta(days=expiry_days)
        cursor.execute(
            'UPDATE users SET is_premium = ?, premium_expiry = ? WHERE user_id = ?',
            (1 if is_premium else 0, expiry_date, user_id)
        )
        self.conn.commit()

    # Fake email management methods
    def create_fake_email(self, user_id, email_address, password):
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                'INSERT INTO fake_emails (user_id, email_address, password) VALUES (?, ?, ?)',
                (user_id, email_address, password)
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_user_emails(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT * FROM fake_emails WHERE user_id = ? AND is_active = 1 ORDER BY created_at DESC',
            (user_id,)
        )
        return cursor.fetchall()

    def get_email_count(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT COUNT(*) FROM fake_emails WHERE user_id = ? AND is_active = 1',
            (user_id,)
        )
        return cursor.fetchone()[0]

    def delete_fake_email(self, email_id, user_id):
        cursor = self.conn.cursor()
        cursor.execute(
            'UPDATE fake_emails SET is_active = 0 WHERE id = ? AND user_id = ?',
            (email_id, user_id)
        )
        self.conn.commit()
        return cursor.rowcount > 0

    # Premium code management methods
    def create_premium_code(self, code, created_by):
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                'INSERT INTO premium_codes (code, created_by) VALUES (?, ?)',
                (code, created_by)
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def use_premium_code(self, code, used_by):
        cursor = self.conn.cursor()
        cursor.execute(
            'UPDATE premium_codes SET used_by = ?, used_at = CURRENT_TIMESTAMP, is_active = 0 WHERE code = ? AND used_by IS NULL AND is_active = 1',
            (used_by, code)
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def get_premium_code(self, code):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM premium_codes WHERE code = ?', (code,))
        return cursor.fetchone()

    # Inbox management methods
    def add_inbox_message(self, email_address, sender, subject, body):
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO inbox_messages (email_address, sender, subject, body) VALUES (?, ?, ?, ?)',
            (email_address, sender, subject, body)
        )
        self.conn.commit()

    def get_inbox_messages(self, email_address):
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT * FROM inbox_messages WHERE email_address = ? ORDER BY received_at DESC',
            (email_address,)
        )
        return cursor.fetchall()

    def get_all_user_inbox(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT im.* FROM inbox_messages im
            JOIN fake_emails fe ON im.email_address = fe.email_address
            WHERE fe.user_id = ? AND fe.is_active = 1
            ORDER BY im.received_at DESC
        ''', (user_id,))
        return cursor.fetchall()