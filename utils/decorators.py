from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user

def confirmed_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_confirmed:
            flash("Please confirm your email to access this feature.", "warning")
            return redirect(url_for('auth.verify_info'))
        return f(*args, **kwargs)
    return decorated_function