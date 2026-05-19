from flask import url_for, current_app, render_template
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer
from utils.extensions import db, mail
from models import User

class AuthService:
    @staticmethod
    def generate_token(email):
        serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        return serializer.dumps(email, salt=current_app.config.get("SECURITY_PASSWORD_SALT"))

    @staticmethod
    def register_user(username, email, password):
        new_user = User(
            username=username.strip(),
            email=email.lower().strip(),
            is_confirmed=False
        )
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.flush() 

        token = AuthService.generate_token(new_user.email)
        confirm_url = url_for('auth.confirm_email', token=token, _external=True)
        
        msg = Message(
            "Confirm Your Email - Diploma Project",
            sender=current_app.config.get('MAIL_DEFAULT_SENDER'),
            recipients=[new_user.email]
        )
        msg.html = render_template('confirm_email.html', confirm_url=confirm_url)
        
        mail.send(msg)
        db.session.commit()
        return new_user