from flask import Blueprint, flash, render_template, request, redirect, url_for, current_app
from loguru import logger
from services.auth_service import AuthService
from utils.decorators import confirmed_required
from utils.extensions import db, mail, limiter
from utils.forms import LoginForm, RegistrationForm
from models import User
from flask_login import login_required, login_required, login_user, logout_user
from flask_mail import Message, Mail
from itsdangerous import URLSafeTimedSerializer



auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
mail = Mail() 


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    form = LoginForm()
    
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data.strip()).first()
        
        if user and user.check_password(form.password.data):
            if not user.is_confirmed:
                error_msg = "Please confirm your email before logging in."
                if request.headers.get('HX-Request'):
                    return f'<div class="alert alert-warning">{error_msg}</div>'
                
                flash(error_msg, "warning")
                return render_template('login.html', form=form)

            login_user(user)
            if request.headers.get('HX-Request'):
                return "", {"HX-Redirect": url_for('budget.budget_dashboard')}
            return redirect(url_for('budget.budget_dashboard'))
        
        error_msg = "Invalid username or password"
        if request.headers.get('HX-Request'):
            return f'<div class="alert alert-danger">{error_msg}</div>'
        
        flash(error_msg, "danger")
            
    return render_template('login.html', form=form)

@auth_bp.route('/logout', methods=['POST'])
@login_required
@confirmed_required
def logout():
    logout_user() 
    
    if request.headers.get('HX-Request'):
        return "", {"HX-Redirect": url_for('auth.login')}
    return redirect(url_for('auth.login'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    
    if form.validate_on_submit():
        try:
            AuthService.register_user(
                form.username.data, 
                form.email.data, 
                form.password.data
            )
            
            if request.headers.get('HX-Request'):
                return "", {"HX-Redirect": url_for('auth.verify_info')}
            return redirect(url_for('auth.verify_info'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Registration Error: {str(e)}")
            error = "Registration failed. Please try again."
            return render_template('register.html', form=form, error=error)

    error = next(iter(form.errors.values()))[0] if form.errors else None
    return render_template('register.html', form=form, error=error)

@auth_bp.route('/confirm/<token>')
def confirm_email(token):
    try:
        serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        email = serializer.loads(token, salt=current_app.config.get("SECURITY_PASSWORD_SALT"), max_age=3600)
    except Exception:
        flash("The confirmation link is invalid or has expired.", "danger")
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(email=email).first_or_404()
    
    if user.is_confirmed:
        flash("Account already confirmed. Please log in.", "info")
    else:
        user.is_confirmed = True
        db.session.commit()
        flash("Your account has been confirmed! You can now log in.", "success")
    
    return redirect(url_for('auth.login'))

@auth_bp.route('/verify-info')
def verify_info():
    return render_template('verify_info.html', message="Check your Mailtrap inbox to confirm your email!")