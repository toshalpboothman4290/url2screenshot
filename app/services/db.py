import sqlite3, os, time
from typing import Dict, Optional

DB_PATH = None

def init_db(database_url: str):
    global DB_PATH
    assert database_url.startswith("sqlite:///"), "Only sqlite supported in MVP"
    DB_PATH = database_url.replace("sqlite:///", "")
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    # جدول کاربران
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
          user_id INTEGER PRIMARY KEY,
          username TEXT,
          first_name TEXT,
          last_name TEXT,
          language_code TEXT,
          is_premium INTEGER DEFAULT 0,
          joined_at INTEGER,
          channel_member_at INTEGER
        );
    """)
    # جدول درخواست‌ها (jobs)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            url TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'queued',   -- queued | running | done | failed
            created_at INTEGER NOT NULL,
            started_at INTEGER,
            finished_at INTEGER,
            error TEXT,
            params_json TEXT,                        -- اختیاری: پارامترهای هر job به صورت JSON
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );
    """)
    # مهاجرت ایمن: اگر ستون params_json قبلاً وجود نداشت، اضافه شود
    cur.execute("PRAGMA table_info(jobs)")
    jcols = {row[1] for row in cur.fetchall()}
    if "params_json" not in jcols:
        try:
            cur.execute("ALTER TABLE jobs ADD COLUMN params_json TEXT")
        except Exception:
            pass

    con.commit()
    con.close()


def upsert_user(u: Dict, channel_member: bool):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
      INSERT INTO users(user_id, username, first_name, last_name, language_code, is_premium, joined_at, channel_member_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
      ON CONFLICT(user_id) DO UPDATE SET
        username=excluded.username,
        first_name=excluded.first_name,
        last_name=excluded.last_name,
        language_code=excluded.language_code,
        is_premium=excluded.is_premium,
        channel_member_at=CASE WHEN excluded.channel_member_at IS NOT NULL THEN excluded.channel_member_at ELSE channel_member_at END
    """, (
        u["id"], u.get("username"), u.get("first_name"), u.get("last_name"),
        u.get("language_code"), int(u.get("is_premium") or 0),
        int(time.time()),
        int(time.time()) if channel_member else None
    ))
    con.commit()
    con.close()


# -------------------------------
# توابع مدیریت صف jobs
# -------------------------------

def enqueue_job(user_id: int, url: str, params_json: Optional[str] = None) -> int:
    """ثبت یک job جدید در صف و برگرداندن id آن"""
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(
        "INSERT INTO jobs (user_id, url, status, created_at, params_json) VALUES (?, ?, 'queued', ?, ?)",
        (user_id, url, int(time.time()), params_json)
    )
    job_id = cur.lastrowid
    con.commit()
    con.close()
    return job_id


def get_queue_depth() -> int:
    """تعداد کل کارهای ناتمام (queued + running)"""
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT COUNT(*) FROM jobs WHERE status IN ('queued','running')")
    (cnt,) = cur.fetchone()
    con.close()
    return int(cnt)


def get_queue_position(job_id: int) -> int:
    """
    جایگاه job در بین کارهای ناتمام (queued+running) بر اساس created_at (و در تساوی id).
    اگر job پیدا نشود، 0.
    """
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT created_at FROM jobs WHERE id=?", (job_id,))
    row = cur.fetchone()
    if not row:
        con.close()
        return 0
    (created_at,) = row

    # همه‌ی کارهای ناتمامِ جلوتر یا برابر (با tie-break روی id) را بشمار
    cur.execute("""
        SELECT COUNT(*) FROM jobs
        WHERE status IN ('queued','running')
          AND (created_at < ?
               OR (created_at = ? AND id <= ?))
    """, (created_at, created_at, job_id))
    (pos,) = cur.fetchone()
    con.close()
    return int(pos)


def next_queued_job() -> dict | None:
    """
    قدیمی‌ترین job در صف را به‌صورت اتمیک انتخاب می‌کند و به حالت running می‌برد.
    از race condition بین چند Worker جلوگیری می‌کند.
    """
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    # کنترل تراکنش دستی
    con.isolation_level = None
    cur = con.cursor()
    try:
        cur.execute("BEGIN IMMEDIATE")
        cur.execute("""
            SELECT * FROM jobs
            WHERE status='queued'
            ORDER BY created_at ASC, id ASC
            LIMIT 1
        """)
        row = cur.fetchone()
        if not row:
            cur.execute("COMMIT")
            con.close()
            return None

        job_id = row["id"]
        cur.execute(
            "UPDATE jobs SET status='running', started_at=? WHERE id=? AND status='queued'",
            (int(time.time()), job_id)
        )
        cur.execute("COMMIT")
        result = dict(row)
        con.close()
        return result
    except Exception:
        cur.execute("ROLLBACK")
        con.close()
        raise


def complete_job(job_id: int, ok: bool, error: str = None):
    """وضعیت job را به done/failed تغییر می‌دهد"""
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    if ok:
        cur.execute(
            "UPDATE jobs SET status='done', finished_at=? WHERE id=?",
            (int(time.time()), job_id)
        )
    else:
        cur.execute(
            "UPDATE jobs SET status='failed', finished_at=?, error=? WHERE id=?",
            (int(time.time()), error, job_id)
        )
    con.commit()
    con.close()
