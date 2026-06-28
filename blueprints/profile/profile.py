from flask import Blueprint, render_template, session, url_for
from models import Budget, User, DailyPlan
from utils.extensions import db
from utils.decorators import confirmed_required
from utils.forms import UpdateEmailForm
from flask_login import login_required, current_user
from loguru import logger


profile_bp = Blueprint('profile', __name__, template_folder='templates', url_prefix='/profile')


@profile_bp.route('/')
@login_required
@confirmed_required
def profile_page():
    user = current_user
    user_budgets = Budget.query.filter_by(user_id=user.id).all()
    total_budgets_count = len(user_budgets)
    
    total_spent = sum(b.spent_amount for b in user_budgets)
    total_plans = DailyPlan.query.filter_by(user_id=user.id).count()
    

    form = UpdateEmailForm()
    return render_template('profile/profile.html', 
                           user=user, 
                           total_budgets=total_budgets_count, 
                           total_spent=total_spent,
                           total_plans=total_plans,
                           form=form)

@profile_bp.route('/update-email', methods=['POST'])
@login_required
@confirmed_required
def update_email():
    form = UpdateEmailForm()
    
    if form.validate_on_submit():
        current_user.email = form.email.data
        db.session.commit()
        return f'<div class="alert alert-success">Email updated to {current_user.email}</div>'
    
    return '<div class="alert alert-danger">Invalid email format.</div>'

@profile_bp.route('/delete-account', methods=['POST'])
@login_required
@confirmed_required
def delete_account():
    try:
        user_id = current_user.id
        user_to_delete = db.session.get(User, user_id)
        
        if user_to_delete:
            db.session.delete(user_to_delete)
            db.session.commit()
            
            session.clear() 
            logger.info(f"User {user_id} successfully deleted.")
            return "", {"HX-Redirect": url_for('auth.login')}
        
        return "User not found", 404
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Account deletion failed for {current_user.id}: {e}")
        return "Failed to delete account", 500