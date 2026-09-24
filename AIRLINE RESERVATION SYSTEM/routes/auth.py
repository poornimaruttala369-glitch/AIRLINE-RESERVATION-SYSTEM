"""
Authentication Blueprint (Routes)
---------------------------------
Handles Registration, Login, Logout, and Session Management.
Academic Context:
- Security: Cryptographic password hashing, SQL injection prevention via parameterization.
- Role-based redirection (Passenger vs Admin).
"""
import re
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database.db import get_db_cursor
from models.user import User

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Passenger account registration."""
    # If user is already logged in, redirect home
    if 'user_id' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Server-side validation
        if not name or not email or not phone or not password:
            flash("All fields are required.", "danger")
            return render_template('register.html', name=name, email=email, phone=phone)

        # Basic email format check
        email_regex = r"^[^@]+@[^@]+\.[^@]+$"
        if not re.match(email_regex, email):
            flash("Please enter a valid email address.", "danger")
            return render_template('register.html', name=name, email=email, phone=phone)

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template('register.html', name=name, email=email, phone=phone)

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template('register.html', name=name, email=email, phone=phone)

        # Check for existing email in database
        try:
            with get_db_cursor(commit=True) as cur:
                cur.execute("SELECT user_id FROM users WHERE email = %s", (email,))
                if cur.fetchone():
                    flash("An account with this email address already exists. Please log in.", "warning")
                    return redirect(url_for('auth.login'))

                # Hash password securely
                hashed = User.hash_password(password)

                # Insert new passenger
                cur.execute("""
                    INSERT INTO users (name, email, phone, password_hash, role)
                    VALUES (%s, %s, %s, %s, 'PASSENGER')
                """, (name, email, phone, hashed))

            flash("Registration successful! Please log in with your credentials.", "success")
            return redirect(url_for('auth.login'))

        except Exception as e:
            flash("An error occurred during registration. Please try again.", "danger")
            print(f"[AUTH ERROR] Registration failed: {e}")
            return render_template('register.html', name=name, email=email, phone=phone)

    return render_template('register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User and Administrator authentication."""
    if 'user_id' in session:
        if session.get('user_role') == 'ADMIN':
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('booking.my_bookings'))

    next_url = request.args.get('next')

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash("Please provide both email and password.", "danger")
            return render_template('login.html', email=email, next=next_url)

        try:
            with get_db_cursor() as cur:
                cur.execute("SELECT * FROM users WHERE email = %s", (email,))
                user_record = cur.fetchone()

            if user_record and User.verify_password(user_record['password_hash'], password):
                # Establish session
                session['user_id'] = user_record['user_id']
                session['user_name'] = user_record['name']
                session['user_email'] = user_record['email']
                session['user_role'] = user_record['role']

                flash(f"Welcome back, {user_record['name']}!", "success")

                # Role-based redirection
                if user_record['role'] == 'ADMIN':
                    return redirect(next_url or url_for('admin.dashboard'))
                else:
                    return redirect(next_url or url_for('flights.search'))
            else:
                flash("Invalid email or password. Please try again.", "danger")

        except Exception as e:
            flash("An error occurred during login. Please try again later.", "danger")
            print(f"[AUTH ERROR] Login failed: {e}")

    return render_template('login.html', next=next_url)


@auth_bp.route('/logout')
def logout():
    """Clears user session and logs out."""
    session.clear()
    flash("You have been successfully logged out. Have a great day!", "info")
    return redirect(url_for('index'))
