"""
auth.py — Authentication & Wishlist persistence for MHT-CET College Finder.

Uses the same SQLite database as college data. Provides:
- User registration with hashed passwords
- User authentication
- Server-side wishlist CRUD
"""

import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask import session, redirect, url_for, jsonify

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(PROJECT_DIR, 'college_data.db')


# ─── Database Setup ──────────────────────────────────────

def get_db():
    """Get a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_auth_tables():
    """Create users and wishlists tables if they don't exist."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wishlists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            college_name TEXT NOT NULL,
            branch_group TEXT,
            category TEXT,
            city TEXT,
            tier TEXT,
            probability_pct REAL,
            cutoff_score REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(user_id, college_name, branch_group, category)
        )
    ''')

    conn.commit()
    conn.close()


# ─── User Operations ────────────────────────────────────

def register_user(name, email, password):
    """
    Register a new user. Returns (success: bool, message: str, user_id: int|None).
    """
    if not name or not email or not password:
        return False, 'All fields are required', None

    if len(password) < 6:
        return False, 'Password must be at least 6 characters', None

    conn = get_db()
    try:
        cursor = conn.cursor()
        password_hash = generate_password_hash(password, method='pbkdf2:sha256')
        cursor.execute(
            'INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)',
            (name.strip(), email.strip().lower(), password_hash)
        )
        conn.commit()
        return True, 'Account created successfully', cursor.lastrowid
    except sqlite3.IntegrityError:
        return False, 'Email already registered', None
    finally:
        conn.close()


def authenticate_user(email, password):
    """
    Authenticate user. Returns (success: bool, message: str, user: dict|None).
    """
    if not email or not password:
        return False, 'Email and password are required', None

    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE email = ?', (email.strip().lower(),))
        row = cursor.fetchone()

        if row is None:
            return False, 'No account found with that email', None

        if not check_password_hash(row['password_hash'], password):
            return False, 'Incorrect password', None

        user = {
            'id': row['id'],
            'name': row['name'],
            'email': row['email']
        }
        return True, 'Login successful', user
    finally:
        conn.close()


def get_user_by_id(user_id):
    """Fetch user details by ID."""
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, email FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        if row:
            return {'id': row['id'], 'name': row['name'], 'email': row['email']}
        return None
    finally:
        conn.close()


# ─── Login Required Decorator ───────────────────────────

def login_required(f):
    """Decorator to require login for routes."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated


def api_login_required(f):
    """Decorator for API routes — returns JSON 401 instead of redirect."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated


# ─── Wishlist Operations ────────────────────────────────

def add_to_wishlist(user_id, data):
    """Add a college to user's wishlist."""
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO wishlists
            (user_id, college_name, branch_group, category, city, tier, probability_pct, cutoff_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            data.get('college_name', ''),
            data.get('branch_group', ''),
            data.get('category', ''),
            data.get('city', ''),
            data.get('tier', ''),
            data.get('probability_pct'),
            data.get('cutoff_score')
        ))
        conn.commit()
        return cursor.lastrowid > 0
    finally:
        conn.close()


def get_user_wishlist(user_id):
    """Get all wishlist items for a user."""
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM wishlists WHERE user_id = ? ORDER BY created_at DESC',
            (user_id,)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def remove_from_wishlist(user_id, wishlist_id):
    """Remove a wishlist item (only if it belongs to the user)."""
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            'DELETE FROM wishlists WHERE id = ? AND user_id = ?',
            (wishlist_id, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def clear_user_wishlist(user_id):
    """Remove all wishlist items for a user."""
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM wishlists WHERE user_id = ?', (user_id,))
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()
