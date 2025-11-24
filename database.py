
# app/database.py
import sqlite3
from datetime import datetime

DB_PATH = "users.db"

def initialize_database():
    """Создает таблицу users при запуске"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        nickname TEXT,
        source_answer TEXT,
        experience_answer TEXT,
        is_approved INTEGER DEFAULT 0,
        approved_by INTEGER,
        created_at TEXT,
        approved_at TEXT
    )
    """)
    
    conn.commit()
    conn.close()

def save_user_application(user_id: int, username: str, full_name: str, 
                          nickname: str, source: str, experience: str):
    """Сохраняет заявку пользователя"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
    INSERT OR REPLACE INTO users 
    (user_id, username, full_name, nickname, source_answer, experience_answer, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, username, full_name, nickname, source, experience, 
          datetime.now().isoformat()))
    
    conn.commit()
    conn.close()

def approve_user(user_id: int, admin_id: int):
    """Одобряет пользователя"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
    UPDATE users 
    SET is_approved = 1, approved_by = ?, approved_at = ?
    WHERE user_id = ?
    """, (admin_id, datetime.now().isoformat(), user_id))
    
    conn.commit()
    conn.close()

def reject_user(user_id: int, admin_id: int):
    """Отклоняет пользователя (is_approved = -1)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
    UPDATE users 
    SET is_approved = -1, approved_by = ?, approved_at = ?
    WHERE user_id = ?
    """, (admin_id, datetime.now().isoformat(), user_id))
    
    conn.commit()
    conn.close()

def get_user(user_id: int):
    """Получает данные пользователя"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    
    conn.close()
    return result

def is_user_approved(user_id: int) -> bool:
    """Проверяет, одобрен ли пользователь"""
    user = get_user(user_id)
    return user and user[6] == 1  # is_approved column