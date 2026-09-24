"""
Authentication & Authorization Decorators
-----------------------------------------
Academic Context:
- Security: Role-Based Access Control (RBAC)
- Python: Higher-order functions & Decorators (@wraps)
"""
from functools import wraps
from flask import session, redirect, url_for, flash, request, g, abort
from database.db import get_db_cursor
from models.user import User, Passenger, Admin


def get_current_user():
    """
    Retrieves the currently logged-in user object from session.
    Returns an instance of Admin or Passenger (OOPJ Polymorphism), or None.
    """
    user_id = session.get('user_id')
    if not user_id:
        return None

    try:
        with get_db_cursor() as cur:
            cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
            if row:
                if row['role'] == 'ADMIN':
                    return Admin(
                        user_id=row['user_id'],
                        name=row['name'],
                        email=row['email'],
                        phone=row['phone'],
                        created_at=row.get('created_at')
                    )
                else:
                    return Passenger(
                        user_id=row['user_id'],
                        name=row['name'],
                        email=row['email'],
                        phone=row['phone'],
                        created_at=row.get('created_at')
                    )
    except Exception as e:
        print(f"[AUTH ERROR] Failed to load user {user_id}: {e}")
    return None


def login_required(f):
    """Decorator ensuring that only authenticated users can access the endpoint."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator ensuring that only users with ADMIN role can access the endpoint."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Administrator login required.", "warning")
            return redirect(url_for('auth.login', next=request.url))
        
        user_role = session.get('user_role')
        if user_role != 'ADMIN':
            flash("Access denied. Administrator privileges required.", "danger")
            abort(403)
        return f(*args, **kwargs)
    return decorated_function
