"""
Database operations for Valentine Bot v2.0
Supports both Vercel Postgres (production) and SQLite (local dev)
"""
import json
import secrets
import logging
from datetime import date, datetime, timedelta
from typing import Optional

import config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# DB connection helper — auto-selects Postgres (Vercel) or SQLite (local)
# ---------------------------------------------------------------------------

_use_postgres = bool(config.POSTGRES_URL)


def _get_pg_conn():
    """Get a psycopg2 connection to Vercel Postgres"""
    import psycopg2
    import psycopg2.extras
    conn = psycopg2.connect(config.POSTGRES_URL)
    conn.autocommit = False
    return conn


def _dict_row(cursor, row):
    """Convert a row to a dict using cursor.description"""
    if row is None:
        return None
    return {col.name: row[idx] for idx, col in enumerate(cursor.description)}


def _fetchone_dict(cursor):
    row = cursor.fetchone()
    return _dict_row(cursor, row)


def _fetchall_dict(cursor):
    rows = cursor.fetchall()
    return [_dict_row(cursor, r) for r in rows]


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------

async def init_db():
    """Initialize database and create tables"""
    if _use_postgres:
        _init_db_pg()
    else:
        await _init_db_sqlite()


def _init_db_pg():
    """Initialize Postgres tables"""
    conn = _get_pg_conn()
    try:
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                registered_at TIMESTAMP DEFAULT NOW(),
                free_sends_today INTEGER DEFAULT 0,
                last_send_date DATE,
                bonus_valentines INTEGER DEFAULT 0,
                zodiac_sign TEXT,
                chain_count INTEGER DEFAULT 0,
                roulette_uses_today INTEGER DEFAULT 0,
                last_roulette_date DATE,
                roulette_free_until TIMESTAMP
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS valentines (
                id SERIAL PRIMARY KEY,
                sender_id BIGINT REFERENCES users(user_id),
                receiver_id BIGINT REFERENCES users(user_id),
                message TEXT NOT NULL,
                is_premium BOOLEAN DEFAULT FALSE,
                is_poem BOOLEAN DEFAULT FALSE,
                is_revealed BOOLEAN DEFAULT FALSE,
                is_delivered BOOLEAN DEFAULT FALSE,
                reaction TEXT,
                voice_file_id TEXT,
                photo_file_id TEXT,
                gift_emoji TEXT,
                music_url TEXT,
                scheduled_for TIMESTAMP,
                is_scheduled_sent BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id),
                amount INTEGER,
                type TEXT,
                valentine_id INTEGER,
                telegram_payment_charge_id TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS anon_chats (
                id TEXT PRIMARY KEY,
                valentine_id INTEGER,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS anon_messages (
                id SERIAL PRIMARY KEY,
                chat_id TEXT,
                from_sender BOOLEAN,
                text TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS roulette_queue (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id),
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                matched BOOLEAN DEFAULT FALSE
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS compatibility_tests (
                id TEXT PRIMARY KEY,
                initiator_id BIGINT,
                partner_id BIGINT,
                initiator_answers TEXT,
                partner_answers TEXT,
                result_percent INTEGER,
                is_paid BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS achievements (
                user_id BIGINT REFERENCES users(user_id),
                badge TEXT NOT NULL,
                earned_at TIMESTAMP DEFAULT NOW(),
                PRIMARY KEY (user_id, badge)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id),
                plan TEXT NOT NULL,
                started_at TIMESTAMP DEFAULT NOW(),
                expires_at TIMESTAMP NOT NULL,
                telegram_payment_charge_id TEXT,
                is_active BOOLEAN DEFAULT TRUE
            )
        """)

        conn.commit()
        logger.info("Postgres database initialized")
    finally:
        conn.close()


async def _init_db_sqlite():
    """Initialize SQLite tables (local dev)"""
    import aiosqlite
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                free_sends_today INTEGER DEFAULT 0,
                last_send_date DATE,
                bonus_valentines INTEGER DEFAULT 0,
                zodiac_sign TEXT,
                chain_count INTEGER DEFAULT 0,
                roulette_uses_today INTEGER DEFAULT 0,
                last_roulette_date DATE,
                roulette_free_until TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS valentines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER REFERENCES users(user_id),
                receiver_id INTEGER REFERENCES users(user_id),
                message TEXT NOT NULL,
                is_premium BOOLEAN DEFAULT FALSE,
                is_poem BOOLEAN DEFAULT FALSE,
                is_revealed BOOLEAN DEFAULT FALSE,
                is_delivered BOOLEAN DEFAULT FALSE,
                reaction TEXT,
                voice_file_id TEXT,
                photo_file_id TEXT,
                gift_emoji TEXT,
                music_url TEXT,
                scheduled_for TIMESTAMP,
                is_scheduled_sent BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES users(user_id),
                amount INTEGER,
                type TEXT,
                valentine_id INTEGER,
                telegram_payment_charge_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS anon_chats (
                id TEXT PRIMARY KEY,
                valentine_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS anon_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT,
                from_sender BOOLEAN,
                text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS roulette_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES users(user_id),
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                matched BOOLEAN DEFAULT FALSE
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS compatibility_tests (
                id TEXT PRIMARY KEY,
                initiator_id INTEGER,
                partner_id INTEGER,
                initiator_answers TEXT,
                partner_answers TEXT,
                result_percent INTEGER,
                is_paid BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS achievements (
                user_id INTEGER REFERENCES users(user_id),
                badge TEXT NOT NULL,
                earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, badge)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES users(user_id),
                plan TEXT NOT NULL,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                telegram_payment_charge_id TEXT,
                is_active BOOLEAN DEFAULT TRUE
            )
        """)
        await db.commit()
        logger.info("SQLite database initialized")


# ==================== USER OPERATIONS ====================

async def get_or_create_user(user_id: int, username: Optional[str] = None,
                             first_name: Optional[str] = None) -> dict:
    """Get existing user or create new one"""
    if _use_postgres:
        conn = _get_pg_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            row = _fetchone_dict(cur)

            if row:
                if username or first_name:
                    cur.execute(
                        "UPDATE users SET username = %s, first_name = %s WHERE user_id = %s",
                        (username or row['username'], first_name or row['first_name'], user_id)
                    )
                    conn.commit()
                return row

            cur.execute(
                "INSERT INTO users (user_id, username, first_name) VALUES (%s, %s, %s)",
                (user_id, username, first_name)
            )
            conn.commit()
            cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            return _fetchone_dict(cur)
        finally:
            conn.close()
    else:
        import aiosqlite
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            if row:
                if username or first_name:
                    await db.execute(
                        "UPDATE users SET username = ?, first_name = ? WHERE user_id = ?",
                        (username or row['username'], first_name or row['first_name'], user_id)
                    )
                    await db.commit()
                return dict(row)
            await db.execute(
                "INSERT INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
                (user_id, username, first_name)
            )
            await db.commit()
            cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            return dict(row)


async def set_zodiac(user_id: int, sign: str):
    """Set user's zodiac sign"""
    if _use_postgres:
        conn = _get_pg_conn()
        try:
            cur = conn.cursor()
            cur.execute("UPDATE users SET zodiac_sign = %s WHERE user_id = %s", (sign, user_id))
            conn.commit()
        finally:
            conn.close()
    else:
        import aiosqlite
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            await db.execute("UPDATE users SET zodiac_sign = ? WHERE user_id = ?", (sign, user_id))
            await db.commit()


async def get_user_zodiac(user_id: int) -> Optional[str]:
    """Get user's zodiac sign"""
    if _use_postgres:
        conn = _get_pg_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT zodiac_sign FROM users WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
            return row[0] if row else None
        finally:
            conn.close()
    else:
        import aiosqlite
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            cursor = await db.execute("SELECT zodiac_sign FROM users WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            return row[0] if row else None


async def increment_chain(user_id: int) -> int:
    """Increment chain count and return new count"""
    if _use_postgres:
        conn = _get_pg_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE users SET chain_count = chain_count + 1 WHERE user_id = %s RETURNING chain_count",
                (user_id,)
            )
            row = cur.fetchone()
            conn.commit()
            return row[0] if row else 0
        finally:
            conn.close()
    else:
        import aiosqlite
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            await db.execute(
                "UPDATE users SET chain_count = chain_count + 1 WHERE user_id = ?", (user_id,)
            )
            await db.commit()
            cursor = await db.execute("SELECT chain_count FROM users WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            return row[0] if row else 0


# ==================== SEND LIMITS ====================

async def can_send_free(user_id: int) -> bool:
    """Check if user can send free valentine today (respects subscription)"""
    from config import FREE_DAILY_LIMIT, ROMANTIC_DAILY_LIMIT

    sub = await get_active_subscription(user_id)
    if sub and sub['plan'] == 'lovebomb':
        return True

    daily_limit = FREE_DAILY_LIMIT
    if sub and sub['plan'] == 'romantic':
        daily_limit = ROMANTIC_DAILY_LIMIT

    if _use_postgres:
        conn = _get_pg_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT free_sends_today, last_send_date, bonus_valentines FROM users WHERE user_id = %s",
                (user_id,)
            )
            row = _fetchone_dict(cur)
            if not row:
                return True
            today = date.today()
            if row['last_send_date'] != today:
                return True
            if row['bonus_valentines'] > 0:
                return True
            return row['free_sends_today'] < daily_limit
        finally:
            conn.close()
    else:
        import aiosqlite
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT free_sends_today, last_send_date, bonus_valentines FROM users WHERE user_id = ?",
                (user_id,)
            )
            row = await cursor.fetchone()
            if not row:
                return True
            today = date.today().isoformat()
            if row['last_send_date'] != today:
                return True
            if row['bonus_valentines'] > 0:
                return True
            return row['free_sends_today'] < daily_limit


