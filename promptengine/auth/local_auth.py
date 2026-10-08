"""
PromptEngine Local Auth — SQLite embedded authentication.

Replaces the FastAPI/PostgreSQL server dependency for user management.
All data stored locally in ~/.promptengine/data.db

Security:
- PBKDF2-HMAC-SHA256 with 600,000 iterations (matches server standard)
- TOTP 2FA via pyotp (same algorithm as server)
- Passwords minimum 8 chars, checked for complexity
"""

import os
import sqlite3
import hashlib
import secrets
import logging
from typing import Optional, Tuple
from datetime import datetime

import pyotp

from promptengine.ui.ansi_colors import C

logger = logging.getLogger("promptengine.auth")

# ── Constants ─────────────────────────────────────────────────────────────────

PBKDF2_ITERATIONS = 600_000
PBKDF2_ALGORITHM = "sha256"
DB_DIR = os.path.expanduser("~/.promptengine")
DB_PATH = os.path.join(DB_DIR, "data.db")


# ── Database Setup ────────────────────────────────────────────────────────────

def _get_conn() -> sqlite3.Connection:
    """Returns a SQLite connection with WAL mode for better concurrency."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Creates the database schema if it doesn't exist."""
    with _get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                email         TEXT UNIQUE NOT NULL COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                salt          TEXT NOT NULL,
                totp_secret   TEXT,
                totp_verified INTEGER DEFAULT 0,
                created_at    TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS history (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                email      TEXT NOT NULL COLLATE NOCASE,
                ai_name    TEXT,
                tone_name  TEXT,
                user_text  TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_history_email ON history(email);
        """)
    logger.debug("SQLite DB initialized at %s", DB_PATH)


# ── Password Utilities ────────────────────────────────────────────────────────

def _generate_salt() -> str:
    return secrets.token_hex(32)


def _hash_password(password: str, salt: str) -> str:
    dk = hashlib.pbkdf2_hmac(
        PBKDF2_ALGORITHM,
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    )
    return dk.hex()


def check_password_complexity(password: str) -> Tuple[bool, str]:
    """Returns (is_valid, error_message)."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter."
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit."
    return True, ""


# ── User Operations ───────────────────────────────────────────────────────────

def user_exists(email: str) -> bool:
    """Returns True if the email is already registered."""
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM users WHERE email = ?", (email.lower(),)
        ).fetchone()
        return row is not None


def register_user(email: str, password: str) -> Tuple[bool, str, Optional[str]]:
    """
    Registers a new user. Does NOT verify TOTP yet.

    Returns:
        (success, error_message, totp_secret)
        If success=True, totp_secret is the TOTP secret to show the user.
        If success=False, error_message contains the reason.
    """
    init_db()
    email = email.strip().lower()

    if user_exists(email):
        return False, f'Email "{email}" is already registered.', None

    valid, err = check_password_complexity(password)
    if not valid:
        return False, err, None

    salt = _generate_salt()
    pw_hash = _hash_password(password, salt)
    totp_secret = pyotp.random_base32()

    try:
        with _get_conn() as conn:
            conn.execute(
                "INSERT INTO users (email, password_hash, salt, totp_secret, totp_verified) "
                "VALUES (?, ?, ?, ?, 0)",
                (email, pw_hash, salt, totp_secret),
            )
        logger.info("User registered (pending 2FA): %s", email)
        return True, "", totp_secret
    except sqlite3.IntegrityError:
        return False, f'Email "{email}" is already registered.', None


def verify_totp_and_activate(email: str, totp_token: str) -> Tuple[bool, str]:
    """
    Verifies the TOTP token and marks the user as 2FA-verified.
    Must be called after register_user().

    Returns:
        (success, error_message)
    """
    email = email.strip().lower()
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT totp_secret FROM users WHERE email = ?", (email,)
        ).fetchone()

    if not row:
        return False, "User not found."

    totp = pyotp.TOTP(row["totp_secret"])
    if not totp.verify(totp_token, valid_window=1):
        return False, "Invalid TOTP code. Please check your authenticator app."

    with _get_conn() as conn:
        conn.execute(
            "UPDATE users SET totp_verified = 1 WHERE email = ?", (email,)
        )
    logger.info("User 2FA verified and activated: %s", email)
    return True, ""


def login_user(email: str, password: str, totp_token: str) -> Tuple[bool, str]:
    """
    Authenticates a user with email + password + TOTP.

    Returns:
        (success, error_message)
    """
    init_db()
    email = email.strip().lower()

    with _get_conn() as conn:
        row = conn.execute(
            "SELECT password_hash, salt, totp_secret, totp_verified "
            "FROM users WHERE email = ?",
            (email,),
        ).fetchone()

    # Anti-enumeration: same message for wrong email or wrong password
    GENERIC_ERROR = "Invalid credentials or TOTP code."

    if not row:
        logger.warning("Login attempt for unknown email: %s", email)
        return False, GENERIC_ERROR

    if not row["totp_verified"]:
        return False, "Account 2FA not yet verified. Please complete registration."

    pw_hash = _hash_password(password, row["salt"])
    if not secrets.compare_digest(pw_hash, row["password_hash"]):
        logger.warning("Failed login attempt (wrong password) for: %s", email)
        return False, GENERIC_ERROR

    totp = pyotp.TOTP(row["totp_secret"])
    if not totp.verify(totp_token, valid_window=1):
        logger.warning("Failed login attempt (wrong TOTP) for: %s", email)
        return False, GENERIC_ERROR

    logger.info("Successful login: %s", email)
    return True, ""


# ── History Operations ────────────────────────────────────────────────────────

def save_history(email: str, ai_name: str, tone_name: str, user_text: str) -> None:
    """Saves a prompt generation event to the local history."""
    init_db()
    try:
        with _get_conn() as conn:
            conn.execute(
                "INSERT INTO history (email, ai_name, tone_name, user_text) "
                "VALUES (?, ?, ?, ?)",
                (email.lower(), ai_name, tone_name, user_text[:500]),
            )
    except Exception as e:
        logger.warning("Could not save history: %s", e)


def load_history(email: str, limit: int = 10) -> list:
    """Loads the last N history entries for the given user."""
    init_db()
    try:
        with _get_conn() as conn:
            rows = conn.execute(
                "SELECT ai_name, tone_name, user_text, created_at "
                "FROM history WHERE email = ? ORDER BY id DESC LIMIT ?",
                (email.lower(), limit),
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []

def wipe_database() -> bool:
    """Completely deletes the SQLite database file."""
    try:
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
            logger.info("SQLite database wiped: %s", DB_PATH)
        return True
    except OSError as e:
        logger.warning("Could not wipe database: %s", e)
        return False
