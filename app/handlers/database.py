import os
import psycopg2
from psycopg2.extras import DictCursor
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")  # postgresql://user:pass@host:port/dbname

def get_conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=DictCursor)

def init_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS users_editorial (
                telegram_id BIGINT PRIMARY KEY REFERENCES users(telegram_id) ON DELETE CASCADE,
                preferred_language TEXT DEFAULT 'fa',
                instructions TEXT,
                preferred_provider TEXT,
                updated_at TIMESTAMP
            )
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                id SERIAL PRIMARY KEY,
                key TEXT UNIQUE,
                value TEXT
            )
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(telegram_id),
                status TEXT,
                provider TEXT,
                retry_count INTEGER DEFAULT 0,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
            """)

            def seed(k, envk, default):
                cur.execute("""
                    INSERT INTO settings(key, value) VALUES(%s, %s)
                    ON CONFLICT (key) DO NOTHING
                """, (k, os.getenv(envk, default)))

            seed("rate_limit_seconds", "RATE_LIMIT_SECONDS", "30")
            seed("max_words", "MAX_WORDS", "5000")
            seed("allowed_languages", "ALLOWED_LANGUAGES", "fa,en,ar")
            seed("default_provider", "DEFAULT_PROVIDER", "openai")

def upsert_user_to_psql(telegram_id: int, full_name: str, username: str, profile_pic_path: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT telegram_id FROM users WHERE telegram_id = %s", (telegram_id,))
            if not cur.fetchone():
                cur.execute("""
                    INSERT INTO users (telegram_id, full_name, username, profile_pic)
                    VALUES (%s, %s, %s, %s)
                """, (telegram_id, full_name, username, profile_pic_path))

            cur.execute("SELECT telegram_id FROM users_editorial WHERE telegram_id = %s", (telegram_id,))
            if not cur.fetchone():
                cur.execute("""
                    INSERT INTO users_editorial (telegram_id)
                    VALUES (%s)
                """, (telegram_id,))