async def use_send_slot(user_id: int) -> bool:
    """Use one send slot (free or bonus). Returns True if successful."""
    today_val = date.today()

    if _use_postgres:
        conn = _get_pg_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT free_sends_today, last_send_date, bonus_valentines FROM users WHERE user_id = %s",
                (user_id,)
            )
            row = _fetchone_dict(cur)
            if row['last_send_date'] != today_val:
                cur.execute(
                    "UPDATE users SET free_sends_today = 1, last_send_date = %s WHERE user_id = %s",
                    (today_val, user_id)
                )
            elif row['bonus_valentines'] > 0:
                cur.execute(
                    "UPDATE users SET bonus_valentines = bonus_valentines - 1 WHERE user_id = %s",
                    (user_id,)
                )
            else:
                cur.execute(
                    "UPDATE users SET free_sends_today = free_sends_today + 1, last_send_date = %s WHERE user_id = %s",
                    (today_val, user_id)
                )
            conn.commit()
            return True
        finally:
            conn.close()
    else:
        import aiosqlite
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT free_sends_today, last_send_date, bonus_valentines FROM users WHERE user_id = ?",
                (user_id,)
            )
            row = await cursor.fetchone()
            today = date.today().isoformat()
            if row['last_send_date'] != today:
                await db.execute(
                    "UPDATE users SET free_sends_today = 1, last_send_date = ? WHERE user_id = ?",
                    (today, user_id)
                )
            elif row['bonus_valentines'] > 0:
                await db.execute(
                    "UPDATE users SET bonus_valentines = bonus_valentines - 1 WHERE user_id = ?",
                    (user_id,)
                )
            else:
                await db.execute(
                    "UPDATE users SET free_sends_today = free_sends_today + 1, last_send_date = ? WHERE user_id = ?",
                    (today, user_id)
                )
            await db.commit()
            return True


