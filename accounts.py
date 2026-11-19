"""Local accounts for the desktop planner."""
import hashlib
import hmac
import os
from pathlib import Path
import re
import sqlite3
from contextlib import closing

DB = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "LithuaniaFlightPlanner" / "accounts.db"
PASSWORD_HASH_ITERATIONS = 600_000
PASSWORD_SALT_BYTES = 16
MIN_USERNAME_LENGTH, MAX_USERNAME_LENGTH = 3, 32
MIN_PASSWORD_LENGTH, MAX_PASSWORD_LENGTH = 8, 256


def derive_password_hash(password, salt, iterations):
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)


def register_or_verify_local_account(username, password, register=False, path=DB):
    username = username.strip()
    if register and not re.fullmatch(rf"[A-Za-z0-9_.-]{{{MIN_USERNAME_LENGTH},{MAX_USERNAME_LENGTH}}}", username):
        raise ValueError(f"Use {MIN_USERNAME_LENGTH} to {MAX_USERNAME_LENGTH} letters, numbers, dots, underscores or hyphens.")
    if len(password) > MAX_PASSWORD_LENGTH or (register and len(password) < MIN_PASSWORD_LENGTH):
        raise ValueError(f"Use a password with {MIN_PASSWORD_LENGTH} to {MAX_PASSWORD_LENGTH} characters.")
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("""CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY COLLATE NOCASE, salt BLOB NOT NULL,
            password_hash BLOB NOT NULL, iterations INTEGER NOT NULL)""")
        if register:
            salt = os.urandom(PASSWORD_SALT_BYTES)
            try:
                db.execute("INSERT INTO users VALUES (?, ?, ?, ?)",
                           (username, salt, derive_password_hash(password, salt, PASSWORD_HASH_ITERATIONS), PASSWORD_HASH_ITERATIONS))
            except sqlite3.IntegrityError as error:
                raise ValueError("That username is already taken.") from error
            return username
        row = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if row and hmac.compare_digest(row[2], derive_password_hash(password, row[1], row[3])):
            return row[0]
        raise ValueError("Incorrect username or password.")
