"""Fresh flow validation file (safe to delete)."""
import subprocess
import sqlite3


def get_user(username: str):
    """Fetch a user record by raw SQL string concatenation."""
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE name = '" + username + "'")
    row = cursor.fetchone()
    return row


def cleanup(path):
    os.remove(path)


import os