async def add_bonus_valentines(user_id: int, count: int = 5):
    """Add bonus valentines to user (from bundle purchase)"""
    if _use_postgres:
        conn = _get_pg_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE users SET bonus_valentines = bonus_valentines + %s WHERE user_id = %s",
                (count, user_id)
            )
            conn.commit()
        finally:
            conn.close()
    else:
        import aiosqlite
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            await db.execute(
                "UPDATE users SET bonus_valentines = bonus_valentines + ? WHERE user_id = ?",
                (count, user_id)
            )
            await db.commit()


# ==================== VALENTINE OPERATIONS ====================

async def create_valentine(sender_id: int, receiver_id: int, message: str,
                          is_premium: bool = False, is_poem: bool = False,
                          voice_file_id: str = None, photo_file_id: str = None,
                          gift_emoji: str = None, music_url: str = None,
                          scheduled_for: str = None) -> int:
    """Create new valentine and return its ID"""
    if _use_postgres:
        conn = _get_pg_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO valentines
                   (sender_id, receiver_id, message, is_premium, is_poem,
                    voice_file_id, photo_file_id, gift_emoji, music_url, scheduled_for)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                (sender_id, receiver_id, message, is_premium, is_poem,
                 voice_file_id, photo_file_id, gift_emoji, music_url, scheduled_for)
            )
            vid = cur.fetchone()[0]
            conn.commit()
            return vid
        finally:
            conn.close()
    else:
        import aiosqlite
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            cursor = await db.execute(
                """INSERT INTO valentines
                   (sender_id, receiver_id, message, is_premium, is_poem,
                    voice_file_id, photo_file_id, gift_emoji, music_url, scheduled_for)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (sender_id, receiver_id, message, is_premium, is_poem,
                 voice_file_id, photo_file_id, gift_emoji, music_url, scheduled_for)
            )
            await db.commit()
            return cursor.lastrowid


async def get_valentine(valentine_id: int) -> Optional[dict]:
    """Get valentine by ID"""
    if _use_postgres:
        conn = _get_pg_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM valentines WHERE id = %s", (valentine_id,))
            return _fetchone_dict(cur)
        finally:
            conn.close()
    else:
        import aiosqlite
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM valentines WHERE id = ?", (valentine_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None


async def mark_delivered(valentine_id: int):
    """Mark valentine as delivered"""
    if _use_postgres:
        conn = _get_pg_conn()
        try:
            cur = conn.cursor()
            cur.execute("UPDATE valentines SET is_delivered = TRUE WHERE id = %s", (valentine_id,))
            conn.commit()
        finally:
            conn.close()
    else:
        import aiosqlite
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            await db.execute("UPDATE valentines SET is_delivered = TRUE WHERE id = ?", (valentine_id,))
            await db.commit()


async def get_inbox(user_id: int, limit: int = 10, offset: int = 0) -> list:
    """Get user's incoming valentines with pagination"""
    if _use_postgres:
        conn = _get_pg_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """SELECT v.*, u.username as sender_username, u.first_name as sender_first_name
                   FROM valentines v
                   LEFT JOIN users u ON v.sender_id = u.user_id
                   WHERE v.receiver_id = %s AND v.is_delivered = TRUE
                   ORDER BY v.created_at DESC
                   LIMIT %s OFFSET %s""",
                (user_id, limit, offset)
            )
            return _fetchall_dict(cur)
        finally:
            conn.close()
    else:
        import aiosqlite
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT v.*, u.username as sender_username, u.first_name as sender_first_name
                   FROM valentines v
                   LEFT JOIN users u ON v.sender_id = u.user_id
                   WHERE v.receiver_id = ? AND v.is_delivered = TRUE
                   ORDER BY v.created_at DESC
                   LIMIT ? OFFSET ?""",
                (user_id, limit, offset)
            )
            return [dict(row) for row in await cursor.fetchall()]


async def get_inbox_count(user_id: int) -> int:
    """Get total count of user's incoming valentines"""
    if _use_postgres:
        conn = _get_pg_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM valentines WHERE receiver_id = %s AND is_delivered = TRUE",
                (user_id,)
            )
            return cur.fetchone()[0]
        finally:
            conn.close()
    else:
        import aiosqlite
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM valentines WHERE receiver_id = ? AND is_delivered = TRUE",
                (user_id,)
            )
            return (await cursor.fetchone())[0]


