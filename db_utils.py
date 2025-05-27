import sqlite3

DB_PATH = "db/user_profiles.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_profile (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_name TEXT NOT NULL,
                user_image TEXT
            )
        ''')
        conn.commit()

def save_user_profile(user_name, user_image):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM user_profile')  # 確保只有一筆
        cursor.execute('''
            INSERT INTO user_profile (user_name, user_image)
            VALUES (?, ?)
        ''', (user_name, user_image))
        conn.commit()

def get_user_profile():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT user_name, user_image FROM user_profile LIMIT 1')
        row = cursor.fetchone()
        if row:
            return {"user_name": row[0], "user_image": row[1]}
        else:
            return None
