"""
Authentication System
Simple session-based login/register with SQLite user storage.
Passwords hashed with hashlib (no extra deps needed).
"""

import hashlib
import secrets
import logging
from functools import wraps
from flask import Blueprint, request, jsonify, session, redirect, url_for, render_template
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)
db = DatabaseManager()


def _hash_password(password: str, salt: str = None) -> tuple:
    if not salt:
        salt = secrets.token_hex(16)
    hashed = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return hashed, salt


def login_required(f):
    """Decorator — redirects to login if not authenticated"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': 'Authentication required', 'redirect': '/login'}), 401
            return redirect(url_for('auth.login_page'))
        return f(*args, **kwargs)
    return decorated


def optional_auth(f):
    """Decorator — passes through whether logged in or not"""
    @wraps(f)
    def decorated(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated


# ─── Pages ───────────────────────────────────────────────────────────────────

@auth_bp.route('/login')
def login_page():
    if session.get('user_id'):
        return redirect(url_for('main.dashboard'))
    return render_template('login.html', page='login')


@auth_bp.route('/register')
def register_page():
    if session.get('user_id'):
        return redirect(url_for('main.dashboard'))
    return render_template('login.html', page='register')


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login_page'))


# ─── API ─────────────────────────────────────────────────────────────────────

@auth_bp.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    email    = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not all([username, email, password]):
        return jsonify({'success': False, 'error': 'All fields are required'}), 400
    if len(password) < 6:
        return jsonify({'success': False, 'error': 'Password must be at least 6 characters'}), 400

    with db.get_connection() as conn:
        # Check duplicate
        existing = conn.execute(
            'SELECT id FROM users WHERE username=? OR email=?', (username, email)
        ).fetchone()
        if existing:
            return jsonify({'success': False, 'error': 'Username or email already exists'}), 400

        hashed, salt = _hash_password(password)
        conn.execute(
            'INSERT INTO users (username, email, password_hash, salt) VALUES (?,?,?,?)',
            (username, email, hashed, salt)
        )
        user_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]

    session['user_id']  = user_id
    session['username'] = username
    session['email']    = email
    logger.info(f"New user registered: {username}")
    return jsonify({'success': True, 'username': username})


@auth_bp.route('/api/auth/login', methods=['POST'])
def login():
    data     = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')

    with db.get_connection() as conn:
        row = conn.execute(
            'SELECT id, username, email, password_hash, salt FROM users WHERE username=? OR email=?',
            (username, username)
        ).fetchone()

    if not row:
        return jsonify({'success': False, 'error': 'User not found'}), 401

    hashed, _ = _hash_password(password, row['salt'])
    if hashed != row['password_hash']:
        return jsonify({'success': False, 'error': 'Incorrect password'}), 401

    session['user_id']  = row['id']
    session['username'] = row['username']
    session['email']    = row['email']
    logger.info(f"User logged in: {row['username']}")
    return jsonify({'success': True, 'username': row['username']})


@auth_bp.route('/api/auth/me')
def me():
    if session.get('user_id'):
        return jsonify({
            'logged_in': True,
            'user_id':   session['user_id'],
            'username':  session['username'],
            'email':     session['email'],
        })
    return jsonify({'logged_in': False})


@auth_bp.route('/api/auth/demo-login', methods=['POST'])
def demo_login():
    """One-click demo login for examiners"""
    session['user_id']  = 0
    session['username'] = 'Demo User'
    session['email']    = 'demo@weatheriq.ai'
    return jsonify({'success': True, 'username': 'Demo User'})