async def reveal_sender(valentine_id: int) -> bool:
    """Mark valentine sender as revealed"""
    if _use_postgres:
        conn = _get_pg_conn()
        try:
            cur = conn.cursor()
            cur.execute("UPDATE valentines SET is_revealed = TRUE WHERE id = %s", (valentine_id,))
            conn.commit()
            return True
        finally:
            conn.close()
    else:
        import aiosqlite
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            await db.execute("UPDATE valentines SET is_revealed = TRUE WHERE id = ?", (valentine_id,))
            await db.commit()
            return True


async def record_payment(user_id: int, amount: int, payment_type: str,
                        valentine_id: Optional[int] = None,
                        charge_id: Optional[str] = None):
    """Record successful payment"""
    if _use_postgres:
        conn = _get_pg_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO payments
                   (user_id, amount, type, valentine_id, telegram_payment_charge_id)
                   VALUES (%s, %s, %s, %s, %s)""",
                (user_id, amount, payment_type, valentine_id, charge_id)
            )
            conn.commit()
        finally:
            conn.close()
    else:
        import aiosqlite
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            await db.execute(
                """INSERT INTO payments
                   (user_id, amount, type, valentine_id, telegram_payment_charge_id)
                   VALUES (?, ?, ?, ?, ?)""",
                (user_id, amount, payment_type, valentine_id, charge_id)
            )
            await db.commit()


async def get_user_stats(user_id: int) -> dict:
    """Get user statistics"""
    if _use_postgres:
        conn = _get_pg_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM valentines WHERE sender_id = %s", (user_id,))
            sent = cur.fetchone()[0]
            cur.execute(
                "SELECT COUNT(*) FROM valentines WHERE receiver_id = %s AND is_delivered = TRUE",
                (user_id,)
            )
            received = cur.fetchone()[0]
            cur.execute(
                "SELECT COUNT(*) FROM valentines WHERE receiver_id = %s AND is_revealed = TRUE",
                (user_id,)
            )
            revealed = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM achievements WHERE user_id = %s", (user_id,))
            badges = cur.fetchone()[0]
            cur.execute("SELECT chain_count FROM users WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
            chain = row[0] if row else 0
            return {"sent": sent, "received": received, "revealed": revealed, "badges": badges, "chain": chain}
        finally:
            conn.close()
    else:
        import aiosqlite
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM valentines WHERE sender_id = ?", (user_id,))
            sent = (await cursor.fetchone())[0]
            cursor = await db.execute(
                "SELECT COUNT(*) FROM valentines WHERE receiver_id = ? AND is_delivered = TRUE", (user_id,)
            )
            received = (await cursor.fetchone())[0]
            cursor = await db.execute(
                "SELECT COUNT(*) FROM valentines WHERE receiver_id = ? AND is_revealed = TRUE", (user_id,)
            )
            revealed = (await cursor.fetchone())[0]
            cursor = await db.execute("SELECT COUNT(*) FROM achievements WHERE user_id = ?", (user_id,))
            badges = (await cursor.fetchone())[0]
            cursor = await db.execute("SELECT chain_count FROM users WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            chain = row[0] if row else 0
            return {"sent": sent, "received": received, "revealed": revealed, "badges": badges, "chain": chain}


async def find_user_by_username(username: str) -> Optional[dict]:
    """Find user by username"""
    username = username.lstrip('@')
    if _use_postgres:
        conn = _get_pg_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(%s)", (username,))
            return _fetchone_dict(cur)
        finally:
            conn.close()
    else:
        import aiosqlite
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(?)", (username,))
            row = await cursor.fetchone()
            return dict(row) if row else None


async def add_reaction(valentine_id: int, emoji: str):
    """Add reaction to valentine"""
    if _use_postgres:
        conn = _get_pg_conn()
        try:
            cur = conn.cursor()
            cur.execute("UPDATE valentines SET reaction = %s WHERE id = %s", (emoji, valentine_id))
            conn.commit()
        finally:
            conn.close()
    else:
        import aiosqlite
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            await db.execute("UPDATE valentines SET reaction = ? WHERE id = ?", (emoji, valentine_id))
            await db.commit()


# ==================== LEADERBOARD ====================

async def get_top_receivers(limit: int = 10) -> list:
    """Get top valentine receivers"""
    if _use_postgres:
        conn = _get_pg_conn()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT u.first_name, u.username, COUNT(v.id) as count
                FROM users u
                JOIN valentines v ON u.user_id = v.receiver_id
                WHERE v.is_delivered = TRUE
                GROUP BY u.user_id, u.first_name, u.username
                ORDER BY count DESC LIMIT %s
            """, (limit,))
            return _fetchall_dict(cur)
        finally:
            conn.close()
    else:
        import aiosqlite
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT u.first_name, u.username, COUNT(v.id) as count
                FROM users u
                JOIN valentines v ON u.user_id = v.receiver_id
                WHERE v.is_delivered = TRUE
                GROUP BY u.user_id
                ORDER BY count DESC LIMIT ?
            """, (limit,))
            return [dict(row) for row in await cursor.fetchall()]


async def get_top_senders(limit: int = 10) -> list:
    """Get top valentine senders"""
    if _use_postgres:
        conn = _get_pg_conn()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT u.first_name, u.username, COUNT(v.id) as count
                FROM users u
                JOIN valentines v ON u.user_id = v.sender_id
                GROUP BY u.user_id, u.first_name, u.username
                ORDER BY count DESC LIMIT %s
            """, (limit,))
            return _fetchall_dict(cur)
        finally:
            conn.close()
    else:
        import aiosqlite
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT u.first_name, u.username, COUNT(v.id) as count
                FROM users u
                JOIN valentines v ON u.user_id = v.sender_id
                GROUP BY u.user_id
                ORDER BY count DESC LIMIT ?
            """, (limit,))
            return [dict(row) for row in await cursor.fetchall()]


# ==================== ANONYMOUS CHAT ====================

async def create_anon_chat(valentine_id: int) -> str:
    """Create anonymous chat session"""
    chat_id = secrets.token_hex(8)
    if _use_postgres:
        conn = _get_pg_conn()
        try:
            cur = conn.cursor()
            cur.execute("INSERT INTO anon_chats (id, valentine_id) VALUES (%s, %s)", (chat_id, valentine_id))
            conn.commit()
        finally:
            conn.close()
    else:
        import aiosqlite
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            await db.execute("INSERT INTO anon_chats (id, valentine_id) VALUES (?, ?)", (chat_id, valentine_id))
            await db.commit()
    return chat_id


async def get_anon_chat(chat_id: str) -> Optional[dict]:
    """Get anon chat by ID"""
    if _use_postgres:
        conn = _get_pg_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM anon_chats WHERE id = %s", (chat_id,))
            return _fetchone_dict(cur)
        finally:
            conn.close()
    else:
        import aiosqlite
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM anon_chats WHERE id = ?", (chat_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None


async def save_anon_message(chat_id: str, from_sender: bool, text: str):
    """Save message in anon chat"""
    if _use_postgres:
        conn = _get_pg_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO anon_messages (chat_id, from_sender, text) VALUES (%s, %s, %s)",
                (chat_id, from_sender, text)
            )
            conn.commit()
        finally:
            conn.close()
    else:
        import aiosqlite
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            await db.execute(
                "INSERT INTO anon_messages (chat_id, from_sender, text) VALUES (?, ?, ?)",
                (chat_id, from_sender, text)
            )
            await db.commit()


# ==================== ROULETTE ====================

async def add_to_roulette(user_id: int, message: str) -> int:
    """Add user to roulette queue, return queue ID"""
    if _use_postgres:
        conn = _get_pg_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO roulette_queue (user_id, message) VALUES (%s, %s) RETURNING id",
                (user_id, message)
            )
            qid = cur.fetchone()[0]
            conn.commit()
            return qid
        finally:
            conn.close()
    else:
        import aiosqlite
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            cursor = await db.execute(
                "INSERT INTO roulette_queue (user_id, message) VALUES (?, ?)",
                (user_id, message)
            )
            await db.commit()
            return cursor.lastrowid


async def find_roulette_match(user_id: int) -> Optional[dict]:
    """Find a match in roulette queue (different user)"""
    if _use_postgres:
        conn = _get_pg_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """SELECT * FROM roulette_queue
                   WHERE user_id != %s AND matched = FALSE
                   ORDER BY created_at ASC LIMIT 1""",
                (user_id,)
            )
            return _fetchone_dict(cur)
        finally:
            conn.close()
    else:
        import aiosqlite
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT * FROM roulette_queue
                   WHERE user_id != ? AND matched = FALSE
                   ORDER BY created_at ASC LIMIT 1""",
                (user_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None


async def mark_roulette_matched(queue_id: int):
    """Mark roulette entry as matched"""
    if _use_postgres:
        conn = _get_pg_conn()
        try:
            cur = conn.cursor()
            cur.execute("UPDATE roulette_queue SET matched = TRUE WHERE id = %s", (queue_id,))
            conn.commit()
        finally:
            conn.close()
    else:
        import aiosqlite
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            await db.execute("UPDATE roulette_queue SET matched = TRUE WHERE id = ?", (queue_id,))
            await db.commit()


# ==================== COMPATIBILITY ====================

async def create_compat_test(initiator_id: int) -> str:
    """Create compatibility test and return test ID"""
    test_id = secrets.token_hex(6)
    if _use_postgres:
        conn = _get_pg_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO compatibility_tests (id, initiator_id) VALUES (%s, %s)",
                (test_id, initiator_id)
            )
            conn.commit()
        finally:
            conn.close()
    else:
        import aiosqlite
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            await db.execute(
                "INSERT INTO compatibility_tests (id, initiator_id) VALUES (?, ?)",
                (test_id, initiator_id)
            )
            await db.commit()
    return test_id


