# routes/auth.py — Login, Logout, Register Officer, Access Decorators
from flask import (Blueprint, render_template, request,
                   redirect, url_for, session, flash)
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from db import get_db

auth_bp = Blueprint('auth', __name__)


# ─────────────────────────────────────────────
#  Access-control decorators
# ─────────────────────────────────────────────

def login_required(f):
    """Redirect to login if no active session."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Allow only admin role; redirect others."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────────
#  Login / Logout
# ─────────────────────────────────────────────

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # If already logged in, skip to dashboard
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('officer.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('Both fields are required.', 'danger')
            return render_template('login.html')

        conn   = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM Users WHERE username = %s AND is_active = 1",
            (username,)
        )
        user = cursor.fetchone()

        if user and check_password_hash(user['password_hash'], password):
            session.permanent = True
            session['user_id']  = user['user_id']
            session['username'] = user['username']
            session['role']     = user['role']

            # Fetch officer_id if applicable
            if user['role'] == 'officer':
                cursor.execute(
                    "SELECT officer_id, full_name FROM Officers WHERE user_id = %s",
                    (user['user_id'],)
                )
                officer = cursor.fetchone()
                if officer:
                    session['officer_id']   = officer['officer_id']
                    session['officer_name'] = officer['full_name']

            # Update last_login timestamp
            cursor.execute(
                "UPDATE Users SET last_login = NOW() WHERE user_id = %s",
                (user['user_id'],)
            )
            conn.commit()

            flash(f"Welcome back, {username}!", 'success')
            if user['role'] == 'admin':
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('officer.dashboard'))
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))


# ─────────────────────────────────────────────
#  Register Officer (Admin only)
# ─────────────────────────────────────────────

@auth_bp.route('/register-officer', methods=['GET', 'POST'])
@login_required
@admin_required
def register_officer():
    if request.method == 'POST':
        form = request.form
        username     = form.get('username', '').strip()
        email        = form.get('email', '').strip()
        password     = form.get('password', '')
        badge_number = form.get('badge_number', '').strip()
        full_name    = form.get('full_name', '').strip()
        department   = form.get('department', '').strip()
        phone        = form.get('phone', '').strip()
        precinct     = form.get('precinct', '').strip()
        role         = form.get('role', 'officer')

        # Basic validation
        if role == 'officer':
            if not all([username, email, password, badge_number, full_name]):
                flash('All starred fields are required.', 'danger')
                return render_template('admin/register_officer.html')
        else:
            if not all([username, email, password, full_name]):
                flash('Username, email, password and full name are required.', 'danger')
                return render_template('admin/register_officer.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return render_template('admin/register_officer.html')

        conn   = get_db()
        cursor = conn.cursor(dictionary=True)

        # Check duplicates
        cursor.execute(
            "SELECT user_id FROM Users WHERE username = %s OR email = %s",
            (username, email)
        )
        if cursor.fetchone():
            flash('Username or email already exists.', 'danger')
            return render_template('admin/register_officer.html')

        cursor.execute(
            "SELECT officer_id FROM Officers WHERE badge_number = %s",
            (badge_number,)
        )
        if cursor.fetchone():
            flash('Badge number already registered.', 'danger')
            return render_template('admin/register_officer.html')

        # Insert User
        password_hash = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO Users (username, password_hash, role, email) VALUES (%s,%s,%s,%s)",
            (username, password_hash, role, email)
        )
        user_id = cursor.lastrowid

        # Insert Officer
        if role == 'officer': 
            cursor.execute(
                """INSERT INTO Officers (user_id, badge_number, full_name, department, phone, precinct)
                VALUES (%s, %s, %s, %s, %s, %s)""",
                (user_id, badge_number, full_name, department, phone, precinct)
            )
        conn.commit()
        flash(f"Officer '{full_name}' registered successfully!", 'success')
        return redirect(url_for('admin.officers'))

    return render_template('admin/register_officer.html')