async def get_compat_test(test_id: str) -> Optional[dict]:
    """Get compatibility test by ID"""
    if _use_postgres:
        conn = _get_pg_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM compatibility_tests WHERE id = %s", (test_id,))
            return _fetchone_dict(cur)
        finally:
            conn.close()
    else:
        import aiosqlite
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM compatibility_tests WHERE id = ?", (test_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None


async def save_compat_answers(test_id: str, user_id: int, answers: list):
    """Save user's answers for compatibility test"""
    answers_json = json.dumps(answers)
    test = await get_compat_test(test_id)
    if not test:
        return

    if _use_postgres:
        conn = _get_pg_conn()
        try:
            cur = conn.cursor()
            if test['initiator_id'] == user_id:
                cur.execute(
                    "UPDATE compatibility_tests SET initiator_answers = %s WHERE id = %s",
                    (answers_json, test_id)
                )
            else:
                cur.execute(
                    "UPDATE compatibility_tests SET partner_id = %s, partner_answers = %s WHERE id = %s",
                    (user_id, answers_json, test_id)
                )
            conn.commit()
        finally:
            conn.close()
    else:
        import aiosqlite
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            if test['initiator_id'] == user_id:
                await db.execute(
                    "UPDATE compatibility_tests SET initiator_answers = ? WHERE id = ?",
                    (answers_json, test_id)
                )
            else:
                await db.execute(
                    "UPDATE compatibility_tests SET partner_id = ?, partner_answers = ? WHERE id = ?",
                    (user_id, answers_json, test_id)
                )
            await db.commit()


async def set_compat_result(test_id: str, percent: int):
    """Set compatibility test result"""
    if _use_postgres:
        conn = _get_pg_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE compatibility_tests SET result_percent = %s WHERE id = %s",
                (percent, test_id)
            )
            conn.commit()
        finally:
            conn.close()
    else:
        import aiosqlite
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            await db.execute(
                "UPDATE compatibility_tests SET result_percent = ? WHERE id = ?",
                (percent, test_id)
            )
            await db.commit()


async def mark_compat_paid(test_id: str):
    """Mark compatibility test as paid"""
    if _use_postgres:
        conn = _get_pg_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE compatibility_tests SET is_paid = TRUE WHERE id = %s",
                (test_id,)
            )
            conn.commit()
        finally:
            conn.close()
    else:
        import aiosqlite
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            await db.execute(
                "UPDATE compatibility_tests SET is_paid = TRUE WHERE id = ?",
                (test_id,)
            )
            await db.commit()


# ==================== ACHIEVEMENTS ====================

async def grant_achievement(user_id: int, badge: str) -> bool:
    """Grant achievement to user. Returns True if new."""
    if _use_postgres:
        conn = _get_pg_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO achievements (user_id, badge) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (user_id, badge)
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()
    else:
        import aiosqlite
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            try:
                await db.execute(
                    "INSERT INTO achievements (user_id, badge) VALUES (?, ?)",
                    (user_id, badge)
                )
                await db.commit()
                return True
            except aiosqlite.IntegrityError:
                return False


async def get_user_achievements(user_id: int) -> list:
    """Get all user achievements"""
    if _use_postgres:
        conn = _get_pg_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM achievements WHERE user_id = %s ORDER BY earned_at DESC",
                (user_id,)
            )
            return _fetchall_dict(cur)
        finally:
            conn.close()
    else:
        import aiosqlite
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM achievements WHERE user_id = ? ORDER BY earned_at DESC",
                (user_id,)
            )
            return [dict(row) for row in await cursor.fetchall()]


# ==================== SCHEDULED VALENTINES ====================

async def get_pending_scheduled() -> list:
    """Get valentines scheduled for delivery now"""
    if _use_postgres:
        conn = _get_pg_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """SELECT * FROM valentines
                   WHERE scheduled_for IS NOT NULL
                   AND scheduled_for <= NOW()
                   AND is_scheduled_sent = FALSE
                   AND is_delivered = FALSE"""
            )
            return _fetchall_dict(cur)
        finally:
            conn.close()
    else:
        import aiosqlite
        now = datetime.now().isoformat()
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT * FROM valentines
                   WHERE scheduled_for IS NOT NULL
                   AND scheduled_for <= ?
                   AND is_scheduled_sent = FALSE
                   AND is_delivered = FALSE""",
                (now,)
            )
            return [dict(row) for row in await cursor.fetchall()]


async def mark_scheduled_sent(valentine_id: int):
    """Mark scheduled valentine as sent"""
    if _use_postgres:
        conn = _get_pg_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE valentines SET is_scheduled_sent = TRUE, is_delivered = TRUE WHERE id = %s",
                (valentine_id,)
            )
            conn.commit()
        finally:
            conn.close()
    else:
        import aiosqlite
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            await db.execute(
                "UPDATE valentines SET is_scheduled_sent = TRUE, is_delivered = TRUE WHERE id = ?",
                (valentine_id,)
            )
            await db.commit()


# ==================== SUBSCRIPTIONS ====================

async def create_subscription(user_id: int, plan: str, days: int,
                               charge_id: Optional[str] = None):
    """Create or extend active subscription for user"""
    expires_at = (datetime.now() + timedelta(days=days)).isoformat()

    if _use_postgres:
        conn = _get_pg_conn()
        try:
            cur = conn.cursor()
            cur.execute("UPDATE subscriptions SET is_active = FALSE WHERE user_id = %s", (user_id,))
            cur.execute(
                """INSERT INTO subscriptions (user_id, plan, expires_at, telegram_payment_charge_id)
                   VALUES (%s, %s, %s, %s)""",
                (user_id, plan, expires_at, charge_id)
            )
            conn.commit()
        finally:
            conn.close()
    else:
        import aiosqlite
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            await db.execute("UPDATE subscriptions SET is_active = FALSE WHERE user_id = ?", (user_id,))
            await db.execute(
                """INSERT INTO subscriptions (user_id, plan, expires_at, telegram_payment_charge_id)
                   VALUES (?, ?, ?, ?)""",
                (user_id, plan, expires_at, charge_id)
            )
            await db.commit()


async def get_active_subscription(user_id: int) -> Optional[dict]:
    """Get user's active non-expired subscription"""
    if _use_postgres:
        conn = _get_pg_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """SELECT * FROM subscriptions
                   WHERE user_id = %s AND is_active = TRUE AND expires_at > NOW()
                   ORDER BY expires_at DESC LIMIT 1""",
                (user_id,)
            )
            return _fetchone_dict(cur)
        finally:
            conn.close()
    else:
        import aiosqlite
        now = datetime.now().isoformat()
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT * FROM subscriptions
                   WHERE user_id = ? AND is_active = TRUE AND expires_at > ?
                   ORDER BY expires_at DESC LIMIT 1""",
                (user_id, now)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None


async def has_premium(user_id: int) -> bool:
    """Check if user has any active subscription"""
    sub = await get_active_subscription(user_id)
    return sub is not None


# ==================== ROULETTE DAILY LIMIT ====================

async def can_use_roulette_free(user_id: int) -> bool:
    """Check if user has free roulette match today"""
    from config import ROULETTE_FREE_DAILY

    sub = await get_active_subscription(user_id)
    if sub:
        return True

    if _use_postgres:
        conn = _get_pg_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT roulette_uses_today, last_roulette_date, roulette_free_until FROM users WHERE user_id = %s",
                (user_id,)
            )
            row = _fetchone_dict(cur)
            if not row:
                return True
            if row['roulette_free_until']:
                if row['roulette_free_until'] > datetime.now():
                    return True
            today = date.today()
            if row['last_roulette_date'] != today:
                return True
            return (row['roulette_uses_today'] or 0) < ROULETTE_FREE_DAILY
        finally:
            conn.close()
    else:
        import aiosqlite
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT roulette_uses_today, last_roulette_date, roulette_free_until FROM users WHERE user_id = ?",
                (user_id,)
            )
            row = await cursor.fetchone()
            if not row:
                return True
            if row['roulette_free_until']:
                now = datetime.now().isoformat()
                if row['roulette_free_until'] > now:
                    return True
            today = date.today().isoformat()
            if row['last_roulette_date'] != today:
                return True
            return (row['roulette_uses_today'] or 0) < ROULETTE_FREE_DAILY


async def use_roulette_slot(user_id: int):
    """Record roulette usage for today"""
    today_val = date.today()

    if _use_postgres:
        conn = _get_pg_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT last_roulette_date FROM users WHERE user_id = %s", (user_id,))
            row = _fetchone_dict(cur)
            if row and row['last_roulette_date'] == today_val:
                cur.execute(
                    "UPDATE users SET roulette_uses_today = roulette_uses_today + 1 WHERE user_id = %s",
                    (user_id,)
                )
            else:
                cur.execute(
                    "UPDATE users SET roulette_uses_today = 1, last_roulette_date = %s WHERE user_id = %s",
                    (today_val, user_id)
                )
            conn.commit()
        finally:
            conn.close()
    else:
        import aiosqlite
        today = date.today().isoformat()
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT last_roulette_date FROM users WHERE user_id = ?", (user_id,)
            )
            row = await cursor.fetchone()
            if row and row['last_roulette_date'] == today:
                await db.execute(
                    "UPDATE users SET roulette_uses_today = roulette_uses_today + 1 WHERE user_id = ?",
                    (user_id,)
                )
            else:
                await db.execute(
                    "UPDATE users SET roulette_uses_today = 1, last_roulette_date = ? WHERE user_id = ?",
                    (today, user_id)
                )
            await db.commit()


async def activate_weekly_bundle(user_id: int):
    """Activate weekly bundle: +20 bonus valentines + 7 days free roulette"""
    roulette_free_until = (datetime.now() + timedelta(days=7)).isoformat()

    if _use_postgres:
        conn = _get_pg_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE users SET bonus_valentines = bonus_valentines + 20, roulette_free_until = %s WHERE user_id = %s",
                (roulette_free_until, user_id)
            )
            conn.commit()
        finally:
            conn.close()
    else:
        import aiosqlite
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            await db.execute(
                "UPDATE users SET bonus_valentines = bonus_valentines + 20, roulette_free_until = ? WHERE user_id = ?",
                (roulette_free_until, user_id)
            )
            await db.commit()
